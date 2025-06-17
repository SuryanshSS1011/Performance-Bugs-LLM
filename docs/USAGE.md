# Usage Guide

This guide explains how to use each component of the Performance Bugs detection system.

## Table of Contents
- [Quick Start](#quick-start)
- [Dataset Usage](#dataset-usage)
- [Bug Detection](#bug-detection)
- [Model Fine-tuning](#model-fine-tuning)
- [Evaluation](#evaluation)
- [Performance Testing](#performance-testing)
- [Advanced Usage](#advanced-usage)

## Quick Start

### Detecting Performance Bugs in Your Code

The simplest use case is detecting performance bugs in a Java file:

```bash
# Activate environment
source venv/bin/activate

# Detect bugs in a single file
python model/inference/detect_performance_bugs.py --file YourJavaFile.java

# Detect bugs in a directory
python model/inference/detect_performance_bugs.py --directory /path/to/java/project

# Save results
python model/inference/detect_performance_bugs.py \
    --file YourJavaFile.java \
    --report report.txt \
    --json results.json
```

### Example Output

```
Performance Bug Detection Report
==================================================
Generated: 2024-01-15 10:30:45
Model: ft:gpt-4o-mini-2024-07-18:personal:perf-bugs-detector:xxxxx

Summary Statistics:
------------------------------
Files analyzed: 1
Total bugs found: 2

Bug Categories:
------------------------------
ALGORITHMIC_INEFFICIENCY: 1
MEMORY_USAGE: 1

Detailed Results:
------------------------------

File: YourJavaFile.java
Bugs found: 2

  Method: processData(List<String>)
  Category: ALGORITHMIC_INEFFICIENCY
  Confidence: high
  Explanation: This method uses a nested loop with O(n²) complexity. 
               The inner loop performs a linear search that could be 
               optimized using a HashSet for O(1) lookups.

  Method: buildString(String[])
  Category: MEMORY_USAGE
  Confidence: medium
  Explanation: String concatenation in a loop creates many temporary
               String objects. Use StringBuilder for better performance.
```

## Dataset Usage

### Loading the Dataset

```python
import json
import pandas as pd

# Load as JSON
with open('dataset/performance_bugs_490.json', 'r') as f:
    bugs = json.load(f)

# Load as DataFrame
df = pd.read_csv('dataset/performance_bugs_490.csv')

# Access a specific bug
bug = bugs[0]
print(f"Bug ID: {bug['bug_id']}")
print(f"Category: {bug['category']}")
print(f"Project: {bug['project']}")
```

### Filtering Bugs by Category

```python
# Get all algorithmic inefficiency bugs
algorithmic_bugs = [
    bug for bug in bugs 
    if bug['category'] == 'ALGORITHMIC_INEFFICIENCY'
]

# Using pandas
memory_bugs = df[df['category'] == 'MEMORY_USAGE']
```

### Analyzing Bug Patterns

```python
# Count bugs by project
project_counts = df['project'].value_counts()

# Average lines changed by category
avg_changes = df.groupby('category')['lines_changed'].mean()

# Find complex bugs (many lines changed)
complex_bugs = df[df['lines_changed'] > 50]
```

## Bug Detection

### Basic Detection

```python
from model.inference.detect_performance_bugs import PerformanceBugDetector

# Initialize detector
detector = PerformanceBugDetector()

# Detect in a file
result = detector.detect_file('path/to/JavaFile.java')

if result['has_bugs']:
    print(f"Found {result['bug_count']} bugs:")
    for bug in result['bugs']:
        print(f"- {bug['category']}: {bug['explanation']}")
```

### Batch Processing

```python
# Process multiple files
import glob

java_files = glob.glob('src/**/*.java', recursive=True)
all_results = []

for file in java_files:
    result = detector.detect_file(file)
    all_results.append(result)

# Generate report
detector.generate_report(all_results, 'batch_report.txt')
```

### Custom Configuration

```python
# Use custom model configuration
detector = PerformanceBugDetector(
    model_config_path='path/to/custom_config.json'
)

# Or configure programmatically
detector.config['temperature'] = 0.2  # More deterministic
detector.config['max_tokens'] = 1000  # Longer explanations
```

## Model Fine-tuning

### Preparing Your Own Dataset

```python
# Format your bugs for fine-tuning
training_data = []

for bug in your_bugs:
    example = {
        "messages": [
            {
                "role": "system",
                "content": "You are a performance bug detection expert..."
            },
            {
                "role": "user",
                "content": f"Analyze this code:\n```java\n{bug['code']}\n```"
            },
            {
                "role": "assistant",
                "content": f"Category: {bug['category']}\nExplanation: {bug['explanation']}"
            }
        ]
    }
    training_data.append(example)

# Save as JSONL
import jsonlines
with jsonlines.open('training_data.jsonl', 'w') as writer:
    writer.write_all(training_data)
```

### Fine-tuning Process

```bash
# Prepare data
python model/fine_tuning/prepare_training_data.py \
    --dataset dataset/performance_bugs_490.json \
    --output training_data/

# Fine-tune model
python model/fine_tuning/fine_tune_gpt4o_mini.py \
    --dataset dataset/performance_bugs_490.json \
    --output fine_tuned_model/

# Monitor progress
# The script will show updates every minute
```

### Using Your Fine-tuned Model

```python
# Update model configuration
config = {
    "model_id": "ft:gpt-4o-mini-2024-07-18:personal:your-model:xxxxx",
    "temperature": 0.3,
    "max_tokens": 500
}

# Save configuration
with open('custom_model_config.json', 'w') as f:
    json.dump(config, f)

# Use with detector
detector = PerformanceBugDetector('custom_model_config.json')
```

## Evaluation

### Running Full Evaluation

```bash
# Evaluate on test set
python evaluation/metrics/calculate_accuracy.py \
    --dataset dataset/performance_bugs_490.json \
    --model-config model/fine_tuning/model_config.json \
    --output evaluation_results/
```

### Custom Evaluation

```python
from evaluation.metrics.calculate_accuracy import ModelEvaluator

# Create evaluator
evaluator = ModelEvaluator('model_config.json')

# Evaluate on custom test set
test_bugs = [...]  # Your test bugs
metrics = evaluator.evaluate_dataset(test_bugs)

print(f"Accuracy: {metrics['overall']['accuracy']:.1%}")
print(f"F1 Score: {metrics['overall']['f1_score']:.1%}")
```

### Analyzing Results

```python
# Load evaluation results
with open('evaluation_results/detailed_results.json', 'r') as f:
    results = json.load(f)

# Find misclassified bugs
errors = [r for r in results if not r['correct']]

# Analyze by confidence
high_conf_accuracy = sum(
    1 for r in results 
    if r['correct'] and r['confidence'] == 'high'
) / len(results)
```

## Performance Testing

### Validating Performance Improvements

```bash
# Test a specific bug fix
python performance_testing/test_harness/run_performance_tests.py \
    --bug-id Chart-11 \
    --iterations 10

# Test multiple bugs
python performance_testing/test_harness/run_performance_tests.py \
    --dataset dataset/performance_bugs_490.json \
    --sample 20 \
    --output performance_results/
```

### Micro-benchmarking

```python
from performance_testing.benchmarks.micro_benchmarks import MicroBenchmark

# Create benchmark
benchmark = MicroBenchmark()

# Test specific code patterns
buggy_code = "String s = ''; for(int i=0; i<n; i++) s += data[i];"
fixed_code = "StringBuilder sb = new StringBuilder(); for(int i=0; i<n; i++) sb.append(data[i]);"

results = benchmark.compare_performance(buggy_code, fixed_code)
print(f"Performance improvement: {results['improvement']:.1%}")
```

## Advanced Usage

### Integration with CI/CD

```yaml
# .github/workflows/performance-check.yml
name: Performance Bug Check

on: [push, pull_request]

jobs:
  check-performance:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.8
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
    
    - name: Check for performance bugs
      run: |
        python model/inference/detect_performance_bugs.py \
          --directory src/ \
          --report performance_report.txt
    
    - name: Upload report
      uses: actions/upload-artifact@v2
      with:
        name: performance-report
        path: performance_report.txt
```

### Custom Categories

```python
# Define custom performance bug categories
CUSTOM_CATEGORIES = {
    'DATABASE_INEFFICIENCY': {
        'patterns': [r'SELECT.*FROM.*WHERE.*IN\s*\(SELECT'],
        'keywords': ['n+1', 'query', 'database', 'sql']
    },
    'CONCURRENCY_ISSUE': {
        'patterns': [r'synchronized.*synchronized'],
        'keywords': ['deadlock', 'race condition', 'thread']
    }
}

# Extend the detector
class CustomDetector(PerformanceBugDetector):
    def _analyze_code(self, code, method_name):
        # First run standard detection
        result = super()._analyze_code(code, method_name)
        
        # Then check custom patterns
        for category, config in CUSTOM_CATEGORIES.items():
            for pattern in config['patterns']:
                if re.search(pattern, code):
                    result['category'] = category
                    break
        
        return result
```

### Bulk Analysis Script

```python
#!/usr/bin/env python3
"""analyze_repository.py - Analyze entire repository"""

import os
import sys
from pathlib import Path
from model.inference.detect_performance_bugs import PerformanceBugDetector

def analyze_repository(repo_path):
    detector = PerformanceBugDetector()
    
    # Find all Java files
    java_files = list(Path(repo_path).rglob('*.java'))
    print(f"Found {len(java_files)} Java files")
    
    # Analyze each file
    total_bugs = 0
    bug_files = []
    
    for file in java_files:
        result = detector.detect_file(str(file))
        if result['has_bugs']:
            total_bugs += result['bug_count']
            bug_files.append(file)
    
    # Generate summary
    print(f"\nAnalysis Complete:")
    print(f"Total files: {len(java_files)}")
    print(f"Files with bugs: {len(bug_files)}")
    print(f"Total bugs found: {total_bugs}")
    
    # Save detailed report
    detector.generate_report(results, 'repository_analysis.txt')

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python analyze_repository.py <repo_path>")
        sys.exit(1)
    
    analyze_repository(sys.argv[1])
```

## Best Practices

### 1. Pre-filtering Files
```python
# Skip test files and generated code
def should_analyze(file_path):
    skip_patterns = ['Test.java', 'test/', 'generated/', 'build/']
    return not any(pattern in file_path for pattern in skip_patterns)

files_to_analyze = [f for f in java_files if should_analyze(f)]
```

### 2. Handling Large Files
```python
# Process large files in chunks
def analyze_large_file(file_path, max_methods=50):
    methods = extractor.extract_methods(file_path)
    
    # Process in batches
    for i in range(0, len(methods), max_methods):
        batch = methods[i:i+max_methods]
        results = detector.analyze_methods(batch)
        yield results
```

### 3. Caching Results
```python
import pickle

# Cache detection results
cache_file = 'detection_cache.pkl'

if os.path.exists(cache_file):
    with open(cache_file, 'rb') as f:
        cache = pickle.load(f)
else:
    cache = {}

# Use cache
file_hash = hash(file_content)
if file_hash in cache:
    result = cache[file_hash]
else:
    result = detector.detect_file(file_path)
    cache[file_hash] = result
```

## Troubleshooting

### Common Issues

1. **Rate Limits**: Add delays between API calls
   ```python
   import time
   time.sleep(1)  # Wait 1 second between calls
   ```

2. **Token Limits**: Split large methods
   ```python
   if len(method_code) > 4000:
       # Process in smaller chunks
   ```

3. **Memory Issues**: Process files in batches
   ```python
   # Process 100 files at a time
   for batch in chunks(files, 100):
       process_batch(batch)
   ```

## Next Steps

- Read the [Model Architecture](MODEL_ARCHITECTURE.md) guide
- Explore the [Jupyter notebooks](../notebooks/)
- Check out [example bugs](../examples/)
- Join our [community discussions](https://github.com/yourusername/performance-bugs-llm/discussions)