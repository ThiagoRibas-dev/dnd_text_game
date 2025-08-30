from __future__ import annotations
from pathlib import Path
import json
import re
from typing import List
import yaml
import typer
from py_expression_eval import Parser
from pydantic import TypeAdapter, ValidationError
from dndrpg.engine.schema_models import (
    EffectDefinition, ConditionDefinition, ResourceDefinition, TaskDefinition, ZoneDefinition
)

# Expression validation config
ALLOWED_FUNCTIONS = {
    "min", "max", "floor", "ceil",
    "ability_mod", "level", "class_level", "caster_level", "initiator_level", "hd",
}

# Common variables used across content (expand as needed)
ALLOWED_SYMBOLS_BASE = {
    # tasks/crafting/downtime
    "item_price", "item_dc", "check_result", "progress",
    "elapsed_hours", "elapsed_minutes", "elapsed_days",
    # zones/effects
    "spell_level", "capacity",
    # ability shorthands sometimes used as variables in ability_mod(…)
    "str", "dex", "con", "int", "wis", "cha",
    # generic names sometimes used in simple math snippets
    "value", "amount", "dc", "n",
}

# Keys that we treat as expressions when their value is a string
EXPR_KEYS = {
    # generic
    "formula", "amount", "value", "dc", "increment_by", "current", "initial_current", "initial",
    "targetAmount", "magnitudeExpr", "factor", "cap", "max_cl", "when",
}

_parser = Parser()

