"""
Interactive demo interface for performance bug detection and explanation.
Provides a command-line interface for testing the system.
"""

import json
import logging
import sys
from pathlib import Path
from typing import Dict, Optional
import argparse

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from explanation.explanation_generator import PerformanceExplanationGenerator
from processing.method_extractor import MethodLevelExtractor, PerformancePatternAnalyzer

logger = logging.getLogger(__name__)

class PerformanceBugDetector:
    """
    Interactive demo for performance bug detection and explanation.
    Implements the complete pipeline from the paper.
    """
    
    def __init__(self, model_path: Optional[str] = None):
        self.explanation_generator = PerformanceExplanationGenerator()
        self.method_extractor = MethodLevelExtractor()
        self.pattern_analyzer = PerformancePatternAnalyzer()
        self.model_path = model_path
        
    def analyze_code(self, code: str, language: str = "java") -> Dict:
        """
        Analyze code snippet for performance issues.
        Returns detection results and explanations.
        """
        
        results = {
            'detected_issues': [],
            'category': None,
            'explanation': None,
            'suggestions': [],
            'confidence': 0.0
        }
        
        # Detect performance patterns
        patterns = self._detect_patterns(code)
        
        if patterns:
            # Categorize the issue
            category = self._categorize_issue(patterns, code)
            results['category'] = category
            
            # Generate explanation
            explanation = self._generate_explanation(code, category, patterns)
            results['explanation'] = explanation
            
            # Generate fix suggestions
            suggestions = self._generate_suggestions(category, patterns)
            results['suggestions'] = suggestions
            
            # Calculate confidence
            results['confidence'] = self._calculate_confidence(patterns, category)
            results['detected_issues'] = patterns
        
        return results
    
    def analyze_patch(self, patch_content: str) -> Dict:
        """
        Analyze a patch/diff for performance improvements.
        """
        
        # Extract method-level changes
        methods = self.method_extractor.extract_patch_methods(patch_content)
        
        results = {
            'total_methods_changed': len(methods),
            'performance_improvements': [],
            'categories_detected': set(),
            'overall_impact': None
        }
        
        for method in methods:
            # Analyze each method change
            category = self.pattern_analyzer.categorize_method_change(method)
            summary = self.pattern_analyzer.generate_method_summary(method)
            
            results['performance_improvements'].append({
                'method': method.method_name,
                'category': category,
                'patterns': method.performance_patterns,
                'complexity_change': method.complexity_change,
                'improvement_type': summary['improvement_type']
            })
            
            results['categories_detected'].add(category)
        
        # Assess overall impact
        if results['performance_improvements']:
            results['overall_impact'] = self._assess_overall_impact(results['performance_improvements'])
        
        return results
    
    def _detect_patterns(self, code: str) -> list:
        """Detect performance anti-patterns in code"""
        
        patterns = []
        code_lower = code.lower()
        
        # Check for common performance issues
        pattern_checks = {
            'nested_loops': self._check_nested_loops(code),
            'string_concatenation': self._check_string_concatenation(code),
            'inefficient_collection': self._check_inefficient_collections(code),
            'synchronization_overhead': self._check_synchronization(code),
            'unbuffered_io': self._check_unbuffered_io(code)
        }
        
        for pattern_name, detected in pattern_checks.items():
            if detected:
                patterns.append(pattern_name)
        
        return patterns
    
    def _check_nested_loops(self, code: str) -> bool:
        """Check for nested loop patterns"""
        lines = code.split('\n')
        loop_depth = 0
        max_depth = 0
        
        for line in lines:
            if 'for' in line or 'while' in line:
                loop_depth += 1
                max_depth = max(max_depth, loop_depth)
            elif '}' in line:
                loop_depth = max(0, loop_depth - 1)
        
        return max_depth >= 2
    
    def _check_string_concatenation(self, code: str) -> bool:
        """Check for string concatenation in loops"""
        return ('string' in code.lower() and '+=' in code) or ('+ "' in code and 'for' in code)
    
    def _check_inefficient_collections(self, code: str) -> bool:
        """Check for inefficient collection usage"""
        return 'arraylist' in code.lower() and ('contains' in code.lower() or 'indexof' in code.lower())
    
    def _check_synchronization(self, code: str) -> bool:
        """Check for excessive synchronization"""
        return code.lower().count('synchronized') > 1
    
    def _check_unbuffered_io(self, code: str) -> bool:
        """Check for unbuffered I/O operations"""
        return ('filereader' in code.lower() or 'filewriter' in code.lower()) and 'buffered' not in code.lower()
    
    def _categorize_issue(self, patterns: list, code: str) -> str:
        """Categorize the performance issue based on detected patterns"""
        
        if 'nested_loops' in patterns or 'inefficient_collection' in patterns:
            return 'algorithmic_inefficiency'
        elif 'string_concatenation' in patterns:
            return 'memory_usage'
        elif 'synchronization_overhead' in patterns:
            return 'cpu_overhead'
        elif 'unbuffered_io' in patterns:
            return 'io_inefficiency'
        else:
            return 'redundant_computation'
    
    def _generate_explanation(self, code: str, category: str, patterns: list) -> str:
        """Generate explanation for detected issues"""
        
        explanations = {
            'algorithmic_inefficiency': "The code contains inefficient algorithmic patterns that scale poorly with input size.",
            'memory_usage': "The code creates excessive memory allocations that could lead to garbage collection overhead.",
            'cpu_overhead': "The code introduces unnecessary CPU overhead through inefficient operations.",
            'io_inefficiency': "The code performs inefficient I/O operations that could be optimized.",
            'redundant_computation': "The code performs redundant computations that could be eliminated."
        }
        
        base_explanation = explanations.get(category, "Performance issue detected in the code.")
        
        # Add pattern-specific details
        if 'nested_loops' in patterns:
            base_explanation += " Nested loops create O(n²) complexity."
        if 'string_concatenation' in patterns:
            base_explanation += " String concatenation in loops creates many temporary objects."
        if 'unbuffered_io' in patterns:
            base_explanation += " Unbuffered I/O causes excessive system calls."
        
        return base_explanation
    
    def _generate_suggestions(self, category: str, patterns: list) -> list:
        """Generate fix suggestions based on detected issues"""
        
        suggestions = []
        
        if 'nested_loops' in patterns:
            suggestions.append("Consider using more efficient data structures like HashMap for lookups")
            suggestions.append("Try to reduce loop nesting through algorithm optimization")
        
        if 'string_concatenation' in patterns:
            suggestions.append("Use StringBuilder instead of string concatenation in loops")
            suggestions.append("Pre-allocate StringBuilder with estimated capacity")
        
        if 'inefficient_collection' in patterns:
            suggestions.append("Use HashSet for contains() operations instead of ArrayList")
            suggestions.append("Consider using appropriate collection types for your access patterns")
        
        if 'synchronization_overhead' in patterns:
            suggestions.append("Minimize synchronized blocks to reduce contention")
            suggestions.append("Consider using concurrent collections or lock-free algorithms")
        
        if 'unbuffered_io' in patterns:
            suggestions.append("Use BufferedReader/BufferedWriter for file operations")
            suggestions.append("Consider batch processing for I/O operations")
        
        return suggestions
    
    def _calculate_confidence(self, patterns: list, category: str) -> float:
        """Calculate confidence score for the detection"""
        
        # Base confidence based on number of patterns detected
        base_confidence = min(0.5 + (len(patterns) * 0.15), 0.9)
        
        # Adjust based on category clarity
        category_boost = {
            'algorithmic_inefficiency': 0.1,
            'memory_usage': 0.1,
            'io_inefficiency': 0.15,
            'cpu_overhead': 0.05,
            'redundant_computation': 0.0
        }
        
        confidence = base_confidence + category_boost.get(category, 0.0)
        
        return min(confidence, 0.95)
    
    def _assess_overall_impact(self, improvements: list) -> str:
        """Assess overall performance impact of improvements"""
        
        if not improvements:
            return "No performance impact detected"
        
        # Count improvement types
        categories = [imp['category'] for imp in improvements]
        unique_categories = len(set(categories))
        
        # Assess based on diversity and count
        if len(improvements) >= 3 or unique_categories >= 2:
            return "High - Multiple performance improvements detected"
        elif len(improvements) == 2:
            return "Medium - Moderate performance improvements"
        else:
            return "Low - Minor performance optimization"

