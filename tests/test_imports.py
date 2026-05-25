"""
The stdlib probe should remain stable even when cwd contains a module
that shadows a stdlib dependency (`glob.py` while importing `pathlib`).

>>> import pathlib
>>> import jaraco.context
>>> from imports import Import
>>> with jaraco.context.temp_dir() as td, jaraco.context.pushd(td):
...     _ = pathlib.Path('glob.py').write_text("raise RuntimeError('shadowed glob')")
...     Import._check_standard.cache_clear()
...     Import('pathlib').standard()
True
>>> Import._check_standard.cache_clear()
"""
