"""
CLI for coherent.deps: emits dependencies for Python files given as globs.

Usage:
    pipx run coherent.deps [options] <glob> [<glob> ...]
    py -m coherent.deps [options] <glob> [<glob> ...]

Options:
    --format=plain|toml|pep723   Output format (default: plain)

For each file matching the globs, parses dependencies and emits them in the requested format.
"""

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


def emit_pep723(deps):
    print("""# ///\n# requires-python = ">=3.8"\n# dependencies = [""")
    print(*map(lambda d: f'#     "{d}",', sorted(deps)), sep="\n")
    print("# ]\n# ///")


def parse_glob(glob):
    print(glob)
    return glob


@main
def main(
    globs: list[str],
    format: str = 'plain',
):
    files = flatten(map(pathlib.Path().glob, globs))
    imps = flatten(map(imports.get_module_imports, files))
    deps = (pypi.distribution_for(imp) for imp in imps if not imp.excluded())
    globals()[f'emit_{format}'](deps)
