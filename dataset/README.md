# Performance Bugs Dataset

[← Back to Main README](../README.md)

This directory contains the dataset of 490 performance bugs extracted from Defects4J projects.

## Files

- **performance_bugs_490.json** - Complete dataset with all fields (main file)
- **performance_bugs_490.csv** - Summary in CSV format for easy analysis
- **category_distribution.json** - Category statistics
- **project_distribution.json** - Project-level statistics

## Quick Statistics

- **Total Bugs**: 490
- **Projects**: 17
- **Categories**: 5
- **Average Methods Changed**: 1.3 per bug
- **Average Lines Changed**: 21.4 per bug

## Category Distribution

| Category | Count | Percentage |
|----------|-------|------------|
| Algorithmic Inefficiency | 165 | 33.7% |
| Memory Usage | 116 | 23.7% |
| CPU Overhead | 99 | 20.2% |
| Redundant Computation | 54 | 11.0% |
| I/O Inefficiency | 56 | 11.4% |

## Loading the Dataset

### Python
```python
import json
import pandas as pd

# Load JSON format
with open('performance_bugs_490.json', 'r') as f:
    bugs = json.load(f)

# Load CSV format
df = pd.read_csv('performance_bugs_490.csv')

# Access specific bug
first_bug = bugs[0]
print(f"Bug ID: {first_bug['bug_id']}")
print(f"Category: {first_bug['category']}")
```

### Key Fields

Each bug entry contains:
- `bug_id`: Unique identifier (e.g., "Chart-11")
- `project`: Project name
- `category`: Performance bug category
- `buggy_code`: Original buggy code
- `fixed_code`: Fixed version
- `llm_comments`: Explanation of the bug
- `performance_metadata`: Additional metadata

## Example Usage

### Find Bugs by Category
```python
# Get all memory-related bugs
memory_bugs = [bug for bug in bugs if bug['category'] == 'MEMORY_USAGE']
```

### Analyze by Project
```python
# Count bugs per project
from collections import Counter
project_counts = Counter(bug['project'] for bug in bugs)
```

### Get High-Impact Bugs
```python
# Bugs with high performance impact
high_impact = [
    bug for bug in bugs 
    if bug['performance_metadata']['performance_impact'] == 'high'
]
```

## Data Quality

- All bugs verified from Defects4J v3.0.1
- Consistent categorization based on code patterns
- LLM explanations reviewed for accuracy

## License and Citation

This dataset is released under the MIT License.

If you use this dataset, please cite:

```bibtex
@inproceedings{performancebugs2025,
  title={Fixing Performance Bugs Through LLM Explanations},
  author={Sijwali, Suryansh Singh and Colom, Angela Marie and Guo, Anbi and Saha, Suman},
  booktitle={Proceedings of the Conference},
  year={2024}
}
```

## Related Documentation

- **[Model Training](../model/)** - How to use this dataset for fine-tuning
- **[Evaluation Metrics](../evaluation/)** - How the dataset performance is measured
- **[Extraction Process](../extraction/)** - How these bugs were extracted from Defects4J
- **[Usage Guide](../docs/USAGE.md)** - Detailed usage instructions

## Contact

For questions about the dataset:
- Open an issue on GitHub
- Contact the paper authors

---
[← Back to Main README](../README.md)