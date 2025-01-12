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
    for dist in tqdm.tqdm(list(pypi.Distribution.query(url=url))):
        dist.save()
