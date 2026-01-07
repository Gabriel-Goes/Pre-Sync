# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'SYNC - Sincronização SDS'
copyright = '2026, Gabriel Góes Rocha de Lima'
author = 'Gabriel Góes Rocha de Lima'
release = '0.1.0'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

import os

extensions = [
    "myst_parser",
    "sphinx_copybutton",
    "sphinx_design",
    "sphinx.ext.autosectionlabel",
    "sphinx.ext.extlinks",
]

templates_path = ['_templates']
exclude_patterns = []
root_doc = "index"

language = 'pt_BR'

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'furo'
html_theme_options = {
    "sidebar_hide_name": True,
    "navigation_with_keys": True,
}
html_static_path = ['_static']

# -
source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "tasklist",
]

myst_heading_anchors = 2
autosectionlabel_prefix_document = True

git_ref = os.environ.get("GITHUB_SHA", "main")
extlinks = {
    "gh": (f"https://github.com/Gabriel-Goes/Pre-Sync/blob/{git_ref}/%s", "%s"),
}
