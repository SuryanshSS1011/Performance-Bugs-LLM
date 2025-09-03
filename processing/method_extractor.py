"""
Method-level diff extraction and analysis.
Implements the methodology from Section IV.A of the paper for extracting
method-level changes from performance bug fixes.
"""

import re
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import difflib

logger = logging.getLogger(__name__)

@dataclass
class MethodDiff:
    """Represents a method-level code change"""
    file_path: str
    method_name: str
    buggy_code: str
    fixed_code: str
    method_signature: str
    start_line: int
    end_line: int
    change_type: str  # 'modified', 'added', 'removed'
    complexity_change: Dict
    performance_patterns: List[str]

class MethodLevelExtractor:
    """
    Extracts method-level diffs from performance bug fixes.
    Implements the paper's approach of focusing on changed methods.
    """
    
    def __init__(self):
        # Performance improvement patterns from the paper
        self.performance_patterns = {
            'loop_optimization': [
                r'for\s*\([^)]*\)\s*\{[^}]*for\s*\([^)]*\)',  # Nested loops
                r'while\s*\([^)]*\)\s*\{[^}]*while\s*\([^)]*\)',  # Nested while loops
                r'Iterator.*hasNext.*next',  # Iterator patterns
            ],
            'algorithm_change': [
                r'ArrayList.*HashMap|HashMap.*ArrayList',  # Data structure changes
                r'Vector.*ArrayList|ArrayList.*Vector',
                r'Hashtable.*HashMap|HashMap.*Hashtable',
                r'LinkedList.*ArrayList|ArrayList.*LinkedList',
            ],
            'string_optimization': [
                r'String\s+\w+\s*=\s*""|StringBuilder',  # String concatenation
                r'\+\s*"[^"]*"|\+=\s*"[^"]*"',  # String concatenation patterns
                r'StringBuffer|StringBuilder',
            ],
            'memory_optimization': [
                r'new\s+\w+\[\]|new\s+ArrayList\(\)',  # Object creation
                r'clone\(\)|new\s+\w+\(',  # Object cloning/creation
                r'ArrayList\(\d+\)|HashMap\(\d+\)',  # Sized collections
            ],
            'io_optimization': [
                r'BufferedReader|BufferedWriter|BufferedInputStream',
                r'FileReader|FileWriter|FileInputStream',
                r'flush\(\)|close\(\)|finish\(\)',  # Resource management
            ],
            'synchronization': [
                r'synchronized\s*\([^)]*\)|volatile\s+\w+',
                r'concurrent\.\w+|atomic\.\w+',
                r'ReentrantLock|ReadWriteLock',
            ],
            'redundancy_removal': [
                r'cache|memoiz|store',  # Caching patterns
                r'break;|continue;|return;',  # Control flow optimization
                r'static\s+final|final\s+static',  # Constants
            ]
        }
    
    def extract_patch_methods(self, patch_content: str, file_path: str = "") -> List[MethodDiff]:
        """
        Extract method-level changes from a unified diff patch.
        Returns list of MethodDiff objects for each changed method.
        """
        methods = []
        
        if not patch_content.strip():
            return methods
        
        try:
            # Parse unified diff to get file-level changes
            file_changes = self._parse_unified_diff(patch_content)
            
            for change in file_changes:
                # Extract methods from the change
                method_changes = self._extract_methods_from_change(change)
                methods.extend(method_changes)
                
        except Exception as e:
            logger.error(f"Failed to extract methods from patch: {e}")
        
        return methods
    
    def _parse_unified_diff(self, patch: str) -> List[Dict]:
        """Parse unified diff format into structured changes"""
        changes = []
        current_file = None
        current_hunks = []
        
        lines = patch.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # File header
            if line.startswith('diff --git'):
                if current_file and current_hunks:
                    changes.append({
                        'file': current_file,
                        'hunks': current_hunks
                    })
                current_hunks = []
                # Extract file path
                parts = line.split()
                if len(parts) >= 4:
                    current_file = parts[3][2:]  # Remove 'b/' prefix
            
            # Hunk header
            elif line.startswith('@@'):
                hunk = self._parse_hunk(lines, i)
                if hunk:
                    current_hunks.append(hunk)
                    i = hunk['end_line_idx']
                    continue
            
            i += 1
        
        # Add last file
        if current_file and current_hunks:
            changes.append({
                'file': current_file,
                'hunks': current_hunks
            })
        
        return changes
    
    def _parse_hunk(self, lines: List[str], start_idx: int) -> Optional[Dict]:
        """Parse a single hunk from unified diff"""
        hunk_line = lines[start_idx]
        
        # Extract line numbers from @@ -old_start,old_count +new_start,new_count @@
        match = re.search(r'@@\s+-(\d+)(?:,(\d+))?\s+\+(\d+)(?:,(\d+))?\s+@@', hunk_line)
        if not match:
            return None
        
        old_start = int(match.group(1))
        old_count = int(match.group(2)) if match.group(2) else 1
        new_start = int(match.group(3))
        new_count = int(match.group(4)) if match.group(4) else 1
        
        # Extract hunk content
        removed_lines = []
        added_lines = []
        context_lines = []
        
        i = start_idx + 1
        while i < len(lines):
            line = lines[i]
            
            if line.startswith('@@') or line.startswith('diff'):
                break
            elif line.startswith('-'):
                removed_lines.append(line[1:])
            elif line.startswith('+'):
                added_lines.append(line[1:])
            elif line.startswith(' '):
                context_lines.append(line[1:])
            
            i += 1
        
        return {
            'old_start': old_start,
            'old_count': old_count,
            'new_start': new_start,
            'new_count': new_count,
            'removed_lines': removed_lines,
            'added_lines': added_lines,
            'context_lines': context_lines,
            'end_line_idx': i - 1
        }
    
    def _extract_methods_from_change(self, file_change: Dict) -> List[MethodDiff]:
        """Extract method-level changes from file-level changes"""
        methods = []
        file_path = file_change['file']
        
        for hunk in file_change['hunks']:
            # Combine removed and added lines to find method boundaries
            all_changed_lines = hunk['removed_lines'] + hunk['added_lines']
            context = hunk['context_lines']
            
            # Find method signatures in the changed code
            method_signatures = self._find_method_signatures(all_changed_lines + context)
            
            for signature in method_signatures:
                # Extract the full method code
                buggy_method = self._extract_method_body(
                    hunk['removed_lines'], signature, context
                )
                fixed_method = self._extract_method_body(
                    hunk['added_lines'], signature, context
                )
                
                if buggy_method or fixed_method:
                    # Analyze performance patterns
                    patterns = self._detect_performance_patterns(
                        buggy_method.get('body', ''), 
                        fixed_method.get('body', '')
                    )
                    
                    # Calculate complexity change
                    complexity_change = self._analyze_complexity_change(
                        buggy_method.get('body', ''),
                        fixed_method.get('body', '')
                    )
                    
                    method_diff = MethodDiff(
                        file_path=file_path,
                        method_name=signature.get('name', 'unknown'),
                        buggy_code=buggy_method.get('body', ''),
                        fixed_code=fixed_method.get('body', ''),
                        method_signature=signature.get('signature', ''),
                        start_line=hunk['old_start'],
                        end_line=hunk['old_start'] + hunk['old_count'],
                        change_type='modified',
                        complexity_change=complexity_change,
                        performance_patterns=patterns
                    )
                    
                    methods.append(method_diff)
        
        return methods
    
    def _find_method_signatures(self, code_lines: List[str]) -> List[Dict]:
        """Find Java method signatures in code lines"""
        signatures = []
        
        # Java method signature patterns
        method_patterns = [
            r'(public|private|protected)?\s*(static)?\s*(final)?\s*(\w+)\s+(\w+)\s*\([^)]*\)\s*\{',
            r'(\w+)\s+(\w+)\s*\([^)]*\)\s*\{',  # Simple method pattern
        ]
        
        for line in code_lines:
            line = line.strip()
            if line:
                for pattern in method_patterns:
                    match = re.search(pattern, line)
                    if match:
                        # Extract method name (last capture group before parameters)
                        groups = match.groups()
                        if len(groups) >= 2:
                            method_name = groups[-1]  # Last group is usually method name
                            signatures.append({
                                'signature': match.group(0),
                                'name': method_name,
                                'full_line': line
                            })
                            break
        
        return signatures
    
    def _extract_method_body(self, code_lines: List[str], signature: Dict, 
                           context: List[str]) -> Optional[Dict]:
        """Extract full method body from code lines"""
        if not code_lines:
            return None
        
        method_name = signature['name']
        all_lines = context + code_lines
        
        # Find method start
        method_start = -1
        for i, line in enumerate(all_lines):
            if method_name in line and '{' in line:
                method_start = i
                break
        
        if method_start == -1:
            return None
        
        # Find method end (matching braces)
        brace_count = 0
        method_end = method_start
        method_lines = []
        
        for i in range(method_start, len(all_lines)):
            line = all_lines[i]
            method_lines.append(line)
            
            # Count braces
            brace_count += line.count('{') - line.count('}')
            
            if brace_count == 0 and i > method_start:
                method_end = i
                break
        
        return {
            'body': '\n'.join(method_lines),
            'start': method_start,
            'end': method_end,
            'line_count': len(method_lines)
        }
    
    def _detect_performance_patterns(self, buggy_code: str, fixed_code: str) -> List[str]:
        """Detect performance improvement patterns between buggy and fixed code"""
        patterns_found = []
        
        buggy_lower = buggy_code.lower()
        fixed_lower = fixed_code.lower()
        
        for pattern_type, regexes in self.performance_patterns.items():
            for regex in regexes:
                # Check if pattern exists in buggy but improved/removed in fixed
                buggy_matches = len(re.findall(regex, buggy_lower))
                fixed_matches = len(re.findall(regex, fixed_lower))
                
                if buggy_matches > fixed_matches:
                    patterns_found.append(f"{pattern_type}_removed")
                elif fixed_matches > buggy_matches:
                    patterns_found.append(f"{pattern_type}_added")
        
        # Specific improvement patterns
        if 'stringbuilder' in fixed_lower and 'stringbuilder' not in buggy_lower:
            patterns_found.append('stringbuilder_optimization')
        
        if buggy_code.count('for') > fixed_code.count('for'):
            patterns_found.append('loop_reduction')
        
        if 'synchronized' in buggy_lower and 'synchronized' not in fixed_lower:
            patterns_found.append('synchronization_removal')
        
        return list(set(patterns_found))
    
    def _analyze_complexity_change(self, buggy_code: str, fixed_code: str) -> Dict:
        """Analyze algorithmic complexity changes"""
        analysis = {
            'loop_nesting_change': 0,
            'collection_efficiency_change': False,
            'algorithm_complexity_change': '',
            'estimated_improvement': ''
        }
        
        # Count nested loops
        buggy_nesting = self._count_loop_nesting(buggy_code)
        fixed_nesting = self._count_loop_nesting(fixed_code)
        analysis['loop_nesting_change'] = buggy_nesting - fixed_nesting
        
        # Check for collection changes
        buggy_collections = self._extract_collections(buggy_code)
        fixed_collections = self._extract_collections(fixed_code)
        
        if buggy_collections != fixed_collections:
            analysis['collection_efficiency_change'] = True
            
            # Estimate complexity improvement
            improvements = {
                ('arraylist', 'hashmap'): 'O(n) to O(1) lookup',
                ('vector', 'arraylist'): 'Removed synchronization overhead',
                ('hashtable', 'hashmap'): 'Reduced synchronization'
            }
            
            for (old, new), improvement in improvements.items():
                if old in buggy_collections and new in fixed_collections:
                    analysis['estimated_improvement'] = improvement
                    break
        
        # Overall complexity assessment
        if analysis['loop_nesting_change'] > 0:
            analysis['algorithm_complexity_change'] = 'Reduced nesting complexity'
        elif analysis['collection_efficiency_change']:
            analysis['algorithm_complexity_change'] = 'Improved data structure efficiency'
        
        return analysis
    
    def _count_loop_nesting(self, code: str) -> int:
        """Count maximum loop nesting depth"""
        max_nesting = 0
        current_nesting = 0
        
        # Simple heuristic: count for/while keywords and braces
        for line in code.split('\n'):
            line = line.strip()
            if re.search(r'\\b(for|while)\\b', line) and '{' in line:
                current_nesting += 1
                max_nesting = max(max_nesting, current_nesting)
            elif '}' in line:
                current_nesting = max(0, current_nesting - 1)
        
        return max_nesting
    
    def _extract_collections(self, code: str) -> List[str]:
        """Extract collection types used in code"""
        collections = []
        collection_types = [
            'arraylist', 'hashmap', 'vector', 'hashtable', 'linkedlist',
            'treemap', 'treeset', 'hashset', 'linkedhashmap'
        ]
        
        code_lower = code.lower()
        for collection in collection_types:
            if collection in code_lower:
                collections.append(collection)
        
        return collections

