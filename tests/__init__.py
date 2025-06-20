# Ensures that the top-level 'tests' directory is treated as a real Python package
# so that pytest imports test modules under the 'tests.' namespace (e.g.
# 'tests.application.util.test_logger') instead of colliding with the real
# 'application' package of the project.

import sys
from importlib import import_module

# Expose the real application package under the expected name if running inside the
# 'tests' package context. This avoids circular import issues during collection.
if 'application' not in sys.modules:
    try:
        import_module('application')
    except ImportError:
        # In CI/linters the package root might not be on PYTHONPATH yet.
        # Fallback: prepend project root (two levels up from this file).
        from pathlib import Path
        root = Path(__file__).resolve().parent.parent
        sys.path.insert(0, str(root))
        import_module('application') 