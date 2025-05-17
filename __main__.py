"""
CLI for coherent.deps: emits dependencies for Python files given as globs.

Usage:
    pipx run coherent.deps [options] <glob> [<glob> ...]
    py -m coherent.deps [options] <glob> [<glob> ...]

Options:
    --format=plain|toml|pep723   Output format (default: plain)

For each file matching the globs, parses dependencies and emits them in the requested format.
"""

import argparse
import glob
import pathlib
import sys

from .imports import Import, get_module_imports
from .pypi import NoDistributionForImport, distribution_for


def parse_args():
    parser = argparse.ArgumentParser(description="Emit dependencies for Python files.")
    parser.add_argument("globs", nargs="+", help="File globs to process")
    parser.add_argument(
        "--format",
        choices=["plain", "toml", "pep723"],
        default="plain",
        help="Output format",
    )
    return parser.parse_args()


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


def main():
    args = parse_args()
    files = set().union(*map(lambda pat: glob.glob(pat, recursive=True), args.globs))

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
    emit = dict(plain=emit_plain, toml=emit_toml, pep723=emit_pep723)[args.format]
    emit(deps)


if __name__ == "__main__":
    main()
