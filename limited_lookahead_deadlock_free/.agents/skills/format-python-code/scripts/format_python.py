"""Whitespace-only Python formatting with strict token and AST invariants."""

import argparse
import ast
import bisect
import hashlib
import io
import json
import os
from pathlib import Path
import tokenize
import zipfile


EXCLUDED_DIRS = {
    ".git", ".venv", "venv", "env", "ENV", "virtualenv", "node_modules",
    "site-packages", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    ".tox", ".nox", ".cache", ".pycache_check", ".tmp_ll_bts", "outputs", "output",
    "tmp", "backups", "__paper", "__ref", "old", ".idea", ".vscode",
}
LAYOUT = {
    tokenize.ENCODING, tokenize.NL, tokenize.NEWLINE, tokenize.INDENT,
    tokenize.DEDENT, tokenize.ENDMARKER,
}
COMPOUND = (
    ast.If, ast.For, ast.AsyncFor, ast.While, ast.With, ast.AsyncWith,
    ast.Try, ast.TryStar, ast.Match, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef,
)
DEFINITION = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
TERMINAL = (ast.Return, ast.Raise, ast.Break, ast.Continue)


def tokens(text):
    return list(tokenize.generate_tokens(io.StringIO(text).readline))


def token_content(text):
    return [(t.type, t.string) for t in tokens(text) if t.type not in LAYOUT]


def syntax_tree(text):
    tree = ast.parse(text, type_comments=True)

    for node in ast.walk(tree):
        if isinstance(node, ast.TypeIgnore):
            node.lineno = 0

    return ast.dump(tree, include_attributes=False)


def char_position(lines, line, byte_column):
    column = len(lines[line - 1].encode("utf-8")[:byte_column].decode("utf-8"))

    return line, column


def argument_equals(tree, ts, lines):
    """Find only keyword/default-argument '=' tokens, using parsed positions."""

    equal_tokens = [t for t in ts if t.type == tokenize.OP and t.string == "="]
    positions = [t.start for t in equal_tokens]
    result = set()

    def before_value(value, lower_bound=None):
        start = char_position(lines, value.lineno, value.col_offset)
        index = bisect.bisect_left(positions, start) - 1

        if index < 0:
            raise ValueError("Default/keyword argument has no preceding '='")

        token = equal_tokens[index]

        if lower_bound is not None and token.start < lower_bound:
            raise ValueError("Keyword argument '=' is outside its parsed span")

        result.add(token.start)

    for node in ast.walk(tree):
        if isinstance(node, ast.keyword) and node.arg is not None:
            before_value(node.value, char_position(lines, node.lineno, node.col_offset))

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            for value in node.args.defaults:
                before_value(value)

            for value in node.args.kw_defaults:
                if value is not None:
                    before_value(value)

    return result


def literal_ranges(tree, lines):
    ranges = []

    for node in ast.walk(tree):
        if isinstance(node, ast.JoinedStr) or (
            isinstance(node, ast.Constant) and isinstance(node.value, (str, bytes))
        ):
            ranges.append((
                char_position(lines, node.lineno, node.col_offset),
                char_position(lines, node.end_lineno, node.end_col_offset),
            ))

    merged = []

    for start, end in sorted(ranges):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))

        else:
            merged.append((start, end))

    return merged


def format_spacing(text):
    lines = text.splitlines(keepends=True)
    tree = ast.parse(text, type_comments=True)
    ts = [t for t in tokens(text) if t.type not in LAYOUT]
    parameter_equals = argument_equals(tree, ts, lines)
    ranges = literal_ranges(tree, lines)
    starts = [start for start, end in ranges]
    edits = {}

    def protected(position):
        index = bisect.bisect_right(starts, position) - 1

        return index >= 0 and position < ranges[index][1]

    def gap(left, right, value):
        if left[0] != right[0]:
            return

        old = lines[left[0] - 1][left[1]:right[1]]

        if not old or old.isspace():
            edits[(left[0], left[1], right[1])] = value

    for index, token in enumerate(ts):
        if token.type != tokenize.OP or protected(token.start):
            continue

        if token.string in ("=", "==", "!=", "<=", ">=", "+=", "-=", "*=", "/=", "//=", "%=", "**=", "&=", "|=", "^=", ">>=", "<<=", "@=", ":="):
            space = "" if token.string == "=" and token.start in parameter_equals else " "

            if index and ts[index - 1].type != tokenize.COMMENT:
                gap(ts[index - 1].end, token.start, space)

            if index + 1 < len(ts) and ts[index + 1].type != tokenize.COMMENT:
                gap(token.end, ts[index + 1].start, space)

        elif token.string == "," and index + 1 < len(ts):
            following = ts[index + 1]

            if following.type != tokenize.COMMENT and following.string not in (")", "]", "}"):
                gap(token.end, following.start, " ")

    for (line, start, end), value in sorted(edits.items(), reverse=True):
        old = lines[line - 1]
        lines[line - 1] = old[:start] + value + old[end:]

    return "".join(lines)


