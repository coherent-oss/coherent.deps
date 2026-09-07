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
import io
import os
import pathlib
import subprocess
import sys
import tokenize
from collections.abc import Generator

import jaraco.context
from jaraco.collections import Projection
from jaraco.compat.py310 import safe_path

from . import _directives


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
        Is this import part of the standard library?

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
        >>> Import('.os').standard()
        False

        Platform-specific stdlib modules are recognized as standard even
        when they're not importable on the current host (e.g. ``winreg``
        on non-Windows).

        >>> Import('winreg').standard()
        True
        """
        return bool(self.top) and (
            self.top in sys.stdlib_module_names or self._check_standard(self.top)
        )

    @property
    def top(self) -> str | None:
        """
        Return the top-level name for this import.

        >>> Import('foo.bar').top
        'foo'
        >>> Import('foo').top
        'foo'
        >>> Import('.foo.bar').top
        """
        return self.split('.')[0] or None

    def builtin(self):
        # for compatibility
        return self.standard()

    def implicit(self):
        """
        Is this module implicitly available (based on other conditions)?

        For example, ``_typeshed`` is made available at runtime by mypy
        and other type checkers and will not have a distribution that
        supplies it.

        >>> Import('_typeshed.StrPath').implicit()
        True
        >>> Import('._typeshed').implicit()
        False
        >>> Import('os').implicit()
        False
        """
        implicit = {'_typeshed'}
        return self.top in implicit

    def excluded(self):
        return self.implicit() or self.standard()

    CPE = jaraco.context.ExceptionTrap(subprocess.CalledProcessError)

    @staticmethod
    @functools.lru_cache
    @CPE.passes
    def _check_standard(top_level_name: str) -> bool:
        """
        Attempt to import the name in a clean Python interpreter.

        Return True if it's found in the standard library, and False otherwise.

        The probe should remain stable even when cwd contains a module that
        shadows a stdlib dependency.

        >>> tmp_path = getfixture('tmp_path')
        >>> monkeypatch = getfixture('monkeypatch')
        >>> _ = (tmp_path / 'glob.py').write_text("raise RuntimeError('shadowed glob')")
        >>> monkeypatch.chdir(tmp_path)
        >>> Import._check_standard.cache_clear()
        >>> Import._check_standard('pathlib')
        True
        """
        # Windows can choke without these vars (python/cpython#120836)
        safe_isolation = Projection(['SYSTEMDRIVE', 'SYSTEMROOT'], os.environ)
        cmd = safe_path.command('-S', '-c', f'import {top_level_name}')
        env = safe_path.environ(safe_isolation)
        subprocess.check_call(cmd, env=env, stderr=subprocess.DEVNULL)


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

    An import annotated to suppress dependency inference is excluded, so
    it doesn't become a declared dependency (#26).

    >>> src = 'import nspkg  # deps: ignore[inferred-dependency]\nimport foo'
    >>> list(get_module_imports(src))
    ['foo']

    """
    excluded_lines = excludes(get_module_comments(module))
    return (
        Import.read(node, alias)
        for node in ast.walk(ast.parse(module))
        if isinstance(node, (ast.Import, ast.ImportFrom))
        and node.lineno not in excluded_lines
        for alias in node.names
    )


@get_module_imports.register
def _(module: pathlib.Path):
    return get_module_imports(module.read_bytes())


@functools.singledispatch
def get_module_comments(code: bytes | str) -> dict[int, str]:
    r"""
    >>> get_module_comments('# foo\n# bar')
    {1: '# foo', 2: '# bar'}
    """
    return {
        token.start[0]: token.string
        for token in tokenize.generate_tokens(io.StringIO(code).readline)
        if token.type == tokenize.COMMENT
    }


def excludes(comments):
    """
    Exclude lines whose comment suppresses dependency inference.

    A ``deps: ignore[inferred-dependency]`` directive (#26) keeps an import
    from becoming a declared dependency.
    """
    return {
        line: comment
        for line, comment in comments.items()
        if _directives.match('deps: ignore[inferred-dependency]', comment)
    }


@get_module_comments.register
def _(code: bytes):
    return get_module_comments(code.decode('utf-8'))


def print_module_imports(path: pathlib.Path):
    print([name for name in get_module_imports(path) if not name.standard()])


__name__ == '__main__' and print_module_imports(pathlib.Path(sys.argv[1]))
