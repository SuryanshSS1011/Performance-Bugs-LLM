"""
Java code parsing utilities for AST analysis and method extraction.
Used for accurate code analysis as described in the paper.
"""

import re
import javalang
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class MethodInfo:
    """Information about a Java method"""
    name: str
    start_line: int
    end_line: int
    parameters: List[str]
    return_type: str
    modifiers: Set[str]
    body: str
    complexity: int
    
class JavaParser:
    """
    Parser for Java code using javalang for AST analysis.
    Provides method extraction and complexity analysis.
    """
    
    def __init__(self):
        self.tree = None
        self.source_lines = []
        
    def parse(self, source_code: str) -> bool:
        """Parse Java source code into AST"""
        try:
            self.source_lines = source_code.split('\n')
            self.tree = javalang.parse.parse(source_code)
            return True
        except Exception as e:
            logger.error(f"Failed to parse Java code: {e}")
            return False
    
    def extract_methods(self) -> List[MethodInfo]:
        """Extract all methods from parsed Java code"""
        if not self.tree:
            return []
        
        methods = []
        for _, node in self.tree.filter(javalang.tree.MethodDeclaration):
            method_info = self._extract_method_info(node)
            if method_info:
                methods.append(method_info)
        
        return methods
    
    def _extract_method_info(self, node: javalang.tree.MethodDeclaration) -> Optional[MethodInfo]:
        """Extract detailed information about a method"""
        try:
            # Get method boundaries
            start_line = node.position.line if node.position else 1
            end_line = self._find_method_end(node, start_line)
            
            # Extract method body
            body = '\n'.join(self.source_lines[start_line-1:end_line])
            
            # Calculate complexity
            complexity = self._calculate_complexity(node)
            
            # Extract parameters
            parameters = []
            if node.parameters:
                for param in node.parameters:
                    param_type = self._get_type_name(param.type)
                    parameters.append(f"{param_type} {param.name}")
            
            return MethodInfo(
                name=node.name,
                start_line=start_line,
                end_line=end_line,
                parameters=parameters,
                return_type=self._get_type_name(node.return_type) if node.return_type else "void",
                modifiers=set(node.modifiers) if node.modifiers else set(),
                body=body,
                complexity=complexity
            )
        except Exception as e:
            logger.error(f"Failed to extract method info: {e}")
            return None
    
    def _find_method_end(self, node: javalang.tree.MethodDeclaration, start_line: int) -> int:
        """Find the end line of a method by counting braces"""
        brace_count = 0
        in_method = False
        
        for i, line in enumerate(self.source_lines[start_line-1:], start=start_line):
            if '{' in line:
                brace_count += line.count('{')
                in_method = True
            if '}' in line and in_method:
                brace_count -= line.count('}')
                if brace_count == 0:
                    return i
        
        return len(self.source_lines)
    
    def _get_type_name(self, type_node) -> str:
        """Get string representation of a type"""
        if not type_node:
            return "void"
        
        if isinstance(type_node, javalang.tree.BasicType):
            return type_node.name
        elif isinstance(type_node, javalang.tree.ReferenceType):
            return type_node.name
        else:
            return str(type_node)
    
    def _calculate_complexity(self, node: javalang.tree.MethodDeclaration) -> int:
        """
        Calculate cyclomatic complexity of a method.
        Counts decision points: if, for, while, case, catch, &&, ||
        """
        complexity = 1  # Base complexity
        
        if not node.body:
            return complexity
        
        # Count control flow statements
        for _, child in node.filter(javalang.tree.IfStatement):
            complexity += 1
        for _, child in node.filter(javalang.tree.ForStatement):
            complexity += 1
        for _, child in node.filter(javalang.tree.WhileStatement):
            complexity += 1
        for _, child in node.filter(javalang.tree.DoStatement):
            complexity += 1
        for _, child in node.filter(javalang.tree.SwitchStatementCase):
            complexity += 1
        for _, child in node.filter(javalang.tree.CatchClause):
            complexity += 1
        
        # Count logical operators in conditions
        # This is simplified - full implementation would parse expressions
        method_text = str(node)
        complexity += method_text.count('&&')
        complexity += method_text.count('||')
        
        return complexity
    
    def find_changed_methods(self, other_parser: 'JavaParser') -> List[Tuple[MethodInfo, MethodInfo]]:
        """Find methods that changed between two versions"""
        self_methods = {m.name: m for m in self.extract_methods()}
        other_methods = {m.name: m for m in other_parser.extract_methods()}
        
        changed = []
        for name, self_method in self_methods.items():
            if name in other_methods:
                other_method = other_methods[name]
                if self_method.body != other_method.body:
                    changed.append((self_method, other_method))
        
        return changed

