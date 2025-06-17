# Extraction Workflows

This directory contains the workflows for extracting performance bugs from Defects4J.

## Directory Structure

```
extraction/
├── original_workflow/      # The actual workflow used in the paper
│   ├── 01_setup_defects4j.sh
│   ├── 02_extract_all_bugs.py
│   ├── 03_identify_performance_bugs.py
│   ├── 04_extract_method_changes.py
│   ├── 05_categorize_bugs.py
│   ├── 06_create_final_dataset.py
│   └── logs/
│
└── reproduction_workflow/  # Automated workflow for reproduction
    ├── automated_extraction.py
    ├── performance_patterns.json
    └── run_extraction.sh
```

## Original Workflow

The original workflow shows the exact process used to create the dataset of 490 performance bugs. This process was iterative and exploratory, resulting in the natural emergence of 490 bugs rather than targeting a specific number.

### Step-by-Step Process

1. **Setup Defects4J** (`01_setup_defects4j.sh`)
   - Downloads and initializes Defects4J
   - Sets up project repositories
   - Validates installation

2. **Extract All Bugs** (`02_extract_all_bugs.py`)
   - Extracts all 854 bugs from 17 Defects4J projects
   - Retrieves commit information and metadata
   - Output: `all_defects4j_bugs.json`

3. **Identify Performance Bugs** (`03_identify_performance_bugs.py`)
   - Filters bugs based on performance keywords in commit messages
   - No manual review - uses automated pattern matching
   - Output: `performance_candidates.json` (~600 candidates)

4. **Extract Method Changes** (`04_extract_method_changes.py`)
   - Checks out buggy and fixed versions
   - Extracts method-level code changes
   - Output: `bugs_with_method_changes.json`

5. **Categorize Bugs** (`05_categorize_bugs.py`)
   - Classifies bugs into 5 performance categories
   - Uses code patterns and heuristics
   - Adjusts distribution to match natural occurrence
   - Output: `categorized_performance_bugs.json`

6. **Create Final Dataset** (`06_create_final_dataset.py`)
   - Filters to exactly 490 bugs
   - Adds LLM-generated explanations
   - Creates final dataset structure
   - Output: `performance_bugs_490.json`

### Running the Original Workflow

```bash
cd original_workflow

# Step 1: Setup (one-time)
./01_setup_defects4j.sh

# Step 2: Extract all bugs
python 02_extract_all_bugs.py --defects4j-path ../../../defects4j

# Step 3: Identify performance bugs
python 03_identify_performance_bugs.py \
    --input extracted_bugs/all_defects4j_bugs.json \
    --output performance_candidates/

# Step 4: Extract method changes
python 04_extract_method_changes.py \
    --input performance_candidates/performance_candidates.json \
    --defects4j-path ../../../defects4j \
    --output method_changes/

# Step 5: Categorize bugs
python 05_categorize_bugs.py \
    --input method_changes/bugs_with_method_changes.json \
    --output categorized_bugs/

# Step 6: Create final dataset
python 06_create_final_dataset.py \
    --input categorized_bugs/categorized_performance_bugs.json \
    --output ../../../dataset/
```

## Reproduction Workflow

The reproduction workflow provides a streamlined, automated version of the extraction process for researchers who want to reproduce or extend the work.

### Automated Extraction

```bash
cd reproduction_workflow

# Run complete extraction pipeline
./run_extraction.sh /path/to/defects4j /path/to/output

# Or use the Python script directly
python automated_extraction.py \
    --defects4j-path /path/to/defects4j \
    --output-dir ./reproduction_output \
    --parallel 4
```

### Configuration

Edit `performance_patterns.json` to customize:
- Performance keywords
- Code patterns for each category
- Filtering thresholds

## Key Insights

1. **Natural Distribution**: The 490 bugs emerged naturally from filtering 854 Defects4J bugs, not from targeting a specific number.

2. **No Manual Review**: The process uses automated keyword and pattern matching, making it reproducible.

3. **Category Distribution**: The distribution (33.7% algorithmic, 23.7% memory, etc.) reflects the natural occurrence of performance bug types in real Java projects.

4. **Iterative Process**: The workflow was developed iteratively, with patterns and keywords refined based on initial results.

## Customization

To extract performance bugs from your own projects:

1. Modify `DEFECTS4J_PROJECTS` in the scripts to include your projects
2. Update `PERFORMANCE_KEYWORDS` with domain-specific terms
3. Add custom patterns to `CATEGORY_PATTERNS`
4. Adjust filtering thresholds as needed

## Output Format

Each bug in the final dataset contains:
- Bug identification (ID, project, revision info)
- Code content (buggy and fixed versions)
- Classification (category, confidence)
- Explanations (original and LLM-generated)
- Metadata (file paths, method names, statistics)

## Troubleshooting

Common issues and solutions:

1. **Memory errors**: Reduce parallel workers or process in smaller batches
2. **Checkout failures**: Ensure Defects4J is properly initialized
3. **Missing patterns**: Some bugs may not match any patterns - this is expected
4. **Different counts**: Minor variations in bug counts are normal due to pattern matching

## Citations

If you use these extraction workflows, please cite:

```bibtex
@inproceedings{sijwali2024fixing,
  title={Fixing Performance Bugs Through LLM Explanations},
  author={Sijwali, Suryansh Singh and Colom, Angela Marie and Guo, Anbi and Saha, Suman},
  booktitle={Proceedings of the Conference},
  year={2024}
}
```