def main():
    """Main demo interface"""
    
    parser = argparse.ArgumentParser(description="Performance Bug Detection Demo")
    parser.add_argument('--code', type=str, help="Code snippet to analyze")
    parser.add_argument('--file', type=str, help="File containing code to analyze")
    parser.add_argument('--patch', type=str, help="Patch file to analyze")
    parser.add_argument('--interactive', action='store_true', help="Run in interactive mode")
    
    args = parser.parse_args()
    
    # Initialize detector
    detector = PerformanceBugDetector()
    
    if args.interactive or (not args.code and not args.file and not args.patch):
        # Interactive mode
        print("Performance Bug Detection System - Interactive Demo")
        print("=" * 50)
        print("\nOptions:")
        print("1. Analyze code snippet")
        print("2. Analyze patch/diff")
        print("3. Exit")
        
        while True:
            choice = input("\nSelect option (1-3): ").strip()
            
            if choice == '1':
                print("\nEnter Java code (type 'END' on a new line to finish):")
                lines = []
                while True:
                    line = input()
                    if line.strip() == 'END':
                        break
                    lines.append(line)
                
                code = '\n'.join(lines)
                if code:
                    results = detector.analyze_code(code)
                    print_analysis_results(results)
            
            elif choice == '2':
                print("\nEnter patch content (type 'END' on a new line to finish):")
                lines = []
                while True:
                    line = input()
                    if line.strip() == 'END':
                        break
                    lines.append(line)
                
                patch = '\n'.join(lines)
                if patch:
                    results = detector.analyze_patch(patch)
                    print_patch_results(results)
            
            elif choice == '3':
                print("Exiting...")
                break
            
            else:
                print("Invalid option. Please select 1-3.")
    
    else:
        # Command-line mode
        if args.code:
            results = detector.analyze_code(args.code)
            print_analysis_results(results)
        
        elif args.file:
            with open(args.file, 'r') as f:
                code = f.read()
            results = detector.analyze_code(code)
            print_analysis_results(results)
        
        elif args.patch:
            with open(args.patch, 'r') as f:
                patch = f.read()
            results = detector.analyze_patch(patch)
            print_patch_results(results)

