"""
Load metadata for unprocessed distributions.
"""

import tqdm
from jaraco.ui.main import main

from .. import pypi


@main
def run():
    res = pypi.Distribution.unprocessed()
    for dist in tqdm.tqdm(res.dists, total=res.count):
        dist.refresh()
        dist.save()
