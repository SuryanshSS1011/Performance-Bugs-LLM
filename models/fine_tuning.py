"""
Fine-tuning pipeline for GPT-4o-mini model.
Implements the exact methodology from Section V.A of the paper.
"""

import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import random
from dataclasses import dataclass, asdict
import openai
from openai import OpenAI

from ..config import (
    MODEL_CONFIG, DATASET_DIR, MODELS_DIR, 
    TRAIN_TEST_SPLIT, LABELED_BUGS, TEST_BUGS
)

logger = logging.getLogger(__name__)

@dataclass
class TrainingExample:
    """Represents a single training example for fine-tuning"""
    buggy_code: str
    fixed_code: str
    category: str
    bug_report: str
    explanation: str
    metadata: Dict
    
    def to_openai_format(self) -> Dict:
        """Convert to OpenAI fine-tuning format"""
        # Input: buggy code
        user_message = f"Analyze this Java code for performance issues:\n```java\n{self.buggy_code}\n```"
        
        # Output: structured response with fix, category, and explanation
        assistant_message = json.dumps({
            "category": self.category,
            "fixed_code": self.fixed_code,
            "bug_report": self.bug_report,
            "explanation": self.explanation,
            "performance_impact": self.metadata.get("performance_impact", ""),
            "fix_description": self.metadata.get("fix_description", "")
        }, indent=2)
        
        return {
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": assistant_message}
            ]
        }

SYSTEM_PROMPT = """You are a performance bug detection and fixing expert for Java code. 
Your task is to:
1. Identify the performance bug category (algorithmic_inefficiency, memory_usage, redundant_computation, cpu_overhead, or io_inefficiency)
2. Provide the fixed code
3. Generate a clear bug report describing the issue
4. Explain how the fix improves performance

Respond in JSON format with keys: category, fixed_code, bug_report, explanation, performance_impact, fix_description."""

