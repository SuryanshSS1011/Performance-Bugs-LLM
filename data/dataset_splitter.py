"""
Dataset splitting module with stratification support.
Ensures proper train/test/validation splits while maintaining category balance.
"""

import json
import random
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from collections import defaultdict, Counter
from sklearn.model_selection import train_test_split
import logging

logger = logging.getLogger(__name__)

class DatasetSplitter:
    """
    Handles dataset splitting with stratification for performance bug categories.
    Ensures balanced representation across train/test/validation sets.
    """
    
    def __init__(self, random_seed: int = 42):
        """
        Initialize the dataset splitter.
        
        Args:
            random_seed: Random seed for reproducibility
        """
        self.random_seed = random_seed
        random.seed(random_seed)
        np.random.seed(random_seed)
        
    def load_dataset(self, file_path: Path) -> List[Dict]:
        """Load dataset from JSON file"""
        with open(file_path, 'r') as f:
            data = json.load(f)
            
        # Handle both formats: {"bugs": [...]} or direct list
        if isinstance(data, dict) and 'bugs' in data:
            return data['bugs']
        return data
    
    def analyze_distribution(self, dataset: List[Dict]) -> Dict[str, int]:
        """
        Analyze category distribution in the dataset.
        
        Args:
            dataset: List of bug records
            
        Returns:
            Dictionary with category counts
        """
        category_counts = Counter()
        
        for bug in dataset:
            category = bug.get('category', 'unknown')
            category_counts[category] += 1
            
        # Log distribution
        total = sum(category_counts.values())
        logger.info(f"Dataset distribution (total: {total}):")
        for category, count in sorted(category_counts.items()):
            percentage = (count / total) * 100
            logger.info(f"  {category}: {count} ({percentage:.1f}%)")
            
        return dict(category_counts)
    
    def stratified_split(
        self,
        dataset: List[Dict],
        test_size: float = 0.2,
        validation_size: Optional[float] = 0.1,
        stratify_by: str = 'category'
    ) -> Tuple[List[Dict], List[Dict], Optional[List[Dict]]]:
        """
        Perform stratified split of the dataset.
        
        Args:
            dataset: List of bug records
            test_size: Proportion of test set (0.2 = 20%)
            validation_size: Proportion of validation set (from training)
            stratify_by: Field to stratify by (default: 'category')
            
        Returns:
            Tuple of (train, test, validation) datasets
        """
        # Extract stratification labels
        labels = [bug.get(stratify_by, 'unknown') for bug in dataset]
        
        # First split: train+val vs test
        train_val, test, train_val_labels, test_labels = train_test_split(
            dataset, labels,
            test_size=test_size,
            stratify=labels,
            random_state=self.random_seed
        )
        
        # Second split: train vs validation (if requested)
        validation = None
        if validation_size:
            val_size_adjusted = validation_size / (1 - test_size)
            train, validation, train_labels, val_labels = train_test_split(
                train_val, train_val_labels,
                test_size=val_size_adjusted,
                stratify=train_val_labels,
                random_state=self.random_seed + 1
            )
        else:
            train = train_val
            
        # Log split statistics
        self._log_split_stats(train, test, validation)
        
        return train, test, validation
    
    def _log_split_stats(
        self, 
        train: List[Dict], 
        test: List[Dict], 
        validation: Optional[List[Dict]]
    ):
        """Log statistics about the dataset split"""
        logger.info("\nDataset split statistics:")
        logger.info(f"  Train: {len(train)} samples")
        logger.info(f"  Test: {len(test)} samples")
        if validation:
            logger.info(f"  Validation: {len(validation)} samples")
            
        # Category distribution per split
        for split_name, split_data in [("Train", train), ("Test", test), ("Validation", validation)]:
            if split_data:
                dist = Counter(bug.get('category', 'unknown') for bug in split_data)
                logger.info(f"\n  {split_name} distribution:")
                for cat, count in sorted(dist.items()):
                    logger.info(f"    {cat}: {count}")
    
    def ensure_minimum_samples(
        self,
        dataset: List[Dict],
        min_per_category: int = 5
    ) -> Tuple[List[Dict], Dict[str, int]]:
        """
        Ensure minimum samples per category for reliable training.
        
        Args:
            dataset: List of bug records
            min_per_category: Minimum samples required per category
            
        Returns:
            Filtered dataset and removed counts
        """
        category_counts = defaultdict(list)
        for bug in dataset:
            category = bug.get('category', 'unknown')
            category_counts[category].append(bug)
        
        filtered_dataset = []
        removed_counts = {}
        
        for category, bugs in category_counts.items():
            if len(bugs) >= min_per_category:
                filtered_dataset.extend(bugs)
            else:
                removed_counts[category] = len(bugs)
                logger.warning(f"Removing category '{category}' with only {len(bugs)} samples")
        
        return filtered_dataset, removed_counts
    
    def balance_dataset(
        self,
        dataset: List[Dict],
        strategy: str = 'undersample',
        target_ratio: Optional[Dict[str, float]] = None
    ) -> List[Dict]:
        """
        Balance the dataset using various strategies.
        
        Args:
            dataset: List of bug records
            strategy: 'undersample', 'oversample', or 'weighted'
            target_ratio: Target distribution ratios
            
        Returns:
            Balanced dataset
        """
        category_bugs = defaultdict(list)
        for bug in dataset:
            category = bug.get('category', 'unknown')
            category_bugs[category].append(bug)
        
        if strategy == 'undersample':
            # Find minimum class size
            min_size = min(len(bugs) for bugs in category_bugs.values())
            balanced = []
            for category, bugs in category_bugs.items():
                sampled = random.sample(bugs, min_size)
                balanced.extend(sampled)
                
        elif strategy == 'oversample':
            # Find maximum class size
            max_size = max(len(bugs) for bugs in category_bugs.values())
            balanced = []
            for category, bugs in category_bugs.items():
                if len(bugs) < max_size:
                    # Oversample with replacement
                    sampled = random.choices(bugs, k=max_size)
                else:
                    sampled = bugs
                balanced.extend(sampled)
                
        elif strategy == 'weighted' and target_ratio:
            # Sample according to target ratios
            total_target = sum(target_ratio.values())
            normalized_ratio = {k: v/total_target for k, v in target_ratio.items()}
            
            # Calculate target counts
            total_samples = len(dataset)
            balanced = []
            
            for category, ratio in normalized_ratio.items():
                if category in category_bugs:
                    target_count = int(total_samples * ratio)
                    bugs = category_bugs[category]
                    
                    if len(bugs) < target_count:
                        # Oversample
                        sampled = random.choices(bugs, k=target_count)
                    else:
                        # Undersample
                        sampled = random.sample(bugs, target_count)
                    balanced.extend(sampled)
        else:
            balanced = dataset
            
        random.shuffle(balanced)
        return balanced
    
    def create_cross_validation_folds(
        self,
        dataset: List[Dict],
        n_folds: int = 5
    ) -> List[Tuple[List[Dict], List[Dict]]]:
        """
        Create cross-validation folds with stratification.
        
        Args:
            dataset: List of bug records
            n_folds: Number of folds
            
        Returns:
            List of (train, validation) tuples
        """
        from sklearn.model_selection import StratifiedKFold
        
        labels = [bug.get('category', 'unknown') for bug in dataset]
        skf = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=self.random_seed)
        
        folds = []
        for train_idx, val_idx in skf.split(dataset, labels):
            train_fold = [dataset[i] for i in train_idx]
            val_fold = [dataset[i] for i in val_idx]
            folds.append((train_fold, val_fold))
            
        return folds
    
    def save_splits(
        self,
        train: List[Dict],
        test: List[Dict],
        validation: Optional[List[Dict]],
        output_dir: Path
    ):
        """Save dataset splits to files"""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save train set
        train_file = output_dir / "train.json"
        with open(train_file, 'w') as f:
            json.dump(train, f, indent=2)
        logger.info(f"Saved training set to {train_file}")
        
        # Save test set
        test_file = output_dir / "test.json"
        with open(test_file, 'w') as f:
            json.dump(test, f, indent=2)
        logger.info(f"Saved test set to {test_file}")
        
        # Save validation set if provided
        if validation:
            val_file = output_dir / "validation.json"
            with open(val_file, 'w') as f:
                json.dump(validation, f, indent=2)
            logger.info(f"Saved validation set to {val_file}")
        
        # Save split metadata
        metadata = {
            "train_size": len(train),
            "test_size": len(test),
            "validation_size": len(validation) if validation else 0,
            "train_distribution": dict(Counter(b.get('category') for b in train)),
            "test_distribution": dict(Counter(b.get('category') for b in test)),
            "validation_distribution": dict(Counter(b.get('category') for b in validation)) if validation else {},
            "random_seed": self.random_seed
        }
        
        metadata_file = output_dir / "split_metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        logger.info(f"Saved split metadata to {metadata_file}")
        
        return metadata


def main():
    """Example usage of DatasetSplitter"""
    from config import DATA_DIR
    
    # Initialize splitter
    splitter = DatasetSplitter(random_seed=42)
    
    # Load dataset
    dataset_file = DATA_DIR / "performance_bugs_490.json"
    if dataset_file.exists():
        dataset = splitter.load_dataset(dataset_file)
        
        # Analyze distribution
        distribution = splitter.analyze_distribution(dataset)
        
        # Create stratified split
        train, test, validation = splitter.stratified_split(
            dataset,
            test_size=0.2,
            validation_size=0.1
        )
        
        # Save splits
        output_dir = DATA_DIR / "splits"
        metadata = splitter.save_splits(train, test, validation, output_dir)
        
        print(f"\nSplit complete:")
        print(f"  Train: {len(train)} samples")
        print(f"  Test: {len(test)} samples")
        print(f"  Validation: {len(validation)} samples")
    else:
        print(f"Dataset not found at {dataset_file}")


if __name__ == "__main__":
    main()