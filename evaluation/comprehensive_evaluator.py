"""
Comprehensive evaluation module with metrics, confusion matrix, and visualization.
Implements all evaluation criteria from the paper.
"""

import json
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report, cohen_kappa_score
)
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import logging
import re
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

class PerformanceEvaluator:
    """
    Comprehensive evaluator for performance bug detection models.
    Evaluates both detection accuracy and explanation quality.
    """
    
    def __init__(self):
        self.categories = [
            'algorithmic_inefficiency',
            'memory_usage', 
            'cpu_overhead',
            'redundant_computation',
            'io_inefficiency'
        ]
        self.results = {}
        
    def evaluate_predictions(
        self,
        predictions: List[Dict],
        ground_truth: List[Dict],
        model_name: str = "model"
    ) -> Dict:
        """
        Evaluate model predictions against ground truth.
        
        Args:
            predictions: List of model predictions
            ground_truth: List of ground truth labels
            model_name: Name of the model being evaluated
            
        Returns:
            Dictionary with evaluation metrics
        """
        # Extract labels
        y_true = [gt.get('category', 'unknown') for gt in ground_truth]
        y_pred = [pred.get('category', 'unknown') for pred in predictions]
        
        # Calculate metrics
        metrics = {
            'model': model_name,
            'timestamp': datetime.now().isoformat(),
            'detection_metrics': self._calculate_detection_metrics(y_true, y_pred),
            'category_metrics': self._calculate_per_category_metrics(y_true, y_pred),
            'confusion_matrix': self._generate_confusion_matrix(y_true, y_pred),
            'report_quality': self._evaluate_report_quality(predictions, ground_truth),
            'code_fix_quality': self._evaluate_code_fixes(predictions, ground_truth)
        }
        
        # Store results
        self.results[model_name] = metrics
        
        return metrics
    
    def _calculate_detection_metrics(
        self,
        y_true: List[str],
        y_pred: List[str]
    ) -> Dict:
        """Calculate overall detection metrics"""
        return {
            'accuracy': accuracy_score(y_true, y_pred),
            'precision': precision_score(y_true, y_pred, average='weighted', zero_division=0),
            'recall': recall_score(y_true, y_pred, average='weighted', zero_division=0),
            'f1_score': f1_score(y_true, y_pred, average='weighted', zero_division=0),
            'cohen_kappa': cohen_kappa_score(y_true, y_pred),
            'total_samples': len(y_true),
            'correct_predictions': sum(1 for t, p in zip(y_true, y_pred) if t == p)
        }
    
    def _calculate_per_category_metrics(
        self,
        y_true: List[str],
        y_pred: List[str]
    ) -> Dict:
        """Calculate metrics for each bug category"""
        category_metrics = {}
        
        for category in self.categories:
            # Binary classification for this category
            y_true_binary = [1 if y == category else 0 for y in y_true]
            y_pred_binary = [1 if y == category else 0 for y in y_pred]
            
            # Skip if category not present
            if sum(y_true_binary) == 0:
                continue
            
            category_metrics[category] = {
                'precision': precision_score(y_true_binary, y_pred_binary, zero_division=0),
                'recall': recall_score(y_true_binary, y_pred_binary, zero_division=0),
                'f1_score': f1_score(y_true_binary, y_pred_binary, zero_division=0),
                'support': sum(y_true_binary),
                'predicted_count': sum(y_pred_binary)
            }
        
        return category_metrics
    
    def _generate_confusion_matrix(
        self,
        y_true: List[str],
        y_pred: List[str]
    ) -> Dict:
        """Generate confusion matrix data"""
        # Calculate confusion matrix
        cm = confusion_matrix(y_true, y_pred, labels=self.categories)
        
        # Convert to dictionary format
        cm_dict = {
            'matrix': cm.tolist(),
            'labels': self.categories,
            'normalized': (cm / cm.sum(axis=1, keepdims=True)).tolist()
        }
        
        return cm_dict
    
    def _evaluate_report_quality(
        self,
        predictions: List[Dict],
        ground_truth: List[Dict]
    ) -> Dict:
        """
        Evaluate the quality of bug report explanations.
        Based on paper's criteria: root cause, identification, precision, impact.
        """
        quality_scores = []
        
        for pred, truth in zip(predictions, ground_truth):
            pred_explanation = pred.get('explanation', '')
            truth_explanation = truth.get('explanation', '')
            
            if not pred_explanation or not truth_explanation:
                continue
            
            # Calculate quality score components
            score = {
                'root_cause': self._score_root_cause(pred_explanation, truth_explanation),
                'issue_identification': self._score_identification(pred_explanation, truth_explanation),
                'technical_precision': self._score_precision(pred_explanation, truth_explanation),
                'impact_assessment': self._score_impact(pred_explanation, truth_explanation)
            }
            
            # Weighted average (based on paper weights)
            weighted_score = (
                score['root_cause'] * 0.35 +
                score['issue_identification'] * 0.25 +
                score['technical_precision'] * 0.25 +
                score['impact_assessment'] * 0.15
            )
            
            score['weighted_score'] = weighted_score
            score['is_match'] = weighted_score >= 0.75  # Threshold from paper
            quality_scores.append(score)
        
        if quality_scores:
            avg_scores = {
                key: np.mean([s[key] for s in quality_scores])
                for key in quality_scores[0].keys()
            }
            match_rate = sum(s['is_match'] for s in quality_scores) / len(quality_scores)
        else:
            avg_scores = {}
            match_rate = 0.0
        
        return {
            'average_scores': avg_scores,
            'match_rate': match_rate,
            'total_evaluated': len(quality_scores)
        }
    
    def _score_root_cause(self, pred: str, truth: str) -> float:
        """Score root cause analysis quality"""
        # Keywords indicating root cause analysis
        root_cause_keywords = [
            'because', 'due to', 'caused by', 'results in',
            'leads to', 'inefficient', 'unnecessary', 'redundant'
        ]
        
        pred_lower = pred.lower()
        truth_lower = truth.lower()
        
        # Check keyword presence
        pred_keywords = sum(1 for kw in root_cause_keywords if kw in pred_lower)
        truth_keywords = sum(1 for kw in root_cause_keywords if kw in truth_lower)
        
        keyword_score = min(pred_keywords / max(truth_keywords, 1), 1.0)
        
        # Similarity score
        similarity = SequenceMatcher(None, pred_lower, truth_lower).ratio()
        
        return (keyword_score + similarity) / 2
    
    def _score_identification(self, pred: str, truth: str) -> float:
        """Score issue identification accuracy"""
        # Performance issue keywords
        issue_keywords = [
            'performance', 'slow', 'memory', 'cpu', 'i/o',
            'algorithm', 'complexity', 'overhead', 'latency'
        ]
        
        pred_issues = [kw for kw in issue_keywords if kw in pred.lower()]
        truth_issues = [kw for kw in issue_keywords if kw in truth.lower()]
        
        if not truth_issues:
            return 1.0 if not pred_issues else 0.5
        
        # Calculate overlap
        overlap = len(set(pred_issues) & set(truth_issues))
        precision = overlap / len(pred_issues) if pred_issues else 0
        recall = overlap / len(truth_issues)
        
        if precision + recall == 0:
            return 0
        
        return 2 * (precision * recall) / (precision + recall)
    
    def _score_precision(self, pred: str, truth: str) -> float:
        """Score technical precision"""
        # Technical terms and patterns
        technical_patterns = [
            r'O\([^)]+\)',  # Complexity notation
            r'\d+',  # Numbers
            r'[A-Z][a-zA-Z]*(?:\.[a-zA-Z]+)*',  # Class/method names
            r'`[^`]+`',  # Code snippets
        ]
        
        pred_technical = []
        truth_technical = []
        
        for pattern in technical_patterns:
            pred_technical.extend(re.findall(pattern, pred))
            truth_technical.extend(re.findall(pattern, truth))
        
        if not truth_technical:
            return 1.0 if not pred_technical else 0.5
        
        # Similarity of technical content
        pred_set = set(pred_technical)
        truth_set = set(truth_technical)
        
        if not pred_set and not truth_set:
            return 1.0
        
        intersection = pred_set & truth_set
        union = pred_set | truth_set
        
        return len(intersection) / len(union) if union else 0
    
    def _score_impact(self, pred: str, truth: str) -> float:
        """Score impact assessment quality"""
        impact_keywords = [
            'improve', 'reduce', 'optimize', 'faster', 'efficient',
            'save', 'decrease', 'increase', 'performance'
        ]
        
        pred_impacts = sum(1 for kw in impact_keywords if kw in pred.lower())
        truth_impacts = sum(1 for kw in impact_keywords if kw in truth.lower())
        
        if truth_impacts == 0:
            return 1.0 if pred_impacts == 0 else 0.5
        
        return min(pred_impacts / truth_impacts, 1.0)
    
    def _evaluate_code_fixes(
        self,
        predictions: List[Dict],
        ground_truth: List[Dict]
    ) -> Dict:
        """Evaluate the quality of code fixes"""
        fix_scores = []
        
        for pred, truth in zip(predictions, ground_truth):
            pred_fix = pred.get('fixed_code', '')
            truth_fix = truth.get('fixed_code', '')
            
            if not pred_fix or not truth_fix:
                continue
            
            # Calculate similarity
            similarity = SequenceMatcher(None, pred_fix, truth_fix).ratio()
            
            # Check if key patterns are preserved
            is_valid = self._is_valid_fix(pred_fix)
            
            fix_scores.append({
                'similarity': similarity,
                'is_valid': is_valid,
                'is_match': similarity >= 0.8
            })
        
        if fix_scores:
            return {
                'average_similarity': np.mean([s['similarity'] for s in fix_scores]),
                'valid_fixes': sum(s['is_valid'] for s in fix_scores) / len(fix_scores),
                'match_rate': sum(s['is_match'] for s in fix_scores) / len(fix_scores)
            }
        
        return {'average_similarity': 0, 'valid_fixes': 0, 'match_rate': 0}
    
    def _is_valid_fix(self, code: str) -> bool:
        """Check if the fix is syntactically valid"""
        # Basic validation
        if not code or len(code) < 10:
            return False
        
        # Check for balanced braces
        open_braces = code.count('{')
        close_braces = code.count('}')
        
        if open_braces != close_braces:
            return False
        
        # Check for basic Java patterns
        has_method = 'public' in code or 'private' in code or 'protected' in code
        has_class = 'class' in code or 'interface' in code or has_method
        
        return has_class
    
    def plot_confusion_matrix(
        self,
        metrics: Dict,
        save_path: Optional[Path] = None
    ) -> plt.Figure:
        """Generate confusion matrix visualization"""
        cm_data = metrics['confusion_matrix']
        cm = np.array(cm_data['matrix'])
        labels = cm_data['labels']
        
        # Create figure
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # Raw counts
        sns.heatmap(
            cm, annot=True, fmt='d', cmap='Blues',
            xticklabels=labels, yticklabels=labels,
            ax=ax1
        )
        ax1.set_title('Confusion Matrix (Counts)')
        ax1.set_ylabel('True Label')
        ax1.set_xlabel('Predicted Label')
        
        # Normalized
        cm_norm = cm / cm.sum(axis=1, keepdims=True)
        sns.heatmap(
            cm_norm, annot=True, fmt='.2f', cmap='Blues',
            xticklabels=labels, yticklabels=labels,
            ax=ax2
        )
        ax2.set_title('Confusion Matrix (Normalized)')
        ax2.set_ylabel('True Label')
        ax2.set_xlabel('Predicted Label')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            logger.info(f"Saved confusion matrix to {save_path}")
        
        return fig
    
    def plot_category_performance(
        self,
        metrics: Dict,
        save_path: Optional[Path] = None
    ) -> plt.Figure:
        """Plot per-category performance metrics"""
        category_metrics = metrics['category_metrics']
        
        # Prepare data
        categories = []
        precision_scores = []
        recall_scores = []
        f1_scores = []
        
        for cat, scores in category_metrics.items():
            categories.append(cat.replace('_', ' ').title())
            precision_scores.append(scores['precision'])
            recall_scores.append(scores['recall'])
            f1_scores.append(scores['f1_score'])
        
        # Create plot
        x = np.arange(len(categories))
        width = 0.25
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        bars1 = ax.bar(x - width, precision_scores, width, label='Precision', color='#2E86AB')
        bars2 = ax.bar(x, recall_scores, width, label='Recall', color='#A23B72')
        bars3 = ax.bar(x + width, f1_scores, width, label='F1 Score', color='#F18F01')
        
        # Formatting
        ax.set_xlabel('Bug Category')
        ax.set_ylabel('Score')
        ax.set_title('Per-Category Performance Metrics')
        ax.set_xticks(x)
        ax.set_xticklabels(categories, rotation=45, ha='right')
        ax.legend()
        ax.set_ylim(0, 1.1)
        
        # Add value labels on bars
        for bars in [bars1, bars2, bars3]:
            for bar in bars:
                height = bar.get_height()
                ax.text(
                    bar.get_x() + bar.get_width()/2., height,
                    f'{height:.2f}',
                    ha='center', va='bottom', fontsize=8
                )
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            logger.info(f"Saved category performance plot to {save_path}")
        
        return fig
    
    def generate_report(
        self,
        metrics: Dict,
        output_path: Path
    ) -> str:
        """Generate comprehensive evaluation report"""
        report = []
        report.append("# Performance Bug Detection Evaluation Report")
        report.append(f"\n**Model:** {metrics['model']}")
        report.append(f"**Timestamp:** {metrics['timestamp']}")
        
        # Overall metrics
        report.append("\n## Overall Detection Metrics")
        det_metrics = metrics['detection_metrics']
        report.append(f"- **Accuracy:** {det_metrics['accuracy']:.3f}")
        report.append(f"- **Precision:** {det_metrics['precision']:.3f}")
        report.append(f"- **Recall:** {det_metrics['recall']:.3f}")
        report.append(f"- **F1 Score:** {det_metrics['f1_score']:.3f}")
        report.append(f"- **Cohen's Kappa:** {det_metrics['cohen_kappa']:.3f}")
        report.append(f"- **Total Samples:** {det_metrics['total_samples']}")
        report.append(f"- **Correct Predictions:** {det_metrics['correct_predictions']}")
        
        # Per-category metrics
        report.append("\n## Per-Category Performance")
        report.append("\n| Category | Precision | Recall | F1 Score | Support |")
        report.append("|----------|-----------|--------|----------|---------|")
        
        for cat, scores in metrics['category_metrics'].items():
            report.append(
                f"| {cat.replace('_', ' ').title()} | "
                f"{scores['precision']:.3f} | "
                f"{scores['recall']:.3f} | "
                f"{scores['f1_score']:.3f} | "
                f"{scores['support']} |"
            )
        
        # Report quality
        report.append("\n## Explanation Quality")
        rq = metrics['report_quality']
        if rq['average_scores']:
            report.append(f"- **Report Match Rate:** {rq['match_rate']:.3f}")
            report.append(f"- **Root Cause Score:** {rq['average_scores']['root_cause']:.3f}")
            report.append(f"- **Issue Identification:** {rq['average_scores']['issue_identification']:.3f}")
            report.append(f"- **Technical Precision:** {rq['average_scores']['technical_precision']:.3f}")
            report.append(f"- **Impact Assessment:** {rq['average_scores']['impact_assessment']:.3f}")
        
        # Code fix quality
        report.append("\n## Code Fix Quality")
        cf = metrics['code_fix_quality']
        report.append(f"- **Average Similarity:** {cf['average_similarity']:.3f}")
        report.append(f"- **Valid Fixes:** {cf['valid_fixes']:.3f}")
        report.append(f"- **Fix Match Rate:** {cf['match_rate']:.3f}")
        
        # Save report
        report_text = '\n'.join(report)
        with open(output_path, 'w') as f:
            f.write(report_text)
        
        logger.info(f"Saved evaluation report to {output_path}")
        return report_text
    
    def compare_with_paper(self, metrics: Dict) -> Dict:
        """Compare results with paper benchmarks"""
        paper_results = {
            'overall_accuracy': 0.837,
            'report_match_rate': 0.902,
            'category_accuracy': {
                'algorithmic_inefficiency': 0.909,
                'memory_usage': 0.826,
                'redundant_computation': 0.818,
                'cpu_overhead': 0.800,
                'io_inefficiency': 0.727
            }
        }
        
        comparison = {
            'accuracy_diff': metrics['detection_metrics']['accuracy'] - paper_results['overall_accuracy'],
            'report_diff': metrics['report_quality']['match_rate'] - paper_results['report_match_rate'],
            'category_comparison': {}
        }
        
        for cat, paper_acc in paper_results['category_accuracy'].items():
            if cat in metrics['category_metrics']:
                our_recall = metrics['category_metrics'][cat]['recall']
                comparison['category_comparison'][cat] = {
                    'our_score': our_recall,
                    'paper_score': paper_acc,
                    'difference': our_recall - paper_acc
                }
        
        return comparison


