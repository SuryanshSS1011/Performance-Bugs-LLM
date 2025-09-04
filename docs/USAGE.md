# Usage Guide

This guide explains how to use each component of the Performance Bugs detection system.

## Table of Contents
- [Quick Start](#quick-start)
- [Dataset Usage](#dataset-usage)
- [Pipeline Stages](#pipeline-stages)
- [Fine-tuning](#fine-tuning)
- [Evaluation](#evaluation)
- [Performance Validation](#performance-validation)
- [Regenerating Paper Figures](#regenerating-paper-figures)

## Quick Start

The end-to-end pipeline is orchestrated by `main.py`:

```bash
source venv/bin/activate
python main.py
```

This runs extraction, categorization, explanation generation, training-data
preparation, fine-tuning (if API keys are configured), and evaluation in sequence.
See `config.yaml` for stage toggles and parameters.

## Dataset Usage

### Loading the Dataset

```python
import json

with open('data/performance_bugs_490.json', 'r') as f:
    bugs = json.load(f)

print(f"Total bugs: {len(bugs)}")

# Inspect a bug record
bug = bugs[0]
print(f"Bug ID:   {bug['bug_id']}")
print(f"Project:  {bug['project']}")
print(f"Category: {bug['category']}")
```

### Filtering by Category

```python
algorithmic = [b for b in bugs if b['category'] == 'algorithmic_inefficiency']
memory      = [b for b in bugs if b['category'] == 'memory_usage']
```

### Category Distribution

```python
from collections import Counter
print(Counter(b['category'] for b in bugs))
```

### Training Splits

Per-category training splits live under `data/training/` as JSONL files:

- `train_algorithmic_inefficiency.jsonl`
- `train_memory_usage.jsonl`
- `train_redundant_computation.jsonl`
- `train_cpu_overhead.jsonl`
- `train_io_inefficiency.jsonl`
- `train_combined.jsonl` — all five concatenated
- `test_combined.jsonl` — held-out test set

## Pipeline Stages

Each stage of the paper's pipeline corresponds to a Python module. Run a single
stage like this:

### 1. Extraction (Section IV.A of the paper)

```bash
python -m extraction.defects4j_extractor
```

Extracts performance-related bugs from Defects4J. Defects4J must be installed and
on your `PATH`.

### 2. Categorization (Section IV.B)

```bash
python -m categorization.bug_categorizer
```

Classifies bugs into the five performance categories using pattern-based heuristics.

### 3. Method-Level Code Extraction

```bash
python -m processing.method_extractor
```

Extracts the buggy and fixed method-level code blocks from each bug.

### 4. Explanation Generation

```bash
python -m explanation.explanation_generator
```

Generates LLM-based explanations for each bug. Requires `OPENAI_API_KEY` in `.env`.

### 5. Training Data Preparation

```bash
python -m models.training_data_generator
```

Builds the per-category JSONL files in `data/training/` for fine-tuning.

## Fine-tuning

```bash
python -m models.fine_tuning_executor
```

Fine-tunes `gpt-4o-mini` on the prepared training data. Configuration lives in
`models/fine_tuning/training_config.json` and `models/fine_tuning/hyperparameters.json`.

For multi-model training:

```bash
python -m models.multi_model_trainer
```

## Evaluation

### Running the Evaluator

```bash
python -m evaluation.comprehensive_evaluator
```

Runs the test set through the fine-tuned model and writes `data/evaluation_report.md`.

### Comparing Models

```bash
python -m evaluation.model_comparison
```

Compares the fine-tuned model against the base GPT-4o-mini and writes
`data/model_comparison_report.md`.

### Custom Evaluation

```python
from evaluation.comprehensive_evaluator import ComprehensiveEvaluator

evaluator = ComprehensiveEvaluator()
metrics = evaluator.evaluate()  # see module for available kwargs
print(metrics)
```

## Performance Validation

```bash
python -m validation.performance_tester
```

Runs micro-benchmarks comparing buggy vs. fixed method execution to confirm that
the fixes actually improve performance.

## Regenerating Paper Figures

The three figures from the paper (Fig. 1 — category distribution, Fig. 2 —
per-project breakdown, Fig. 3 — per-category P/R/F1) can be regenerated from the
published numbers:

```bash
python scripts/generate_paper_figures.py
```

PNG outputs are written to `results/visualizations/`.

## Notebooks

The `notebooks/` directory contains stage-by-stage analysis notebooks:

- `01_data_extraction_analysis.ipynb`
- `02_bug_categorization.ipynb`
- `03_model_fine_tuning.ipynb`
- `04_model_evaluation.ipynb`
- `05_results_visualization.ipynb`
- `06_defects4j_integration.ipynb`

```bash
jupyter notebook notebooks/01_data_extraction_analysis.ipynb
```

## Troubleshooting

### Rate Limits
Add delays between API calls or batch requests:
```python
import time
time.sleep(1)
```

### Token Limits
Long methods may exceed the model's context window. The pipeline handles
truncation, but you can adjust limits in `config.yaml`.

### Missing API Key
If `OPENAI_API_KEY` is not set, stages requiring the API will fail. Add it to
`.env`:
```
OPENAI_API_KEY=sk-...
```

## Further Reading

- [Installation Guide](INSTALLATION_GUIDE.md)
- [Dataset Description](DATASET_DESCRIPTION.md)
- [Technical Guide](../ref/TECHNICAL_GUIDE.md)
- [Paper (IEEE Xplore)](https://ieeexplore.ieee.org/document/11127255)
