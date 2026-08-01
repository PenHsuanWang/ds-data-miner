# Installation

## Requirements

- Python **≥ 3.10**
- Core dependencies: `numpy`, `scipy`, `pydantic`
- Optional: `pandas` (for `df.miner` accessor)

## Option A — pip

```bash
# Core only
pip install ds-data-miner

# With Pandas integration
pip install "ds-data-miner[pandas]"
```

## Option B — uv (recommended)

```bash
# 1. Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Clone
git clone https://github.com/your-org/ds-data-miner.git
cd ds-data-miner

# 3. Create isolated venv + install with all extras
uv venv .venv --python 3.11
uv pip install -e ".[dev,pandas,docs]" --python .venv/bin/python

# 4. Activate
source .venv/bin/activate

# 5. Verify
python -c "import ds_data_miner; print(ds_data_miner.__version__)"
```

## Option C — from Git

```bash
pip install "git+https://github.com/your-org/ds-data-miner.git"
```