def main():
    """Example usage"""
    from config import RESULTS_DIR, VIZ_DIR
    
    # Initialize evaluator
    evaluator = PerformanceEvaluator()
    
    # Example predictions and ground truth
    predictions = [
        {'category': 'algorithmic_inefficiency', 'explanation': 'Nested loops cause O(n²) complexity'},
        {'category': 'memory_usage', 'explanation': 'String concatenation in loop creates many objects'}
    ]
    
    ground_truth = [
        {'category': 'algorithmic_inefficiency', 'explanation': 'Inefficient nested loops with O(n²) time'},
        {'category': 'memory_usage', 'explanation': 'String + operator in loop causes memory overhead'}
    ]
    
    # Evaluate
    metrics = evaluator.evaluate_predictions(predictions, ground_truth, "test_model")
    
    # Generate visualizations
    evaluator.plot_confusion_matrix(metrics, VIZ_DIR / "confusion_matrix.png")
    evaluator.plot_category_performance(metrics, VIZ_DIR / "category_performance.png")
    
    # Generate report
    evaluator.generate_report(metrics, RESULTS_DIR / "evaluation_report.md")
    
    # Compare with paper
    comparison = evaluator.compare_with_paper(metrics)
    print(f"Comparison with paper: {comparison}")


if __name__ == "__main__":
    main()