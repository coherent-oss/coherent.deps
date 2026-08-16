"""
Compatibility for Python 3.10.

Remove this module when support for Python 3.10 is dropped.
"""

import sys

# The ``-P`` (PYTHONSAFEPATH) interpreter option, which keeps the current
# working directory from shadowing imports, was added in Python 3.11. On 3.10,
# fall back to ``-I`` (isolated mode), which also drops the cwd from sys.path.
safe_path = '-P' if sys.version_info >= (3, 11) else '-I'
