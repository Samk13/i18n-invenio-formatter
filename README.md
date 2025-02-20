# Invenio i18n Formatter

A command-line tool to semi-automatically convert Python string formatting in InvenioRDM translation calls `lazy_gettext("{var}").format(var=var)` to old-style `lazy_gettext("{var}", var=var)` formatting, and`gettext("{]")`  to `gettext("%(var)") % { "var": var}` for compatibility with InvenioRDM's i18n system. The tool also logs errors for f-strings found in translation calls.

## Installation

```bash
uv run i18n-invenio-formatter.py -- <path-to-invenio-package>
```

Double check the changes, format with `isort . && black .` and commit.
