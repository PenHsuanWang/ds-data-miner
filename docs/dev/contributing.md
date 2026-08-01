# Contributing

## Development Setup

```bash
git clone https://github.com/your-org/ds-data-miner.git
cd ds-data-miner
uv venv .venv --python 3.11
uv pip install -e ".[dev,pandas,docs]" --python .venv/bin/python
source .venv/bin/activate
```

## Running Tests

```bash
pytest                                         # all tests
pytest --cov=ds_data_miner --cov-report=html   # with HTML coverage
tox                                            # full multi-Python matrix
```

## Code Style

- Formatter: `ruff format`
- Linter: `ruff check`
- Type checker: `mypy --strict`

All three must pass before a PR is merged.

```bash
ruff format src/ tests/ && ruff check src/ tests/ && mypy src/
```

## Docstring Style

Use **Sphinx reStructuredText** (`:param:`, `:return:`, `:raises:`).
Types are taken from annotations — do **not** add `:type param:` tags.

```python
def fit(self, data: np.ndarray) -> DistributionProfile:
    """Full-scan profile of a 1-D numeric array.

    :param data: 1-D NumPy array of numeric dtype.
    :return: Frozen :class:`DistributionProfile`.
    :raises DataQualityError: If data is entirely NaN.
    """
```

## Building the Docs

```bash
cd docs/
make html
open _build/html/index.html
```
