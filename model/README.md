# Model Directory

This directory contains the fine-tuning and inference code for the GPT-4o-mini performance bug detector.

## Directory Structure

```
model/
├── fine_tuning/
│   ├── prepare_training_data.py    # Prepare data for fine-tuning
│   ├── fine_tune_gpt4o_mini.py     # Fine-tuning script
│   ├── training_config.json        # Training configuration
│   ├── hyperparameters.json        # Hyperparameter settings
│   └── data/                       # Training data (generated)
│
├── inference/
│   ├── detect_performance_bugs.py  # Bug detection script
│   ├── generate_explanations.py   # Explanation generation
│   └── model_config.json          # Model configuration
│
└── checkpoints/                    # Model checkpoints
    └── .gitkeep
```

## Fine-tuning

### Prerequisites

1. OpenAI API key with fine-tuning access
2. The performance bugs dataset
3. Sufficient API credits (approximately $50-100 for full fine-tuning)

### Fine-tuning Process

1. **Prepare Training Data**
   ```bash
   cd fine_tuning
   python prepare_training_data.py \
       --dataset ../../dataset/performance_bugs_490.json \
       --output ./data/
   ```
   
   This creates:
   - `training_data.jsonl` (392 examples, 80%)
   - `validation_data.jsonl` (98 examples, 20%)

2. **Start Fine-tuning**
   ```bash
   python fine_tune_gpt4o_mini.py \
       --dataset ../../dataset/performance_bugs_490.json \
       --output ./
   ```
   
   The script will:
   - Upload training files to OpenAI
   - Create a fine-tuning job
   - Monitor progress (updates every minute)
   - Save the model ID when complete

3. **Monitor Progress**
   - Training typically takes 2-3 hours
   - You'll see periodic updates with loss metrics
   - Final model ID will be saved to `model_config.json`

### Training Configuration

Key hyperparameters (from `training_config.json`):
- **Epochs**: 3
- **Batch Size**: 8
- **Learning Rate Multiplier**: 0.1
- **Temperature**: 0.3 (for consistent outputs)

These were tuned to achieve 83.7% accuracy on the test set.

## Inference

### Using the Fine-tuned Model

1. **Single File Analysis**
   ```bash
   cd inference
   python detect_performance_bugs.py --file YourJavaFile.java
   ```

2. **Directory Analysis**
   ```bash
   python detect_performance_bugs.py --directory /path/to/project
   ```

3. **With Custom Output**
   ```bash
   python detect_performance_bugs.py \
       --file YourJavaFile.java \
       --report analysis_report.txt \
       --json results.json
   ```

### Model Configuration

The `model_config.json` file contains:
```json
{
  "model_id": "ft:gpt-4o-mini-2024-07-18:personal:perf-bugs-detector:xxxxx",
  "system_prompt": "...",
  "temperature": 0.3,
  "max_tokens": 500,
  "categories": [...]
}
```

### API Usage

```python
from model.inference.detect_performance_bugs import PerformanceBugDetector

# Initialize detector
detector = PerformanceBugDetector()

# Analyze code
result = detector.detect_file('Example.java')

# Check results
if result['has_bugs']:
    for bug in result['bugs']:
        print(f"{bug['category']}: {bug['explanation']}")
```

## Model Performance

### Metrics (from paper)
- **Accuracy**: 83.7%
- **Precision**: 83.0%
- **Recall**: 81.8%
- **F1 Score**: 82.3%
- **Report Match Rate**: 90.2%

### Per-Category Performance
| Category | Precision | Recall | F1 Score |
|----------|-----------|--------|----------|
| Algorithmic Inefficiency | 0.89 | 0.91 | 0.90 |
| Memory Usage | 0.84 | 0.82 | 0.83 |
| CPU Overhead | 0.81 | 0.79 | 0.80 |
| Redundant Computation | 0.78 | 0.76 | 0.77 |
| I/O Inefficiency | 0.73 | 0.71 | 0.72 |

## Cost Estimation

### Fine-tuning Costs
- Training tokens: ~2M tokens
- Validation tokens: ~500K tokens
- Estimated cost: $50-100 (depending on current pricing)

### Inference Costs
- Average tokens per analysis: 200-300
- Cost per bug detection: ~$0.001
- 1000 file analyses: ~$1-2

## Advanced Usage

### Custom Categories

To add custom performance bug categories:

1. Update the system prompt in `model_config.json`
2. Add patterns to detection logic
3. Fine-tune on examples of the new category

### Batch Processing

For large-scale analysis:

```python
# process_repository.py
import glob
from concurrent.futures import ThreadPoolExecutor

def analyze_repository(repo_path):
    detector = PerformanceBugDetector()
    java_files = glob.glob(f"{repo_path}/**/*.java", recursive=True)
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(detector.detect_file, java_files))
    
    return results
```

### Integration with IDEs

The model can be integrated with IDEs through:
- VS Code extensions
- IntelliJ plugins
- Git pre-commit hooks
- CI/CD pipelines

## Troubleshooting

### Common Issues

1. **Rate Limits**
   - Add delays between API calls
   - Use exponential backoff
   - Consider batch processing

2. **Token Limits**
   - Split large files into methods
   - Process methods individually
   - Summarize results

3. **Model Not Found**
   - Ensure model ID is correct
   - Check API key permissions
   - Verify fine-tuning completed

## Future Improvements

Potential enhancements:
1. Support for additional languages (Python, JavaScript)
2. Real-time performance profiling integration
3. Automated fix generation
4. IDE plugin development
5. Continuous learning from user feedback

## Support

For issues or questions:
1. Check the [FAQ](../docs/FAQ.md)
2. Open a GitHub issue
3. Contact the authors

## License

This code is provided under the MIT License. The fine-tuned model remains subject to OpenAI's usage policies.