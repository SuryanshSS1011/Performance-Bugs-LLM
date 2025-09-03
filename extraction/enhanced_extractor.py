"""
Enhanced Defects4J extractor with detailed bug information extraction.
Implements the complete extraction methodology from Section IV of the paper.
"""

import json
import logging
import subprocess
import tempfile
import shutil
import csv
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime
import hashlib
import re

from ..config import DEFECTS4J_HOME, DEFECTS4J_PROJECTS, CACHE_DIR
from ..utils.java_parser import JavaParser, CodeDiffAnalyzer

logger = logging.getLogger(__name__)

@dataclass
class DetailedBugInfo:
    """Complete bug information as described in the paper"""
    # Basic identification
    project: str
    bug_id: int
    identifier: str  # Format: Project-BugID
    
    # Version control info
    buggy_commit: str
    fixed_commit: str
    commit_date: str
    commit_message: str
    commit_author: str
    
    # Bug tracking info
    issue_id: Optional[str]
    issue_url: Optional[str]
    issue_title: Optional[str]
    issue_description: Optional[str]
    
    # Code changes
    modified_files: List[str]
    modified_methods: List[Dict]  # Method-level changes
    added_lines: int
    removed_lines: int
    
    # Test information
    failing_tests: List[str]
    test_error_messages: List[str]
    
    # Performance indicators
    is_performance_bug: bool
    performance_keywords: List[str]
    performance_score: float
    
    # Categorization (filled later)
    category: Optional[str] = None
    category_confidence: Optional[float] = None
    
    # Timestamps
    extracted_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)

