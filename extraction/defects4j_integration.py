"""
Defects4J Integration Module
Proper integration with Defects4J framework using CSV metadata and command-line tools.
"""

import csv
import json
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import pandas as pd
import re

from ..config import DEFECTS4J_HOME, DEFECTS4J_PROJECTS, DATA_DIR

logger = logging.getLogger(__name__)

@dataclass
class Defects4JBug:
    """Bug data structure matching Defects4J format"""
    project: str
    bug_id: int
    identifier: str
    buggy_commit: str
    fixed_commit: str
    report_id: str
    report_url: str
    
    # Extracted metadata
    modified_classes: List[str] = None
    trigger_tests: List[str] = None
    patch_content: str = ""
    
    # Performance analysis
    is_performance_bug: bool = False
    performance_keywords: List[str] = None
    performance_score: float = 0.0

class Defects4JIntegrator:
    """
    Proper Defects4J integration using the framework's metadata and tools.
    Uses CSV files and command-line interface as recommended.
    """
    
    def __init__(self, defects4j_path: str):
        self.d4j_path = Path(defects4j_path)
        self.framework_path = self.d4j_path / "framework"
        self.projects_path = self.framework_path / "projects"
        self.bin_path = self.framework_path / "bin"
        
        # Performance keywords from the paper methodology
        self.performance_keywords = [
            "performance", "slow", "fast", "speed", "optimize", "optimization",
            "efficient", "efficiency", "inefficient", "memory", "heap", "gc",
            "garbage", "leak", "cpu", "thread", "latency", "delay", "timeout",
            "hang", "freeze", "time", "duration", "complexity", "o(n", "quadratic",
            "linear", "scale", "scaling", "loop", "nested", "redundant", 
            "unnecessary", "bottleneck", "hotspot", "cache", "buffer"
        ]
    
    def load_project_bugs(self, project: str) -> List[Defects4JBug]:
        """Load all bugs for a project from CSV metadata"""
        project_dir = self.projects_path / project
        active_bugs_csv = project_dir / "active-bugs.csv"
        
        if not active_bugs_csv.exists():
            logger.error(f"No active bugs CSV found for {project}")
            return []
        
        bugs = []
        try:
            with open(active_bugs_csv, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    bug = Defects4JBug(
                        project=project,
                        bug_id=int(row['bug.id']),
                        identifier=f"{project}-{row['bug.id']}",
                        buggy_commit=row['revision.id.buggy'],
                        fixed_commit=row['revision.id.fixed'],
                        report_id=row['report.id'],
                        report_url=row['report.url']
                    )
                    bugs.append(bug)
            
            logger.info(f"Loaded {len(bugs)} bugs from {project}")
            
        except Exception as e:
            logger.error(f"Failed to load bugs from {project}: {e}")
        
        return bugs
    
    def enrich_bug_metadata(self, bug: Defects4JBug) -> Defects4JBug:
        """Enrich bug with additional metadata from Defects4J files"""
        project_dir = self.projects_path / bug.project
        
        # Load modified classes
        modified_classes_file = project_dir / "modified_classes" / f"{bug.bug_id}.src"
        if modified_classes_file.exists():
            with open(modified_classes_file, 'r') as f:
                bug.modified_classes = [line.strip() for line in f if line.strip()]
        
        # Load trigger tests
        trigger_tests_file = project_dir / "trigger_tests" / str(bug.bug_id)
        if trigger_tests_file.exists():
            with open(trigger_tests_file, 'r') as f:
                content = f.read()
                # Extract test method names from the stack trace
                test_methods = re.findall(r'(\w+::\w+)', content)
                bug.trigger_tests = test_methods
        
        # Load patch content
        patch_file = project_dir / "patches" / f"{bug.bug_id}.src.patch"
        if patch_file.exists():
            with open(patch_file, 'r') as f:
                bug.patch_content = f.read()
        
        return bug
    
    def analyze_performance_indicators(self, bug: Defects4JBug) -> Defects4JBug:
        """Analyze if bug is performance-related using multiple signals"""
        score = 0.0
        keywords_found = []
        
        # 1. Check issue title/URL for performance keywords (from JIRA URL)
        if bug.report_id:
            report_lower = bug.report_id.lower()
            for keyword in self.performance_keywords:
                if keyword in report_lower:
                    score += 0.2
                    keywords_found.append(keyword)
        
        # 2. Analyze patch content for performance patterns
        if bug.patch_content:
            patch_lower = bug.patch_content.lower()
            
            # Look for performance-related changes
            perf_patterns = {
                'loop_optimization': ['for.*while', 'nested.*loop', 'iteration'],
                'algorithm_change': ['arraylist.*hashmap', 'o\\(n\\)', 'complexity'],
                'caching': ['cache', 'memoiz', 'store', 'reuse'],
                'memory_optimization': ['stringbuilder', 'buffer', 'memory'],
                'redundancy_removal': ['redundant', 'duplicate', 'unnecessary']
            }
            
            for pattern_type, patterns in perf_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, patch_lower):
                        score += 0.15
                        keywords_found.append(pattern_type)
        
        # 3. Analyze specific patch changes
        if bug.patch_content:
            # Look for specific performance-related changes
            patch = bug.patch_content
            
            # Missing break statements (potential fall-through optimization)
            if '- break;' in patch and '+ break;' not in patch:
                score += 0.1
                keywords_found.append('break_removal')
            
            # String concatenation optimization
            if 'StringBuilder' in patch or 'StringBuffer' in patch:
                score += 0.2
                keywords_found.append('string_optimization')
            
            # Collection type changes
            if any(x in patch for x in ['ArrayList', 'HashMap', 'LinkedList', 'TreeMap']):
                score += 0.15
                keywords_found.append('collection_optimization')
            
            # Synchronization changes
            if any(x in patch for x in ['synchronized', 'volatile', 'concurrent']):
                score += 0.1
                keywords_found.append('concurrency_optimization')
        
        # Update bug with performance analysis
        bug.performance_score = min(1.0, score)
        bug.performance_keywords = list(set(keywords_found))
        bug.is_performance_bug = score >= 0.2  # Lower threshold for broader inclusion
        
        return bug
    
    def extract_all_performance_bugs(self, target_count: int = 490) -> List[Defects4JBug]:
        """
        Extract performance bugs from all projects until we have target_count.
        Implements the methodology from Section IV of the paper.
        """
        all_bugs = []
        performance_bugs = []
        
        # Process each project
        for project in DEFECTS4J_PROJECTS:
            logger.info(f"Processing project: {project}")
            
            # Load bugs from CSV
            project_bugs = self.load_project_bugs(project)
            
            for bug in project_bugs:
                # Enrich with Defects4J metadata
                bug = self.enrich_bug_metadata(bug)
                
                # Analyze performance indicators
                bug = self.analyze_performance_indicators(bug)
                
                all_bugs.append(bug)
                
                if bug.is_performance_bug:
                    performance_bugs.append(bug)
                    logger.debug(f"Found performance bug: {bug.identifier} (score: {bug.performance_score:.2f})")
                
                # Stop if we have enough performance bugs
                if len(performance_bugs) >= target_count:
                    break
            
            if len(performance_bugs) >= target_count:
                break
        
        logger.info(f"Extracted {len(performance_bugs)} performance bugs from {len(all_bugs)} total bugs")
        return performance_bugs[:target_count]
    
    def query_bug_metadata(self, project: str, properties: List[str]) -> pd.DataFrame:
        """Use defects4j query command to get structured metadata"""
        try:
            # Build query command
            prop_str = ",".join(properties)
            cmd = [str(self.bin_path / "defects4j"), "query", "-p", project, "-q", prop_str]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            # Parse CSV output
            from io import StringIO
            df = pd.read_csv(StringIO(result.stdout))
            return df
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to query {project}: {e}")
            return pd.DataFrame()
    
    def analyze_bug_patterns(self, bugs: List[Defects4JBug]) -> Dict:
        """Analyze patterns in performance bugs for categorization"""
        patterns = {
            'algorithmic_inefficiency': {
                'keywords': ['loop', 'nested', 'complexity', 'o(n', 'quadratic', 'linear'],
                'patches': ['for.*for', 'while.*while', 'nested.*loop'],
                'count': 0
            },
            'memory_usage': {
                'keywords': ['memory', 'heap', 'gc', 'garbage', 'leak', 'stringbuilder'],
                'patches': ['StringBuilder', 'StringBuffer', 'memory', 'heap'],
                'count': 0
            },
            'cpu_overhead': {
                'keywords': ['cpu', 'thread', 'synchroniz', 'concurrent', 'volatile'],
                'patches': ['synchronized', 'volatile', 'concurrent', 'thread'],
                'count': 0
            },
            'redundant_computation': {
                'keywords': ['redundant', 'duplicate', 'unnecessary', 'repeated', 'cache'],
                'patches': ['redundant', 'duplicate', 'cache', 'memoiz'],
                'count': 0
            },
            'io_inefficiency': {
                'keywords': ['io', 'file', 'stream', 'buffer', 'reader', 'writer'],
                'patches': ['InputStream', 'OutputStream', 'buffer', 'Reader', 'Writer'],
                'count': 0
            }
        }
        
        # Analyze each bug
        for bug in bugs:
            if not bug.is_performance_bug:
                continue
            
            # Check keywords and patch content
            text_to_check = (
                " ".join(bug.performance_keywords) + " " + 
                bug.patch_content.lower()
            )
            
            best_category = None
            best_score = 0
            
            for category, pattern_info in patterns.items():
                score = 0
                
                # Check keywords
                for keyword in pattern_info['keywords']:
                    if keyword in text_to_check:
                        score += 1
                
                # Check patch patterns
                for pattern in pattern_info['patches']:
                    if re.search(pattern.lower(), text_to_check):
                        score += 2
                
                if score > best_score:
                    best_score = score
                    best_category = category
            
            if best_category:
                patterns[best_category]['count'] += 1
        
        return patterns
    
    def save_performance_dataset(self, bugs: List[Defects4JBug], output_file: str):
        """Save performance bugs dataset in the format expected by the paper"""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to the format used in the paper
        dataset = []
        for bug in bugs:
            if bug.is_performance_bug:
                bug_data = {
                    "identifier": bug.identifier,
                    "project": bug.project,
                    "bug_id": bug.bug_id,
                    "buggy_commit": bug.buggy_commit,
                    "fixed_commit": bug.fixed_commit,
                    "report_id": bug.report_id,
                    "report_url": bug.report_url,
                    "modified_classes": bug.modified_classes or [],
                    "trigger_tests": bug.trigger_tests or [],
                    "patch_content": bug.patch_content,
                    "performance_keywords": bug.performance_keywords or [],
                    "performance_score": bug.performance_score,
                    "extracted_from": "defects4j_framework"
                }
                dataset.append(bug_data)
        
        with open(output_path, 'w') as f:
            json.dump(dataset, f, indent=2)
        
        logger.info(f"Saved {len(dataset)} performance bugs to {output_path}")
        return len(dataset)

def main():
    """Main extraction function"""
    logging.basicConfig(level=logging.INFO)
    
    # Initialize integrator with the cloned Defects4J path
    integrator = Defects4JIntegrator("/tmp/defects4j-repo")
    
    logger.info("Starting Defects4J performance bug extraction")
    
    # Extract performance bugs
    performance_bugs = integrator.extract_all_performance_bugs(target_count=490)
    
    # Analyze patterns for categorization
    patterns = integrator.analyze_bug_patterns(performance_bugs)
    
    logger.info("Performance bug categories found:")
    for category, info in patterns.items():
        logger.info(f"  {category}: {info['count']} bugs")
    
    # Save dataset
    output_file = DATA_DIR / "defects4j_performance_bugs.json"
    count = integrator.save_performance_dataset(performance_bugs, str(output_file))
    
    # Save pattern analysis
    pattern_file = DATA_DIR / "performance_patterns.json"
    with open(pattern_file, 'w') as f:
        json.dump(patterns, f, indent=2)
    
    logger.info(f"Extraction complete. Found {count} performance bugs.")
    return performance_bugs

if __name__ == "__main__":
    main()