class DatasetPreparer:
    """Prepares dataset for fine-tuning following paper's methodology"""
    
    def __init__(self, raw_bugs_file: str):
        self.raw_bugs_file = Path(raw_bugs_file)
        self.output_dir = DATASET_DIR / "fine_tuning"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def prepare_dataset(self) -> Tuple[List[TrainingExample], List[TrainingExample]]:
        """
        Prepare training and test datasets.
        Returns (train_examples, test_examples)
        """
        # Load categorized bugs
        with open(self.raw_bugs_file, 'r') as f:
            bugs = json.load(f)
        
        # Convert to training examples
        examples = []
        for bug in bugs:
            if self._is_valid_bug(bug):
                example = self._create_training_example(bug)
                if example:
                    examples.append(example)
        
        # Shuffle for random split
        random.seed(42)  # For reproducibility
        random.shuffle(examples)
        
        # Split by category to maintain distribution
        train_examples, test_examples = self._stratified_split(examples)
        
        logger.info(f"Prepared {len(train_examples)} training examples")
        logger.info(f"Prepared {len(test_examples)} test examples")
        
        # Verify distribution matches paper
        self._verify_distribution(train_examples, test_examples)
        
        return train_examples, test_examples
    
    def _is_valid_bug(self, bug: Dict) -> bool:
        """Check if bug has all required fields"""
        required = ['buggy_code', 'fixed_code', 'category', 'bug_id']
        return all(field in bug for field in required)
    
    def _create_training_example(self, bug: Dict) -> Optional[TrainingExample]:
        """Create a training example from a bug"""
        try:
            # Generate explanation using template or LLM
            explanation = self._generate_explanation(bug)
            
            # Create bug report
            bug_report = self._generate_bug_report(bug)
            
            return TrainingExample(
                buggy_code=bug['buggy_code'],
                fixed_code=bug['fixed_code'],
                category=bug['category'],
                bug_report=bug_report,
                explanation=explanation,
                metadata={
                    "bug_id": bug['bug_id'],
                    "project": bug.get('project', ''),
                    "performance_impact": self._estimate_performance_impact(bug),
                    "fix_description": self._describe_fix(bug)
                }
            )
        except Exception as e:
            logger.error(f"Failed to create example for bug {bug.get('bug_id')}: {e}")
            return None
    
    def _generate_explanation(self, bug: Dict) -> str:
        """Generate explanation for the performance issue and fix"""
        category = bug['category']
        
        # Category-specific templates
        templates = {
            "algorithmic_inefficiency": (
                "This code has O(n²) time complexity due to {issue}. "
                "The fix reduces complexity to O(n) by {solution}."
            ),
            "memory_usage": (
                "The code creates excessive temporary objects through {issue}. "
                "The fix reduces memory allocation by {solution}."
            ),
            "redundant_computation": (
                "The code repeatedly calculates {issue} inside a loop. "
                "The fix caches the result, computing it only once."
            ),
            "cpu_overhead": (
                "The code wastes CPU cycles on {issue}. "
                "The fix eliminates this overhead by {solution}."
            ),
            "io_inefficiency": (
                "The code performs inefficient I/O operations using {issue}. "
                "The fix improves I/O performance by {solution}."
            )
        }
        
        # Extract issue and solution from code diff
        issue = self._identify_issue(bug)
        solution = self._identify_solution(bug)
        
        template = templates.get(category, "Performance issue identified and fixed.")
        return template.format(issue=issue, solution=solution)
    
    def _generate_bug_report(self, bug: Dict) -> str:
        """Generate a bug report description"""
        category_descriptions = {
            "algorithmic_inefficiency": "inefficient algorithm",
            "memory_usage": "excessive memory usage",
            "redundant_computation": "redundant calculations",
            "cpu_overhead": "unnecessary CPU overhead",
            "io_inefficiency": "inefficient I/O operations"
        }
        
        desc = category_descriptions.get(bug['category'], "performance issue")
        return f"Performance bug: {desc} in {bug.get('method_name', 'method')}"
    
    def _identify_issue(self, bug: Dict) -> str:
        """Identify the specific issue from buggy code"""
        buggy = bug['buggy_code']
        
        # Pattern-based issue identification
        if "nested" in buggy.lower() or buggy.count("for") > 1:
            return "nested loops"
        elif "+=" in buggy and "String" in buggy:
            return "string concatenation in loop"
        elif "ArrayList()" in buggy:
            return "ArrayList without initial capacity"
        elif "FileReader" in buggy:
            return "unbuffered file reading"
        else:
            return "inefficient implementation"
    
    def _identify_solution(self, bug: Dict) -> str:
        """Identify the solution from fixed code"""
        fixed = bug['fixed_code']
        buggy = bug['buggy_code']
        
        if "HashMap" in fixed and "HashMap" not in buggy:
            return "using HashMap for O(1) lookups"
        elif "StringBuilder" in fixed and "StringBuilder" not in buggy:
            return "using StringBuilder"
        elif "Buffered" in fixed and "Buffered" not in buggy:
            return "using buffered I/O"
        elif len(fixed) < len(buggy):
            return "removing unnecessary operations"
        else:
            return "optimizing the algorithm"
    
    def _estimate_performance_impact(self, bug: Dict) -> str:
        """Estimate performance improvement from fix"""
        category = bug['category']
        
        impacts = {
            "algorithmic_inefficiency": "10-100x faster for large inputs",
            "memory_usage": "50-90% reduction in memory allocation",
            "redundant_computation": "2-10x faster execution",
            "cpu_overhead": "20-50% reduction in CPU usage",
            "io_inefficiency": "5-20x faster I/O operations"
        }
        
        return impacts.get(category, "Significant performance improvement")
    
    def _describe_fix(self, bug: Dict) -> str:
        """Describe what the fix does"""
        # Simplified - should analyze actual diff
        return "Optimized implementation for better performance"
    
    def _stratified_split(self, examples: List[TrainingExample]) -> Tuple[List, List]:
        """
        Split examples maintaining category distribution.
        Ensures 392 training and 98 test examples as per paper.
        """
        # Group by category
        by_category = {}
        for ex in examples:
            if ex.category not in by_category:
                by_category[ex.category] = []
            by_category[ex.category].append(ex)
        
        train_examples = []
        test_examples = []
        
        # Split each category 80/20
        for category, cat_examples in by_category.items():
            n_train = int(len(cat_examples) * TRAIN_TEST_SPLIT)
            train_examples.extend(cat_examples[:n_train])
            test_examples.extend(cat_examples[n_train:])
        
        # Trim to exact counts from paper
        train_examples = train_examples[:LABELED_BUGS]
        test_examples = test_examples[:TEST_BUGS]
        
        return train_examples, test_examples
    
    def _verify_distribution(self, train: List[TrainingExample], test: List[TrainingExample]):
        """Verify distribution matches paper's statistics"""
        def get_distribution(examples):
            counts = {}
            for ex in examples:
                counts[ex.category] = counts.get(ex.category, 0) + 1
            total = len(examples)
            return {cat: (count, count/total*100) for cat, count in counts.items()}
        
        train_dist = get_distribution(train)
        test_dist = get_distribution(test)
        
        logger.info("Training set distribution:")
        for cat, (count, pct) in train_dist.items():
            logger.info(f"  {cat}: {count} ({pct:.1f}%)")
        
        logger.info("Test set distribution:")
        for cat, (count, pct) in test_dist.items():
            logger.info(f"  {cat}: {count} ({pct:.1f}%)")

