"""
Sphinx configuration for ds-data-miner.

Uses the Furo theme + autodoc + napoleon (Google/NumPy docstrings) +
sphinx-autodoc-typehints (pulls types from annotations, not docstrings).
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make the package importable without installation
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import ds_data_miner  # noqa: E402

# ---------------------------------------------------------------------------
# Project information
# ---------------------------------------------------------------------------
project = "ds-data-miner"
author = "ds-data-miner contributors"
copyright = f"2024, {author}"
release = ds_data_miner.__version__
version = ".".join(release.split(".")[:2])  # e.g. "0.1"

# ---------------------------------------------------------------------------
# General configuration
# ---------------------------------------------------------------------------
extensions = [
    "sphinx.ext.autodoc",          # auto-generate API docs from docstrings
    "sphinx.ext.napoleon",         # Google / NumPy docstring styles
    "sphinx.ext.viewcode",         # [source] links in API pages
    "sphinx.ext.intersphinx",      # cross-links to numpy, scipy, pydantic docs
    "sphinx_autodoc_typehints",    # pull type hints into docs automatically
    "sphinx_copybutton",           # copy-to-clipboard on code blocks
    "myst_parser",                 # write docs in Markdown instead of RST
]

# File extensions accepted by Sphinx
source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# ---------------------------------------------------------------------------
# Autodoc settings
# ---------------------------------------------------------------------------
autodoc_default_options = {
    "members": True,
    "undoc-members": False,
    "show-inheritance": True,
    "special-members": "__init__",
}

# sphinx-autodoc-typehints: render types from annotations (not :type: tags)
always_document_param_types = True
typehints_fully_qualified = False
simplify_optional_unions = True

# Napoleon settings (Sphinx-style reST docstrings are used in this project)
napoleon_google_docstring = False
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = True
napoleon_use_param = True
napoleon_use_rtype = True

# ---------------------------------------------------------------------------
# Intersphinx — cross-reference external docs
# ---------------------------------------------------------------------------
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "numpy": ("https://numpy.org/doc/stable", None),
    "scipy": ("https://docs.scipy.org/doc/scipy", None),
    "pydantic": ("https://docs.pydantic.dev/latest", None),
    "pandas": ("https://pandas.pydata.org/docs", None),
}

# ---------------------------------------------------------------------------
# HTML output — Furo theme
# ---------------------------------------------------------------------------
html_theme = "furo"
html_title = f"ds-data-miner {release}"
html_static_path = ["_static"]

html_theme_options = {
    "sidebar_hide_name": False,
    "navigation_with_keys": True,
    "source_repository": "https://github.com/your-org/ds-data-miner/",
    "source_branch": "main",
    "source_directory": "docs/",
}

# Copy-button: skip prompts in shell examples
copybutton_prompt_text = r">>> |\.\.\. |\$ "
copybutton_prompt_is_regexp = True
