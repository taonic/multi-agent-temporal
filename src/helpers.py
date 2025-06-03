import importlib
import inspect
from typing import List


# Moved to libs/ directory
def load_functions(module: str) -> List[callable]:
    """Dynamically load Activities as tools.

    Args:
        module: Name of the module to load functions from

    Returns:
        List of functions from the module
    """
    functions_module = importlib.import_module(module)
    functions = [
        func for name, func in inspect.getmembers(functions_module, inspect.isfunction)
        if func.__module__ == module
    ]
    return functions