def _expr_functions(expr: str) -> set[str]:
    # Very pragmatic: find identifiers followed by '('
    return set(re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", expr))

def _expr_symbols(expr: str, used_funcs: set[str]) -> set[str]:
    # All identifiers; subtract function names and numeric-only tokens
    syms = set(re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\b", expr))
    return {s for s in syms if s not in used_funcs}

def _prevalidate_expr_string(expr: str, *, strict: bool, file_path: str, field_path: str) -> list[str]:
    errors: list[str] = []
    # Parse
    try:
        _parser.parse(expr)
    except Exception as e:
        errors.append(f"{file_path}:{field_path}: invalid expression syntax: {e}")
        return errors

    funcs = _expr_functions(expr)
    unknown_funcs = funcs - ALLOWED_FUNCTIONS
    if unknown_funcs:
        errors.append(f"{file_path}:{field_path}: unknown function(s): {sorted(unknown_funcs)}; allowed: {sorted(ALLOWED_FUNCTIONS)}")

    if strict:
        # Conservative variable check: allow a common base set and snake_case names; warn on odd tokens
        syms = _expr_symbols(expr, funcs)
        # Filter out numeric-looking tokens (shouldn't be present anyway)
        syms = {s for s in syms if not re.fullmatch(r"\d+(\.\d+)?", s)}
        suspicious = set()
        for s in syms:
            if s in ALLOWED_SYMBOLS_BASE:
                continue
            # allow snake_case-ish names (authors may introduce new vars; keep strict but not hostile)
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", s):
                suspicious.add(s)
        if suspicious:
            errors.append(f"{file_path}:{field_path}: suspicious symbol name(s): {sorted(suspicious)} "
                          f"(variables should be snake_case identifiers; functions allowed: {sorted(ALLOWED_FUNCTIONS)})")
    return errors

def _walk_exprs(data: object, *, file_path: str, prefix: str, strict: bool) -> list[str]:
    """
    Recursively walk a dict/list tree; for any key in EXPR_KEYS whose value is a str,
    parse and prevalidate the expression. Returns a list of error strings.
    """
    errs: list[str] = []
    if isinstance(data, dict):
        for k, v in data.items():
            path = f"{prefix}.{k}" if prefix else k
            if isinstance(v, str) and k in EXPR_KEYS:
                errs.extend(_prevalidate_expr_string(v, strict=strict, file_path=file_path, field_path=path))
            # Nested containers
            if isinstance(v, (dict, list)):
                errs.extend(_walk_exprs(v, file_path=file_path, prefix=path, strict=strict))
    elif isinstance(data, list):
        for idx, item in enumerate(data):
            path = f"{prefix}[{idx}]"
            errs.extend(_walk_exprs(item, file_path=file_path, prefix=path, strict=strict))
    return errs

app = typer.Typer(add_completion=False)

def _load(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in (".yaml", ".yml"):
        return yaml.safe_load(text) or {}
    return json.loads(text)

def _iter(root: Path, exts=(".json",".yaml",".yml")):
    if not root.exists():
        return
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in exts:
            yield p

@app.command("export-schemas")
def export_schemas_cmd(out: Path = typer.Option(Path("docs/schemas"), "--out")):
    from dndrpg.tools.export_schemas import export_schemas
    export_schemas(out)
    typer.echo(f"Exported schemas to {out}")

@app.command("validate-content")
def validate_content(
    content_dir: Path = typer.Argument(Path("src/dndrpg/content")),
    strict_expr: bool = typer.Option(False, "--strict-expr", help="Disallow unknown functions and suspicious symbols in expressions")
):
    ok = True
    groups = [
        ("effects", TypeAdapter(EffectDefinition)),
        ("conditions", TypeAdapter(ConditionDefinition)),
        ("resources", TypeAdapter(ResourceDefinition)),
        ("tasks", TypeAdapter(TaskDefinition)),
        ("zones", TypeAdapter(ZoneDefinition)),
    ]

    parsed: dict[str, list] = {k: [] for k, _ in groups}
    for sub, adapter in groups:
        folder = content_dir / sub
        if not folder.exists():
            continue
        for fp in _iter(folder):
            data = _load(fp)
            # 1) Schema validation
            try:
                obj = adapter.validate_python(data)
                parsed[sub].append((fp, obj, data))
            except ValidationError as e:
                ok = False
                typer.echo(f"[ERROR] {fp}: {e}", err=True)
                continue
            # 2) Expression prevalidation
            expr_errs = _walk_exprs(data, file_path=str(fp), prefix=sub, strict=strict_expr)
            if expr_errs:
                ok = False
                for msg in expr_errs:
                    typer.echo(f"[ERROR] {msg}", err=True)

    # Cross-file checks: precedence uniqueness (as before)
    precedences: dict[int, list[str]] = {}
    for fp, cond, _raw in parsed.get("conditions", []):
        prec = getattr(cond, "precedence", None)
        if prec is None:
            continue
        precedences.setdefault(prec, []).append(getattr(cond, "id", str(fp)))
    dups = {p: ids for p, ids in precedences.items() if len(ids) > 1}
    if dups:
        ok = False
        for p, ids in dups.items():
            typer.echo(f"[ERROR] Condition precedence '{p}' is used by multiple conditions: {', '.join(ids)}", err=True)

    if not ok:
        raise typer.Exit(code=1)
    typer.echo("Content validated successfully.")

# Map a file path to its adapter based on subfolder
TYPE_MAP = {
    "effects": TypeAdapter(EffectDefinition),
    "conditions": TypeAdapter(ConditionDefinition),
    "resources": TypeAdapter(ResourceDefinition),
    "tasks": TypeAdapter(TaskDefinition),
    "zones": TypeAdapter(ZoneDefinition),
}

def _which_adapter(path: Path) -> TypeAdapter | None:
    # Expect content/<kind>/... paths
    parts = path.as_posix().split("/")
    try:
        idx = parts.index("content")
        kind = parts[idx + 1]
    except Exception:
        return None
    return TYPE_MAP.get(kind)

@app.command("validate-files")
def validate_files(
    paths: List[Path] = typer.Argument(...),
    strict_expr: bool = typer.Option(False, "--strict-expr", help="Disallow unknown functions and suspicious symbols in expressions")
):
    ok = True
    for fp in paths:
        if fp.suffix.lower() not in (".json", ".yaml", ".yml"):
            continue
        data = _load(fp)
        adapter = _which_adapter(fp)
        if adapter is None:
            continue
        try:
            adapter.validate_python(data)
        except ValidationError as e:
            ok = False
            typer.echo(f"[ERROR] {fp}: {e}", err=True)
            continue
        # Expression prevalidation
        expr_errs = _walk_exprs(data, file_path=str(fp), prefix=fp.as_posix(), strict=strict_expr)
        if expr_errs:
            ok = False
            for msg in expr_errs:
                typer.echo(f"[ERROR] {msg}", err=True)

    if not ok:
        raise typer.Exit(code=1)
    typer.echo("Selected files validated successfully.")

if __name__ == "__main__":
    app()