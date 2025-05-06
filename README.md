Coherent deps (dependencies) provides insights into the dependencies used by a code base, resolving imports to the dependencies that supply those imports. The Coherent OSS community presents this library to make the functionality available for a variety of uses.

The [Coherent System](https://bit.ly/coherent-system) implements automatic dependency inference using coherent.deps, allowing Python projects to avoid the need to declare dependencies and to instead focus on the implementation.

[pip-run](https://pypi.org/project/pip-run) leverages this library to enable on-demand installation of dependencies required by scripts, as implied by their imports.

See the code documentation for details. See also the [usage in `coherent.build`](https://github.com/coherent-oss/coherent.build/blob/a95e65df11c86658a689a7b7f5f6626321802f7e/discovery.py#L162-L175) for the usage by the build backend.

## Design Overview

`coherent.deps` is implemented primarily by two modules, `imports` and `pypi`.

`imports` performs the function of statically analyzing code to detect imports from a codebase and separate `stdlib` imports from third-party packages backed by dependencies.

`pypi` provides the package index support, providing a mapping of imports to package names in PyPI. It leverages a world-readable MongoDB database hosted in MongoDB Atlas to implement the mapping. Each PyPI project gets an entry in the `coherent builder:pypi:distributions` collection.

Each entry has the following structure:

- `_id`: the MongoDB generated unique ID
- `id`: the normalized name of the package (e.g. `typing-extensions` or `cherrypy`)
- `name`: the package's canonical name (e.g. `typing_extensions` or `CherryPy`)
- `updated`: The last time this package was updated from PyPI
- `downloads`: The number of downloads in the past 30 days as returned by the pypinfo query.
- `roots`: A collection of root importable names presented by the package (e.g. `requests` or `coherent.deps` but not `requests.errors`).
- `error`: Any error that occurred when attempting to process the package.

Only `id` and `downloads` are required. An entry without `updated` is due to be updated by the `process` routine. An entry without `roots` or `name` has never been processed.

## Maintaining the mapping

There is a subpackage, `distributions`, which contains two scripts, `load` and `process` (invoked by `python -m coherent.deps.distributions.{load,process}`) to load the distributions from a "top downloads" summary and then process those by loading their data from PyPI.

To get the full set of "top downloaded" packages that contain at least one download, run this query:

```
 🐚 pipx run --python 3.13 pypinfo --json --indent 0 --limit 800000 --days 30 "" project > ~/Downloads/top-pypi-packages-30-days.json
```

Note that this pypinfo script requires a Google API key and with a very high limit like 800000, will cost several dollars to run, so the maintainer only runs it about twice a year.

Then, to refresh the database with the downloaded dataset:

```
 🐚 py -3.13 -m pip-run coherent.deps -- -m coherent.deps.distributions.load ~/Downloads/top-pypi-packages-30-days.json
```

This process will ensure that all packages are up-to-date with their latest download stats.

From there, ensure that any newly-added packages are processed:

```
 🐚 py -3.13 -m pip-run coherent.deps -- -m coherent.deps.distributions.process
```

Note that only those entries without an `updated` field will be processed. To re-process packgaes that may have grown stale, clear the `updated` field on those entries. For example, to mark stale any entries older than 6 months:

```
max_age = datetime.timedelta(days=6*30)
filter = {'updated': {'$lt': datetime.today() - max_age}}
op = {'$unset': 'updated'}
collection.update_many(filter, op)
```

Thereafter, re-run the `process` routine, which will re-process the packages without the `updated` field.