def print_analysis_results(results: Dict):
    """Print code analysis results"""
    
    print("\n" + "=" * 50)
    print("ANALYSIS RESULTS")
    print("=" * 50)
    
    if results['detected_issues']:
        print(f"\nDetected Issues: {', '.join(results['detected_issues'])}")
        print(f"Category: {results['category'].replace('_', ' ').title()}")
        print(f"Confidence: {results['confidence']:.1%}")
        
        print(f"\nExplanation:")
        print(results['explanation'])
        
        if results['suggestions']:
            print(f"\nSuggestions for improvement:")
            for i, suggestion in enumerate(results['suggestions'], 1):
                print(f"  {i}. {suggestion}")
    else:
        print("\nNo performance issues detected.")

def print_patch_results(results: Dict):
    """Print patch analysis results"""
    
    print("\n" + "=" * 50)
    print("PATCH ANALYSIS RESULTS")
    print("=" * 50)
    
    print(f"\nMethods Changed: {results['total_methods_changed']}")
    print(f"Categories Detected: {', '.join(results['categories_detected'])}")
    print(f"Overall Impact: {results['overall_impact']}")
    
    if results['performance_improvements']:
        print("\nDetailed Analysis:")
        for imp in results['performance_improvements']:
            print(f"\n  Method: {imp['method']}")
            print(f"  Category: {imp['category'].replace('_', ' ').title()}")
            print(f"  Improvement Type: {imp['improvement_type'].replace('_', ' ').title()}")
            if imp['patterns']:
                print(f"  Patterns: {', '.join(imp['patterns'])}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()