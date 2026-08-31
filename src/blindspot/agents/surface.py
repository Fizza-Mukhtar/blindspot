"""Extract the callable surface of an implementation with ``ast``.

This is a deterministic tool, not an agent.  It exists to answer exactly one
question for the adversary -- *how do I call this code?* -- while leaking as
little as possible about *what the code does*.

The information barrier is not "the adversary sees nothing".  It is "the
adversary sees the interface and the specification, and forms its expectations
from the specification".  Docstrings are the one judgement call: they are
author-written prose that can restate a misreading, so they are excluded by
default and their exclusion is logged.
"""

from __future__ import annotations

import ast

from ..types import FunctionInfo, ParamInfo, SurfaceMap


def _annotation(node: ast.expr | None) -> str | None:
    if node is None:
        return None
    try:
        return ast.unparse(node)
    except Exception:  # pragma: no cover - defensive
        return None


def _default(node: ast.expr | None) -> str | None:
    if node is None:
        return None
    try:
        return ast.unparse(node)
    except Exception:  # pragma: no cover
        return None


def _params(args: ast.arguments) -> list[ParamInfo]:
    params: list[ParamInfo] = []

    positional = list(args.posonlyargs) + list(args.args)
    padding = len(positional) - len(args.defaults)
    for index, arg in enumerate(positional):
        default = args.defaults[index - padding] if index >= padding else None
        params.append(
            ParamInfo(
                name=arg.arg,
                annotation=_annotation(arg.annotation),
                default=_default(default),
                kind="positional_only" if arg in args.posonlyargs else "positional_or_keyword",
            )
        )
    if args.vararg:
        params.append(
            ParamInfo(
                name=f"*{args.vararg.arg}",
                annotation=_annotation(args.vararg.annotation),
                kind="var_positional",
            )
        )
    for arg, default in zip(args.kwonlyargs, args.kw_defaults, strict=False):
        params.append(
            ParamInfo(
                name=arg.arg,
                annotation=_annotation(arg.annotation),
                default=_default(default),
                kind="keyword_only",
            )
        )
    if args.kwarg:
        params.append(
            ParamInfo(
                name=f"**{args.kwarg.arg}",
                annotation=_annotation(args.kwarg.annotation),
                kind="var_keyword",
            )
        )
    return params


def _raised_names(node: ast.AST) -> list[str]:
    """Exception *types* the function raises.

    Only the type is taken.  The message is author prose and may encode the
    same misreading as the code, so it stays behind the barrier.
    """
    names: list[str] = []
    for child in ast.walk(node):
        if not isinstance(child, ast.Raise) or child.exc is None:
            continue
        exc = child.exc
        if isinstance(exc, ast.Call):
            exc = exc.func
        if isinstance(exc, ast.Name):
            names.append(exc.id)
        elif isinstance(exc, ast.Attribute):
            names.append(exc.attr)
    return sorted(set(names))


def extract_surface(source: str, *, include_docstrings: bool = False) -> SurfaceMap:
    """Parse ``source`` and return its public callable surface."""
    tree = ast.parse(source)
    surface = SurfaceMap(module="impl")

    for node in tree.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            if node.name.startswith("_"):
                continue
            surface.functions.append(
                FunctionInfo(
                    name=node.name,
                    params=_params(node.args),
                    returns=_annotation(node.returns),
                    docstring=ast.get_docstring(node) if include_docstrings else None,
                    raises=_raised_names(node),
                    is_async=isinstance(node, ast.AsyncFunctionDef),
                )
            )
        elif isinstance(node, ast.ClassDef):
            surface.classes.append(node.name)
            bases = {ast.unparse(b) for b in node.bases if isinstance(b, ast.Name | ast.Attribute)}
            if bases & {"Exception", "ValueError", "RuntimeError", "TypeError", "BaseException"}:
                surface.exceptions_defined.append(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.isupper():
                    try:
                        surface.constants[target.id] = ast.unparse(node.value)[:80]
                    except Exception:  # pragma: no cover
                        continue
        elif isinstance(node, ast.Import | ast.ImportFrom):
            try:
                surface.imports.append(ast.unparse(node))
            except Exception:  # pragma: no cover
                continue

    # Exception types raised anywhere in the module, including helpers, are part
    # of the observable contract.
    module_raises = _raised_names(tree)
    for fn in surface.functions:
        fn.raises = sorted(set(fn.raises) | set(module_raises))
    return surface
