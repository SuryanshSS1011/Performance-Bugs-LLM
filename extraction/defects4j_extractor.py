"""
Defects4J bug extractor - extracts performance bugs from all 17 projects.
Implements the methodology from Section IV of the paper.
"""

import json
import logging
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import tempfile
import shutil

from ..config import (
    DEFECTS4J_HOME, DEFECTS4J_PROJECTS, PERFORMANCE_KEYWORDS,
    CACHE_DIR, DATA_DIR
)

logger = logging.getLogger(__name__)

@dataclass
class BugInfo:
    """Represents a single bug from Defects4J"""
    project: str
    bug_id: int
    commit_hash: str
    buggy_commit: str
    fixed_commit: str
    test_suite: List[str]
    modified_files: List[str]
    commit_message: str
    issue_id: Optional[str] = None
    issue_url: Optional[str] = None
    
    @property
    def identifier(self) -> str:
        return f"{self.project}-{self.bug_id}"

class Defects4JExtractor:
    """Extracts bugs from Defects4J projects"""
    
    def __init__(self, defects4j_home: str = DEFECTS4J_HOME):
        self.d4j_home = Path(defects4j_home)
        self.d4j_cmd = self.d4j_home / "framework" / "bin" / "defects4j"
        
        if not self.d4j_cmd.exists():
            raise FileNotFoundError(f"Defects4J not found at {self.d4j_cmd}")
        
        self.cache_dir = CACHE_DIR / "defects4j"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
    def get_project_bugs(self, project: str) -> List[BugInfo]:
        """Get all bugs for a specific project"""
        logger.info(f"Extracting bugs from project: {project}")
        
        # Get bug IDs for the project
        try:
            result = subprocess.run(
                [str(self.d4j_cmd), "bids", "-p", project],
                capture_output=True, text=True, check=True
            )
            bug_ids = [int(bid) for bid in result.stdout.strip().split('\n')]
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to get bug IDs for {project}: {e}")
            return []
        
        bugs = []
        for bug_id in bug_ids:
            bug_info = self._extract_bug_info(project, bug_id)
            if bug_info:
                bugs.append(bug_info)
        
        logger.info(f"Extracted {len(bugs)} bugs from {project}")
        return bugs
    
    def _extract_bug_info(self, project: str, bug_id: int) -> Optional[BugInfo]:
        """Extract detailed information for a specific bug"""
        cache_file = self.cache_dir / f"{project}_{bug_id}.json"
        
        # Check cache first
        if cache_file.exists():
            with open(cache_file, 'r') as f:
                data = json.load(f)
                return BugInfo(**data)
        
        try:
            # Get bug information
            info_cmd = [str(self.d4j_cmd), "info", "-p", project, "-b", str(bug_id)]
            result = subprocess.run(info_cmd, capture_output=True, text=True, check=True)
            info_lines = result.stdout.strip().split('\n')
            
            # Parse the output
            info_dict = {}
            for line in info_lines:
                if ':' in line:
                    key, value = line.split(':', 1)
                    info_dict[key.strip()] = value.strip()
            
            # Get commit message
            commit_msg = self._get_commit_message(project, bug_id)
            
            # Get modified files
            modified_files = self._get_modified_files(project, bug_id)
            
            bug_info = BugInfo(
                project=project,
                bug_id=bug_id,
                commit_hash=info_dict.get('Revision ID(fixed)', ''),
                buggy_commit=info_dict.get('Revision ID(buggy)', ''),
                fixed_commit=info_dict.get('Revision ID(fixed)', ''),
                test_suite=info_dict.get('Root cause in triggering tests', '').split(','),
                modified_files=modified_files,
                commit_message=commit_msg,
                issue_id=info_dict.get('Report ID', None),
                issue_url=info_dict.get('Report URL', None)
            )
            
            # Cache the result
            with open(cache_file, 'w') as f:
                json.dump(asdict(bug_info), f, indent=2)
            
            return bug_info
            
        except Exception as e:
            logger.error(f"Failed to extract bug {project}-{bug_id}: {e}")
            return None
    
    def _get_commit_message(self, project: str, bug_id: int) -> str:
        """Get the commit message for a bug fix"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Checkout the fixed version
            checkout_cmd = [
                str(self.d4j_cmd), "checkout",
                "-p", project, "-v", f"{bug_id}f",
                "-w", tmpdir
            ]
            
            try:
                subprocess.run(checkout_cmd, capture_output=True, check=True)
                
                # Get commit message using git
                git_cmd = ["git", "log", "--format=%B", "-n", "1"]
                result = subprocess.run(
                    git_cmd, cwd=tmpdir, capture_output=True, text=True
                )
                return result.stdout.strip()
            except:
                return ""
    
    def _get_modified_files(self, project: str, bug_id: int) -> List[str]:
        """Get list of files modified in the bug fix"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Checkout both versions
            buggy_dir = Path(tmpdir) / "buggy"
            fixed_dir = Path(tmpdir) / "fixed"
            
            for version, target_dir in [("b", buggy_dir), ("f", fixed_dir)]:
                checkout_cmd = [
                    str(self.d4j_cmd), "checkout",
                    "-p", project, "-v", f"{bug_id}{version}",
                    "-w", str(target_dir)
                ]
                subprocess.run(checkout_cmd, capture_output=True, check=True)
            
            # Get diff
            diff_cmd = [
                "diff", "-rq", str(buggy_dir), str(fixed_dir)
            ]
            result = subprocess.run(diff_cmd, capture_output=True, text=True)
            
            # Parse diff output for modified files
            modified = []
            for line in result.stdout.split('\n'):
                if 'differ' in line:
                    # Extract file path
                    parts = line.split()
                    if len(parts) >= 2:
                        file_path = parts[1].replace(str(buggy_dir) + '/', '')
                        if file_path.endswith('.java'):
                            modified.append(file_path)
            
            return modified
    
    def is_performance_bug(self, bug_info: BugInfo) -> bool:
        """
        Check if a bug is performance-related based on keywords.
        Implements filtering logic from Section IV.A of the paper.
        """
        # Check commit message
        commit_lower = bug_info.commit_message.lower()
        for keyword in PERFORMANCE_KEYWORDS:
            if keyword in commit_lower:
                return True
        
        # Check issue URL/ID if available
        if bug_info.issue_url:
            # Could fetch and analyze issue description here
            pass
        
        # Check for specific patterns in modified files
        performance_patterns = [
            r'optimize', r'performance', r'speed.*up', r'faster',
            r'efficient', r'cache', r'memory.*leak', r'timeout'
        ]
        
        for pattern in performance_patterns:
            if re.search(pattern, commit_lower, re.IGNORECASE):
                return True
        
        return False
    
    def extract_all_performance_bugs(self) -> List[BugInfo]:
        """Extract all performance bugs from all projects"""
        all_bugs = []
        performance_bugs = []
        
        for project in DEFECTS4J_PROJECTS:
            logger.info(f"Processing project: {project}")
            bugs = self.get_project_bugs(project)
            all_bugs.extend(bugs)
            
            # Filter for performance bugs
            for bug in bugs:
                if self.is_performance_bug(bug):
                    performance_bugs.append(bug)
                    logger.debug(f"Found performance bug: {bug.identifier}")
        
        logger.info(f"Total bugs: {len(all_bugs)}")
        logger.info(f"Performance bugs: {len(performance_bugs)}")
        
        # Save results
        output_file = DATA_DIR / "extracted_performance_bugs.json"
        with open(output_file, 'w') as f:
            json.dump([asdict(b) for b in performance_bugs], f, indent=2)
        
        logger.info(f"Saved {len(performance_bugs)} performance bugs to {output_file}")
        return performance_bugs

