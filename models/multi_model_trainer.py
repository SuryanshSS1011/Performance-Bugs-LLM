"""
Multi-model training pipeline supporting various LLMs.
Handles fine-tuning for OpenAI, Anthropic, and local models.
"""

import json
import time
import openai
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import logging
from abc import ABC, abstractmethod
import requests
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class TrainingExample:
    """Represents a single training example"""
    input_code: str
    category: str
    fixed_code: str
    explanation: str
    bug_id: str
    
    def to_openai_format(self) -> Dict:
        """Convert to OpenAI fine-tuning format"""
        return {
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert at detecting and fixing performance bugs in Java code. Analyze the code, identify the performance issue, suggest a fix, and explain the problem."
                },
                {
                    "role": "user",
                    "content": f"Analyze this Java code for performance issues:\n\n```java\n{self.input_code}\n```"
                },
                {
                    "role": "assistant",
                    "content": json.dumps({
                        "category": self.category,
                        "fixed_code": self.fixed_code,
                        "explanation": self.explanation,
                        "bug_type": self._get_bug_type_description()
                    })
                }
            ]
        }
    
    def to_anthropic_format(self) -> Dict:
        """Convert to Anthropic training format"""
        return {
            "prompt": f"Human: Analyze this Java code for performance issues and provide a fix:\n\n```java\n{self.input_code}\n```\n\nAssistant:",
            "completion": json.dumps({
                "category": self.category,
                "fixed_code": self.fixed_code,
                "explanation": self.explanation
            })
        }
    
    def _get_bug_type_description(self) -> str:
        """Get human-readable bug type description"""
        descriptions = {
            "algorithmic_inefficiency": "Inefficient algorithm or data structure",
            "memory_usage": "Excessive memory allocation",
            "cpu_overhead": "CPU cycle waste",
            "redundant_computation": "Redundant calculations",
            "io_inefficiency": "Unoptimized I/O operations"
        }
        return descriptions.get(self.category, "Performance issue")


class ModelTrainer(ABC):
    """Abstract base class for model trainers"""
    
    @abstractmethod
    def prepare_training_data(self, examples: List[TrainingExample]) -> Any:
        """Prepare training data in model-specific format"""
        pass
    
    @abstractmethod
    def train(self, training_data: Any, validation_data: Optional[Any] = None) -> str:
        """Train the model and return model ID"""
        pass
    
    @abstractmethod
    def predict(self, model_id: str, input_code: str) -> Dict:
        """Make prediction using trained model"""
        pass


