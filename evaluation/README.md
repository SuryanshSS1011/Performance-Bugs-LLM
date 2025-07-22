# Evaluation Directory

[← Back to Main README](../README.md)

This directory contains scripts and tools for evaluating the performance bug detection model.

## Directory Structure

```
evaluation/
├── metrics/
│   ├── calculate_accuracy.py       # Overall accuracy metrics
│   ├── report_match_evaluation.py # Report quality evaluation
│   ├── category_confusion_matrix.py # Confusion matrix generation
│   └── per_project_analysis.py    # Project-level analysis
│
├── benchmarks/
│   ├── performance_validation.py  # Validate performance improvements
│   ├── before_after_comparison.py # Compare buggy vs fixed performance
│   └── runtime_analysis.py        # Runtime complexity analysis
│
└── results/
    ├── evaluation_results.json    # Metric results
    └── figures/                   # Generated plots
```

## Evaluation Metrics

### Primary Metrics (from paper)

| Metric | Base Model | Fine-tuned Model | Improvement |
|--------|------------|------------------|-------------|
| Accuracy | 67.3% | 83.7% | +16.4% |
| Precision | 65.1% | 83.0% | +17.9% |
| Recall | 64.2% | 81.8% | +17.6% |
| F1 Score | 64.6% | 82.3% | +17.7% |
| Report Match | 73.5% | 90.2% | +16.7% |

### Running Evaluations

1. **Complete Evaluation Suite**
   ```bash
   cd metrics
   python calculate_accuracy.py \
       --dataset ../../dataset/performance_bugs_490.json \
       --model-config ../../model/fine_tuning/model_config.json \
       --output ../results/
   ```

2. **Report Match Evaluation**
   ```bash
   python report_match_evaluation.py \
       --predictions ../results/detailed_results.json \
       --ground-truth ../../dataset/performance_bugs_490.json \
       --output ../results/
   ```

3. **Confusion Matrix**
   ```bash
   python category_confusion_matrix.py \
       --results ../results/detailed_results.json \
       --output ../results/figures/
   ```

4. **Per-Project Analysis**
   ```bash
   python per_project_analysis.py \
       --results ../results/detailed_results.json \
       --dataset ../../dataset/performance_bugs_490.json \
       --output ../results/
   ```

## Evaluation Components

### 1. Accuracy Calculation (`calculate_accuracy.py`)

Evaluates the model on the 20% test set (98 bugs):
- Splits data using same seed as training
- Measures classification accuracy
- Calculates precision, recall, F1 per category
- Generates confusion matrix
- Compares with paper results

**Output Files:**
- `evaluation_metrics.json`: All metrics
- `detailed_results.json`: Per-bug predictions
- `evaluation_results.csv`: Tabular results
- `confusion_matrix.png`: Visual confusion matrix

### 2. Report Match Evaluation (`report_match_evaluation.py`)

Evaluates the quality of generated explanations:
- Compares generated vs. ground truth explanations
- Uses semantic similarity metrics
- Checks for key concept coverage
- Measures explanation completeness

**Evaluation Criteria:**
- Technical accuracy
- Clarity and coherence
- Actionability of recommendations
- Coverage of performance concepts

### 3. Category Confusion Analysis

Analyzes classification errors:
- Which categories are confused most often
- Common misclassification patterns
- Confidence correlation with accuracy

**Key Findings:**
- Algorithmic ↔ CPU Overhead: Most confused pair
- Memory ↔ Redundant: Sometimes overlap
- I/O: Most distinct category

### 4. Project-Level Analysis

Breaks down performance by project:
- Accuracy per project
- Category distribution per project
- Project-specific challenges

## Performance Validation

### Validating Bug Fixes

The `benchmarks/` directory contains tools to verify that the identified bugs actually improve performance:

```bash
cd benchmarks
python performance_validation.py \
    --bug-id Chart-11 \
    --defects4j-path ../../../defects4j \
    --iterations 100
```

### Metrics Collected
- Execution time (before/after)
- Memory usage (before/after)
- CPU utilization
- Complexity analysis

### Example Results
```
Bug: Chart-11
Category: ALGORITHMIC_INEFFICIENCY
Buggy version: 2.34s (avg over 100 runs)
Fixed version: 0.12s (avg over 100 runs)
Improvement: 94.9% faster
Statistical significance: p < 0.001
```

