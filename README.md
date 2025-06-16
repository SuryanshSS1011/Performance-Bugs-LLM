# Performance Bugs Through LLM Explanations

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Defects4J](https://img.shields.io/badge/Defects4J-v3.0.1-green.svg)](https://github.com/rjust/defects4j)

This repository contains the code, dataset, and models from our paper "Fixing Performance Bugs Through LLM Explanations". We provide tools to extract performance bugs from Defects4J, fine-tune GPT-4o-mini for performance bug detection, and evaluate the results.

## 📊 Dataset Statistics

- **Total Performance Bugs**: 490
- **Projects**: 17 Defects4J projects
- **Categories**: 5 (Algorithmic, Memory, CPU, Redundant Computation, I/O)
- **Training/Test Split**: 392/98 (80/20)

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/yourusername/performance-bugs-llm.git
cd performance-bugs-llm

# Set up the environment
./scripts/setup_environment.sh

# Download and prepare the dataset
python scripts/validate_dataset.py

# Run the model on a Java file of your choice to 
python model/inference/detect_performance_bugs.py --file YourJavaFile.java
```

## 📁 Repository Structure

- **`dataset/`**: The 490 performance bugs dataset with categories and metadata
- **`extraction/`**: Scripts for extracting performance bugs from Defects4J
- **`model/`**: Fine-tuning and inference code for GPT-4o-mini
- **`evaluation/`**: Evaluation metrics and analysis scripts
- **`performance_testing/`**: Code for validating performance improvements
- **`docs/`**: Detailed documentation
- **`notebooks/`**: Jupyter notebooks for exploration and visualization

## 🔧 Installation

### Prerequisites

- Python 3.8+
- Java 8
- Maven 3.6+
- Git
- At least 50GB free disk space

### Setup

1. **Clone the repository**:
```bash
git clone https://github.com/SuryanshSS1011/performance-bugs-llm.git
cd performance-bugs-llm
```

2. **Create a virtual environment**:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Set up environment variables**:
```bash
cp .env.example .env
# Edit .env and add your OpenAI API key
```

5. **Install Defects4J** (if reproducing extraction):
```bash
./scripts/download_defects4j.sh
```

## 📊 Using the Dataset

The dataset is available in both JSON and CSV formats:

```python
import json
import pandas as pd

# Load JSON format
with open('dataset/performance_bugs_490.json', 'r') as f:
    bugs = json.load(f)

# Load CSV format
df = pd.read_csv('dataset/performance_bugs_490.csv')

# View category distribution
print(df['category'].value_counts())
```

## 🤖 Using the Model

### Detection
```python
from model.inference.detect_performance_bugs import PerformanceBugDetector

detector = PerformanceBugDetector()
result = detector.detect_file('path/to/YourJavaFile.java')

print(f"Performance bug detected: {result['is_performance_bug']}")
print(f"Category: {result['category']}")
print(f"Explanation: {result['explanation']}")
```

### Fine-tuning (Reproduction)
```bash
# Prepare training data
python model/fine_tuning/prepare_training_data.py

# Fine-tune the model
python model/fine_tuning/fine_tune_gpt4o_mini.py --config model/fine_tuning/training_config.json
```

## 📈 Reproducing Paper Results

To reproduce all results from the paper:

```bash
./scripts/reproduce_paper_results.sh
```

This will:
1. Extract performance bugs from Defects4J
2. Fine-tune the model
3. Run evaluation metrics
4. Generate all figures and tables

## 🧪 Performance Validation

We provide tools to validate that the identified bugs actually improve performance:

```bash
cd performance_testing
python test_harness/run_performance_tests.py --bug-id Chart-11
```

## 📚 Documentation

- [Installation Guide](docs/INSTALLATION.md) - Detailed setup instructions
- [Usage Guide](docs/USAGE.md) - How to use each component
- [Dataset Description](docs/DATASET_DESCRIPTION.md) - Detailed dataset documentation
- [Model Architecture](docs/MODEL_ARCHITECTURE.md) - Model details and training process
- [Reproduction Guide](docs/REPRODUCTION_GUIDE.md) - Step-by-step reproduction instructions

## 📊 Key Results

| Metric | Base Model | Fine-tuned Model |
|--------|------------|------------------|
| Accuracy | 67.3% | 83.7% |
| Precision | 65.1% | 83.0% |
| Recall | 64.2% | 81.8% |
| F1 Score | 64.6% | 82.3% |

## 🔍 Category Distribution

| Category | Count | Percentage |
|----------|-------|------------|
| Algorithmic Inefficiency | 165 | 33.7% |
| Memory Usage | 116 | 23.7% |
| CPU Overhead | 99 | 20.2% |
| Redundant Computation | 54 | 11.0% |
| I/O Inefficiency | 56 | 11.4% |

## 📖 Citation

If you use this dataset or code, please cite our paper:

```bibtex
@inproceedings{performancebugs2025,
  title={Fixing Performance Bugs Through LLM Explanations},
  author={Sijwali, Suryansh Singh and Colom, Angela Marie and Guo, Anbi and Saha, Suman},
  booktitle={Proceedings of the Conference},
  year={2025}
}
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md).

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- The Defects4J team for providing the bug dataset
- OpenAI for GPT-4o-mini access
- All contributors and reviewers

## 📧 Contact

For questions or issues, please:
- Open an issue on GitHub
- Contact the authors through the paper

## 🔗 Links

- [Paper](https://arxiv.org/abs/your-paper-id)
- [Defects4J](https://github.com/rjust/defects4j)
