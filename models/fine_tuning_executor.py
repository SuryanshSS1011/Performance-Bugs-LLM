"""
Fine-tuning execution script for GPT-4o-mini.
Implements the complete fine-tuning workflow from the paper.
"""

import json
import logging
import os
import time
from pathlib import Path
from typing import Dict, Optional
from training_data_generator import OpenAIFineTuner

logger = logging.getLogger(__name__)

class FineTuningExecutor:
    """
    Executes the complete fine-tuning workflow for performance bug detection.
    Implements the methodology from Section V.A of the paper.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            logger.warning("OpenAI API key not found. Set OPENAI_API_KEY environment variable.")
        
        self.fine_tuner = OpenAIFineTuner(self.api_key) if self.api_key else None
        self.jobs_file = Path('data/training/fine_tuning_jobs.json')
        
    def execute_fine_tuning_workflow(self, training_dir: str = 'data/training') -> Dict:
        """
        Execute the complete fine-tuning workflow:
        1. Validate training data
        2. Submit fine-tuning job
        3. Monitor progress
        4. Save results
        """
        
        workflow_results = {
            'validation': {},
            'job_submission': {},
            'monitoring': {},
            'final_model': None
        }
        
        training_path = Path(training_dir)
        
        # Step 1: Validate training data
        logger.info("Step 1: Validating training data...")
        validation = self._validate_training_data(training_path)
        workflow_results['validation'] = validation
        
        if not validation['is_valid']:
            logger.error("Training data validation failed")
            return workflow_results
        
        # Step 2: Submit fine-tuning job
        logger.info("Step 2: Submitting fine-tuning job...")
        if self.fine_tuner:
            job_info = self._submit_fine_tuning_job(training_path)
            workflow_results['job_submission'] = job_info
            
            if 'error' not in job_info:
                # Step 3: Monitor job (simplified for demo)
                logger.info("Step 3: Monitoring fine-tuning job...")
                monitoring = self._monitor_job_progress(job_info['job_id'])
                workflow_results['monitoring'] = monitoring
                workflow_results['final_model'] = monitoring.get('fine_tuned_model')
        
        return workflow_results
    
    def _validate_training_data(self, training_path: Path) -> Dict:
        """Validate training data files meet OpenAI requirements"""
        
        validation = {
            'is_valid': True,
            'files_checked': [],
            'total_examples': 0,
            'category_examples': {},
            'errors': []
        }
        
        # Check required files exist
        required_files = ['train_combined.jsonl', 'test_combined.jsonl']
        
        for file_name in required_files:
            file_path = training_path / file_name
            if not file_path.exists():
                validation['errors'].append(f"Missing required file: {file_name}")
                validation['is_valid'] = False
                continue
                
            # Validate JSONL format
            try:
                example_count = 0
                with open(file_path, 'r') as f:
                    for line_num, line in enumerate(f, 1):
                        if line.strip():
                            example = json.loads(line)
                            
                            # Validate OpenAI format
                            if 'messages' not in example:
                                validation['errors'].append(f"{file_name}:{line_num} - Missing 'messages' field")
                                validation['is_valid'] = False
                                break
                            
                            messages = example['messages']
                            if len(messages) != 3:
                                validation['errors'].append(f"{file_name}:{line_num} - Expected 3 messages, got {len(messages)}")
                                validation['is_valid'] = False
                                break
                            
                            # Check message roles
                            expected_roles = ['system', 'user', 'assistant']
                            actual_roles = [msg['role'] for msg in messages]
                            if actual_roles != expected_roles:
                                validation['errors'].append(f"{file_name}:{line_num} - Invalid message roles: {actual_roles}")
                                validation['is_valid'] = False
                                break
                            
                            example_count += 1
                
                validation['files_checked'].append({
                    'file': file_name,
                    'examples': example_count,
                    'valid': validation['is_valid']
                })
                validation['total_examples'] += example_count
                
            except json.JSONDecodeError as e:
                validation['errors'].append(f"Invalid JSON in {file_name}: {e}")
                validation['is_valid'] = False
            except Exception as e:
                validation['errors'].append(f"Error validating {file_name}: {e}")
                validation['is_valid'] = False
        
        # Check category-specific files
        category_files = list(training_path.glob('train_*.jsonl'))
        for cat_file in category_files:
            if cat_file.name != 'train_combined.jsonl':
                category = cat_file.name.replace('train_', '').replace('.jsonl', '')
                try:
                    with open(cat_file, 'r') as f:
                        cat_count = sum(1 for line in f if line.strip())
                    validation['category_examples'][category] = cat_count
                except Exception as e:
                    validation['errors'].append(f"Error reading {cat_file.name}: {e}")
        
        return validation
    
    def _submit_fine_tuning_job(self, training_path: Path) -> Dict:
        """Submit fine-tuning job to OpenAI"""
        
        train_file = training_path / 'train_combined.jsonl'
        test_file = training_path / 'test_combined.jsonl'
        
        if not self.fine_tuner:
            return {'error': 'OpenAI fine-tuner not initialized (missing API key)'}
        
        try:
            # Submit job
            job_info = self.fine_tuner.create_fine_tuning_job(
                training_file=str(train_file),
                validation_file=str(test_file)
            )
            
            # Save job info
            self._save_job_info(job_info)
            
            return job_info
            
        except Exception as e:
            logger.error(f"Failed to submit fine-tuning job: {e}")
            return {'error': str(e)}
    
    def _monitor_job_progress(self, job_id: str, max_wait_time: int = 3600) -> Dict:
        """Monitor fine-tuning job progress (simplified for demo)"""
        
        if not self.fine_tuner:
            return {'error': 'OpenAI fine-tuner not initialized'}
        
        start_time = time.time()
        monitoring_log = []
        
        try:
            while time.time() - start_time < max_wait_time:
                status = self.fine_tuner.monitor_job(job_id)
                monitoring_log.append({
                    'timestamp': time.time(),
                    'status': status
                })
                
                logger.info(f"Job {job_id} status: {status.get('status', 'unknown')}")
                
                # Check if job is complete
                if status.get('status') in ['succeeded', 'failed', 'cancelled']:
                    return {
                        'final_status': status,
                        'monitoring_log': monitoring_log,
                        'total_time': time.time() - start_time
                    }
                
                # Wait before next check
                time.sleep(60)  # Check every minute
            
            return {
                'status': 'timeout',
                'monitoring_log': monitoring_log,
                'total_time': max_wait_time
            }
            
        except Exception as e:
            return {
                'error': str(e),
                'monitoring_log': monitoring_log
            }
    
    def _save_job_info(self, job_info: Dict):
        """Save fine-tuning job information"""
        
        # Load existing jobs if file exists
        jobs_data = {'jobs': [], 'latest_job': None}
        if self.jobs_file.exists():
            try:
                with open(self.jobs_file, 'r') as f:
                    jobs_data = json.load(f)
            except Exception as e:
                logger.warning(f"Could not load existing jobs file: {e}")
        
        # Add new job
        jobs_data['jobs'].append({
            'job_info': job_info,
            'submitted_at': time.time(),
            'submitted_date': time.strftime('%Y-%m-%d %H:%M:%S')
        })
        jobs_data['latest_job'] = job_info.get('job_id')
        
        # Save updated jobs
        self.jobs_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.jobs_file, 'w') as f:
            json.dump(jobs_data, f, indent=2)
        
        logger.info(f"Saved job info to {self.jobs_file}")
    
    def get_job_status(self, job_id: Optional[str] = None) -> Dict:
        """Get status of a fine-tuning job"""
        
        if not self.fine_tuner:
            return {'error': 'OpenAI fine-tuner not initialized'}
        
        # Use latest job if no ID provided
        if not job_id:
            if not self.jobs_file.exists():
                return {'error': 'No jobs found'}
            
            with open(self.jobs_file, 'r') as f:
                jobs_data = json.load(f)
            
            job_id = jobs_data.get('latest_job')
            if not job_id:
                return {'error': 'No latest job found'}
        
        return self.fine_tuner.monitor_job(job_id)
    
    def list_fine_tuned_models(self) -> Dict:
        """List all fine-tuned models from previous jobs"""
        
        models = []
        
        if self.jobs_file.exists():
            try:
                with open(self.jobs_file, 'r') as f:
                    jobs_data = json.load(f)
                
                for job_entry in jobs_data['jobs']:
                    job_info = job_entry['job_info']
                    if 'job_id' in job_info:
                        # Get current status
                        current_status = self.get_job_status(job_info['job_id'])
                        models.append({
                            'job_id': job_info['job_id'],
                            'submitted_date': job_entry['submitted_date'],
                            'status': current_status.get('status', 'unknown'),
                            'fine_tuned_model': current_status.get('fine_tuned_model'),
                            'trained_tokens': current_status.get('trained_tokens')
                        })
            
            except Exception as e:
                return {'error': f"Failed to list models: {e}"}
        
        return {'models': models}

def main():
    """Main execution function"""
    
    # Initialize executor
    executor = FineTuningExecutor()
    
    print("Performance Bug Fine-tuning Executor")
    print("=" * 50)
    
    # Check if API key is available
    if not executor.api_key:
        print("WARNING: OpenAI API key not found!")
        print("   Set OPENAI_API_KEY environment variable to enable fine-tuning")
        print("   For now, showing training data validation only...")
        print()
    
    # Validate training data
    print("Validating training data...")
    validation = executor._validate_training_data(Path('data/training'))
    
    if validation['is_valid']:
        print("Training data validation successful!")
        print(f"   Total examples: {validation['total_examples']}")
        print(f"   Files validated: {len(validation['files_checked'])}")
        
        if validation['category_examples']:
            print("   Category breakdown:")
            for category, count in validation['category_examples'].items():
                print(f"     {category:25s}: {count:3d} examples")
    else:
        print("Training data validation failed!")
        for error in validation['errors']:
            print(f"   Error: {error}")
        return
    
    # Fine-tuning execution (if API key available)
    if executor.api_key:
        print("\nStarting fine-tuning workflow...")
        
        # Execute workflow
        results = executor.execute_fine_tuning_workflow()
        
        print("\nFine-tuning Results:")
        print(f"   Validation: {'Success' if results['validation']['is_valid'] else 'Failed'}")
        
        if 'job_submission' in results and results['job_submission']:
            job_info = results['job_submission']
            if 'error' not in job_info:
                print(f"   Job ID: {job_info['job_id']}")
                print(f"   Status: {job_info['status']}")
                print(f"   Model: {job_info['model']}")
            else:
                print(f"   Job submission failed: {job_info['error']}")
    
    else:
        print("\nTo enable fine-tuning:")
        print("   1. Set your OpenAI API key: export OPENAI_API_KEY='your-key-here'")
        print("   2. Install OpenAI library: pip install openai")
        print("   3. Re-run this script")
        
        print("\nTraining files ready at:")
        print("   - data/training/train_combined.jsonl")
        print("   - data/training/test_combined.jsonl")
        print("   - Individual category files: train_*.jsonl")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()