class OpenAITrainer(ModelTrainer):
    """OpenAI model trainer (GPT-3.5, GPT-4, etc.)"""
    
    def __init__(self, api_key: str, model_name: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.model_name = model_name
        openai.api_key = api_key
        self.client = openai.OpenAI(api_key=api_key)
        
    def prepare_training_data(self, examples: List[TrainingExample]) -> Path:
        """Prepare training data in JSONL format for OpenAI"""
        output_file = Path("training_data_openai.jsonl")
        
        with open(output_file, 'w') as f:
            for example in examples:
                json_line = json.dumps(example.to_openai_format())
                f.write(json_line + '\n')
        
        logger.info(f"Prepared {len(examples)} training examples in {output_file}")
        return output_file
    
    def train(self, training_data: Path, validation_data: Optional[Path] = None) -> str:
        """Fine-tune OpenAI model"""
        try:
            # Upload training file
            with open(training_data, 'rb') as f:
                training_file = self.client.files.create(
                    file=f,
                    purpose='fine-tune'
                )
            
            logger.info(f"Uploaded training file: {training_file.id}")
            
            # Upload validation file if provided
            validation_file_id = None
            if validation_data:
                with open(validation_data, 'rb') as f:
                    validation_file = self.client.files.create(
                        file=f,
                        purpose='fine-tune'
                    )
                validation_file_id = validation_file.id
                logger.info(f"Uploaded validation file: {validation_file.id}")
            
            # Create fine-tuning job
            job_params = {
                "training_file": training_file.id,
                "model": self.model_name,
                "hyperparameters": {
                    "n_epochs": 3,
                    "batch_size": 4,
                    "learning_rate_multiplier": 0.5
                }
            }
            
            if validation_file_id:
                job_params["validation_file"] = validation_file_id
            
            job = self.client.fine_tuning.jobs.create(**job_params)
            
            logger.info(f"Created fine-tuning job: {job.id}")
            
            # Wait for job completion
            while True:
                job_status = self.client.fine_tuning.jobs.retrieve(job.id)
                status = job_status.status
                
                if status == 'succeeded':
                    model_id = job_status.fine_tuned_model
                    logger.info(f"Fine-tuning completed! Model ID: {model_id}")
                    return model_id
                elif status == 'failed':
                    raise Exception(f"Fine-tuning failed: {job_status.error}")
                else:
                    logger.info(f"Fine-tuning status: {status}")
                    time.sleep(30)
                    
        except Exception as e:
            logger.error(f"Error during OpenAI fine-tuning: {e}")
            raise
    
    def predict(self, model_id: str, input_code: str) -> Dict:
        """Make prediction using fine-tuned model"""
        try:
            response = self.client.chat.completions.create(
                model=model_id,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at detecting and fixing performance bugs in Java code."
                    },
                    {
                        "role": "user",
                        "content": f"Analyze this Java code for performance issues:\n\n```java\n{input_code}\n```"
                    }
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            # Parse response
            content = response.choices[0].message.content
            try:
                result = json.loads(content)
            except json.JSONDecodeError:
                # Fallback parsing
                result = {
                    "category": "unknown",
                    "explanation": content,
                    "fixed_code": input_code
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Error during prediction: {e}")
            return {
                "category": "error",
                "explanation": str(e),
                "fixed_code": input_code
            }


class AnthropicTrainer(ModelTrainer):
    """Anthropic Claude model trainer"""
    
    def __init__(self, api_key: str, model_name: str = "claude-3-haiku"):
        self.api_key = api_key
        self.model_name = model_name
        self.base_url = "https://api.anthropic.com/v1"
        
    def prepare_training_data(self, examples: List[TrainingExample]) -> Path:
        """Prepare training data for Anthropic"""
        output_file = Path("training_data_anthropic.jsonl")
        
        with open(output_file, 'w') as f:
            for example in examples:
                json_line = json.dumps(example.to_anthropic_format())
                f.write(json_line + '\n')
        
        logger.info(f"Prepared {len(examples)} training examples in {output_file}")
        return output_file
    
    def train(self, training_data: Path, validation_data: Optional[Path] = None) -> str:
        """Note: Anthropic doesn't support fine-tuning via API yet"""
        logger.warning("Anthropic fine-tuning not available via API. Using base model.")
        return self.model_name
    
    def predict(self, model_id: str, input_code: str) -> Dict:
        """Make prediction using Claude"""
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        data = {
            "model": model_id,
            "messages": [
                {
                    "role": "user",
                    "content": f"Analyze this Java code for performance issues and provide a fix:\n\n```java\n{input_code}\n```\n\nProvide response in JSON format with 'category', 'fixed_code', and 'explanation' fields."
                }
            ],
            "max_tokens": 2000,
            "temperature": 0.3
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/messages",
                headers=headers,
                json=data
            )
            response.raise_for_status()
            
            result = response.json()
            content = result['content'][0]['text']
            
            # Parse JSON from response
            try:
                parsed = json.loads(content)
                return parsed
            except json.JSONDecodeError:
                return {
                    "category": "unknown",
                    "explanation": content,
                    "fixed_code": input_code
                }
                
        except Exception as e:
            logger.error(f"Error with Claude prediction: {e}")
            return {
                "category": "error",
                "explanation": str(e),
                "fixed_code": input_code
            }


class LocalModelTrainer(ModelTrainer):
    """Trainer for local models (LLaMA, CodeLLaMA, etc.)"""
    
    def __init__(self, model_path: str, base_url: str = "http://localhost:8000"):
        self.model_path = model_path
        self.base_url = base_url
        
    def prepare_training_data(self, examples: List[TrainingExample]) -> Path:
        """Prepare training data for local model"""
        output_file = Path("training_data_local.jsonl")
        
        with open(output_file, 'w') as f:
            for example in examples:
                training_pair = {
                    "input": f"Analyze this Java code for performance issues:\n{example.input_code}",
                    "output": json.dumps({
                        "category": example.category,
                        "fixed_code": example.fixed_code,
                        "explanation": example.explanation
                    })
                }
                f.write(json.dumps(training_pair) + '\n')
        
        logger.info(f"Prepared {len(examples)} training examples in {output_file}")
        return output_file
    
    def train(self, training_data: Path, validation_data: Optional[Path] = None) -> str:
        """Train local model (requires local training infrastructure)"""
        logger.info("Local model training requires custom infrastructure")
        # Implement based on your local setup (e.g., using Hugging Face transformers)
        return self.model_path
    
    def predict(self, model_id: str, input_code: str) -> Dict:
        """Make prediction using local model"""
        try:
            response = requests.post(
                f"{self.base_url}/predict",
                json={
                    "model": model_id,
                    "prompt": f"Analyze this Java code for performance issues:\n{input_code}",
                    "temperature": 0.3,
                    "max_tokens": 2000
                }
            )
            response.raise_for_status()
            
            result = response.json()
            return json.loads(result.get('output', '{}'))
            
        except Exception as e:
            logger.error(f"Error with local model prediction: {e}")
            return {
                "category": "error",
                "explanation": str(e),
                "fixed_code": input_code
            }


class MultiModelPipeline:
    """Orchestrates training across multiple models"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.trainers = {}
        self._initialize_trainers()
        
    def _initialize_trainers(self):
        """Initialize trainers based on configuration"""
        if 'openai' in self.config.get('models', {}):
            api_key = self.config['models']['openai'].get('api_key')
            if api_key:
                self.trainers['openai'] = OpenAITrainer(api_key)
        
        if 'anthropic' in self.config.get('models', {}):
            api_key = self.config['models']['anthropic'].get('api_key')
            if api_key:
                self.trainers['anthropic'] = AnthropicTrainer(api_key)
        
        if 'local' in self.config.get('models', {}):
            model_path = self.config['models']['local'].get('model_path')
            if model_path:
                self.trainers['local'] = LocalModelTrainer(model_path)
    
    def load_training_data(self, data_path: Path) -> List[TrainingExample]:
        """Load and convert training data to TrainingExample objects"""
        with open(data_path, 'r') as f:
            data = json.load(f)
        
        examples = []
        for bug in data:
            # Extract relevant fields
            example = TrainingExample(
                input_code=bug.get('buggy_code', ''),
                category=bug.get('category', 'unknown'),
                fixed_code=bug.get('fixed_code', ''),
                explanation=bug.get('explanation', ''),
                bug_id=bug.get('identifier', '')
            )
            examples.append(example)
        
        return examples
    
    def train_all_models(
        self,
        training_data: List[TrainingExample],
        validation_data: Optional[List[TrainingExample]] = None
    ) -> Dict[str, str]:
        """Train all configured models"""
        trained_models = {}
        
        for name, trainer in self.trainers.items():
            logger.info(f"Training {name} model...")
            
            # Prepare data
            train_file = trainer.prepare_training_data(training_data)
            val_file = None
            if validation_data:
                val_file = trainer.prepare_training_data(validation_data)
            
            # Train
            try:
                model_id = trainer.train(train_file, val_file)
                trained_models[name] = model_id
                logger.info(f"Successfully trained {name}: {model_id}")
            except Exception as e:
                logger.error(f"Failed to train {name}: {e}")
        
        # Save model mapping
        model_file = Path("trained_models.json")
        with open(model_file, 'w') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "models": trained_models,
                "training_size": len(training_data),
                "validation_size": len(validation_data) if validation_data else 0
            }, f, indent=2)
        
        return trained_models
    
    def compare_models(
        self,
        test_data: List[TrainingExample],
        model_ids: Dict[str, str]
    ) -> Dict[str, Dict]:
        """Compare performance across models"""
        results = {}
        
        for name, model_id in model_ids.items():
            if name in self.trainers:
                trainer = self.trainers[name]
                correct = 0
                predictions = []
                
                for example in test_data:
                    prediction = trainer.predict(model_id, example.input_code)
                    predictions.append(prediction)
                    
                    # Check if category matches
                    if prediction.get('category') == example.category:
                        correct += 1
                
                accuracy = correct / len(test_data) if test_data else 0
                results[name] = {
                    "model_id": model_id,
                    "accuracy": accuracy,
                    "correct": correct,
                    "total": len(test_data),
                    "predictions": predictions
                }
                
                logger.info(f"{name} accuracy: {accuracy:.2%}")
        
        return results


def main():
    """Example usage"""
    from config import DATA_DIR, OPENAI_API_KEY
    
    # Configuration
    config = {
        "models": {
            "openai": {"api_key": OPENAI_API_KEY}
        }
    }
    
    # Initialize pipeline
    pipeline = MultiModelPipeline(config)
    
    # Load data
    train_file = DATA_DIR / "splits" / "train.json"
    if train_file.exists():
        training_data = pipeline.load_training_data(train_file)
        
        # Train models
        trained_models = pipeline.train_all_models(training_data[:10])  # Small sample for testing
        
        print(f"Trained models: {trained_models}")
    else:
        print(f"Training data not found at {train_file}")


if __name__ == "__main__":
    main()