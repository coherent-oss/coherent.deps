"""
Load distributions into the database.
"""

import pathlib
import urllib.parse

import tqdm
import typer
from jaraco.ui.main import main

from .. import pypi


def _make_url(url_or_path: str) -> str:
    if not urllib.parse.urlparse(url_or_path).scheme:
        return f'file://{pathlib.Path(url_or_path).expanduser().absolute()}'
    return url_or_path


@main
def run(
    url: str = typer.Argument(pypi.top_8k, callback=_make_url),
):
    try:
        skip = int(pathlib.Path('skip').read_text())
    except FileNotFoundError:
        skip = 0
    dists = tqdm.tqdm(list(pypi.Distribution.query(url=url))[skip:], initial=skip)
    try:
        for dist in dists:
            dist.save()
    except BaseException:
        pathlib.Path('skip').write_text(str(dists.n))
        raise