class CodeDiffExtractor:
    """Extracts code diffs between buggy and fixed versions"""
    
    def __init__(self, defects4j_home: str = DEFECTS4J_HOME):
        self.d4j_home = Path(defects4j_home)
        self.d4j_cmd = self.d4j_home / "framework" / "bin" / "defects4j"
        self.cache_dir = CACHE_DIR / "diffs"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def extract_method_diff(self, project: str, bug_id: int) -> Dict:
        """
        Extract method-level diffs for a bug.
        Returns buggy and fixed versions of modified methods.
        """
        cache_file = self.cache_dir / f"{project}_{bug_id}_diff.json"
        
        if cache_file.exists():
            with open(cache_file, 'r') as f:
                return json.load(f)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            buggy_dir = Path(tmpdir) / "buggy"
            fixed_dir = Path(tmpdir) / "fixed"
            
            # Checkout both versions
            for version, target_dir in [("b", buggy_dir), ("f", fixed_dir)]:
                checkout_cmd = [
                    str(self.d4j_cmd), "checkout",
                    "-p", project, "-v", f"{bug_id}{version}",
                    "-w", str(target_dir)
                ]
                subprocess.run(checkout_cmd, capture_output=True, check=True)
            
            # Find modified Java files
            diff_result = subprocess.run(
                ["diff", "-rq", str(buggy_dir), str(fixed_dir)],
                capture_output=True, text=True
            )
            
            methods_diff = []
            for line in diff_result.stdout.split('\n'):
                if 'differ' in line and '.java' in line:
                    # Extract file path
                    parts = line.split()
                    if len(parts) >= 4:
                        buggy_file = Path(parts[1])
                        fixed_file = Path(parts[3])
                        
                        # Extract methods that changed
                        methods = self._extract_changed_methods(
                            buggy_file, fixed_file
                        )
                        methods_diff.extend(methods)
            
            result = {
                "project": project,
                "bug_id": bug_id,
                "modified_methods": methods_diff
            }
            
            # Cache result
            with open(cache_file, 'w') as f:
                json.dump(result, f, indent=2)
            
            return result
    
    def _extract_changed_methods(self, buggy_file: Path, fixed_file: Path) -> List[Dict]:
        """Extract methods that changed between two versions"""
        # This is simplified - in production, use proper Java AST parser
        with open(buggy_file, 'r') as f:
            buggy_content = f.read()
        with open(fixed_file, 'r') as f:
            fixed_content = f.read()
        
        # Get unified diff
        diff_cmd = ["diff", "-u", str(buggy_file), str(fixed_file)]
        diff_result = subprocess.run(diff_cmd, capture_output=True, text=True)
        
        # Parse diff to find changed line ranges
        changed_lines = self._parse_diff_hunks(diff_result.stdout)
        
        # Extract methods containing changed lines
        buggy_methods = self._extract_methods_at_lines(buggy_content, changed_lines)
        fixed_methods = self._extract_methods_at_lines(fixed_content, changed_lines)
        
        methods = []
        for method_name in buggy_methods:
            methods.append({
                "method_name": method_name,
                "buggy_code": buggy_methods[method_name],
                "fixed_code": fixed_methods.get(method_name, ""),
                "file_path": str(buggy_file.name)
            })
        
        return methods
    
    def _parse_diff_hunks(self, diff_output: str) -> List[Tuple[int, int]]:
        """Parse unified diff to get changed line ranges"""
        ranges = []
        for line in diff_output.split('\n'):
            if line.startswith('@@'):
                # Parse hunk header: @@ -start,count +start,count @@
                match = re.match(r'@@ -(\d+),?(\d*) \+(\d+),?(\d*) @@', line)
                if match:
                    start = int(match.group(3))
                    count = int(match.group(4)) if match.group(4) else 1
                    ranges.append((start, start + count))
        return ranges
    
    def _extract_methods_at_lines(self, content: str, line_ranges: List[Tuple[int, int]]) -> Dict[str, str]:
        """Extract methods that contain the specified line ranges"""
        methods = {}
        lines = content.split('\n')
        
        # Simple method extraction (production should use AST)
        current_method = []
        method_name = None
        brace_count = 0
        
        for i, line in enumerate(lines, 1):
            # Detect method start
            if re.match(r'\s*(public|private|protected).*\(.*\)\s*{?', line):
                if brace_count == 0:
                    # Extract method name
                    match = re.search(r'(\w+)\s*\(', line)
                    if match:
                        method_name = match.group(1)
                        current_method = [line]
                        if '{' in line:
                            brace_count = 1
            elif current_method:
                current_method.append(line)
                brace_count += line.count('{') - line.count('}')
                
                if brace_count == 0 and method_name:
                    # Check if this method contains changed lines
                    method_start = i - len(current_method) + 1
                    method_end = i
                    
                    for start, end in line_ranges:
                        if not (end < method_start or start > method_end):
                            methods[method_name] = '\n'.join(current_method)
                            break
                    
                    current_method = []
                    method_name = None
        
        return methods

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Extract all performance bugs
    extractor = Defects4JExtractor()
    performance_bugs = extractor.extract_all_performance_bugs()
    
    # Extract diffs for each bug
    diff_extractor = CodeDiffExtractor()
    for bug in performance_bugs[:5]:  # Test with first 5
        diff = diff_extractor.extract_method_diff(bug.project, bug.bug_id)
        print(f"Extracted diff for {bug.identifier}: {len(diff['modified_methods'])} methods")