def add_block_spacing(text):
    lines = text.splitlines(keepends=True)
    tree = ast.parse(text, type_comments=True)
    newline = "\r\n" if "\r\n" in text else "\n"
    protected_lines = set()

    for token in tokens(text):
        if token.type == tokenize.STRING:
            protected_lines.update(range(token.start[0] + 1, token.end[0] + 1))

    insertions = {}

    for parent in ast.walk(tree):
        for field, value in ast.iter_fields(parent):
            if not isinstance(value, list) or not value or not all(isinstance(x, ast.stmt) for x in value):
                continue

            for previous, following in zip(value, value[1:]):
                start = following.lineno

                if isinstance(following, DEFINITION) and following.decorator_list:
                    start = min(start, *(d.lineno for d in following.decorator_list))

                if start <= previous.end_lineno:
                    continue

                previous_docstring = isinstance(previous, ast.Expr) and isinstance(previous.value, ast.Constant) and isinstance(previous.value.value, str)
                import_boundary = isinstance(previous, (ast.Import, ast.ImportFrom)) and not isinstance(following, (ast.Import, ast.ImportFrom))
                boundary = isinstance(previous, COMPOUND) or isinstance(following, COMPOUND + TERMINAL) or previous_docstring or import_boundary

                if not boundary:
                    continue

                needed = 2 if isinstance(parent, ast.Module) and (
                    isinstance(previous, DEFINITION) or isinstance(following, DEFINITION)
                ) else 1
                insertion = start

                # Keep a leading comment block attached to the following code.
                while insertion - 1 > previous.end_lineno and lines[insertion - 2].lstrip().startswith("#"):
                    insertion -= 1

                blank_count = sum(not line.strip() for line in lines[previous.end_lineno:insertion - 1])
                missing = max(0, needed - blank_count)

                if missing and insertion not in protected_lines:
                    insertions[insertion] = max(insertions.get(insertion, 0), missing)

    for line, count in sorted(insertions.items(), reverse=True):
        lines.insert(line - 1, newline * count)

    return "".join(lines)


def format_source(text):
    formatted = add_block_spacing(format_spacing(text))

    if token_content(text) != token_content(formatted):
        raise ValueError("Non-layout tokens changed; refusing to write")

    if syntax_tree(text) != syntax_tree(formatted):
        raise ValueError("Syntax tree changed; refusing to write")

    return formatted


def source_files(root):
    for parent, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in EXCLUDED_DIRS and not d.startswith(".venv") and not d.startswith("[paper]"))

        for name in sorted(files):
            path = Path(parent) / name

            if path.suffix == ".py" and not path.is_symlink() and path.resolve().is_relative_to(root):
                yield path


def self_check():
    original = 'def f(x: int =1, y =2):\n    """keep  x=1,y=2 unchanged"""\n    text="x=1,y=2" #keep comment=raw\n    a=1;b=2\n    if a==b:\n        return dict(x =x,y =y)\n    return f(x =a,y =b)\n'
    formatted = format_source(original)
    assert 'def f(x: int=1, y=2):' in formatted
    assert 'dict(x=x, y=y)' in formatted
    assert 'a = 1;b = 2' in formatted
    assert 'if a == b:' in formatted
    assert '#keep comment=raw' in formatted
    assert '"x=1,y=2"' in formatted
    assert '\n\n    if' in formatted
    assert format_source(formatted) == formatted
    unicode_case = 'def f(参数 =1):\n    值=2\n    return f(参数 =值)\n'
    assert 'f(参数=值)' in format_source(unicode_case)
    fstring = 'def f(x =1):\n    value=f"{x = }"\n    return value\n'
    assert 'f"{x = }"' in format_source(fstring)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--backup", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    self_check()
    root = args.root.resolve()
    prepared = []

    for path in source_files(root):
        original = path.read_bytes()
        encoding, _ = tokenize.detect_encoding(io.BytesIO(original).readline)
        text = original.decode(encoding)
        formatted = format_source(text)

        if format_source(formatted) != formatted:
            raise ValueError("Formatting is not idempotent: " + str(path))

        prepared.append((path, original, formatted.encode(encoding)))

    changed = [(p, old, new) for p, old, new in prepared if old != new]

    if args.write:
        if args.backup is None:
            parser.error("--write requires --backup")

        args.backup.parent.mkdir(parents=True, exist_ok=True)

        if args.backup.exists():
            raise FileExistsError("Backup already exists: " + str(args.backup))

        with zipfile.ZipFile(args.backup, "w", zipfile.ZIP_DEFLATED) as archive:
            for path, old, new in prepared:
                archive.writestr(path.relative_to(root).as_posix(), old)

        for path, old, new in changed:
            if path.read_bytes() != old:
                raise RuntimeError("Source changed during formatting: " + str(path))

            temporary = path.with_suffix(path.suffix + ".format-tmp")
            temporary.write_bytes(new)
            temporary.replace(path)

    report = dict(root=str(root), checked_files=len(prepared), changed_files=len(changed), written=args.write,
        ast_unchanged=True, non_layout_tokens_unchanged=True, idempotent=True,
        files=[dict(path=p.relative_to(root).as_posix(), changed=old != new,
            before_sha256=hashlib.sha256(old).hexdigest(), after_sha256=hashlib.sha256(new).hexdigest()) for p, old, new in prepared])

    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({k: v for k, v in report.items() if k != "files"}, ensure_ascii=False))

    if args.check and changed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