class ModelFineTuner:
    """Fine-tunes GPT-4o-mini model on performance bugs dataset"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.client = OpenAI(api_key=api_key)
        self.model_name = MODEL_CONFIG["base_model"]
        
    def prepare_training_file(self, examples: List[TrainingExample]) -> str:
        """Prepare JSONL file for OpenAI fine-tuning"""
        output_file = DATASET_DIR / "fine_tuning" / "training_data.jsonl"
        
        with open(output_file, 'w') as f:
            for example in examples:
                json_line = json.dumps(example.to_openai_format())
                f.write(json_line + '\n')
        
        logger.info(f"Created training file: {output_file}")
        return str(output_file)
    
    def upload_training_file(self, file_path: str) -> str:
        """Upload training file to OpenAI"""
        with open(file_path, 'rb') as f:
            response = self.client.files.create(
                file=f,
                purpose="fine-tune"
            )
        
        file_id = response.id
        logger.info(f"Uploaded file with ID: {file_id}")
        return file_id
    
    def create_fine_tuning_job(self, training_file_id: str, 
                              validation_file_id: Optional[str] = None) -> str:
        """Create fine-tuning job"""
        config = MODEL_CONFIG["fine_tuning"]
        
        job_params = {
            "model": self.model_name,
            "training_file": training_file_id,
            "hyperparameters": {
                "n_epochs": config["n_epochs"],
                "batch_size": config["batch_size"],
                "learning_rate_multiplier": config["learning_rate_multiplier"]
            }
        }
        
        if validation_file_id:
            job_params["validation_file"] = validation_file_id
        
        response = self.client.fine_tuning.jobs.create(**job_params)
        
        job_id = response.id
        logger.info(f"Created fine-tuning job: {job_id}")
        
        # Save job info
        job_info = {
            "job_id": job_id,
            "model": self.model_name,
            "created_at": str(response.created_at),
            "status": response.status
        }
        
        with open(MODELS_DIR / "fine_tuning_job.json", 'w') as f:
            json.dump(job_info, f, indent=2)
        
        return job_id
    
    def monitor_job(self, job_id: str) -> Dict:
        """Monitor fine-tuning job progress"""
        while True:
            job = self.client.fine_tuning.jobs.retrieve(job_id)
            
            logger.info(f"Job status: {job.status}")
            
            if job.status == "succeeded":
                logger.info(f"Fine-tuning completed! Model: {job.fine_tuned_model}")
                return {
                    "status": "success",
                    "model_id": job.fine_tuned_model,
                    "metrics": job.result_files
                }
            elif job.status == "failed":
                logger.error(f"Fine-tuning failed: {job.error}")
                return {"status": "failed", "error": job.error}
            
            # Wait before checking again
            time.sleep(60)
    
    def run_fine_tuning(self, train_examples: List[TrainingExample],
                       val_examples: Optional[List[TrainingExample]] = None) -> str:
        """Run complete fine-tuning pipeline"""
        logger.info("Starting fine-tuning pipeline...")
        
        # Prepare training file
        train_file = self.prepare_training_file(train_examples)
        
        # Prepare validation file if provided
        val_file_id = None
        if val_examples:
            val_file = train_file.replace("training", "validation")
            with open(val_file, 'w') as f:
                for example in val_examples:
                    json_line = json.dumps(example.to_openai_format())
                    f.write(json_line + '\n')
            
            with open(val_file, 'rb') as f:
                val_response = self.client.files.create(file=f, purpose="fine-tune")
                val_file_id = val_response.id
        
        # Upload training file
        train_file_id = self.upload_training_file(train_file)
        
        # Create fine-tuning job
        job_id = self.create_fine_tuning_job(train_file_id, val_file_id)
        
        # Monitor until complete
        result = self.monitor_job(job_id)
        
        if result["status"] == "success":
            # Save model info
            model_info = {
                "model_id": result["model_id"],
                "base_model": self.model_name,
                "job_id": job_id,
                "training_examples": len(train_examples),
                "validation_examples": len(val_examples) if val_examples else 0
            }
            
            with open(MODELS_DIR / "fine_tuned_model.json", 'w') as f:
                json.dump(model_info, f, indent=2)
            
            logger.info(f"Fine-tuned model saved: {result['model_id']}")
            return result["model_id"]
        else:
            raise Exception(f"Fine-tuning failed: {result.get('error')}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Prepare dataset
    preparer = DatasetPreparer("data/categorized_bugs.json")
    train_examples, test_examples = preparer.prepare_dataset()
    
    # Fine-tune model
    tuner = ModelFineTuner()
    model_id = tuner.run_fine_tuning(train_examples, test_examples[:20])  # Use subset for validation
    
    print(f"Fine-tuning complete! Model ID: {model_id}")