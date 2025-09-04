
# Model Comparison Report: Fine-tuned vs Base GPT-4o-mini

## Executive Summary

This report compares the performance of the fine-tuned GPT-4o-mini model against
the base (no fine-tuning) GPT-4o-mini model for performance bug detection and
explanation generation, evaluated on the 98-bug held-out test set (20% of the
490-bug curated dataset across 17 Defects4J projects).

## Model Performance Overview (Paper Table VI)

| Model | Accuracy (%) | Precision (%) | Recall (%) | F1 Score (%) |
|-------|--------------|---------------|------------|--------------|
| Fine-tuned LLM (Proposed)   | 83.7 | 83.0 | 81.8 | 82.3 |
| Base LLM (No Fine-tuning)   | 67.3 | 65.1 | 64.2 | 64.6 |

## Improvement Analysis

### Overall Improvements (Fine-tuned − Base)
- **Accuracy**: +16.4 points
- **Precision**: +17.9 points
- **Recall**: +17.6 points
- **F1 Score**: +17.7 points

### Category-Level Detection Rates (Fine-tuned, Paper Table II)

| Category | Bug Count | Detected | Detection Rate (%) | Match Rate (%) |
|----------|-----------|----------|--------------------|----------------|
| Algorithmic Inefficiency | 33 | 30 | 90.9 | 93.3 |
| Memory Usage             | 23 | 19 | 82.6 | 89.5 |
| Redundant Computation    | 11 |  9 | 81.8 | 88.9 |
| CPU Overhead             | 20 | 16 | 80.0 | 87.5 |
| I/O Inefficiency         | 11 |  8 | 72.7 | 87.5 |
| **Overall**              | **98** | **82** | **83.7** | **90.2** |

## Detailed Analysis

### Best Performing Category
**Algorithmic Inefficiency** — highest recall (91%) and F1 (87.9%). The most common
category in the dataset (33.7%) and the model's strongest area.

### Most Challenging Category
**I/O Inefficiency** — lowest detection rate (72.7%) and F1 (77.3%). Bugs appear in
larger files (avg. 290 lines) with subtle resource-handling patterns.

### Dataset Characteristics
- **Total Test Cases**: 98 (20% holdout from 490 bugs)
- **Training Set**: 392 bugs (80% of 490) across 17 Defects4J projects
- **Five Categories**: Algorithmic Inefficiency, Memory Usage, Redundant Computation,
  CPU Overhead, I/O Inefficiency

## Key Findings

### Strengths of Fine-tuned Model
1. **Substantially Improved Accuracy**: +16.4-point gain over the base model
2. **Enhanced Explanation Quality**: 90.2% report match rate, indicating generated
   explanations align well with original developer bug reports
3. **Consistent Gains Across Categories**: Improvements observed in every one of the
   five performance bug categories

### Areas for Further Improvement
1. **I/O Inefficiency Detection**: Lower detection rate suggests need for more
   labeled I/O examples and structural cues (e.g., interprocedural data flow)
2. **Algorithmic Inefficiency vs. CPU Overhead**: Categories are frequently confused
   because inefficient algorithms often produce CPU overhead
3. **Larger Datasets**: Test on more diverse datasets beyond Defects4J for stronger
   generalization claims

## Recommendations

### For Production Deployment
1. **Use Fine-tuned Model**: 16.4-point accuracy gain justifies deployment
2. **Monitor Performance**: Track per-category accuracy continuously in production
3. **Feedback Loop**: Implement developer feedback collection for ongoing refinement

### For Future Development
1. **Targeted Data Augmentation**: More examples for I/O Inefficiency and Redundant
   Computation (the smallest categories)
2. **Boundary Refinement**: Stronger contrastive examples to distinguish algorithmic
   from CPU-overhead bugs
3. **Human Evaluation**: Add readability/comprehensibility studies for explanations

## Conclusion

The fine-tuned GPT-4o-mini model achieves 83.7% accuracy vs 67.3% for the base
model — a 16.4-point gain — with consistent improvements across precision, recall,
and F1. Results validate that task-specific fine-tuning with contextual signals
(code diffs, developer comments, bug reports) substantially improves performance
bug detection and explanation generation.

**Recommendation**: Deploy the fine-tuned model for production use.
