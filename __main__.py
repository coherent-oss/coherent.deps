"""
CLI for coherent.deps: emits dependencies for Python files given as globs.

Usage:
    pipx run coherent.deps [options] <glob> [<glob> ...]
    py -m coherent.deps [options] <glob> [<glob> ...]

For each file matching the globs, parses dependencies and emits them in the requested format.
"""

import glob
import pathlib

from jaraco.ui.main import main
from more_itertools import consume, flatten

from . import imports, pypi


def emit_plain(deps):
    yield from deps


def emit_toml(deps):
    yield "[project]\nrequires = ["
    yield from map(lambda d: f'    "{d}",', deps)
    yield "]"


def emit_inline(deps):
    yield """# ///\n# requires-python = ">=3.8"\n# dependencies = ["""
    yield from map(lambda d: f'#     "{d}",', deps)
    yield "# ]\n# ///"


def emit_python(deps):
    yield """__requires__ = ["""
    yield from map(lambda d: f'    "{d}",', deps)
    yield "]"


def parse_glob(spec: str):
    return map(pathlib.Path, glob.glob(spec))


@main
def main(
    globs: list[str],
    format: str = 'plain',
):
    files = flatten(map(parse_glob, globs))
    imps = flatten(map(imports.get_module_imports, files))
    deps = (pypi.distribution_for(imp) for imp in imps if not imp.excluded())
    lines = globals()[f'emit_{format}'](deps)
    consume(map(print, lines))
