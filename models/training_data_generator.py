"""
Training data generator for GPT-4o-mini fine-tuning.
Implements the data preparation methodology from Section V.A of the paper.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import random

logger = logging.getLogger(__name__)

@dataclass
class TrainingExample:
    """Training example for fine-tuning"""
    messages: List[Dict[str, str]]
    category: str
    bug_id: str
    performance_score: float

class PerformanceTrainingDataGenerator:
    """
    Generates training data in OpenAI fine-tuning format.
    Implements the paper's methodology for preparing training examples.
    """
    
    def __init__(self):
        # System prompt that teaches the model about performance bugs
        self.system_prompt = """You are an expert Java performance engineer. Your task is to:

1. **Detect** performance bugs in Java code
2. **Fix** the performance issue with optimal code
3. **Explain** the issue and fix in clear, technical language

When analyzing code, focus on these performance bug categories:
- **Algorithmic Inefficiency**: Inefficient algorithms/data structures (O(n²) vs O(n log n))
- **Memory Usage**: Excessive allocations, String concatenation, oversized collections
- **Redundant Computation**: Repeated calculations, unnecessary work in loops
- **CPU Overhead**: Boxing/unboxing, oversynchronization, thread overhead  
- **I/O Inefficiency**: Unbuffered I/O, resource leaks, inefficient file operations

For each bug, provide:
1. **Root Cause**: What specifically causes the performance issue
2. **Fix**: Optimized code that resolves the issue
3. **Impact**: How the fix improves performance (time/space complexity, resource usage)
4. **Category**: Which performance bug type this represents

Always write clear, actionable explanations that help developers understand both the problem and the solution."""
        
        # Templates for different bug categories from the paper
        self.explanation_templates = {
            'algorithmic_inefficiency': {
                'root_cause': "The code uses an inefficient algorithm with {complexity} complexity",
                'fix_approach': "Replace with {optimized_approach} to achieve {new_complexity} complexity",
                'impact': "Reduces time complexity from {old_complexity} to {new_complexity}"
            },
            'memory_usage': {
                'root_cause': "The code creates excessive memory allocations through {memory_issue}",
                'fix_approach': "Use {memory_solution} to reduce object creation and garbage collection",
                'impact': "Reduces memory allocations and GC pressure by {improvement_factor}"
            },
            'redundant_computation': {
                'root_cause': "The code performs {redundant_operation} multiple times unnecessarily",
                'fix_approach': "Cache the result or eliminate redundant calculations",
                'impact': "Eliminates {redundancy_count} redundant operations per execution"
            },
            'cpu_overhead': {
                'root_cause': "The code causes CPU overhead through {cpu_issue}",
                'fix_approach': "Remove unnecessary {overhead_source} to reduce CPU usage",
                'impact': "Reduces CPU overhead by eliminating {specific_overhead}"
            },
            'io_inefficiency': {
                'root_cause': "The code performs inefficient I/O operations through {io_issue}",
                'fix_approach': "Use {io_solution} for better I/O performance",
                'impact': "Reduces I/O operations and improves throughput by {io_improvement}"
            }
        }
    
    def prepare_training_data(self, bugs_dataset: List[Dict], 
                            train_split: float = 0.8) -> Tuple[List[TrainingExample], List[TrainingExample]]:
        """
        Prepare training data in OpenAI fine-tuning format.
        Implements the 80:20 train/test split from the paper.
        """
        
        # Shuffle bugs for random split
        shuffled_bugs = bugs_dataset.copy()
        random.seed(42)  # For reproducibility
        random.shuffle(shuffled_bugs)
        
        # Calculate split point
        split_point = int(len(shuffled_bugs) * train_split)
        train_bugs = shuffled_bugs[:split_point]
        test_bugs = shuffled_bugs[split_point:]
        
        logger.info(f"Creating training data: {len(train_bugs)} train, {len(test_bugs)} test")
        
        # Generate training examples
        train_examples = []
        test_examples = []
        
        for bug in train_bugs:
            example = self._create_training_example(bug)
            if example:
                train_examples.append(example)
        
        for bug in test_bugs:
            example = self._create_training_example(bug)
            if example:
                test_examples.append(example)
        
        logger.info(f"Generated {len(train_examples)} training examples, {len(test_examples)} test examples")
        
        return train_examples, test_examples
    
    def _create_training_example(self, bug: Dict) -> Optional[TrainingExample]:
        """Create a single training example from a bug"""
        
        # Extract necessary information
        identifier = bug.get('identifier', '')
        category = bug.get('category', '')
        patch_content = bug.get('patch_content', '')
        
        if not patch_content or not category:
            return None
        
        # Extract buggy and fixed code from patch
        buggy_code, fixed_code = self._extract_code_from_patch(patch_content)
        
        if not buggy_code or not fixed_code:
            return None
        
        # Generate explanation based on category and patterns
        explanation = self._generate_performance_explanation(bug, buggy_code, fixed_code)
        
        # Create the training messages in OpenAI format
        messages = [
            {
                "role": "system",
                "content": self.system_prompt
            },
            {
                "role": "user", 
                "content": f"""Analyze this Java code for performance issues:

