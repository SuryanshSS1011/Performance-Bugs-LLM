"""Model training and inference module"""

# Handle optional dependencies gracefully
try:
    from .fine_tuning import ModelFineTuner, DatasetPreparer, TrainingExample
    __all__ = ['ModelFineTuner', 'DatasetPreparer', 'TrainingExample']
except ImportError:
    # OpenAI not available, but that's okay for core functionality
    __all__ = []