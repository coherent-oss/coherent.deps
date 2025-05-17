"""
CLI for coherent.deps: emits dependencies for Python files given as globs.

Usage:
    pipx run coherent.deps [options] <glob> [<glob> ...]
    py -m coherent.deps [options] <glob> [<glob> ...]

Options:
    --format=plain|toml|pep723   Output format (default: plain)

For each file matching the globs, parses dependencies and emits them in the requested format.
"""

import glob
import pathlib

from jaraco.ui.main import main
from more_itertools import flatten

from . import imports, pypi


def emit_plain(deps):
    print(*sorted(deps), sep="\n")


def emit_toml(deps):
    print("[project]\nrequires = [")
    print(*map(lambda d: f'    "{d}",', sorted(deps)), sep="\n")
    print("]")


def emit_inline(deps):
    print("""# ///\n# requires-python = ">=3.8"\n# dependencies = [""")
    print(*map(lambda d: f'#     "{d}",', sorted(deps)), sep="\n")
    print("# ]\n# ///")


def emit_python(deps):
    print("""__requires__ = [""")
    print(*map(lambda d: f'    "{d}",', sorted(deps)), sep="\n")
    print("]")


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
    globals()[f'emit_{format}'](deps)
