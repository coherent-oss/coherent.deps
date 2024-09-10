"""
Parse source files and extract the imports in those source files.

Uses static analysis to find all imports (relative and absolute).

Categorizes imports as standard (from the standard library) or
not (third party).

Run this module against a specific file to emit the third-party
imports for that module:

    python -m coherent.deps.imports imports.py
"""

from __future__ import annotations

import ast
import functools
import os
import pathlib
import subprocess
import sys
from typing import Generator

import jaraco.context
from jaraco.collections import Projection


def rel_prefix(node):
    return '.' * getattr(node, 'level', 0)


class Import(str):
    @classmethod
    def read(cls, node, alias):
        return cls(
            rel_prefix(node)
            + '.'.join(
                filter(bool, [getattr(node, 'module', None), alias.name]),
            )
        )

    def relative_to(self, parent):
        """
        >>> Import('.foo').relative_to('coherent')
        'coherent.foo'
        >>> Import('..foo').relative_to('coherent')
        'foo'
        >>> Import('foo').relative_to('coherent')
        'foo'
        >>> Import('..foo.bar').relative_to('coherent._private.mod')
        'coherent._private.foo.bar'
        """
        if not self.startswith('.'):
            return self
        p_names = parent.split('.')
        l_names = self[1:].split('.')
        blanks = l_names.count('')
        parents = p_names[:-blanks] if blanks else p_names
        return '.'.join(parents + l_names[blanks:])

    def standard(self):
        """
        Is this import part of the stdandard library?

        An import is standard if it's top-level name is importable
        without any third-party packages.

        >>> Import('requests').standard()
        False
        >>> Import('urllib.parse').standard()
        True
        >>> Import('os').standard()
        True
        >>> Import('pip').standard()
        False
        """
        return self._check_standard(self.split('.')[0])

    def builtin(self):
        # for compatibility
        return self.standard()

    CPE = jaraco.context.ExceptionTrap(subprocess.CalledProcessError)

    @staticmethod
    @functools.lru_cache
    @CPE.passes
    def _check_standard(top_level_name: str) -> bool:
        """
        Attempt to import the name in a clean Python interpreter.

        Return True if it's found in the standard library, and False otherwise.
        """
        # Windows can choke without these vars (python/cpython#120836)
        safe_isolation = Projection(['SYSTEMDRIVE', 'SYSTEMROOT'], os.environ)
        cmd = [sys.executable, '-S', '-c', f'import {top_level_name}']
        subprocess.check_call(cmd, env=safe_isolation, stderr=subprocess.DEVNULL)


@functools.singledispatch
def get_module_imports(module: pathlib.Path | str | bytes) -> Generator[str]:
    r"""
    Parse a Python module to extract imported names.

    >>> list(get_module_imports('import ast\nimport requests'))
    ['ast', 'requests']

    >>> list(get_module_imports('from foo import bar'))
    ['foo.bar']

    Handles relative imports.

    >>> list(get_module_imports('from .. import foo'))
    ['..foo']

    >>> list(get_module_imports('from .foo import bar'))
    ['.foo.bar']

    """
    return (
        Import.read(node, alias)
        for node in ast.walk(ast.parse(module))
        if isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom)
        for alias in node.names
    )


@get_module_imports.register
def _(module: pathlib.Path):
    return get_module_imports(module.read_bytes())


def print_module_imports(path: pathlib.Path):
    print(list(name for name in get_module_imports(path) if not name.standard()))


__name__ == '__main__' and print_module_imports(pathlib.Path(sys.argv[1]))
