# Invenio i18n Formatter

A command-line tool to convert Python string formatting in InvenioRDM translation calls from new-style to old-style formatting:

- Converts `gettext("{var}").format(var=value)` to `gettext("%(var)s") % {"var": value}`
- Converts `lazy_gettext("{var}").format(var=value)` to `lazy_gettext("%(var)s", var=value)`

Features:

- Preserves original quote style (single/double quotes)
- Detects and warns about positional placeholders
- Logs errors for f-strings in translation calls
- Handles both `gettext` and `lazy_gettext` imports from invenio_i18n

## Usage

```bash
uv run i18n-invenio-formatter.py -- <path-to-invenio-package>
```

Always review the changes and run code formatters (`isort . && black .`) before committing.
