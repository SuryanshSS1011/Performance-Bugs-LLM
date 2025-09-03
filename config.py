"""
Configuration module for Performance Bugs LLM system.
Supports flexible model selection and dynamic experiment configuration.
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

# Optional YAML import
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent

# Base paths
BASE_DIR = PROJECT_ROOT
DATA_DIR = BASE_DIR / "data"
DATASET_DIR = DATA_DIR / "dataset"
MODELS_DIR = BASE_DIR / "models"
RESULTS_DIR = BASE_DIR / "results"
CACHE_DIR = BASE_DIR / ".cache"
VIZ_DIR = RESULTS_DIR / "visualizations"

# Ensure directories exist
for dir_path in [DATA_DIR, DATASET_DIR, MODELS_DIR, RESULTS_DIR, CACHE_DIR, VIZ_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# Load configuration from YAML if exists
CONFIG_FILE = PROJECT_ROOT / "config.yaml"

def load_yaml_config():
    """Load configuration from YAML file if it exists"""
    if CONFIG_FILE.exists() and YAML_AVAILABLE:
        with open(CONFIG_FILE, 'r') as f:
            return yaml.safe_load(f)
    return None

# Load YAML config or use defaults
yaml_config = load_yaml_config() if YAML_AVAILABLE else None

# Defects4J Configuration
DEFECTS4J_HOME = os.getenv("DEFECTS4J_HOME", str(BASE_DIR / "defects4j"))
DEFECTS4J_PROJECTS = yaml_config['dataset']['projects'] if yaml_config else [
    "Chart", "Closure", "Lang", "Math", "Time",  # Original Defects4J
    "Collections", "Compress", "Codec", "Csv", "Gson",  # Extended
    "JacksonCore", "JacksonDatabind", "JacksonXml",
    "Jsoup", "JxPath", "Mockito", "Cli"
]

# Paper specifications (can vary based on actual dataset)
TOTAL_BUGS = 490  # Target from paper
LABELED_BUGS = 392  # Used for training (80%)
TEST_BUGS = 98  # 20% for testing
TRAIN_TEST_SPLIT = yaml_config['training']['test_split'] if yaml_config else 0.8

# Bug Categories with flexible distribution
BUG_CATEGORIES = {
    "algorithmic_inefficiency": {
        "description": "Use of inefficient algorithms or data structures",
        "expected_ratio": 0.337,
        "patterns": [
            r"O\(n[\^²2]\)",
            r"nested.*loop",
            r"bubble.*sort",
            r"inefficient.*algorithm",
            r"HashMap.*lookup"
        ],
        "examples": ["bubble sort", "nested loops for lookup", "inefficient search"]
    },
    "memory_usage": {
        "description": "Excessive or unnecessary memory allocations",
        "expected_ratio": 0.237,
        "patterns": [
            r"ArrayList\(\)",
            r"String\s*\+",
            r"new.*\[\]",
            r"StringBuilder",
            r"memory.*leak"
        ],
        "examples": ["String concatenation with +", "ArrayList without size"]
    },
    "redundant_computation": {
        "description": "Performing same calculations multiple times",
        "expected_ratio": 0.110,
        "patterns": [
            r"Math\.pow.*loop",
            r"calculate.*multiple",
            r"recomputing",
            r"cache",
            r"repeated.*calculation"
        ],
        "examples": ["Recomputing Math.pow", "uncached method calls"]
    },
    "cpu_overhead": {
        "description": "Operations that waste CPU cycles",
        "expected_ratio": 0.202,
        "patterns": [
            r"Integer.*int",
            r"boxing",
            r"unboxing",
            r"synchroniz",
            r"lock.*tight.*loop"
        ],
        "examples": ["boxing/unboxing", "excessive synchronization"]
    },
    "io_inefficiency": {
        "description": "Unoptimized I/O operations",
        "expected_ratio": 0.114,
        "patterns": [
            r"FileReader",
            r"BufferedReader",
            r"FileInputStream",
            r"unbuffered",
            r"I/O.*operation"
        ],
        "examples": ["FileReader instead of BufferedReader", "unbuffered I/O"]
    }
}

# Performance bug keywords (Section IV.A of paper)
PERFORMANCE_KEYWORDS = [
    "slow", "optimize", "performance", "latency", "speed",
    "efficient", "fast", "quick", "bottleneck", "overhead",
    "memory", "cpu", "resource", "scale", "timeout",
    "hang", "freeze", "unresponsive", "lag", "delay"
]

# Flexible Model Configuration
AVAILABLE_MODELS = {
    "gpt-4o-mini": {
        "temperature": 0.3,
        "max_tokens": 2048,
        "top_p": 0.95,
        "api_type": "openai"
    },
    "gpt-3.5-turbo": {
        "temperature": 0.4,
        "max_tokens": 1500,
        "top_p": 0.9,
        "api_type": "openai"
    },
    "gpt-4": {
        "temperature": 0.2,
        "max_tokens": 3000,
        "top_p": 0.95,
        "api_type": "openai"
    },
    "claude-3-haiku": {
        "temperature": 0.3,
        "max_tokens": 2000,
        "top_p": 0.9,
        "api_type": "anthropic"
    },
    "claude-3-sonnet": {
        "temperature": 0.3,
        "max_tokens": 2500,
        "top_p": 0.95,
        "api_type": "anthropic"
    }
}

# Default model selection
DEFAULT_MODEL = yaml_config['models']['default'] if yaml_config else "gpt-4o-mini"
MODEL_CONFIG = AVAILABLE_MODELS.get(DEFAULT_MODEL, AVAILABLE_MODELS["gpt-4o-mini"])

# Fine-tuning configuration
FINE_TUNING_CONFIG = {
    "n_epochs": 3,
    "batch_size": 4,
    "learning_rate_multiplier": 0.5,
    "validation_split": 0.1,
    "prompt_loss_weight": 0.1
}

# Evaluation Metrics Configuration (Section V.C)
EVALUATION_CONFIG = {
    "metrics": ["accuracy", "precision", "recall", "f1_score"],
    "report_quality_weights": {
        "root_cause_analysis": 0.35,
        "issue_identification": 0.25,
        "technical_precision": 0.25,
        "impact_assessment": 0.15
    },
    "quality_threshold": 0.75  # Scores >= 0.75 considered matches
}

# Results from paper (Table II and VI)
PAPER_RESULTS = {
    "overall": {
        "detection_rate": 0.837,  # 83.7%
        "report_match_rate": 0.902  # 90.2%
    },
    "by_category": {
        "algorithmic_inefficiency": {"detection": 0.909, "match": 0.933},
        "memory_usage": {"detection": 0.826, "match": 0.895},
        "redundant_computation": {"detection": 0.818, "match": 0.889},
        "cpu_overhead": {"detection": 0.800, "match": 0.875},
        "io_inefficiency": {"detection": 0.727, "match": 0.875}
    },
    "base_vs_finetuned": {
        "base": {"accuracy": 0.673, "precision": 0.651, "recall": 0.642, "f1": 0.646},
        "finetuned": {"accuracy": 0.837, "precision": 0.830, "recall": 0.818, "f1": 0.823}
    }
}

# Data Processing Configuration
DIFF_CONTEXT_LINES = 3
METHOD_EXTRACTION_CONTEXT = 50  # Lines around the change
MIN_METHOD_SIZE = 5  # Minimum lines for a valid method
MAX_METHOD_SIZE = 500  # Maximum lines to avoid huge methods

# API Keys (load from environment)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    print("Warning: OPENAI_API_KEY not set in environment")

# Logging Configuration
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default"
        },
        "file": {
            "class": "logging.FileHandler",
            "filename": str(BASE_DIR / "performance_bugs.log"),
            "formatter": "default"
        }
    },
    "root": {
        "level": "INFO",
        "handlers": ["console", "file"]
    }
}