## Custom Evaluation

### Adding New Metrics

```python
# custom_metric.py
from evaluation.metrics.base import MetricBase

class CustomMetric(MetricBase):
    def calculate(self, predictions, ground_truth):
        # Your metric logic
        return score
    
    def report(self):
        # Generate report
        pass
```

### Evaluating on Custom Data

```python
from evaluation.metrics.calculate_accuracy import ModelEvaluator

# Load your data
custom_bugs = load_your_bugs()

# Create evaluator
evaluator = ModelEvaluator('model_config.json')

# Run evaluation
results = evaluator.evaluate_dataset(custom_bugs)

# Generate report
evaluator.generate_report(results, 'custom_report.txt')
```

## Statistical Analysis

### Significance Testing

```python
from scipy import stats

# Compare two models
model1_scores = [...]  # Accuracy scores
model2_scores = [...]

t_stat, p_value = stats.ttest_rel(model1_scores, model2_scores)
print(f"Paired t-test: t={t_stat:.3f}, p={p_value:.4f}")
```

### Confidence Intervals

```python
import numpy as np
from scipy import stats

# Bootstrap confidence intervals
def bootstrap_ci(scores, n_bootstrap=1000):
    bootstrap_means = []
    for _ in range(n_bootstrap):
        sample = np.random.choice(scores, size=len(scores), replace=True)
        bootstrap_means.append(np.mean(sample))
    
    return np.percentile(bootstrap_means, [2.5, 97.5])

ci_low, ci_high = bootstrap_ci(accuracy_scores)
print(f"95% CI: [{ci_low:.3f}, {ci_high:.3f}]")
```

## Visualization

### Generating Plots

All evaluation scripts can generate visualizations:

1. **Confusion Matrix**: Heatmap of predictions vs. truth
2. **Per-Category Performance**: Bar charts of metrics
3. **Learning Curves**: Training/validation loss over time
4. **ROC Curves**: For binary classification tasks
5. **Error Analysis**: Distribution of error types

### Example Visualizations

```python
# Generate all standard plots
python generate_all_plots.py --results ../results/ --output ../results/figures/
```

## Ablation Studies

### Component Importance

Test the importance of different components:

1. **Without LLM comments**: How much do explanations help?
2. **Without code context**: Impact of method context
3. **Category-specific models**: Specialized vs. unified
4. **Different base models**: GPT-4o-mini vs. others

## Reproducibility

### Ensuring Reproducible Results

1. **Fixed Random Seeds**: All scripts use seed=42
2. **Versioned Dependencies**: Exact package versions in requirements.txt
3. **Data Splits**: Same train/test split as paper
4. **Model Checkpoints**: Saved after each epoch

### Verification Steps

```bash
# Verify your setup matches the paper
python verify_reproduction.py

# This checks:
# - Data split correctness
# - Model configuration
# - Metric calculations
# - Statistical tests
```

## Troubleshooting

### Common Issues

1. **Different Results than Paper**
   - Check random seed
   - Verify data split
   - Ensure same model version

2. **Memory Errors**
   - Reduce batch size
   - Use gradient accumulation
   - Process sequentially

3. **Slow Evaluation**
   - Use caching for repeated calls
   - Parallelize across multiple GPUs
   - Batch API requests

## Next Steps

After evaluation:

1. **Error Analysis**: Examine misclassified bugs
2. **Model Improvement**: Fine-tune on errors
3. **Deploy**: Create production pipeline
4. **Monitor**: Track real-world performance

## Related Components

- **[Dataset](../dataset/)** - The performance bugs being evaluated
- **[Model](../model/)** - The fine-tuned model being evaluated
- **[Extraction](../extraction/)** - How the evaluated bugs were extracted
- **[Installation Guide](../docs/INSTALLATION_GUIDE.md)** - Setup requirements

## References

- [Paper: Fixing Performance Bugs Through LLM Explanations] ()
- [OpenAI Fine-tuning Documentation] (https://platform.openai.com/docs/guides/fine-tuning)
- [Scikit-learn Metrics Guide] (https://scikit-learn.org/stable/modules/model_evaluation.html)

---
[← Back to Main README](../README.md)