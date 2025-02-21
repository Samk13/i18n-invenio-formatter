import argparse
import ast
import re
import os
import string
from pathlib import Path


def find_translation_imports(tree):
    """Find imports of gettext or lazy_gettext from invenio_i18n and return their aliases with types."""
    translations = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "invenio_i18n":
            for alias in node.names:
                if alias.name in ("gettext", "lazy_gettext"):
                    alias_name = alias.asname or alias.name
                    translations[alias_name] = alias.name
    return translations


def calculate_offset(lines, lineno, col_offset):
    """Calculate the character offset in the source from line and column numbers."""
    return sum(len(line) + 1 for line in lines[: lineno - 1]) + col_offset


def log_error(filepath, lineno, message):
    """Log an error message with file name and line number."""
    print(f"Error in {filepath} at line {lineno}: {message}")


def get_original_quote_style(source, string_node):
    """Determine the original quote style (single or double) from the source code."""
    start = calculate_offset(
        source.split("\n"), string_node.lineno, string_node.col_offset
    )
    # Look at the character just before the string content
    while start > 0 and source[start - 1] in " \t(":
        start -= 1
    if start > 0 and source[start - 1] in "'\"":
        return source[start - 1]
    return '"'  # Default to double quotes if unclear


def escape_string_for_quotes(value, quote_char):
    """Escape quotes in a string based on the desired wrapping quote character."""
    if quote_char == '"':
        return value.replace('"', '\\"')
    elif quote_char == "'":
        return value.replace("'", "\\'")
    return value


def process_file(filepath):
    """Process a single Python file to update translation string formatting."""
    with open(filepath, "r", encoding="utf-8") as f:
        source = f.read()
    lines = source.split("\n")
    tree = ast.parse(source)
    translation_aliases = find_translation_imports(tree)

    if not translation_aliases:
        return

    substitutions = []

    # Process .format() calls on translation functions
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "format"
        ):
            func_call = node.func.value
            if (
                isinstance(func_call, ast.Call)
                and isinstance(func_call.func, ast.Name)
                and func_call.func.id in translation_aliases
            ):
                trans_type = translation_aliases[func_call.func.id]

                # Get the original translation call
                start = calculate_offset(lines, func_call.lineno, func_call.col_offset)
                end = calculate_offset(
                    lines, func_call.end_lineno, func_call.end_col_offset
                )

                # Get the translation string
                string_node = func_call.args[0]
                original_str = string_node.value

                # Check for positional placeholders
                formatter = string.Formatter()
                parsed = list(formatter.parse(original_str))
                for literal, field_name, format_spec, conversion in parsed:
                    if field_name is not None and (
                        field_name == "" or field_name.isdigit()
                    ):
                        log_error(
                            filepath,
                            string_node.lineno,
                            "Positional placeholders found in translation string",
                        )
                        continue  # Skip this node

                # Modify the string to use %()s for named placeholders
                modified_str = re.sub(r"{(\w+)}", r"%(\1)s", original_str)

                # Get the original quote style and escape accordingly
                quote_char = get_original_quote_style(source, string_node)
                modified_str_escaped = escape_string_for_quotes(
                    modified_str, quote_char
                )
                modified_str_literal = f"{quote_char}{modified_str_escaped}{quote_char}"

                # Process based on translation type
                if trans_type == "gettext":
                    # Generate % substitution with dictionary
                    format_dict_parts = [
                        f'"{k.arg}": {ast.unparse(k.value)}' for k in node.keywords
                    ]
                    format_dict = "{" + ", ".join(format_dict_parts) + "}"
                    new_call = f"_({modified_str_literal}) % {format_dict}"
                elif trans_type == "lazy_gettext":
                    # Generate keyword arguments in the translation call
                    format_kwargs = [
                        f"{k.arg}={ast.unparse(k.value)}" for k in node.keywords
                    ]
                    kw_args = ", ".join(format_kwargs)
                    new_call = (
                        f"_({modified_str_literal}, {kw_args})"
                        if kw_args
                        else f"_({modified_str_literal})"
                    )

                # Replace entire .format() call
                full_start = calculate_offset(
                    lines, func_call.lineno, func_call.col_offset
                )
                full_end = calculate_offset(lines, node.end_lineno, node.end_col_offset)
                substitutions.append((full_start, full_end, new_call))

    # Process f-strings in translation calls
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in translation_aliases
        ):
            if node.args and isinstance(node.args[0], (ast.JoinedStr, ast.Constant)):
                string_node = node.args[0]
                if isinstance(string_node, ast.JoinedStr):
                    log_error(filepath, node.lineno, "f-string found in _() call")

    # Apply changes in reverse order
    for start, end, new in sorted(substitutions, reverse=True, key=lambda x: x[0]):
        source = source[:start] + new + source[end:]

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(source)


def main():
    """Handle CLI arguments and process files."""
    parser = argparse.ArgumentParser(
        description="Update InvenioRDM translation strings to use proper formatting"
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=os.getcwd(),
        help="Path to file or directory (default: current directory)",
    )
    args = parser.parse_args()

    path = Path(args.path).resolve()

    if path.is_file():
        process_file(path)
    elif path.is_dir():
        for root, _, files in os.walk(path):
            for file in files:
                if file.endswith(".py"):
                    process_file(Path(root) / file)
    else:
        print(f"Error: Path {path} does not exist")
        exit(1)


if __name__ == "__main__":
    main()
