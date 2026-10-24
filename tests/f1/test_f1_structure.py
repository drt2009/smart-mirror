"""Shape of the f1 package: who is allowed to know about what.

These read the source files with ``ast`` and never import f1.module, so they run
without a display and without tkinter.

Rules
-----
* f1/models.py     imports no network, threading or tkinter code.
* f1/state.py      imports no network, threading, tkinter, or f1.client.
* f1/views.py      imports no network, threading, tkinter or f1.client, reads no
                   clock (no .now / .today / .utcnow) and does not hard-code a zone
                   (no ZoneInfo): ``now`` and ``tz`` arrive as arguments.
* f1/client.py     imports no tkinter or threading, reads no clock, and has no
                   strptime (it breaks on older Pythons).
* f1/module.py     records failures with state.mark_failed(), and is the only file that imports tkinter, threading or queue; it
                   hands the work to F1State / f1_lines / fetch_next_race instead of
                   formatting or parsing itself, and never calls datetime.today().
* No file in the package has docstrings (your rule), and the module has no
  ``except`` or ``if`` branch whose whole body is ``pass`` (the swallowed error).
"""
import ast
import importlib.util
from pathlib import Path

import pytest


def source_of(name):
    spec = importlib.util.find_spec(f"f1.{name}")
    assert spec is not None and spec.origin, f"f1/{name}.py is missing"
    return Path(spec.origin).read_text(encoding="utf-8")


def tree_of(name):
    return ast.parse(source_of(name))


def imported_modules(tree):
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name.split(".")[0] for alias in node.names)
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module.split(".")[0])
            found.add(node.module)
    return found


def imported_names(tree):
    return {alias.name for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
            for alias in node.names}


def attribute_names(tree):
    return {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}


def called_names(tree):
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            f = node.func
            names.add(f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", None))
    return names


UI_OR_IO = {"tkinter", "threading", "queue", "requests"}


@pytest.mark.parametrize("name", ["models", "state", "views"])
def test_the_pure_files_know_nothing_about_io_or_the_ui(name):
    assert not (imported_modules(tree_of(name)) & UI_OR_IO)


@pytest.mark.parametrize("name", ["state", "views"])
def test_state_and_views_do_not_reach_into_the_client(name):
    assert "f1.client" not in imported_modules(tree_of(name))


def test_views_do_not_read_a_clock_or_hard_code_a_zone():
    tree = tree_of("views")
    assert not (attribute_names(tree) & {"now", "today", "utcnow"})
    assert "ZoneInfo" not in imported_names(tree)
    assert "ZoneInfo" not in {getattr(n, "id", None) for n in ast.walk(tree)}


def test_the_client_has_no_ui_threading_or_clock():
    tree = tree_of("client")
    assert not (imported_modules(tree) & {"tkinter", "threading", "queue"})
    assert not (attribute_names(tree) & {"now", "today", "utcnow"})


def test_the_client_does_not_use_strptime():
    assert "strptime" not in attribute_names(tree_of("client"))


def test_only_the_module_file_touches_tkinter_and_threads():
    for name in ("models", "state", "views", "client"):
        assert not (imported_modules(tree_of(name)) & {"tkinter", "threading", "queue"}), name
    assert "tkinter" in imported_modules(tree_of("module"))


def test_the_module_uses_the_state_the_views_and_the_client():
    names = imported_names(tree_of("module"))
    assert {"F1State", "f1_lines", "fetch_next_race"} <= names
    assert {"F1State", "f1_lines", "fetch_next_race"} <= called_names(tree_of("module"))


def test_the_module_does_not_format_parse_or_read_the_clock_itself():
    tree = tree_of("module")
    assert not (attribute_names(tree) & {"strptime", "strftime", "today", "utcnow"})


def test_the_module_does_not_swallow_errors_with_a_bare_pass():
    for node in ast.walk(tree_of("module")):
        if isinstance(node, (ast.ExceptHandler, ast.If)):
            assert not all(isinstance(stmt, ast.Pass) for stmt in node.body)


def test_the_module_records_a_failed_fetch_on_the_state():
    assert "mark_failed" in attribute_names(tree_of("module"))


@pytest.mark.parametrize("name", ["models", "state", "views", "client", "module"])
def test_there_are_no_docstrings(name):
    tree = tree_of(name)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            assert ast.get_docstring(node) is None, (name, getattr(node, "name", "module"))
