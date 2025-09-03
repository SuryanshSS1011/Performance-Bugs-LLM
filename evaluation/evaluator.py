"""
Evaluation framework for performance bug detection and report quality.
Implements metrics from Section V.B and V.C of the paper.
"""

import json
import logging
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from sklearn.metrics import precision_recall_fscore_support, confusion_matrix, accuracy_score
import matplotlib.pyplot as plt
import seaborn as sns
from openai import OpenAI

from ..config import (
    EVALUATION_CONFIG, PAPER_RESULTS, BUG_CATEGORIES,
    RESULTS_DIR, MODEL_CONFIG
)

logger = logging.getLogger(__name__)

@dataclass
class PredictionResult:
    """Result of a single bug prediction"""
    bug_id: str
    true_category: str
    predicted_category: str
    confidence: float
    bug_report: str
    explanation: str
    fixed_code: str
    detection_correct: bool
    report_match_score: float

class PerformanceEvaluator:
    """
    Evaluates model performance on bug detection and report quality.
    Reproduces results from Tables II, III, IV, and VI of the paper.
    """
    
    def __init__(self, model_id: str, api_key: Optional[str] = None):
        self.client = OpenAI(api_key=api_key)
        self.model_id = model_id
        self.results_dir = RESULTS_DIR / "evaluation"
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
    def evaluate_model(self, test_examples: List) -> Dict:
        """
        Complete model evaluation matching paper's methodology.
        Returns comprehensive evaluation metrics.
        """
        logger.info(f"Evaluating model {self.model_id} on {len(test_examples)} examples")
        
        # Get predictions for all test examples
        predictions = []
        for example in test_examples:
            pred = self._get_prediction(example)
            predictions.append(pred)
        
        # Calculate metrics
        metrics = {
            "detection_metrics": self._calculate_detection_metrics(predictions),
            "category_metrics": self._calculate_category_metrics(predictions),
            "report_quality": self._calculate_report_quality(predictions),
            "confusion_matrix": self._generate_confusion_matrix(predictions),
            "project_breakdown": self._calculate_project_metrics(predictions)
        }
        
        # Generate visualizations
        self._generate_visualizations(metrics)
        
        # Compare with paper results
        comparison = self._compare_with_paper(metrics)
        metrics["paper_comparison"] = comparison
        
        # Save results
        self._save_results(metrics, predictions)
        
        return metrics
    
    def _get_prediction(self, example: Dict) -> PredictionResult:
        """Get model prediction for a single example"""
        try:
            # Prepare prompt
            prompt = f"Analyze this Java code for performance issues:\n```java\n{example['buggy_code']}\n```"
            
            # Get prediction from fine-tuned model
            response = self.client.chat.completions.create(
                model=self.model_id,
                messages=[
                    {"role": "system", "content": "You are a performance bug detection expert."},
                    {"role": "user", "content": prompt}
                ],
                temperature=MODEL_CONFIG["temperature"],
                max_tokens=MODEL_CONFIG["max_tokens"]
            )
            
            # Parse response
            response_text = response.choices[0].message.content
            try:
                result = json.loads(response_text)
            except:
                # Fallback parsing if not valid JSON
                result = self._parse_text_response(response_text)
            
            # Calculate report match score
            report_score = self._score_report_quality(
                result.get("bug_report", ""),
                result.get("explanation", ""),
                example
            )
            
            return PredictionResult(
                bug_id=example.get("bug_id", "unknown"),
                true_category=example["category"],
                predicted_category=result.get("category", "unknown"),
                confidence=result.get("confidence", 0.5),
                bug_report=result.get("bug_report", ""),
                explanation=result.get("explanation", ""),
                fixed_code=result.get("fixed_code", ""),
                detection_correct=(result.get("category") == example["category"]),
                report_match_score=report_score
            )
            
        except Exception as e:
            logger.error(f"Prediction failed for {example.get('bug_id')}: {e}")
            return PredictionResult(
                bug_id=example.get("bug_id", "unknown"),
                true_category=example["category"],
                predicted_category="error",
                confidence=0.0,
                bug_report="",
                explanation="",
                fixed_code="",
                detection_correct=False,
                report_match_score=0.0
            )
    
    def _parse_text_response(self, text: str) -> Dict:
        """Parse non-JSON response text"""
        result = {
            "category": "unknown",
            "bug_report": "",
            "explanation": text,
            "fixed_code": ""
        }
        
        # Try to extract category
        for cat in BUG_CATEGORIES.keys():
            if cat in text.lower():
                result["category"] = cat
                break
        
        return result
    
    def _score_report_quality(self, bug_report: str, explanation: str, 
                             ground_truth: Dict) -> float:
        """
        Score report quality using weighted criteria from paper.
        Returns score between 0 and 1.
        """
        weights = EVALUATION_CONFIG["report_quality_weights"]
        scores = {}
        
        # Root cause analysis (35%)
        scores["root_cause"] = self._score_root_cause(
            explanation, ground_truth.get("category", "")
        )
        
        # Issue identification (25%)
        scores["issue_id"] = self._score_issue_identification(
            bug_report, ground_truth
        )
        
        # Technical precision (25%)
        scores["technical"] = self._score_technical_precision(
            explanation, ground_truth
        )
        
        # Impact assessment (15%)
        scores["impact"] = self._score_impact_assessment(
            explanation, ground_truth
        )
        
        # Calculate weighted score
        total_score = sum(
            scores[key] * weights[key.replace("_", "_analysis" if key == "root_cause" else "")]
            for key in scores
        )
        
        return min(1.0, total_score)
    
    def _score_root_cause(self, explanation: str, true_category: str) -> float:
        """Score root cause analysis accuracy"""
        score = 0.0
        explanation_lower = explanation.lower()
        
        # Category-specific keywords
        category_keywords = {
            "algorithmic_inefficiency": ["o(n", "complexity", "nested", "algorithm"],
            "memory_usage": ["memory", "allocation", "garbage", "object creation"],
            "redundant_computation": ["redundant", "repeated", "cache", "recompute"],
            "cpu_overhead": ["cpu", "boxing", "synchroniz", "thread"],
            "io_inefficiency": ["i/o", "buffer", "file", "stream"]
        }
        
        if true_category in category_keywords:
            keywords = category_keywords[true_category]
            matches = sum(1 for kw in keywords if kw in explanation_lower)
            score = matches / len(keywords)
        
        return score
    
    def _score_issue_identification(self, bug_report: str, ground_truth: Dict) -> float:
        """Score issue identification accuracy"""
        if not bug_report:
            return 0.0
        
        # Check if key issue terms are mentioned
        score = 0.0
        report_lower = bug_report.lower()
        
        if "performance" in report_lower:
            score += 0.3
        if ground_truth["category"].replace("_", " ") in report_lower:
            score += 0.4
        if any(word in report_lower for word in ["bug", "issue", "problem"]):
            score += 0.3
        
        return min(1.0, score)
    
    def _score_technical_precision(self, explanation: str, ground_truth: Dict) -> float:
        """Score technical precision of explanation"""
        score = 0.0
        
        # Check for technical terms and accuracy
        technical_terms = [
            "time complexity", "space complexity", "big o",
            "memory leak", "buffer", "cache", "optimization"
        ]
        
        explanation_lower = explanation.lower()
        for term in technical_terms:
            if term in explanation_lower:
                score += 0.15
        
        # Check for code-specific mentions
        if "method" in explanation_lower or "function" in explanation_lower:
            score += 0.1
        if "loop" in explanation_lower or "iteration" in explanation_lower:
            score += 0.1
        
        return min(1.0, score)
    
    def _score_impact_assessment(self, explanation: str, ground_truth: Dict) -> float:
        """Score impact assessment quality"""
        score = 0.0
        explanation_lower = explanation.lower()
        
        # Check for performance impact mentions
        impact_terms = [
            "faster", "slower", "improvement", "reduction",
            "increase", "decrease", "%", "times", "x"
        ]
        
        for term in impact_terms:
            if term in explanation_lower:
                score += 0.2
        
        return min(1.0, score)
    
    def _calculate_detection_metrics(self, predictions: List[PredictionResult]) -> Dict:
        """Calculate detection accuracy metrics (Table II)"""
        y_true = [p.true_category for p in predictions]
        y_pred = [p.predicted_category for p in predictions]
        
        # Overall metrics
        accuracy = accuracy_score(y_true, y_pred)
        
        # Per-category metrics
        categories = list(BUG_CATEGORIES.keys())
        category_metrics = {}
        
        for category in categories:
            cat_true = [1 if t == category else 0 for t in y_true]
            cat_pred = [1 if p == category else 0 for p in y_pred]
            
            if sum(cat_true) > 0:  # Only if category exists in test set
                precision, recall, f1, _ = precision_recall_fscore_support(
                    cat_true, cat_pred, average='binary', zero_division=0
                )
                
                detected = sum(1 for t, p in zip(y_true, y_pred) 
                             if t == category and p == category)
                total = sum(1 for t in y_true if t == category)
                
                category_metrics[category] = {
                    "detected": detected,
                    "total": total,
                    "detection_rate": detected / total if total > 0 else 0,
                    "precision": precision,
                    "recall": recall,
                    "f1_score": f1
                }
        
        # Report match rates
        report_matches = [p for p in predictions 
                         if p.report_match_score >= EVALUATION_CONFIG["quality_threshold"]]
        
        return {
            "overall_accuracy": accuracy,
            "overall_detection_rate": len([p for p in predictions if p.detection_correct]) / len(predictions),
            "overall_report_match_rate": len(report_matches) / len(predictions),
            "by_category": category_metrics
        }
    
    def _calculate_category_metrics(self, predictions: List[PredictionResult]) -> Dict:
        """Calculate per-category precision, recall, F1 (Figure 3)"""
        y_true = [p.true_category for p in predictions]
        y_pred = [p.predicted_category for p in predictions]
        
        categories = list(BUG_CATEGORIES.keys())
        labels = [i for i, cat in enumerate(categories)]
        
        # Convert categories to numeric labels
        y_true_numeric = [categories.index(y) if y in categories else -1 for y in y_true]
        y_pred_numeric = [categories.index(y) if y in categories else -1 for y in y_pred]
        
        # Calculate metrics
        precision, recall, f1, support = precision_recall_fscore_support(
            y_true_numeric, y_pred_numeric, labels=labels, average=None, zero_division=0
        )
        
        # Overall metrics
        precision_avg, recall_avg, f1_avg, _ = precision_recall_fscore_support(
            y_true_numeric, y_pred_numeric, labels=labels, average='weighted', zero_division=0
        )
        
        metrics = {
            "categories": categories,
            "precision": precision.tolist(),
            "recall": recall.tolist(),
            "f1_score": f1.tolist(),
            "support": support.tolist(),
            "overall": {
                "precision": precision_avg,
                "recall": recall_avg,
                "f1_score": f1_avg
            }
        }
        
        return metrics
    
    def _calculate_report_quality(self, predictions: List[PredictionResult]) -> Dict:
        """Calculate report quality metrics"""
        scores = [p.report_match_score for p in predictions]
        
        return {
            "mean_score": np.mean(scores),
            "std_score": np.std(scores),
            "min_score": np.min(scores),
            "max_score": np.max(scores),
            "above_threshold": sum(1 for s in scores 
                                 if s >= EVALUATION_CONFIG["quality_threshold"]),
            "threshold": EVALUATION_CONFIG["quality_threshold"]
        }
    
    def _generate_confusion_matrix(self, predictions: List[PredictionResult]) -> np.ndarray:
        """Generate confusion matrix (Table III)"""
        y_true = [p.true_category for p in predictions]
        y_pred = [p.predicted_category for p in predictions]
        
        categories = list(BUG_CATEGORIES.keys())
        cm = confusion_matrix(y_true, y_pred, labels=categories)
        
        return cm.tolist()
    
    def _calculate_project_metrics(self, predictions: List[PredictionResult]) -> Dict:
        """Calculate metrics by project (Table IV)"""
        # Group predictions by project (extracted from bug_id)
        by_project = {}
        for pred in predictions:
            # Extract project name from bug_id (e.g., "Chart-11" -> "Chart")
            project = pred.bug_id.split('-')[0] if '-' in pred.bug_id else "Unknown"
            
            if project not in by_project:
                by_project[project] = []
            by_project[project].append(pred)
        
        # Calculate metrics for each project
        project_metrics = {}
        for project, preds in by_project.items():
            if preds:
                accuracy = sum(1 for p in preds if p.detection_correct) / len(preds)
                project_metrics[project] = {
                    "total_bugs": len(preds),
                    "accuracy": accuracy,
                    "by_category": self._get_project_category_accuracy(preds)
                }
        
        return project_metrics
    
    def _get_project_category_accuracy(self, predictions: List[PredictionResult]) -> Dict:
        """Get per-category accuracy for a project"""
        by_category = {}
        for cat in BUG_CATEGORIES.keys():
            cat_preds = [p for p in predictions if p.true_category == cat]
            if cat_preds:
                correct = sum(1 for p in cat_preds if p.detection_correct)
                by_category[cat] = {
                    "count": len(cat_preds),
                    "accuracy": correct / len(cat_preds)
                }
        return by_category
    
    def _generate_visualizations(self, metrics: Dict):
        """Generate visualizations matching paper's figures"""
        # Figure 3: Per-category performance
        self._plot_category_performance(metrics["category_metrics"])
        
        # Confusion matrix heatmap
        self._plot_confusion_matrix(metrics["confusion_matrix"])
        
        # Distribution chart
        self._plot_distribution(metrics["detection_metrics"])
    
    def _plot_category_performance(self, category_metrics: Dict):
        """Plot precision, recall, F1 by category (Figure 3)"""
        fig, ax = plt.subplots(figsize=(10, 6))
        
        categories = category_metrics["categories"]
        x = np.arange(len(categories))
        width = 0.25
        
        precision = category_metrics["precision"]
        recall = category_metrics["recall"]
        f1 = category_metrics["f1_score"]
        
        ax.bar(x - width, precision, width, label='Precision', color='#2E86AB')
        ax.bar(x, recall, width, label='Recall', color='#A23B72')
        ax.bar(x + width, f1, width, label='F1 Score', color='#F18F01')
        
        ax.set_xlabel('Bug Category')
        ax.set_ylabel('Score')
        ax.set_title('Performance Metrics by Bug Category')
        ax.set_xticks(x)
        ax.set_xticklabels([cat.replace('_', '\n') for cat in categories], rotation=0)
        ax.legend()
        ax.grid(axis='y', alpha=0.3)
        
        # Add support counts
        for i, (cat, support) in enumerate(zip(categories, category_metrics["support"])):
            ax.text(i, 1.05, f'count: {support}', ha='center', fontsize=9)
        
        plt.tight_layout()
        plt.savefig(self.results_dir / "category_performance.png", dpi=300)
        plt.close()
    
    def _plot_confusion_matrix(self, cm: List):
        """Plot confusion matrix heatmap"""
        fig, ax = plt.subplots(figsize=(8, 6))
        
        categories = list(BUG_CATEGORIES.keys())
        cm_array = np.array(cm)
        
        sns.heatmap(cm_array, annot=True, fmt='d', cmap='Blues',
                   xticklabels=[c.replace('_', '\n') for c in categories],
                   yticklabels=[c.replace('_', '\n') for c in categories],
                   ax=ax)
        
        ax.set_xlabel('Predicted Category')
        ax.set_ylabel('Actual Category')
        ax.set_title('Confusion Matrix of Bug Categories')
        
        plt.tight_layout()
        plt.savefig(self.results_dir / "confusion_matrix.png", dpi=300)
        plt.close()
    
    def _plot_distribution(self, detection_metrics: Dict):
        """Plot bug distribution chart"""
        fig, ax = plt.subplots(figsize=(10, 6))
        
        categories = []
        counts = []
        percentages = []
        
        for cat, metrics in detection_metrics["by_category"].items():
            categories.append(cat.replace('_', ' ').title())
            counts.append(metrics["total"])
            percentages.append(metrics["detection_rate"] * 100)
        
        x = np.arange(len(categories))
        
        bars = ax.bar(x, counts, color='#4A90E2')
        
        # Add percentage labels
        for i, (bar, pct) in enumerate(zip(bars, percentages)):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                   f'{pct:.1f}%', ha='center', va='bottom')
        
        ax.set_xlabel('Bug Category')
        ax.set_ylabel('Number of Bugs')
        ax.set_title('Performance Bug Distribution and Detection Rates')
        ax.set_xticks(x)
        ax.set_xticklabels(categories, rotation=45, ha='right')
        
        plt.tight_layout()
        plt.savefig(self.results_dir / "bug_distribution.png", dpi=300)
        plt.close()
    
    def _compare_with_paper(self, metrics: Dict) -> Dict:
        """Compare results with paper's reported metrics"""
        comparison = {
            "overall": {},
            "by_category": {}
        }
        
        # Overall comparison
        paper_overall = PAPER_RESULTS["overall"]
        our_overall = metrics["detection_metrics"]
        
        comparison["overall"] = {
            "detection_rate": {
                "paper": paper_overall["detection_rate"],
                "ours": our_overall["overall_detection_rate"],
                "difference": our_overall["overall_detection_rate"] - paper_overall["detection_rate"]
            },
            "report_match_rate": {
                "paper": paper_overall["report_match_rate"],
                "ours": our_overall["overall_report_match_rate"],
                "difference": our_overall["overall_report_match_rate"] - paper_overall["report_match_rate"]
            }
        }
        
        # Category comparison
        paper_categories = PAPER_RESULTS["by_category"]
        our_categories = metrics["detection_metrics"]["by_category"]
        
        for cat in paper_categories:
            if cat in our_categories:
                comparison["by_category"][cat] = {
                    "detection_rate": {
                        "paper": paper_categories[cat]["detection"],
                        "ours": our_categories[cat]["detection_rate"],
                        "difference": our_categories[cat]["detection_rate"] - paper_categories[cat]["detection"]
                    }
                }
        
        return comparison
    
    def _save_results(self, metrics: Dict, predictions: List[PredictionResult]):
        """Save evaluation results to files"""
        # Save metrics
        with open(self.results_dir / "evaluation_metrics.json", 'w') as f:
            # Convert numpy arrays to lists for JSON serialization
            metrics_serializable = self._make_serializable(metrics)
            json.dump(metrics_serializable, f, indent=2)
        
        # Save predictions
        predictions_data = [
            {
                "bug_id": p.bug_id,
                "true_category": p.true_category,
                "predicted_category": p.predicted_category,
                "confidence": p.confidence,
                "detection_correct": p.detection_correct,
                "report_match_score": p.report_match_score,
                "bug_report": p.bug_report[:200],  # Truncate for storage
                "explanation": p.explanation[:200]
            }
            for p in predictions
        ]
        
        with open(self.results_dir / "predictions.json", 'w') as f:
            json.dump(predictions_data, f, indent=2)
        
        # Generate summary report
        self._generate_summary_report(metrics, predictions)
    
    def _make_serializable(self, obj):
        """Convert numpy arrays and other non-serializable objects for JSON"""
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, dict):
            return {k: self._make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._make_serializable(item) for item in obj]
        elif isinstance(obj, (np.integer, np.floating)):
            return float(obj)
        else:
            return obj
    
    def _generate_summary_report(self, metrics: Dict, predictions: List[PredictionResult]):
        """Generate human-readable summary report"""
        report = []
        report.append("="*80)
        report.append("PERFORMANCE BUG DETECTION EVALUATION REPORT")
        report.append("="*80)
        report.append("")
        
        # Overall metrics
        detection = metrics["detection_metrics"]
        report.append("OVERALL PERFORMANCE:")
        report.append(f"  Detection Rate: {detection['overall_detection_rate']:.1%}")
        report.append(f"  Report Match Rate: {detection['overall_report_match_rate']:.1%}")
        report.append("")
        
        # Category breakdown
        report.append("PERFORMANCE BY CATEGORY:")
        report.append("-"*40)
        for cat, cat_metrics in detection["by_category"].items():
            report.append(f"\n{cat.replace('_', ' ').title()}:")
            report.append(f"  Detected: {cat_metrics['detected']}/{cat_metrics['total']}")
            report.append(f"  Detection Rate: {cat_metrics['detection_rate']:.1%}")
            report.append(f"  Precision: {cat_metrics['precision']:.3f}")
            report.append(f"  Recall: {cat_metrics['recall']:.3f}")
            report.append(f"  F1 Score: {cat_metrics['f1_score']:.3f}")
        
        # Comparison with paper
        report.append("\n" + "="*40)
        report.append("COMPARISON WITH PAPER RESULTS:")
        report.append("-"*40)
        
        comparison = metrics["paper_comparison"]["overall"]
        report.append("\nDetection Rate:")
        report.append(f"  Paper: {comparison['detection_rate']['paper']:.1%}")
        report.append(f"  Ours: {comparison['detection_rate']['ours']:.1%}")
        report.append(f"  Difference: {comparison['detection_rate']['difference']:+.1%}")
        
        report.append("\nReport Match Rate:")
        report.append(f"  Paper: {comparison['report_match_rate']['paper']:.1%}")
        report.append(f"  Ours: {comparison['report_match_rate']['ours']:.1%}")
        report.append(f"  Difference: {comparison['report_match_rate']['difference']:+.1%}")
        
        # Save report
        report_text = "\n".join(report)
        with open(self.results_dir / "evaluation_report.txt", 'w') as f:
            f.write(report_text)
        
        # Also print to console
        print(report_text)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Load test data
    with open(DATASET_DIR / "test_examples.json", 'r') as f:
        test_examples = json.load(f)
    
    # Run evaluation
    evaluator = PerformanceEvaluator("ft:gpt-4o-mini:org:job-xxxxx")  # Use actual model ID
    results = evaluator.evaluate_model(test_examples)
    
    print(f"\nEvaluation complete! Results saved to {evaluator.results_dir}")