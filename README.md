# Performance Bugs Through LLM Explanations

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Defects4J](https://img.shields.io/badge/Defects4J-v3.0.1-green.svg)](https://github.com/rjust/defects4j)
![Repository Status](https://img.shields.io/badge/Status-Under%20Development-orange)

This repository contains the code, dataset, and models from our paper **["Fixing Performance Bugs Through LLM Explanations"](https://ieeexplore.ieee.org/document/11127255)** (IEEE AITest 2025). We provide tools to extract performance bugs from Defects4J, fine-tune GPT-4o-mini for performance bug detection, and evaluate the results.

🌐 **[View Project Website](https://suryanshss1011.github.io/Performance-Bugs-LLM/)** | 📊 **[Interactive Presentation](https://suryanshss1011.github.io/Performance-Bugs-LLM/presentation/presentation.html)** | 📄 **[Paper (IEEE Xplore)](https://ieeexplore.ieee.org/document/11127255)**

## 📊 Dataset Statistics

- **Total Performance Bugs**: 490
- **Projects**: 17 Defects4J projects
- **Categories**: 5 (Algorithmic, Memory, CPU, Redundant Computation, I/O)
- **Training/Test Split**: 392/98 (80/20)

## 📑 Documentation Index

### Core Components
- **[Dataset](data/)** - The 490 performance bugs and per-category training/test splits
- **[Bug Extraction](extraction/)** - Scripts to extract performance bugs from Defects4J projects
- **[Bug Categorization](categorization/)** - Classifies bugs into the five performance categories
- **[Explanation Generation](explanation/)** - Generates LLM-based explanations for each bug
- **[Model Training](models/)** - Fine-tuning code for GPT-4o-mini
- **[Evaluation Framework](evaluation/)** - Metrics, benchmarks, and model comparison
- **[Performance Validation](validation/)** - Tools to validate that fixes improve performance
- **[Notebooks](notebooks/)** - Jupyter notebooks for analysis and visualization
- **[Conference Presentation](presentation/)** - Interactive slides

### Detailed Guides
- **[Installation Guide](docs/INSTALLATION_GUIDE.md)** - Step-by-step setup instructions
- **[Usage Guide](docs/USAGE.md)** - How to use each component
- **[Dataset Description](docs/DATASET_DESCRIPTION.md)** - Detailed dataset documentation

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/SuryanshSS1011/Performance-Bugs-LLM.git
cd Performance-Bugs-LLM

# Set up the environment (creates venv and installs requirements)
./scripts/setup_environment.sh

# Run the end-to-end pipeline
python main.py
```

## 📁 Repository Structure

- **`data/`**: The 490 performance bugs dataset, training splits, and evaluation reports
- **`extraction/`**: Scripts for extracting performance bugs from Defects4J
- **`categorization/`**: Classifies bugs into the five performance categories
- **`explanation/`**: Generates LLM-based bug explanations
- **`processing/`**: Method-level code extraction
- **`models/`**: Fine-tuning code for GPT-4o-mini
- **`evaluation/`**: Evaluation metrics, comparison framework, and reports
- **`validation/`**: Code for validating performance improvements
- **`notebooks/`**: Jupyter notebooks for exploration and visualization
- **`results/visualizations/`**: Generated figures (Fig. 1–3 from the paper)
- **`scripts/`**: Setup script and figure generation
- **`docs/`**: Installation, usage, and dataset documentation
- **`ref/`**: Reference materials (technical guide; paper PDF gitignored)

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

5. **Install Defects4J** (only needed if reproducing bug extraction). Follow the
   official setup at https://github.com/rjust/defects4j and ensure the `defects4j`
   command is on your `PATH`.

## 📊 Using the Dataset

The dataset is provided as JSON:

```python
import json
from collections import Counter

with open('data/performance_bugs_490.json', 'r') as f:
    bugs = json.load(f)

print(f"Total bugs: {len(bugs)}")
print("Category distribution:", Counter(b['category'] for b in bugs))
```

Per-category training splits live in `data/training/` as JSONL files
(`train_algorithmic_inefficiency.jsonl`, etc.) plus `train_combined.jsonl` and
`test_combined.jsonl`.

## 🤖 Reproducing the Pipeline

The end-to-end pipeline is orchestrated by `main.py`:

```bash
python main.py
```

Individual stages can also be run via their modules:

- **Extraction**: `python -m extraction.defects4j_extractor`
- **Categorization**: `python -m categorization.bug_categorizer`
- **Explanation generation**: `python -m explanation.explanation_generator`
- **Fine-tuning**: `python -m models.fine_tuning_executor`
- **Evaluation**: `python -m evaluation.comprehensive_evaluator`
- **Performance validation**: `python -m validation.performance_tester`

## 📈 Regenerating Paper Figures

The three figures from the paper (Fig. 1 — category distribution, Fig. 2 — per-project
breakdown, Fig. 3 — per-category P/R/F1) can be regenerated from the published numbers:

```bash
python scripts/generate_paper_figures.py
```

Outputs are written to `results/visualizations/`.

## 📚 Documentation

- [Installation Guide](docs/INSTALLATION_GUIDE.md) - Detailed setup instructions
- [Usage Guide](docs/USAGE.md) - How to use each component
- [Dataset Description](docs/DATASET_DESCRIPTION.md) - Detailed dataset documentation
- [Technical Guide](ref/TECHNICAL_GUIDE.md) - Implementation notes and design decisions

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
@inproceedings{sijwali2025fixing,
  title={Fixing Performance Bugs Through LLM Explanations},
  author={Sijwali, Suryansh Singh and Colom, Angela Marie and Guo, Anbi and Saha, Suman},
  booktitle={2025 IEEE International Conference on Artificial Intelligence Testing (AITest)},
  year={2025},
  pages={102--109},
  doi={10.1109/AITest66680.2025.00020}
}
```

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

- [Paper (IEEE Xplore)](https://ieeexplore.ieee.org/document/11127255)
- [Defects4J](https://github.com/rjust/defects4j)
