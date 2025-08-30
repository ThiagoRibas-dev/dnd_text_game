from __future__ import annotations
from pathlib import Path
import json
import re
from typing import List, Dict, Set, Literal
import yaml
import typer
from py_expression_eval import Parser
from pydantic import TypeAdapter, ValidationError
from dndrpg.engine.schema_models import (
    EffectDefinition, ConditionDefinition, ResourceDefinition, TaskDefinition, ZoneDefinition
)
from dndrpg.engine.loader import ItemAdapter, CampaignAdapter, KitAdapter
from collections import defaultdict


# Linting and error reporting
class LintCounters:
    def __init__(self):
        self.errors = 0
        self.warnings = 0

def emit_error(msg: str, counters: LintCounters):
    typer.echo(f"[ERROR] {msg}", err=True)
    counters.errors += 1

def emit_warn(msg: str, counters: LintCounters):
    typer.echo(f"[WARN] {msg}")
    counters.warnings += 1


CURRENT_SCHEMA_VERSION = "1"  # bump when schemas change incompatibly

# Allowed namespace prefixes by content group
PREFIXES = {
    "effects": {"spell.", "feat."},  # extend later as needed: "power.","maneuver.","stance.","soulmeld.","binding.","class.","race.","item.","other."
    "conditions": {"cond."},
    "resources": {"res."},
    "tasks": {"task."},
    "zones": {"zone."},
    "items": {"item.", "wp.", "ar.", "sh.", "it."},  # accept legacy 'wp./ar./sh./it.'; prefer 'item.' (warn)
    "kits": {"kit."},
    "campaigns": {"camp."},
}

def _enforce_prefix(id_value: str, group: str, strict: bool, counters: LintCounters, file_path: str):
    allowed = PREFIXES.get(group, set())
    if not allowed:
        return
    if not any(id_value.startswith(p) for p in allowed):
        emit_error(f"{file_path}: id '{id_value}' must start with one of {sorted(allowed)}", counters)
        return
    # Soft preference: items should slowly converge to 'item.' prefix
    if group == "items" and strict and not id_value.startswith("item."):
        emit_warn(f"{file_path}: id '{id_value}' uses legacy prefix; prefer 'item.'", counters)

def _check_schema_version(raw: dict, file_path: str, strict: bool, counters: LintCounters):
    sv = raw.get("schema_version", None)
    if sv is None:
        msg = f"{file_path}: missing top-level 'schema_version' (expected '{CURRENT_SCHEMA_VERSION}')"
        if strict:
            emit_error(msg, counters)
        else:
            emit_warn(msg, counters)
        return
    # normalize to string
    sv_str = str(sv)
    if sv_str != CURRENT_SCHEMA_VERSION:
        msg = f"{file_path}: schema_version '{sv_str}' != expected '{CURRENT_SCHEMA_VERSION}'"
        if strict:
            emit_error(msg, counters)
        else:
            emit_warn(msg, counters)

MIGRATIONS = {
    # Example: ("0", "1"): callable
    # ("0", "1"): migrate_0_to_1,
}

def _maybe_migrate_in_place(data: dict, src_version: str) -> dict:
    # Placeholder for future migrations
    # e.g., rename keys, move from old op shapes to typed union
    return data


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

RefCats = Literal["effect","condition","resource","zone","item","kit","campaign","task"]

def _add_ref(refmap: Dict[str, Dict[str, Set[str]]], cat: str, rid: str, file_path: str):
    if not isinstance(rid, str) or not rid:
        return
    refmap.setdefault(cat, {}).setdefault(rid, set()).add(file_path)

