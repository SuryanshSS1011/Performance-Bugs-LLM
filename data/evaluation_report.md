
# Performance Bug Detection Evaluation Report

## Overall Performance Metrics

### Detection Performance
- **Detection Accuracy**: 83.7%
- **Precision**: 83.0%
- **Recall**: 81.8%
- **F1 Score**: 82.3%

### Explanation Quality
- **Report Match Rate**: 90.2%
- **Root Cause Accuracy**: 87.4%
- **Technical Precision**: 81.5%
- **Impact Assessment Quality**: 78.9%
- **Overall Quality Score**: 84.1%

## Comparison with Base Model

| Metric | Base GPT-4o-mini | Fine-tuned GPT-4o-mini | Improvement |
|--------|------------------|------------------------|-------------|
| Accuracy | 67.3% | 83.7% | +16.4% |
| Precision | 65.1% | 83.0% | +17.9% |
| Recall | 64.2% | 81.8% | +17.6% |
| F1 Score | 64.6% | 82.3% | +17.7% |

## Category-Level Performance

### Bug Detection and Report Match Rates by Category

| Bug Type | Bug Count | Detected | Detection Rate (%) | Report Match | Match Rate (%) |
|----------|-----------|----------|--------------------|--------------| ---------------|
| Algorithmic Inefficiency | 33 | 30 | 90.9 | 28 | 93.3 |
| Memory Usage | 23 | 19 | 82.6 | 17 | 89.5 |
| Redundant Computation | 11 | 9 | 81.8 | 8 | 88.9 |
| CPU Overhead | 20 | 16 | 80.0 | 14 | 87.5 |
| I/O Inefficiency | 11 | 8 | 72.7 | 7 | 87.5 |
| **Overall** | **98** | **82** | **83.7** | **74** | **90.2** |

### Per-Category Precision / Recall / F1

| Category | Support | Precision (%) | Recall (%) | F1 (%) |
|----------|---------|---------------|------------|--------|
| Algorithmic Inefficiency | 33 | 85.0 | 91.0 | 87.9 |
| Memory Usage | 23 | 87.0 | 83.0 | 85.0 |
| Redundant Computation | 11 | 75.0 | 82.0 | 78.4 |
| CPU Overhead | 20 | 86.0 | 80.0 | 82.9 |
| I/O Inefficiency | 11 | 82.0 | 73.0 | 77.3 |

## Bug Detection Accuracy by Project Category

| Project Category | Count | Overall Acc. (%) | Algo. Ineff. | Memory | Redundant | CPU | I/O |
|------------------|-------|------------------|--------------|--------|-----------|-----|-----|
| Data Processing Libraries | 19 | 89.5 | 85.7 | 80.0 | 100.0 | 100.0 | 0.0 |
| Mathematical Libraries | 17 | 82.4 | 80.0 | 75.0 | 100.0 | 75.0 | 100.0 |
| Text Processing | 18 | 83.3 | 100.0 | 80.0 | 50.0 | 100.0 | 100.0 |
| XML/JSON Processing | 18 | 77.8 | 100.0 | 80.0 | 50.0 | 75.0 | 100.0 |
| General Utilities | 26 | 84.6 | 100.0 | 100.0 | 100.0 | 66.7 | 71.4 |
| **Overall** | **98** | **83.7** | **89.5** | **82.6** | **81.8** | **80.0** | **72.7** |

## Analysis and Insights

### Strengths
- Strong performance on Algorithmic Inefficiency (highest F1 = 87.9%), the most common category
- Memory Usage shows highest precision (87%), indicating reliable labeling when flagged
- Fine-tuning yields consistent gains across all five categories vs. the base model
- 90.2% report match rate demonstrates explanations align well with original developer reports

### Areas for Improvement
- I/O Inefficiency has the lowest detection rate (72.7%) and F1 (77.3%) — bugs appear in larger files (avg. 290 lines) with subtler patterns
- Confusion between Algorithmic Inefficiency and CPU Overhead, since inefficient algorithms often manifest as CPU overhead
- Redundant Computation precision (75%) is lower than recall (82%), suggesting over-prediction of this category

### Recommendations
1. Add more labeled I/O examples and structural cues (interprocedural data flow, API usage patterns)
2. Refine boundary between algorithmic and CPU-overhead categories with stronger contrastive examples
3. Test on larger, more diverse datasets beyond Defects4J
4. Add human-centered evaluation for explanation readability/comprehensibility

## Conclusion

The fine-tuned GPT-4o-mini model achieves 83.7% detection accuracy and 90.2% explanation
match rate, outperforming the base model by 16.4% on accuracy. Results validate that
task-specific fine-tuning with contextual signals (code diffs, comments, bug reports)
substantially improves performance bug detection and explanation quality.
