import argparse
import ast
import re
import os
from pathlib import Path

def find_translation_imports(tree):
    """Find imports of gettext or lazy_gettext from invenio_i18n and return their aliases."""
    aliases = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == 'invenio_i18n':
            for alias in node.names:
                if alias.name in ('gettext', 'lazy_gettext'):
                    aliases.add(alias.asname or alias.name)
    return aliases

def calculate_offset(lines, lineno, col_offset):
    """Calculate the character offset in the source from line and column numbers."""
    return sum(len(line) + 1 for line in lines[:lineno-1]) + col_offset

def apply_string_replacements(source):
    """Replace new-style {} formatting in translation strings with old-style %()."""
    substitutions = []
    lines = source.split('\n')
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return source  # Skip files with syntax errors
    translation_aliases = find_translation_imports(tree)

    if not translation_aliases:
        return source  # No changes needed

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id in translation_aliases:
                if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                    string_node = node.args[0]
                    original = string_node.value
                    if re.search(r'{\w+}', original):
                        # Calculate positions
                        start_lineno = string_node.lineno
                        start_col = string_node.col_offset
                        end_lineno = string_node.end_lineno
                        end_col = string_node.end_col_offset

                        start_offset = calculate_offset(lines, start_lineno, start_col)
                        end_offset = calculate_offset(lines, end_lineno, end_col)
                        original_sub = source[start_offset:end_offset]

                        # Check quotes and replace formatting
                        if len(original_sub) >= 2 and original_sub[0] == original_sub[-1] and original_sub[0] in ('"', "'"):
                            quote = original_sub[0]
                            content = original_sub[1:-1]
                            modified = re.sub(r'{(\w+)}', r'%(\1)s', content)
                            new_sub = f"{quote}{modified}{quote}"
                            substitutions.append((start_offset, end_offset, new_sub))

    # Apply substitutions in reverse order
    for start, end, new in sorted(substitutions, reverse=True, key=lambda x: x[0]):
        source = source[:start] + new + source[end:]

    return source

def apply_format_replacements(source):
    """Replace .format() calls on translations with % operator and dictionary."""
    substitutions = []
    lines = source.split('\n')
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return source  # Skip files with syntax errors
    translation_aliases = find_translation_imports(tree)

    if not translation_aliases:
        return source  # No changes needed

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            # Check if it's a .format() call on a translation function result
            if (isinstance(node.func, ast.Attribute) and node.func.attr == 'format' and
                    isinstance(node.func.value, ast.Call)):
                func_call = node.func.value
                if (isinstance(func_call.func, ast.Name) and
                        func_call.func.id in translation_aliases):
                    # Calculate positions of the entire Call node (the .format() call)
                    start_lineno = node.lineno
                    start_col = node.col_offset
                    end_lineno = node.end_lineno
                    end_col = node.end_col_offset

                    start_offset = calculate_offset(lines, start_lineno, start_col)
                    end_offset = calculate_offset(lines, end_lineno, end_col)

                    # Collect keyword arguments to build the % dictionary
                    dict_entries = []
                    for keyword in node.keywords:
                        arg_name = keyword.arg
                        value_node = keyword.value
                        # Calculate value positions
                        value_start = calculate_offset(lines, value_node.lineno, value_node.col_offset)
                        value_end = calculate_offset(lines, value_node.end_lineno, value_node.end_col_offset)
                        value_source = source[value_start:value_end]
                        dict_entries.append(f'"{arg_name}": {value_source}')

                    if dict_entries:
                        dict_str = "{" + ", ".join(dict_entries) + "}"
                        # Get the translation call's source code (func_call)
                        translation_start = calculate_offset(lines, func_call.lineno, func_call.col_offset)
                        translation_end = calculate_offset(lines, func_call.end_lineno, func_call.end_col_offset)
                        translation_source = source[translation_start:translation_end]
                        # Construct the replacement: translation_source % dict_str
                        replacement = f"{translation_source} % {dict_str}"
                        substitutions.append((start_offset, end_offset, replacement))

    # Apply substitutions in reverse order
    for start, end, new in sorted(substitutions, reverse=True, key=lambda x: x[0]):
        source = source[:start] + new + source[end:]

    return source

def process_file(filepath):
    """Process a single Python file to update translation string formatting and .format() calls."""
    with open(filepath, 'r', encoding='utf-8') as f:
        source = f.read()

    # First pass: replace {} in translation strings
    modified_source = apply_string_replacements(source)

    # Second pass: replace .format() calls
    modified_source = apply_format_replacements(modified_source)

    # Write changes back to the file
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(modified_source)

def main():
    """Walk through the repository or process single file based on CLI argument."""
    parser = argparse.ArgumentParser(description='Update translation string formatting for InvenioRDM')
    parser.add_argument('path', nargs='?', default=os.getcwd(),
                      help='Path to file or directory to process (default: current directory)')
    args = parser.parse_args()

    repo_path = Path(args.path).resolve()

    if repo_path.is_file():
        # Process single file
        if repo_path.suffix == '.py':
            process_file(repo_path)
    elif repo_path.is_dir():
        # Process all Python files in directory
        for root, dirs, files in os.walk(repo_path):
            for file in files:
                if file.endswith('.py'):
                    filepath = Path(root) / file
                    process_file(filepath)
    else:
        print(f"Error: Path {repo_path} does not exist")
        exit(1)

if __name__ == "__main__":
    main()