class PerformancePatternAnalyzer:
    """
    Analyzes performance patterns in method-level changes.
    Implements pattern recognition from the paper's methodology.
    """
    
    def __init__(self):
        # Categories and their indicators from Table I in the paper
        self.category_indicators = {
            'algorithmic_inefficiency': {
                'keywords': ['loop', 'nested', 'bubble', 'sort', 'search', 'algorithm'],
                'patterns': ['O(n²)', 'O(n*m)', 'nested_loop', 'inefficient_search'],
                'code_smells': ['for.*for', 'while.*while', 'indexOf.*loop']
            },
            'memory_usage': {
                'keywords': ['string', 'arraylist', 'buffer', 'allocation', 'gc'],
                'patterns': ['string_concatenation', 'object_creation', 'memory_leak'],
                'code_smells': ['String.*+=', 'new.*loop', 'ArrayList\\(\\)']
            },
            'redundant_computation': {
                'keywords': ['cache', 'redundant', 'duplicate', 'repeated', 'memoiz'],
                'patterns': ['repeated_calculation', 'cache_miss', 'redundant_call'],
                'code_smells': ['Math\\.\\w+.*Math\\.\\w+', 'calculateTotal.*loop']
            },
            'cpu_overhead': {
                'keywords': ['synchronized', 'boxing', 'unboxing', 'thread', 'lock'],
                'patterns': ['boxing_unboxing', 'oversynchronization', 'thread_creation'],
                'code_smells': ['Integer.*int', 'synchronized.*tight.*loop']
            },
            'io_inefficiency': {
                'keywords': ['file', 'stream', 'reader', 'writer', 'buffer', 'flush'],
                'patterns': ['unbuffered_io', 'resource_leak', 'inefficient_io'],
                'code_smells': ['FileReader.*BufferedReader', 'new.*Stream.*loop']
            }
        }
    
    def categorize_method_change(self, method_diff: MethodDiff) -> str:
        """Categorize a method change into performance bug categories"""
        
        # Combine buggy and fixed code for analysis
        combined_text = (method_diff.buggy_code + ' ' + method_diff.fixed_code).lower()
        
        category_scores = {}
        
        for category, indicators in self.category_indicators.items():
            score = 0.0
            
            # Check keywords
            for keyword in indicators['keywords']:
                if keyword in combined_text:
                    score += 0.2
            
            # Check code smell patterns
            for pattern in indicators['code_smells']:
                if re.search(pattern, combined_text):
                    score += 0.3
            
            # Check detected performance patterns
            for pattern in method_diff.performance_patterns:
                if any(p in pattern for p in indicators['patterns']):
                    score += 0.4
            
            category_scores[category] = score
        
        # Return category with highest score
        if category_scores:
            best_category = max(category_scores.items(), key=lambda x: x[1])
            if best_category[1] > 0.2:  # Minimum threshold
                return best_category[0]
        
        return 'algorithmic_inefficiency'  # Default to most common category
    
    def generate_method_summary(self, method_diff: MethodDiff) -> Dict:
        """Generate summary of method-level changes"""
        
        buggy_lines = len(method_diff.buggy_code.split('\n'))
        fixed_lines = len(method_diff.fixed_code.split('\n'))
        
        summary = {
            'method_name': method_diff.method_name,
            'file_path': method_diff.file_path,
            'lines_before': buggy_lines,
            'lines_after': fixed_lines,
            'line_change': fixed_lines - buggy_lines,
            'performance_patterns': method_diff.performance_patterns,
            'complexity_analysis': method_diff.complexity_change,
            'estimated_category': self.categorize_method_change(method_diff),
            'improvement_type': self._classify_improvement_type(method_diff)
        }
        
        return summary
    
    def _classify_improvement_type(self, method_diff: MethodDiff) -> str:
        """Classify the type of performance improvement"""
        
        patterns = method_diff.performance_patterns
        
        if 'loop_reduction' in patterns or 'algorithm_change' in patterns:
            return 'algorithmic_optimization'
        elif 'stringbuilder_optimization' in patterns or 'memory_optimization' in patterns:
            return 'memory_optimization'
        elif 'synchronization_removal' in patterns:
            return 'concurrency_optimization'
        elif 'redundancy_removal' in patterns:
            return 'redundancy_elimination'
        elif 'io_optimization' in patterns:
            return 'io_optimization'
        else:
            return 'general_optimization'

