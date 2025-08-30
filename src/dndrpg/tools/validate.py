from __future__ import annotations
from pathlib import Path
import json
import yaml
import typer
from pydantic import TypeAdapter, ValidationError
from typing import List
from dndrpg.engine.schema_models import (
    EffectDefinition, ConditionDefinition, ResourceDefinition, TaskDefinition, ZoneDefinition
)

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
def validate_content(content_dir: Path = typer.Argument(Path("src/dndrpg/content"))):
    ok = True
    groups = [
        ("effects", TypeAdapter(EffectDefinition)),
        ("conditions", TypeAdapter(ConditionDefinition)),
        ("resources", TypeAdapter(ResourceDefinition)),
        ("tasks", TypeAdapter(TaskDefinition)),
        ("zones", TypeAdapter(ZoneDefinition)),
    ]

    # First pass: schema-validate each file
    parsed: dict[str, list] = {k: [] for k, _ in groups}
    for sub, adapter in groups:
        folder = content_dir / sub
        if not folder.exists():
            continue
        for fp in _iter(folder):
            data = _load(fp)
            try:
                obj = adapter.validate_python(data)
                parsed[sub].append((fp, obj))
            except ValidationError as e:
                ok = False
                typer.echo(f"[ERROR] {fp}: {e}", err=True)

    # Second pass: cross-file lints/checks
    # A) Condition precedence must be unique (ignoring None)
    precedences: dict[int, list[str]] = {}
    for fp, cond in parsed.get("conditions", []):
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
def validate_files(paths: List[Path] = typer.Argument(...)):
    """
    Validate only the provided files (used by pre-commit).
    Expects paths under src/dndrpg/content/{effects|conditions|resources|tasks|zones}/...
    """
    ok = True
    for fp in paths:
        # Only consider json/yaml
        if fp.suffix.lower() not in (".json", ".yaml", ".yml"):
            continue
        data = _load(fp)
        adapter = _which_adapter(fp)
        if adapter is None:
            # Skip files that are not under recognized content dirs
            continue
        try:
            adapter.validate_python(data)
        except ValidationError as e:
            ok = False
            typer.echo(f"[ERROR] {fp}: {e}", err=True)
    if not ok:
        raise typer.Exit(code=1)
    typer.echo("Selected files validated successfully.")

if __name__ == "__main__":
    app()