class PerformancePatternDetector:
    """
    Detects performance bug patterns in Java code.
    Implements pattern recognition from the paper.
    """
    
    def __init__(self):
        self.patterns = self._load_patterns()
    
    def _load_patterns(self) -> Dict[str, List[re.Pattern]]:
        """Load performance bug patterns for each category"""
        return {
            "algorithmic_inefficiency": [
                re.compile(r'for\s*\([^)]*\)\s*{[^}]*for\s*\([^)]*\)', re.DOTALL),  # Nested loops
                re.compile(r'\.get\([^)]*\).*for\s*\(', re.DOTALL),  # Get in loop
                re.compile(r'Collections\.sort.*for\s*\(', re.DOTALL),  # Sort in loop
                re.compile(r'indexOf.*for\s*\(', re.DOTALL),  # indexOf in loop
            ],
            "memory_usage": [
                re.compile(r'new\s+ArrayList\s*\(\s*\)'),  # ArrayList without size
                re.compile(r'String\s+\w+\s*=.*\+(?!=)', re.MULTILINE),  # String concatenation
                re.compile(r'\+=.*String'),  # String += 
                re.compile(r'new\s+\w+\[.*\].*for\s*\(', re.DOTALL),  # Array creation in loop
            ],
            "redundant_computation": [
                re.compile(r'Math\.\w+\([^)]*\).*for\s*\(', re.DOTALL),  # Math in loop
                re.compile(r'(\w+)\s*=\s*([^;]+);.*\1\s*=\s*\2;', re.DOTALL),  # Repeated assignment
                re.compile(r'\.size\(\).*for\s*\(.*\.size\(\)', re.DOTALL),  # Multiple size() calls
                re.compile(r'calculate\w*\([^)]*\).*for\s*\(', re.DOTALL),  # Calculate in loop
            ],
            "cpu_overhead": [
                re.compile(r'Integer|Double|Long|Float|Boolean|Character|Byte|Short'),  # Boxing
                re.compile(r'synchronized.*for\s*\(', re.DOTALL),  # Sync in loop
                re.compile(r'lock\(\).*for\s*\(', re.DOTALL),  # Lock in loop
                re.compile(r'Thread\.sleep', re.DOTALL),  # Sleep in code
            ],
            "io_inefficiency": [
                re.compile(r'new\s+FileReader'),  # Unbuffered file reader
                re.compile(r'new\s+FileWriter'),  # Unbuffered file writer
                re.compile(r'FileInputStream(?!.*Buffered)'),  # Unbuffered input
                re.compile(r'FileOutputStream(?!.*Buffered)'),  # Unbuffered output
            ]
        }
    
    def detect_patterns(self, code: str) -> Dict[str, List[str]]:
        """Detect performance patterns in code"""
        detected = {}
        
        for category, patterns in self.patterns.items():
            matches = []
            for pattern in patterns:
                found = pattern.findall(code)
                if found:
                    matches.extend([f"Pattern: {pattern.pattern[:50]}..." for _ in found])
            
            if matches:
                detected[category] = matches
        
        return detected
    
    def analyze_complexity_change(self, buggy_code: str, fixed_code: str) -> Dict[str, any]:
        """Analyze complexity changes between buggy and fixed versions"""
        analysis = {
            "loop_reduction": False,
            "method_extraction": False,
            "algorithm_change": False,
            "caching_added": False,
            "buffering_added": False
        }
        
        # Check for loop reduction
        buggy_loops = len(re.findall(r'for\s*\(|while\s*\(', buggy_code))
        fixed_loops = len(re.findall(r'for\s*\(|while\s*\(', fixed_code))
        analysis["loop_reduction"] = fixed_loops < buggy_loops
        
        # Check for method extraction (code moved to separate method)
        buggy_methods = len(re.findall(r'(public|private|protected)\s+\w+\s+\w+\s*\(', buggy_code))
        fixed_methods = len(re.findall(r'(public|private|protected)\s+\w+\s+\w+\s*\(', fixed_code))
        analysis["method_extraction"] = fixed_methods > buggy_methods
        
        # Check for algorithm change (HashMap instead of ArrayList, etc.)
        if "HashMap" in fixed_code and "HashMap" not in buggy_code:
            analysis["algorithm_change"] = True
        if "HashSet" in fixed_code and "ArrayList" in buggy_code:
            analysis["algorithm_change"] = True
        
        # Check for caching
        cache_keywords = ["cache", "cached", "memoiz", "stored"]
        for keyword in cache_keywords:
            if keyword in fixed_code.lower() and keyword not in buggy_code.lower():
                analysis["caching_added"] = True
                break
        
        # Check for buffering
        if "Buffered" in fixed_code and "Buffered" not in buggy_code:
            analysis["buffering_added"] = True
        
        return analysis