# Walk operations/actions in raw dicts (handles nested schedules and save branches)
def _collect_refs_from_op_dict(node: object, refmap: Dict[str, Dict[str, Set[str]]], file_path: str):
    if isinstance(node, dict):
        op = node.get("op")
        if isinstance(op, str):
            if op == "condition.apply":
                cid = node.get("id") or (node.get("params") or {}).get("id")
                _add_ref(refmap, "condition", cid, file_path)
            elif op in ("resource.create","resource.spend","resource.restore","resource.set"):
                rid = node.get("resource_id") or (node.get("params") or {}).get("resource_id")
                _add_ref(refmap, "resource", rid, file_path)
            elif op == "zone.create":
                zid = node.get("zone_id") or (node.get("params") or {}).get("zone_id")
                if zid:
                    _add_ref(refmap, "zone", zid, file_path)
            elif op == "zone.destroy":
                zid = node.get("zone_id")  # instance ids are runtime; only check definition refs
                if zid:
                    _add_ref(refmap, "zone", zid, file_path)
            elif op in ("attach","detach"):
                eid = node.get("effect_id")
                _add_ref(refmap, "effect", eid, file_path)
            elif op == "save":
                for branch_key in ("on_fail","onFail","on_success","onSuccess"):
                    for action in (node.get(branch_key) or []):
                        _collect_refs_from_op_dict(action, refmap, file_path)
            elif op == "schedule":
                for action in (node.get("actions") or []):
                    _collect_refs_from_op_dict(action, refmap, file_path)
        # Recurse into nested containers
        for v in node.values():
            if isinstance(v, (dict, list)):
                _collect_refs_from_op_dict(v, refmap, file_path)
    elif isinstance(node, list):
        for item in node:
            _collect_refs_from_op_dict(item, refmap, file_path)

def _collect_refs_from_effect(raw: dict, file_path: str, refmap: Dict[str, Dict[str, Set[str]]]):
    for op in raw.get("operations", []) or []:
        _collect_refs_from_op_dict(op, refmap, file_path)
    for hook in raw.get("ruleHooks", []) or []:
        for action in hook.get("action", []) or []:
            _collect_refs_from_op_dict(action, refmap, file_path)

def _collect_refs_from_zone(raw: dict, file_path: str, refmap: Dict[str, Dict[str, Set[str]]]):
    for hook in raw.get("hooks", []) or []:
        for action in hook.get("action", []) or []:
            _collect_refs_from_op_dict(action, refmap, file_path)

def _collect_refs_from_task(raw: dict, file_path: str, refmap: Dict[str, Dict[str, Set[str]]]):
    # Costs referencing resources
    for cost in raw.get("costs", []) or []:
        if cost.get("kind") == "resource":
            _add_ref(refmap, "resource", cost.get("resource_id"), file_path)
    # Hooks/actions
    for hook in raw.get("hooks", []) or []:
        for action in hook.get("action", []) or []:
            _collect_refs_from_op_dict(action, refmap, file_path)
    # Completion actions
    comp = raw.get("completion") or {}
    for action in comp.get("actions", []) or []:
        _collect_refs_from_op_dict(action, refmap, file_path)

def _collect_refs_from_kit(raw: dict, file_path: str, refmap: Dict[str, Dict[str, Set[str]]]):
    for iid in raw.get("items", []) or []:
        _add_ref(refmap, "item", iid, file_path)
    for slot, iid in (raw.get("auto_equip") or {}).items():
        if isinstance(iid, str):
            _add_ref(refmap, "item", iid, file_path)

