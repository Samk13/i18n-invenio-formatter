# Invenio i18n Formatter

A command-line tool to automatically convert Python string formatting in InvenioRDM translation calls (`_()`) from new-style `{}` to old-style `%()` formatting, for compatibility with InvenioRDM's i18n system.

## Installation

```bash
uv run i18n-invenio-formatter.py -- <path-to-invenio-package>
```

Double check the changes, format with `isort . && black .` and commit.
