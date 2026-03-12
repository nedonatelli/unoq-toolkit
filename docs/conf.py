"""Sphinx configuration for unoq-toolkit."""

import os
import sys

# Add project root to path for autodoc
sys.path.insert(0, os.path.abspath(".."))

project = "unoq-toolkit"
author = "nedonatelli"
release = "0.1.0"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
    "sphinx.ext.napoleon",
    "myst_parser",
]

# Support both .rst and .md
source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

templates_path = ["_templates"]
exclude_patterns = ["_build"]

html_theme = "sphinx_rtd_theme"
html_static_path = []

# Napoleon settings for Google/NumPy style docstrings
napoleon_google_docstrings = True
napoleon_numpy_docstrings = True

# Autodoc settings
autodoc_member_order = "bysource"
autodoc_mock_imports = ["tkinter"]
