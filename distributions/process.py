"""
Load metadata for unprocessed distributions.
"""

import concurrent.futures
import os

import tqdm
from jaraco.ui.main import main
from more_itertools import consume

from .. import pypi


@main
def run():
    res = pypi.Distribution.unprocessed()
    with concurrent.futures.ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
        futures = (executor.submit(dist.process) for dist in res.dists)
        completes = concurrent.futures.as_completed(futures)
        consume(tqdm.tqdm(completes, total=res.count, smoothing=0.1))
