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
import sys

from jaraco.ui.main import main
from more_itertools import flatten

from .imports import Import, get_module_imports
from .pypi import NoDistributionForImport, distribution_for


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
    files = list(flatten(map(pathlib.Path().glob, globs)))

    def import_to_dep(name):
        imp = Import(name)
        if imp.excluded():
            return None
        try:
            return distribution_for(imp.top)
        except NoDistributionForImport:
            return None

    def file_deps(file):
        try:
            return filter(
                None, map(import_to_dep, get_module_imports(pathlib.Path(file)))
            )
        except Exception as e:
            print(f"Error processing {file}: {e}", file=sys.stderr)
            return []

    deps = set(filter(None, (dep for file in files for dep in file_deps(file))))
    emit = globals()[f'emit_{format}']
    emit(deps)