class CodeDiffAnalyzer:
    """
    Analyzes differences between buggy and fixed code versions.
    Extracts features for bug categorization.
    """
    
    def __init__(self):
        self.parser = JavaParser()
        self.pattern_detector = PerformancePatternDetector()
    
    def analyze_diff(self, buggy_code: str, fixed_code: str) -> Dict:
        """Comprehensive diff analysis"""
        analysis = {
            "code_metrics": self._calculate_metrics(buggy_code, fixed_code),
            "patterns_removed": self.pattern_detector.detect_patterns(buggy_code),
            "patterns_added": self.pattern_detector.detect_patterns(fixed_code),
            "complexity_changes": self.pattern_detector.analyze_complexity_change(buggy_code, fixed_code),
            "method_changes": self._analyze_method_changes(buggy_code, fixed_code),
            "api_changes": self._detect_api_changes(buggy_code, fixed_code)
        }
        
        return analysis
    
    def _calculate_metrics(self, buggy_code: str, fixed_code: str) -> Dict:
        """Calculate code metrics for both versions"""
        return {
            "buggy_lines": len(buggy_code.split('\n')),
            "fixed_lines": len(fixed_code.split('\n')),
            "lines_added": self._count_added_lines(buggy_code, fixed_code),
            "lines_removed": self._count_removed_lines(buggy_code, fixed_code),
            "buggy_complexity": self._estimate_complexity(buggy_code),
            "fixed_complexity": self._estimate_complexity(fixed_code)
        }
    
    def _count_added_lines(self, buggy: str, fixed: str) -> int:
        """Count lines added in fixed version"""
        buggy_lines = set(buggy.split('\n'))
        fixed_lines = set(fixed.split('\n'))
        return len(fixed_lines - buggy_lines)
    
    def _count_removed_lines(self, buggy: str, fixed: str) -> int:
        """Count lines removed from buggy version"""
        buggy_lines = set(buggy.split('\n'))
        fixed_lines = set(fixed.split('\n'))
        return len(buggy_lines - fixed_lines)
    
    def _estimate_complexity(self, code: str) -> int:
        """Estimate cyclomatic complexity"""
        complexity = 1
        complexity += code.count('if ')
        complexity += code.count('for ')
        complexity += code.count('while ')
        complexity += code.count('case ')
        complexity += code.count('catch ')
        complexity += code.count('&&')
        complexity += code.count('||')
        return complexity
    
    def _analyze_method_changes(self, buggy_code: str, fixed_code: str) -> Dict:
        """Analyze changes at method level"""
        buggy_parser = JavaParser()
        fixed_parser = JavaParser()
        
        changes = {
            "methods_modified": 0,
            "complexity_reduced": False,
            "method_extracted": False
        }
        
        if buggy_parser.parse(buggy_code) and fixed_parser.parse(fixed_code):
            buggy_methods = buggy_parser.extract_methods()
            fixed_methods = fixed_parser.extract_methods()
            
            changes["methods_modified"] = len(buggy_parser.find_changed_methods(fixed_parser))
            
            # Check if complexity reduced
            buggy_complexity = sum(m.complexity for m in buggy_methods)
            fixed_complexity = sum(m.complexity for m in fixed_methods)
            changes["complexity_reduced"] = fixed_complexity < buggy_complexity
            
            # Check if methods extracted
            changes["method_extracted"] = len(fixed_methods) > len(buggy_methods)
        
        return changes
    
    def _detect_api_changes(self, buggy_code: str, fixed_code: str) -> List[str]:
        """Detect API/library changes"""
        changes = []
        
        # Common performance-related API changes
        api_changes = [
            ("ArrayList", "HashMap", "Changed to HashMap for O(1) lookup"),
            ("FileReader", "BufferedReader", "Added buffering for I/O"),
            ("String +", "StringBuilder", "Using StringBuilder for concatenation"),
            ("LinkedList", "ArrayList", "Changed to ArrayList for better cache locality"),
            ("TreeMap", "HashMap", "Changed to HashMap for better average performance")
        ]
        
        for old_api, new_api, description in api_changes:
            if old_api in buggy_code and new_api in fixed_code:
                changes.append(description)
        
        return changes

if __name__ == "__main__":
    # Test the parser
    test_code = """
    public class Example {
        public void inefficientMethod(List<String> items) {
            for (int i = 0; i < items.size(); i++) {
                for (int j = 0; j < items.size(); j++) {
                    String result = items.get(i) + items.get(j);
                    System.out.println(result);
                }
            }
        }
    }
    """
    
    parser = JavaParser()
    if parser.parse(test_code):
        methods = parser.extract_methods()
        for method in methods:
            print(f"Method: {method.name}, Complexity: {method.complexity}")
    
    detector = PerformancePatternDetector()
    patterns = detector.detect_patterns(test_code)
    print(f"Detected patterns: {patterns}")