# Invenio i18n Formatter

A command-line tool to semi-automatically convert Python string formatting in InvenioRDM translation calls (`_()` and `lazy_gettext()`) from new-style `{}` to old-style `%()` formatting, for compatibility with InvenioRDM's i18n system. The tool also logs errors for f-strings found in translation calls.

## Installation

```bash
uv run i18n-invenio-formatter.py -- <path-to-invenio-package>
```

Double check the changes, format with `isort . && black .` and commit.
