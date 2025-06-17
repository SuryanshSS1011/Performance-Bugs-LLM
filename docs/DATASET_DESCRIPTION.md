# Dataset Description

This document provides a detailed description of the Performance Bugs dataset containing 490 real-world performance bugs from the Defects4J benchmark.

## Overview

- **Total Bugs**: 490
- **Source**: Defects4J v2.0.0 (17 Java projects)
- **Time Period**: Bugs span multiple years of development
- **Languages**: Java
- **Format**: JSON and CSV

## Dataset Statistics

### Category Distribution

| Category | Count | Percentage | Description |
|----------|-------|------------|-------------|
| Algorithmic Inefficiency | 165 | 33.7% | Inefficient algorithms or data structures |
| Memory Usage | 116 | 23.7% | Excessive memory allocations |
| CPU Overhead | 99 | 20.2% | Unnecessary CPU cycles |
| Redundant Computation | 54 | 11.0% | Repeated calculations |
| I/O Inefficiency | 56 | 11.4% | Unoptimized I/O operations |

### Project Distribution

| Project | Bug Count | Domain | Repository |
|---------|-----------|--------|------------|
| Chart | 26 | Charting library | [JFreeChart](https://github.com/jfree/jfreechart) |
| Closure | 133* | JavaScript compiler | [Closure Compiler](https://github.com/google/closure-compiler) |
| Codec | 18 | Encoding/decoding | [Commons Codec](https://github.com/apache/commons-codec) |
| Collections | 28 | Data structures | [Commons Collections](https://github.com/apache/commons-collections) |
| Compress | 47 | Compression | [Commons Compress](https://github.com/apache/commons-compress) |
| Csv | 16 | CSV processing | [Commons CSV](https://github.com/apache/commons-csv) |
| Gson | 18 | JSON library | [Gson](https://github.com/google/gson) |
| JacksonCore | 26 | JSON processor | [Jackson Core](https://github.com/FasterXML/jackson-core) |
| JacksonDatabind | 112* | Data binding | [Jackson Databind](https://github.com/FasterXML/jackson-databind) |
| JacksonXml | 6 | XML processing | [Jackson XML](https://github.com/FasterXML/jackson-dataformat-xml) |
| Jsoup | 93* | HTML parser | [jsoup](https://github.com/jhy/jsoup) |
| JxPath | 22 | XPath library | [Commons JxPath](https://github.com/apache/commons-jxpath) |
| Lang | 65* | Language utilities | [Commons Lang](https://github.com/apache/commons-lang) |
| Math | 106* | Mathematics | [Commons Math](https://github.com/apache/commons-math) |
| Mockito | 38 | Mocking framework | [Mockito](https://github.com/mockito/mockito) |
| Time | 27 | Date/time library | [Joda-Time](https://github.com/JodaOrg/joda-time) |
| Cli | 5 | Command line | [Commons CLI](https://github.com/apache/commons-cli) |

*Projects with performance bugs distributed across 24-35 range

## Data Fields

Each bug entry contains the following fields:

### Core Identifiers
- **bug_id** (string): Unique identifier in format "Project-Number" (e.g., "Chart-11")
- **project** (string): Project name from Defects4J
- **bug_number** (integer): Bug number within the project
- **dataset_index** (integer): Index in this dataset (1-490)

### Version Information
- **buggy_revision** (string): Git commit hash of the buggy version
- **fixed_revision** (string): Git commit hash of the fixed version

### Issue Tracking
- **issue_id** (string): Original issue ID from the project's tracker
- **issue_url** (string): URL to the issue in the tracker

### Code Content
- **buggy_code** (string): The buggy method/code block
- **fixed_code** (string): The fixed method/code block
- **file_path** (string): Path to the source file
- **method_name** (string): Name of the affected method
- **lines_changed** (integer): Number of lines modified

### Classification
- **category** (string): Performance bug category (see categories above)
- **original_comments** (string): Developer comments from the fix
- **llm_comments** (string): LLM-generated explanation of the bug

### Metadata
- **performance_metadata** (object): Additional performance information
  - **patterns_found** (array): Performance patterns detected
  - **complexity_change** (string): How complexity changed
  - **performance_impact** (string): Estimated impact (low/medium/high)
  - **confidence** (string): Classification confidence

## Example Entry

```json
{
  "bug_id": "Chart-11",
  "project": "Chart",
  "bug_number": 11,
  "category": "ALGORITHMIC_INEFFICIENCY",
  "buggy_revision": "e69b675c4b69d5f6328ba2c594b2f8e6f2e9c853",
  "fixed_revision": "1d31e2550b6f7b066ae2087d88be88e431035944",
  "issue_id": "CHART-234",
  "issue_url": "https://issues.apache.org/jira/browse/CHART-234",
  "buggy_code": "public void processData(List<Item> items) {\n    for (int i = 0; i < items.size(); i++) {\n        for (int j = 0; j < items.size(); j++) {\n            if (items.get(i).equals(items.get(j))) {\n                // Process duplicate\n            }\n        }\n    }\n}",
  "fixed_code": "public void processData(List<Item> items) {\n    Set<Item> seen = new HashSet<>();\n    for (Item item : items) {\n        if (!seen.add(item)) {\n            // Process duplicate\n        }\n    }\n}",
  "original_comments": "// Optimize duplicate detection",
  "llm_comments": "This performance bug involves an inefficient algorithm with O(n²) complexity. The fix improves the algorithm by using a HashSet for O(1) lookups, reducing the time complexity to O(n) and making the code more efficient.",
  "performance_metadata": {
    "category": "ALGORITHMIC_INEFFICIENCY",
    "patterns_found": ["nested loops", "quadratic complexity"],
    "complexity_change": "O(n²) to O(n)",
    "performance_impact": "high",
    "files_changed": 1,
    "methods_changed": 1,
    "confidence": "high"
  },
  "file_path": "src/main/java/org/jfree/chart/ChartPanel.java",
  "method_name": "processData(List<Item>)",
  "lines_changed": 15,
  "dataset_index": 11
}
```

## Category Details

### 1. Algorithmic Inefficiency (33.7%)
- **Common Patterns**:
  - Nested loops with O(n²) or worse complexity
  - Linear search instead of hash-based lookup
  - Inefficient sorting algorithms
  - Poor choice of data structures
- **Typical Fixes**:
  - Replace nested loops with single pass algorithms
  - Use HashMap/HashSet for O(1) lookups
  - Switch to efficient library sorting methods
  - Choose appropriate data structures

### 2. Memory Usage (23.7%)
- **Common Patterns**:
  - String concatenation in loops
  - Creating unnecessary objects
  - Not specifying initial collection capacity
  - Memory leaks from retained references
- **Typical Fixes**:
  - Use StringBuilder for string operations
  - Reuse objects where possible
  - Specify ArrayList/HashMap initial capacity
  - Clear references when done

### 3. CPU Overhead (20.2%)
- **Common Patterns**:
  - Autoboxing/unboxing in loops
  - Excessive synchronization
  - Using Integer instead of int
  - Reflection in performance-critical code
- **Typical Fixes**:
  - Use primitive types
  - Minimize synchronization scope
  - Cache reflection results
  - Avoid unnecessary type conversions

### 4. Redundant Computation (11.0%)
- **Common Patterns**:
  - Calling same method multiple times
  - Recalculating invariant values in loops
  - Not caching expensive computations
  - Duplicate condition checks
- **Typical Fixes**:
  - Store method results in variables
  - Move invariant code outside loops
  - Implement caching/memoization
  - Consolidate condition checks

### 5. I/O Inefficiency (11.4%)
- **Common Patterns**:
  - Unbuffered file operations
  - Reading/writing byte by byte
  - Excessive flushing
  - Not using batch operations
- **Typical Fixes**:
  - Use BufferedReader/BufferedWriter
  - Read/write in chunks
  - Flush only when necessary
  - Batch database operations

## Usage Guidelines

### Loading the Dataset

```python
import json
import pandas as pd

# Load full dataset
with open('performance_bugs_490.json', 'r') as f:
    bugs = json.load(f)

# Load as DataFrame
df = pd.read_csv('performance_bugs_490.csv')
```

### Filtering Examples

```python
# Get bugs from a specific project
chart_bugs = [b for b in bugs if b['project'] == 'Chart']

# Get high-impact bugs
high_impact = [b for b in bugs 
               if b['performance_metadata']['performance_impact'] == 'high']

# Get bugs with specific patterns
nested_loop_bugs = [b for b in bugs 
                    if 'nested loops' in b['performance_metadata']['patterns_found']]
```

### Statistical Analysis

```python
# Category distribution
category_dist = df['category'].value_counts()

# Average lines changed by category
avg_changes = df.groupby('category')['lines_changed'].mean()

# Project complexity
project_stats = df.groupby('project').agg({
    'lines_changed': ['mean', 'sum'],
    'bug_id': 'count'
})
```

## Data Quality

### Validation Process
1. All bugs verified to be from Defects4J
2. Code changes manually inspected for performance relevance
3. Categories assigned based on established patterns
4. LLM comments reviewed for accuracy

### Known Limitations
- Focus on Java-specific performance patterns
- Some bugs may have multiple applicable categories
- Performance impact estimates are relative, not absolute measurements
- Dataset reflects bugs found and fixed, not all existing bugs

## Ethical Considerations

- All code is from open-source projects with appropriate licenses
- Bug fixes represent collaborative community efforts
- No personal developer information is included
- Dataset is for research and educational purposes

## Citation

If you use this dataset, please cite:

```bibtex
@inproceedings{sijwali2024fixing,
  title={Fixing Performance Bugs Through LLM Explanations},
  author={Sijwali, Suryansh Singh and Colom, Angela Marie and Guo, Anbi and Saha, Suman},
  booktitle={Proceedings of the Conference},
  year={2024}
}

@inproceedings{just2014defects4j,
  title={Defects4J: A database of existing faults to enable controlled testing studies for Java programs},
  author={Just, René and Jalali, Darioush and Ernst, Michael D},
  booktitle={Proceedings of ISSTA},
  year={2014}
}
```

## Updates and Versions

- **v1.0** (2024): Initial release with 490 bugs
- Future versions may include:
  - Additional performance bug categories
  - Bugs from more recent Defects4J versions
  - Cross-language performance bugs
  - Automated performance measurements