def process_performance_bugs_dataset(dataset_file: str, output_file: str):
    """
    Process the performance bugs dataset to extract method-level changes.
    This is the main function that implements the paper's data processing pipeline.
    """
    
    # Load the performance bugs dataset
    with open(dataset_file, 'r') as f:
        data = json.load(f)
    
    bugs = data['bugs']
    extractor = MethodLevelExtractor()
    analyzer = PerformancePatternAnalyzer()
    
    processed_bugs = []
    
    logger.info(f"Processing {len(bugs)} performance bugs for method-level extraction")
    
    for i, bug in enumerate(bugs):
        if i % 50 == 0:
            logger.info(f"Processed {i}/{len(bugs)} bugs")
        
        # Extract method-level changes from patch
        method_diffs = extractor.extract_patch_methods(
            bug.get('patch_content', ''), 
            bug.get('identifier', '')
        )
        
        # Analyze each method change
        method_summaries = []
        for method_diff in method_diffs:
            summary = analyzer.generate_method_summary(method_diff)
            method_summaries.append(summary)
        
        # Enhanced bug record
        enhanced_bug = bug.copy()
        enhanced_bug.update({
            'method_changes': method_summaries,
            'method_count': len(method_summaries),
            'primary_improvement_type': method_summaries[0]['improvement_type'] if method_summaries else 'unknown',
            'complexity_improvements': [m['complexity_analysis'] for m in method_summaries],
            'all_patterns': [p for m in method_summaries for p in m['performance_patterns']]
        })
        
        processed_bugs.append(enhanced_bug)
    
    # Save processed dataset
    output_data = {
        'bugs': processed_bugs,
        'metadata': {
            'total_bugs': len(processed_bugs),
            'processing_date': '2025-09-02',
            'method_extraction': True,
            'pattern_analysis': True,
            'source_dataset': dataset_file
        }
    }
    
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    logger.info(f"Saved {len(processed_bugs)} processed bugs to {output_file}")
    
    # Generate statistics
    stats = {
        'bugs_with_methods': len([b for b in processed_bugs if b['method_count'] > 0]),
        'total_methods': sum(b['method_count'] for b in processed_bugs),
        'avg_methods_per_bug': sum(b['method_count'] for b in processed_bugs) / len(processed_bugs),
        'improvement_types': Counter(b['primary_improvement_type'] for b in processed_bugs),
        'pattern_frequency': Counter([p for b in processed_bugs for p in b['all_patterns']])
    }
    
    return stats

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Process the dataset
    stats = process_performance_bugs_dataset(
        'data/performance_bugs_490.json',
        'data/processed_performance_bugs.json'
    )
    
    print("\\nProcessing Statistics:")
    print(f"  Bugs with method changes: {stats['bugs_with_methods']}")
    print(f"  Total methods extracted: {stats['total_methods']}")
    print(f"  Average methods per bug: {stats['avg_methods_per_bug']:.1f}")
    
    print("\\nImprovement types:")
    for imp_type, count in stats['improvement_types'].most_common():
        print(f"  {imp_type}: {count}")
    
    print("\\nTop performance patterns:")
    for pattern, count in stats['pattern_frequency'].most_common(10):
        print(f"  {pattern}: {count}")