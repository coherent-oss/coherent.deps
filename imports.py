from __future__ import annotations

import ast
import functools
import pathlib
import subprocess
import sys

from typing import Generator

import jaraco.context


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

    CPE = jaraco.context.ExceptionTrap(subprocess.CalledProcessError)

    @CPE.passes
    def builtin(self):
        """
        Is this import built-in (part of the stdandard library)?

        An import is built-in if it's top-level name is importable
        without any third-party packages.

        >>> Import('requests').builtin()
        False
        >>> Import('urllib.parse').builtin()
        True
        >>> Import('os').builtin()
        True
        >>> Import('pip').builtin()
        False
        """
        top_level_name = self.split('.')[0]
        cmd = [sys.executable, '-S', '-c', f'import {top_level_name}']
        subprocess.check_call(cmd, env={}, stderr=subprocess.DEVNULL)


@functools.singledispatch
def get_module_imports(module: pathlib.Path | str) -> Generator[str]:
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
    return get_module_imports(module.read_text())


__name__ == '__main__' and print(list(get_module_imports(pathlib.Path(sys.argv[1]))))