```java
{buggy_code}
```

Please:
1. Identify any performance bugs
2. Provide the fixed code
3. Explain the issue and how your fix improves performance
4. Categorize the bug type"""
            },
            {
                "role": "assistant",
                "content": f"""**Performance Bug Detected: {category.replace('_', ' ').title()}**

**Root Cause:** {explanation['root_cause']}

**Fixed Code:**
```java
{fixed_code}
```

**Explanation:** {explanation['detailed_explanation']}

**Performance Impact:** {explanation['impact']}

**Category:** {category}"""
            }
        ]
        
        return TrainingExample(
            messages=messages,
            category=category,
            bug_id=identifier,
            performance_score=bug.get('performance_score', 0.0)
        )
    
    def _extract_code_from_patch(self, patch_content: str) -> Tuple[str, str]:
        """Extract buggy and fixed code from unified diff patch"""
        
        # Find the main code changes (ignore file headers)
        lines = patch_content.split('\n')
        
        buggy_lines = []
        fixed_lines = []
        context_lines = []
        
        in_hunk = False
        for line in lines:
            if line.startswith('@@'):
                in_hunk = True
                continue
            elif line.startswith('diff') or line.startswith('index'):
                continue
            elif not in_hunk:
                continue
            
            if line.startswith('-') and not line.startswith('---'):
                buggy_lines.append(line[1:])  # Remove '-' prefix
            elif line.startswith('+') and not line.startswith('+++'):
                fixed_lines.append(line[1:])  # Remove '+' prefix
            elif line.startswith(' '):
                context_lines.append(line[1:])  # Context line
        
        # Combine context with changes to create complete methods
        buggy_code = self._reconstruct_method(context_lines, buggy_lines, fixed_lines, 'buggy')
        fixed_code = self._reconstruct_method(context_lines, buggy_lines, fixed_lines, 'fixed')
        
        return buggy_code, fixed_code
    
    def _reconstruct_method(self, context: List[str], removed: List[str], 
                          added: List[str], version: str) -> str:
        """Reconstruct complete method code for training"""
        
        if version == 'buggy':
            # Use context + removed lines
            method_lines = context + removed
        else:
            # Use context + added lines  
            method_lines = context + added
        
        # Clean up and format
        method_code = '\n'.join(line for line in method_lines if line.strip())
        
        # If no clear method boundary, take first 20 lines as method
        lines = method_code.split('\n')
        if len(lines) > 20:
            method_code = '\n'.join(lines[:20])
        
        return method_code
    
    def _generate_performance_explanation(self, bug: Dict, buggy_code: str, fixed_code: str) -> Dict:
        """Generate performance explanation based on bug category and patterns"""
        
        category = bug.get('category', '')
        keywords = bug.get('performance_keywords', [])
        report_id = bug.get('report_id', '')
        
        # Get template for this category
        template = self.explanation_templates.get(category, self.explanation_templates['algorithmic_inefficiency'])
        
        # Generate specific explanations based on detected patterns
        explanations = {
            'algorithmic_inefficiency': self._explain_algorithmic_issue,
            'memory_usage': self._explain_memory_issue,
            'redundant_computation': self._explain_redundancy_issue,
            'cpu_overhead': self._explain_cpu_issue,
            'io_inefficiency': self._explain_io_issue
        }
        
        explanation_func = explanations.get(category, explanations['algorithmic_inefficiency'])
        return explanation_func(bug, buggy_code, fixed_code, keywords)
    
    def _explain_algorithmic_issue(self, bug: Dict, buggy: str, fixed: str, keywords: List[str]) -> Dict:
        """Generate explanation for algorithmic inefficiency"""
        
        # Detect specific algorithmic issues
        if 'for' in buggy and buggy.count('for') > fixed.count('for'):
            root_cause = "The code uses nested loops creating O(n²) complexity where a more efficient approach is possible"
            impact = "Reduces time complexity from O(n²) to O(n) or O(log n)"
        elif 'arraylist' in buggy.lower() and 'hashmap' in fixed.lower():
            root_cause = "The code uses ArrayList for lookups, causing O(n) search time instead of O(1)"
            impact = "Improves lookup performance from O(n) to O(1) using HashMap"
        else:
            root_cause = "The code uses an inefficient algorithm that doesn't scale well with input size"
            impact = "Optimizes the algorithm to reduce computational complexity"
        
        return {
            'root_cause': root_cause,
            'detailed_explanation': f"The original implementation has algorithmic inefficiencies that become apparent with larger datasets. The fix addresses this by optimizing the core algorithm.",
            'impact': impact
        }
    
    def _explain_memory_issue(self, bug: Dict, buggy: str, fixed: str, keywords: List[str]) -> Dict:
        """Generate explanation for memory usage issues"""
        
        if 'stringbuilder' in fixed.lower() and '+=' in buggy:
            root_cause = "String concatenation in a loop creates multiple temporary String objects"
            impact = "Reduces memory allocations by 80% and eliminates GC pressure"
        elif 'arraylist(' in buggy.lower() and 'arraylist(' in fixed.lower():
            root_cause = "Collection created without initial capacity, causing multiple array reallocations"
            impact = "Eliminates array reallocations by pre-sizing the collection"
        else:
            root_cause = "The code creates excessive memory allocations that could be optimized"
            impact = "Reduces memory usage and garbage collection overhead"
        
        return {
            'root_cause': root_cause,
            'detailed_explanation': f"Memory inefficiencies arise from unnecessary object creation. The fix optimizes memory usage patterns.",
            'impact': impact
        }
    
    def _explain_redundancy_issue(self, bug: Dict, buggy: str, fixed: str, keywords: List[str]) -> Dict:
        """Generate explanation for redundant computation"""
        
        if 'math.' in buggy.lower() and buggy.count('Math.') > fixed.count('Math.'):
            root_cause = "The same expensive mathematical calculation is performed multiple times"
            impact = "Eliminates redundant calculations by caching the result"
        elif 'break;' in buggy and 'break;' not in fixed:
            root_cause = "Missing break statements cause unnecessary fall-through execution"
            impact = "Prevents redundant execution paths by adding proper control flow"
        else:
            root_cause = "The code performs redundant operations that can be cached or eliminated"
            impact = "Eliminates unnecessary computation and improves efficiency"
        
        return {
            'root_cause': root_cause,
            'detailed_explanation': f"Redundant computations waste CPU cycles. The fix eliminates unnecessary work.",
            'impact': impact
        }
    
    def _explain_cpu_issue(self, bug: Dict, buggy: str, fixed: str, keywords: List[str]) -> Dict:
        """Generate explanation for CPU overhead"""
        
        if 'synchronized' in buggy.lower():
            root_cause = "Excessive synchronization creates CPU contention and lock overhead"
            impact = "Reduces synchronization overhead and improves thread performance"
        elif 'integer' in buggy.lower() and 'int' in fixed.lower():
            root_cause = "Boxing/unboxing of primitive types creates unnecessary CPU overhead"
            impact = "Eliminates boxing overhead by using primitive types directly"
        else:
            root_cause = "The code creates unnecessary CPU overhead through inefficient operations"
            impact = "Optimizes CPU usage by removing unnecessary overhead"
        
        return {
            'root_cause': root_cause,
            'detailed_explanation': f"CPU overhead reduces overall system performance. The fix optimizes processor usage.",
            'impact': impact
        }
    
    def _explain_io_issue(self, bug: Dict, buggy: str, fixed: str, keywords: List[str]) -> Dict:
        """Generate explanation for I/O inefficiency"""
        
        if 'bufferedreader' in fixed.lower() or 'bufferedwriter' in fixed.lower():
            root_cause = "Unbuffered I/O operations cause excessive system calls"
            impact = "Reduces system calls by 90% through proper buffering"
        elif 'close()' in fixed and 'close()' not in buggy:
            root_cause = "Resources are not properly closed, causing resource leaks"
            impact = "Prevents resource leaks and improves I/O performance"
        else:
            root_cause = "I/O operations are not optimized for performance"
            impact = "Improves I/O throughput and reduces system overhead"
        
        return {
            'root_cause': root_cause,
            'detailed_explanation': f"I/O inefficiencies create bottlenecks. The fix optimizes I/O operations.",
            'impact': impact
        }
    
    def generate_training_files(self, dataset_file: str, output_dir: str):
        """
        Generate training files for OpenAI fine-tuning.
        Creates separate files for each category as mentioned in the paper.
        """
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Load dataset
        with open(dataset_file, 'r') as f:
            data = json.load(f)
        
        bugs = data['bugs']
        logger.info(f"Generating training data from {len(bugs)} bugs")
        
        # Split into training and test
        train_examples, test_examples = self.prepare_training_data(bugs)
        
        # Group by category for separate training files
        train_by_category = {}
        test_by_category = {}
        
        for example in train_examples:
            category = example.category
            if category not in train_by_category:
                train_by_category[category] = []
            train_by_category[category].append(example)
        
        for example in test_examples:
            category = example.category
            if category not in test_by_category:
                test_by_category[category] = []
            test_by_category[category].append(example)
        
        # Save training files by category (as mentioned in paper Section V.A)
        for category, examples in train_by_category.items():
            train_file = output_path / f"train_{category}.jsonl"
            self._save_training_file(examples, train_file)
            logger.info(f"Saved {len(examples)} training examples for {category}")
        
        # Save combined training file
        all_train_examples = [ex for examples in train_by_category.values() for ex in examples]
        combined_train_file = output_path / "train_combined.jsonl"
        self._save_training_file(all_train_examples, combined_train_file)
        
        # Save test files
        all_test_examples = [ex for examples in test_by_category.values() for ex in examples]
        test_file = output_path / "test_combined.jsonl"
        self._save_training_file(all_test_examples, test_file)
        
        # Generate summary
        summary = {
            'total_bugs': len(bugs),
            'train_examples': len(all_train_examples),
            'test_examples': len(all_test_examples),
            'train_split': len(all_train_examples) / (len(all_train_examples) + len(all_test_examples)),
            'categories': {
                category: {
                    'train': len(train_by_category.get(category, [])),
                    'test': len(test_by_category.get(category, []))
                }
                for category in ['algorithmic_inefficiency', 'memory_usage', 'redundant_computation', 
                               'cpu_overhead', 'io_inefficiency']
            }
        }
        
        with open(output_path / "training_summary.json", 'w') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"Training data generation complete. Summary saved to {output_path}")
        return summary
    
    def _save_training_file(self, examples: List[TrainingExample], file_path: Path):
        """Save training examples in JSONL format for OpenAI fine-tuning"""
        
        with open(file_path, 'w') as f:
            for example in examples:
                # OpenAI fine-tuning format
                training_record = {
                    "messages": example.messages
                }
                f.write(json.dumps(training_record) + '\n')

class OpenAIFineTuner:
    """
    Handles GPT-4o-mini fine-tuning process.
    Implements the fine-tuning methodology from Section V.A.
    """
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.model_name = "gpt-4o-mini-2024-07-18"  # Base model from paper
        
    def create_fine_tuning_job(self, training_file: str, validation_file: str = None) -> Dict:
        """
        Create fine-tuning job using OpenAI API.
        Returns job information for monitoring.
        """
        
        try:
            import openai
            openai.api_key = self.api_key
            
            # Upload training file
            with open(training_file, 'rb') as f:
                training_file_obj = openai.File.create(
                    file=f,
                    purpose='fine-tune'
                )
            
            # Upload validation file if provided
            validation_file_obj = None
            if validation_file:
                with open(validation_file, 'rb') as f:
                    validation_file_obj = openai.File.create(
                        file=f,
                        purpose='fine-tune'
                    )
            
            # Create fine-tuning job
            job_params = {
                "training_file": training_file_obj.id,
                "model": self.model_name,
                "suffix": "performance-bugs-v1",
                "hyperparameters": {
                    "n_epochs": 3,  # As mentioned in paper
                    "batch_size": 8,
                    "learning_rate_multiplier": 1.0
                }
            }
            
            if validation_file_obj:
                job_params["validation_file"] = validation_file_obj.id
            
            fine_tuning_job = openai.FineTuningJob.create(**job_params)
            
            logger.info(f"Fine-tuning job created: {fine_tuning_job.id}")
            
            return {
                "job_id": fine_tuning_job.id,
                "status": fine_tuning_job.status,
                "model": fine_tuning_job.model,
                "training_file": training_file_obj.id,
                "validation_file": validation_file_obj.id if validation_file_obj else None
            }
            
        except ImportError:
            logger.warning("OpenAI library not available. Please install: pip install openai")
            return {"error": "OpenAI library not available"}
        except Exception as e:
            logger.error(f"Fine-tuning job creation failed: {e}")
            return {"error": str(e)}
    
    def monitor_job(self, job_id: str) -> Dict:
        """Monitor fine-tuning job progress"""
        
        try:
            import openai
            openai.api_key = self.api_key
            
            job = openai.FineTuningJob.retrieve(job_id)
            
            return {
                "id": job.id,
                "status": job.status,
                "trained_tokens": job.trained_tokens,
                "fine_tuned_model": job.fine_tuned_model,
                "created_at": job.created_at,
                "finished_at": job.finished_at
            }
            
        except Exception as e:
            logger.error(f"Failed to monitor job {job_id}: {e}")
            return {"error": str(e)}

def main():
    """Main function to generate training data"""
    
    # Generate training data
    generator = PerformanceTrainingDataGenerator()
    
    summary = generator.generate_training_files(
        'data/performance_bugs_490.json',
        'data/training'
    )
    
    print("Training Data Generation Summary:")
    print(f"  Total bugs processed: {summary['total_bugs']}")
    print(f"  Training examples: {summary['train_examples']}")
    print(f"  Test examples: {summary['test_examples']}")
    print(f"  Train/test split: {summary['train_split']:.1%}")
    
    print("\nExamples per category:")
    for category, counts in summary['categories'].items():
        total = counts['train'] + counts['test']
        print(f"  {category:25s}: {total:3d} ({counts['train']:3d} train, {counts['test']:2d} test)")
    
    print("\nTraining files created in data/training/")
    print("Ready for GPT-4o-mini fine-tuning")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()