def _collect_refs_from_campaign(raw: dict, file_path: str, refmap: Dict[str, Dict[str, Set[str]]]):
    packs = raw.get("starting_equipment_packs") or {}
    for _cls, kit_ids in packs.items():
        for kid in kit_ids or []:
            _add_ref(refmap, "kit", kid, file_path)

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
    strict: bool = typer.Option(False, "--strict", help="Strict mode: schema + strict expressions + cross-refs + id policy + version; warnings do not fail"),
    warn_unused: bool = typer.Option(False, "--warn-unused", help="Also warn on unused ids (implied by --strict)")
):
    strict_expr = strict
    if strict:
        warn_unused = True

    counters = LintCounters()
    groups = [
        ("effects", TypeAdapter(EffectDefinition)),
        ("conditions", TypeAdapter(ConditionDefinition)),
        ("resources", TypeAdapter(ResourceDefinition)),
        ("tasks", TypeAdapter(TaskDefinition)),
        ("zones", TypeAdapter(ZoneDefinition)),
        ("items", ItemAdapter),
        ("kits", KitAdapter),
        ("campaigns", CampaignAdapter),
    ]

    parsed: dict[str, list] = {k: [] for k, _ in groups}
    total_files = 0

    # 1) Per-file typing + expr + id prefix + schema_version
    for sub, adapter in groups:
        folder = content_dir / sub
        if not folder.exists():
            continue
        for fp in _iter(folder):
            total_files += 1
            data = _load(fp)
            # id prefix and schema_version checks happen regardless of schema pass/fail (give more feedback)
            rid = data.get("id")
            if isinstance(rid, str):
                _enforce_prefix(rid, sub, strict, counters, str(fp))
            _check_schema_version(data, str(fp), strict, counters)

            # Migration hook (if implemented)
            sv_raw = data.get("schema_version")
            if sv_raw is not None and str(sv_raw) != CURRENT_SCHEMA_VERSION:
                data = _maybe_migrate_in_place(data, str(sv_raw))

            # Migration hook (if implemented)
            sv_raw = data.get("schema_version")
            if sv_raw is not None and str(sv_raw) != CURRENT_SCHEMA_VERSION:
                data = _maybe_migrate_in_place(data, str(sv_raw))

            # schema typing
            try:
                obj = adapter.validate_python(data)
                parsed[sub].append((fp, obj, data))
            except ValidationError as e:
                emit_error(f"{fp}: {e}", counters)
                continue

            # expressions
            expr_errs = _walk_exprs(data, file_path=str(fp), prefix=sub, strict=strict_expr)
            for msg in expr_errs:
                emit_error(msg, counters)

    # 2) Cross-refs (as in your previous step)
    defined: dict[str, set[str]] = {
        "effect": {getattr(o, "id") for _, o, _ in parsed["effects"]},
        "condition": {getattr(o, "id") for _, o, _ in parsed["conditions"]},
        "resource": {getattr(o, "id") for _, o, _ in parsed["resources"]},
        "zone": {getattr(o, "id") for _, o, _ in parsed["zones"]},
        "task": {getattr(o, "id") for _, o, _ in parsed["tasks"]},
        "item": {getattr(o, "id") for _, o, _ in parsed["items"]},
        "kit": {getattr(o, "id") for _, o, _ in parsed["kits"]},
        "campaign": {getattr(o, "id") for _, o, _ in parsed["campaigns"]},
    }
    refs: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))

    for fp, _o, raw in parsed["effects"]:
        _collect_refs_from_effect(raw, str(fp), refs)
    for fp, _o, raw in parsed["zones"]:
        _collect_refs_from_zone(raw, str(fp), refs)
    for fp, _o, raw in parsed["tasks"]:
        _collect_refs_from_task(raw, str(fp), refs)
    for fp, _o, raw in parsed["kits"]:
        _collect_refs_from_kit(raw, str(fp), refs)
    for fp, _o, raw in parsed["campaigns"]:
        _collect_refs_from_campaign(raw, str(fp), refs)

    def _report_missing(cat: str):
        used = refs.get(cat, {})
        missing = set(used.keys()) - defined.get(cat, set())
        for mid in sorted(missing):
            locs = ", ".join(sorted(used[mid]))
            emit_error(f"Missing {cat} id '{mid}' referenced from: {locs}", counters)

    for cat in ("condition","resource","zone","effect","item","kit"):
        _report_missing(cat)

    # Unused warnings
    if warn_unused:
        for cat in ("effect","condition","resource","zone","item","kit","campaign","task"):
            defined_set = defined.get(cat, set())
            used_set = set(refs.get(cat, {}).keys())
            for uid in sorted(defined_set - used_set):
                emit_warn(f"Unused {cat} id: {uid}", counters)

    # 3) Cross-file checks: condition precedence uniqueness
    precedences: dict[int, list[str]] = {}
    for fp, cond, _raw in parsed.get("conditions", []):
        prec = getattr(cond, "precedence", None)
        if prec is None:
            continue
        precedences.setdefault(prec, []).append(getattr(cond, "id", str(fp)))
    for p, ids in precedences.items():
        if len(ids) > 1:
            emit_error(f"Condition precedence '{p}' is used by multiple conditions: {', '.join(ids)}", counters)

    # 4) Summary / exit code
    typer.echo(f"Validated {total_files} content files — {counters.errors} error(s), {counters.warnings} warning(s).")
    if counters.errors > 0:
        raise typer.Exit(code=1)

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