class EnhancedDefects4JExtractor:
    """
    Enhanced extractor that implements the complete methodology from the paper.
    Extracts 490 performance bugs with detailed information.
    """
    
    def __init__(self, defects4j_home: str = DEFECTS4J_HOME):
        self.d4j_home = Path(defects4j_home)
        self.d4j_cmd = self.d4j_home / "framework" / "bin" / "defects4j"
        self.projects_path = self.d4j_home / "framework" / "projects"
        self.cache_dir = CACHE_DIR / "enhanced_extraction"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Performance keywords from the paper
        self.performance_keywords = [
            # Primary indicators
            "performance", "slow", "fast", "speed", "optimize", "optimization",
            "efficient", "efficiency", "inefficient",
            
            # Resource-related
            "memory", "heap", "gc", "garbage", "leak", "cpu", "thread",
            "resource", "cache", "buffer",
            
            # Time-related
            "latency", "delay", "timeout", "hang", "freeze", "responsive",
            "time", "duration", "quick",
            
            # Complexity-related
            "complexity", "o(n", "quadratic", "linear", "exponential",
            "scale", "scaling", "scalability",
            
            # Specific patterns
            "loop", "nested", "redundant", "unnecessary", "repeated",
            "bottleneck", "hotspot"
        ]
        
        self.diff_analyzer = CodeDiffAnalyzer()
    
    def extract_all_bugs(self, projects: List[str] = None) -> List[DetailedBugInfo]:
        """Extract all bugs from specified projects"""
        if projects is None:
            projects = DEFECTS4J_PROJECTS
        
        all_bugs = []
        for project in projects:
            logger.info(f"Extracting bugs from project: {project}")
            project_bugs = self.extract_project_bugs(project)
            all_bugs.extend(project_bugs)
            logger.info(f"Extracted {len(project_bugs)} bugs from {project}")
        
        return all_bugs
    
    def extract_project_bugs(self, project: str) -> List[DetailedBugInfo]:
        """Extract all bugs from a specific project"""
        bugs = []
        
        # Get bug IDs
        bug_ids = self._get_bug_ids(project)
        logger.info(f"Found {len(bug_ids)} bugs in {project}")
        
        for bug_id in bug_ids:
            cache_file = self.cache_dir / f"{project}_{bug_id}_detailed.json"
            
            if cache_file.exists():
                # Load from cache
                with open(cache_file, 'r') as f:
                    bug_data = json.load(f)
                    bug = DetailedBugInfo(**bug_data)
            else:
                # Extract bug information
                bug = self._extract_detailed_bug_info(project, bug_id)
                if bug:
                    # Save to cache
                    with open(cache_file, 'w') as f:
                        json.dump(bug.to_dict(), f, indent=2)
            
            if bug:
                bugs.append(bug)
        
        return bugs
    
    def _get_bug_ids(self, project: str) -> List[int]:
        """Get all bug IDs for a project using CSV file"""
        try:
            csv_file = self.projects_path / project / "active-bugs.csv"
            if not csv_file.exists():
                return []
            
            bug_ids = []
            with open(csv_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    bug_ids.append(int(row['bug.id']))
            
            return bug_ids
        except Exception as e:
            logger.error(f"Failed to get bug IDs for {project}: {e}")
            return []
    
    def _extract_detailed_bug_info(self, project: str, bug_id: int) -> Optional[DetailedBugInfo]:
        """Extract comprehensive information about a bug"""
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                tmpdir = Path(tmpdir)
                
                # Checkout both versions
                buggy_dir = tmpdir / "buggy"
                fixed_dir = tmpdir / "fixed"
                
                # Checkout buggy version
                self._checkout_version(project, bug_id, "b", buggy_dir)
                # Checkout fixed version
                self._checkout_version(project, bug_id, "f", fixed_dir)
                
                # Get basic info
                info = self._get_bug_info(project, bug_id)
                
                # Get commit information
                commit_info = self._get_commit_info(fixed_dir)
                
                # Get code changes
                code_changes = self._analyze_code_changes(buggy_dir, fixed_dir)
                
                # Get test information
                test_info = self._get_test_info(project, bug_id, buggy_dir)
                
                # Check if it's a performance bug
                perf_check = self._check_performance_bug(
                    commit_info.get("message", ""),
                    code_changes,
                    test_info
                )
                
                # Create detailed bug info
                bug = DetailedBugInfo(
                    project=project,
                    bug_id=bug_id,
                    identifier=f"{project}-{bug_id}",
                    buggy_commit=info.get("buggy_commit", ""),
                    fixed_commit=info.get("fixed_commit", ""),
                    commit_date=commit_info.get("date", ""),
                    commit_message=commit_info.get("message", ""),
                    commit_author=commit_info.get("author", ""),
                    issue_id=info.get("issue_id"),
                    issue_url=info.get("issue_url"),
                    issue_title=None,  # Would need to fetch from issue tracker
                    issue_description=None,
                    modified_files=code_changes.get("modified_files", []),
                    modified_methods=code_changes.get("modified_methods", []),
                    added_lines=code_changes.get("added_lines", 0),
                    removed_lines=code_changes.get("removed_lines", 0),
                    failing_tests=test_info.get("failing_tests", []),
                    test_error_messages=test_info.get("error_messages", []),
                    is_performance_bug=perf_check["is_performance"],
                    performance_keywords=perf_check["keywords_found"],
                    performance_score=perf_check["score"]
                )
                
                return bug
                
        except Exception as e:
            logger.error(f"Failed to extract bug {project}-{bug_id}: {e}")
            return None
    
    def _checkout_version(self, project: str, bug_id: int, version: str, target_dir: Path):
        """Checkout a specific version of a bug"""
        subprocess.run(
            [str(self.d4j_cmd), "checkout", "-p", project, 
             "-v", f"{bug_id}{version}", "-w", str(target_dir)],
            capture_output=True, check=True
        )
    
    def _get_bug_info(self, project: str, bug_id: int) -> Dict:
        """Get basic bug information from Defects4J"""
        info = {}
        
        try:
            result = subprocess.run(
                [str(self.d4j_cmd), "info", "-p", project, "-b", str(bug_id)],
                capture_output=True, text=True, check=True
            )
            
            for line in result.stdout.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    if "Revision ID(buggy)" in key:
                        info["buggy_commit"] = value
                    elif "Revision ID(fixed)" in key:
                        info["fixed_commit"] = value
                    elif "Report ID" in key:
                        info["issue_id"] = value
                    elif "Report URL" in key:
                        info["issue_url"] = value
        except:
            pass
        
        return info
    
    def _get_commit_info(self, repo_dir: Path) -> Dict:
        """Get commit information from git"""
        info = {}
        
        try:
            # Get commit message
            result = subprocess.run(
                ["git", "log", "-1", "--format=%B"],
                cwd=repo_dir, capture_output=True, text=True
            )
            info["message"] = result.stdout.strip()
            
            # Get commit author
            result = subprocess.run(
                ["git", "log", "-1", "--format=%an <%ae>"],
                cwd=repo_dir, capture_output=True, text=True
            )
            info["author"] = result.stdout.strip()
            
            # Get commit date
            result = subprocess.run(
                ["git", "log", "-1", "--format=%ai"],
                cwd=repo_dir, capture_output=True, text=True
            )
            info["date"] = result.stdout.strip()
        except:
            pass
        
        return info
    
    def _analyze_code_changes(self, buggy_dir: Path, fixed_dir: Path) -> Dict:
        """Analyze code changes between buggy and fixed versions"""
        changes = {
            "modified_files": [],
            "modified_methods": [],
            "added_lines": 0,
            "removed_lines": 0
        }
        
        # Get list of Java files
        java_files = self._find_java_files(buggy_dir)
        
        for java_file in java_files:
            rel_path = java_file.relative_to(buggy_dir)
            fixed_file = fixed_dir / rel_path
            
            if fixed_file.exists():
                # Compare files
                with open(java_file, 'r') as f:
                    buggy_content = f.read()
                with open(fixed_file, 'r') as f:
                    fixed_content = f.read()
                
                if buggy_content != fixed_content:
                    changes["modified_files"].append(str(rel_path))
                    
                    # Extract method-level changes
                    method_changes = self._extract_method_changes(
                        buggy_content, fixed_content, str(rel_path)
                    )
                    changes["modified_methods"].extend(method_changes)
                    
                    # Count line changes
                    buggy_lines = buggy_content.count('\n')
                    fixed_lines = fixed_content.count('\n')
                    if fixed_lines > buggy_lines:
                        changes["added_lines"] += fixed_lines - buggy_lines
                    else:
                        changes["removed_lines"] += buggy_lines - fixed_lines
        
        return changes
    
    def _find_java_files(self, directory: Path) -> List[Path]:
        """Find all Java files in a directory"""
        return list(directory.glob("**/*.java"))
    
    def _extract_method_changes(self, buggy_content: str, fixed_content: str, 
                               file_path: str) -> List[Dict]:
        """Extract method-level changes"""
        changes = []
        
        try:
            # Parse both versions
            buggy_parser = JavaParser()
            fixed_parser = JavaParser()
            
            if buggy_parser.parse(buggy_content) and fixed_parser.parse(fixed_content):
                # Find changed methods
                changed_methods = buggy_parser.find_changed_methods(fixed_parser)
                
                for buggy_method, fixed_method in changed_methods:
                    # Analyze the change
                    analysis = self.diff_analyzer.analyze_diff(
                        buggy_method.body, fixed_method.body
                    )
                    
                    changes.append({
                        "file": file_path,
                        "method_name": buggy_method.name,
                        "buggy_code": buggy_method.body,
                        "fixed_code": fixed_method.body,
                        "buggy_complexity": buggy_method.complexity,
                        "fixed_complexity": fixed_method.complexity,
                        "analysis": analysis
                    })
        except Exception as e:
            logger.debug(f"Could not parse methods in {file_path}: {e}")
            # Fallback to file-level change
            changes.append({
                "file": file_path,
                "method_name": "unknown",
                "buggy_code": buggy_content[:1000],  # First 1000 chars
                "fixed_code": fixed_content[:1000],
                "analysis": {}
            })
        
        return changes
    
    def _get_test_info(self, project: str, bug_id: int, buggy_dir: Path) -> Dict:
        """Get information about failing tests"""
        info = {
            "failing_tests": [],
            "error_messages": []
        }
        
        try:
            # Get failing tests
            result = subprocess.run(
                [str(self.d4j_cmd), "test", "-r", "-w", str(buggy_dir)],
                capture_output=True, text=True, timeout=300
            )
            
            # Parse test results
            for line in result.stdout.split('\n'):
                if "FAIL" in line:
                    test_name = line.split()[0]
                    info["failing_tests"].append(test_name)
                elif "Error:" in line or "Failure:" in line:
                    info["error_messages"].append(line)
        except:
            pass
        
        return info
    
    def _check_performance_bug(self, commit_message: str, 
                              code_changes: Dict, test_info: Dict) -> Dict:
        """
        Check if a bug is performance-related using multiple signals.
        Implements the filtering logic from Section IV.A of the paper.
        """
        score = 0.0
        keywords_found = []
        
        # Check commit message (highest weight)
        commit_lower = commit_message.lower()
        for keyword in self.performance_keywords:
            if keyword in commit_lower:
                score += 0.3
                keywords_found.append(keyword)
        
        # Check for performance patterns in code changes
        for method_change in code_changes.get("modified_methods", []):
            analysis = method_change.get("analysis", {})
            
            # Complexity reduction is a strong signal
            if analysis.get("complexity_changes", {}).get("loop_reduction"):
                score += 0.2
                keywords_found.append("loop_reduction")
            
            # Algorithm change (e.g., ArrayList to HashMap)
            if analysis.get("complexity_changes", {}).get("algorithm_change"):
                score += 0.2
                keywords_found.append("algorithm_change")
            
            # Caching added
            if analysis.get("complexity_changes", {}).get("caching_added"):
                score += 0.15
                keywords_found.append("caching")
            
            # Buffering added
            if analysis.get("complexity_changes", {}).get("buffering_added"):
                score += 0.15
                keywords_found.append("buffering")
        
        # Check test messages for performance keywords
        for msg in test_info.get("error_messages", []):
            msg_lower = msg.lower()
            if any(kw in msg_lower for kw in ["timeout", "slow", "performance"]):
                score += 0.1
                keywords_found.append("test_performance")
        
        # Normalize score
        score = min(1.0, score)
        
        return {
            "is_performance": score >= 0.3,  # Threshold for performance bug
            "score": score,
            "keywords_found": list(set(keywords_found))
        }
    
    def filter_performance_bugs(self, bugs: List[DetailedBugInfo], 
                               threshold: float = 0.3) -> List[DetailedBugInfo]:
        """Filter to keep only performance-related bugs"""
        perf_bugs = [bug for bug in bugs if bug.performance_score >= threshold]
        
        logger.info(f"Filtered {len(bugs)} bugs to {len(perf_bugs)} performance bugs")
        logger.info(f"Performance bug rate: {len(perf_bugs)/len(bugs)*100:.1f}%")
        
        return perf_bugs
    
    def save_bugs(self, bugs: List[DetailedBugInfo], output_file: str):
        """Save bugs to JSON file"""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump([bug.to_dict() for bug in bugs], f, indent=2)
        
        logger.info(f"Saved {len(bugs)} bugs to {output_path}")
    
    def generate_statistics(self, bugs: List[DetailedBugInfo]) -> Dict:
        """Generate statistics about extracted bugs"""
        perf_bugs = [b for b in bugs if b.is_performance_bug]
        
        stats = {
            "total_bugs": len(bugs),
            "performance_bugs": len(perf_bugs),
            "performance_rate": len(perf_bugs) / len(bugs) * 100 if bugs else 0,
            "by_project": {},
            "keyword_frequency": {},
            "complexity_reductions": 0,
            "algorithm_changes": 0,
            "caching_additions": 0,
            "buffering_additions": 0
        }
        
        # Count by project
        for bug in perf_bugs:
            project = bug.project
            if project not in stats["by_project"]:
                stats["by_project"][project] = 0
            stats["by_project"][project] += 1
        
        # Count keyword frequency
        for bug in perf_bugs:
            for keyword in bug.performance_keywords:
                if keyword not in stats["keyword_frequency"]:
                    stats["keyword_frequency"][keyword] = 0
                stats["keyword_frequency"][keyword] += 1
        
        # Count specific improvements
        for bug in perf_bugs:
            for method in bug.modified_methods:
                analysis = method.get("analysis", {})
                changes = analysis.get("complexity_changes", {})
                
                if changes.get("loop_reduction"):
                    stats["complexity_reductions"] += 1
                if changes.get("algorithm_change"):
                    stats["algorithm_changes"] += 1
                if changes.get("caching_added"):
                    stats["caching_additions"] += 1
                if changes.get("buffering_added"):
                    stats["buffering_additions"] += 1
        
        return stats

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Test extraction
    extractor = EnhancedDefects4JExtractor()
    
    # Extract bugs from a sample project
    bugs = extractor.extract_project_bugs("Collections")
    
    # Filter performance bugs
    perf_bugs = extractor.filter_performance_bugs(bugs)
    
    # Generate statistics
    stats = extractor.generate_statistics(bugs)
    print(json.dumps(stats, indent=2))
    
    # Save results
    extractor.save_bugs(perf_bugs, "data/collections_performance_bugs.json")