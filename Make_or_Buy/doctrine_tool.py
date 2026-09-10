#!/usr/bin/env python3
"""
doctrine_tool.py — validation, mise à jour contrôlée et export de contexte LLM.

Usage:
  python doctrine_tool.py validate doctrine.json
  python doctrine_tool.py update doctrine.json update.json --bump minor
  python doctrine_tool.py context doctrine.json --output llm_context.json
  python doctrine_tool.py checksum doctrine.json
"""
from __future__ import annotations
import argparse
import copy
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys

def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def dump(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def version_tuple(v):
    if not re.fullmatch(r"\d+\.\d+\.\d+", v):
        raise ValueError(f"Version sémantique invalide: {v}")
    return tuple(map(int, v.split(".")))

def bump_version(v, kind):
    major, minor, patch = version_tuple(v)
    if kind == "major":
        return f"{major+1}.0.0"
    if kind == "minor":
        return f"{major}.{minor+1}.0"
    if kind == "patch":
        return f"{major}.{minor}.{patch+1}"
    raise ValueError(kind)

def get_parent(root, dotted, create=False):
    parts = dotted.split(".")
    cur = root
    for p in parts[:-1]:
        if p not in cur:
            if not create:
                raise KeyError(dotted)
            cur[p] = {}
        if not isinstance(cur[p], dict):
            raise TypeError(f"{p} n'est pas un objet JSON")
        cur = cur[p]
    return cur, parts[-1]

def apply_change(doc, change):
    op = change["op"]
    path = change["path"]
    parent, key = get_parent(doc, path, create=(op == "set"))
    old = copy.deepcopy(parent.get(key)) if isinstance(parent, dict) else None
    if op == "set":
        parent[key] = change.get("value")
    elif op == "delete":
        if key not in parent:
            raise KeyError(path)
        del parent[key]
    elif op == "append":
        if key not in parent or not isinstance(parent[key], list):
            raise TypeError(f"{path} doit pointer vers une liste")
        parent[key].append(change.get("value"))
    else:
        raise ValueError(f"Opération inconnue: {op}")
    return old

def validate_internal(doc):
    errors = []
    required = ["metadata","purpose","principles","product_classes","decision_modes",
                "criteria","guardrails","decision_workflow","llm_research_protocol"]
    for k in required:
        if k not in doc:
            errors.append(f"Section manquante: {k}")

    md = doc.get("metadata", {})
    if not re.fullmatch(r"\d+\.\d+\.\d+", str(md.get("machine_version",""))):
        errors.append("metadata.machine_version doit être au format MAJOR.MINOR.PATCH")

    criteria = doc.get("criteria", {})
    weights = []
    for cid, c in criteria.items():
        try:
            w = float(c["weight"])
            if not 0 <= w <= 1:
                errors.append(f"{cid}.weight hors intervalle [0,1]")
            weights.append(w)
        except Exception:
            errors.append(f"{cid}.weight invalide")
    if weights and abs(sum(weights)-1.0) > 1e-9:
        errors.append(f"La somme des poids des critères vaut {sum(weights):.6f}, attendu 1.0")

    steps = [x.get("step") for x in doc.get("decision_workflow", [])]
    if steps and steps != list(range(1, len(steps)+1)):
        errors.append("decision_workflow doit être numéroté sans rupture à partir de 1")

    allowed_classes = set(doc.get("product_classes",{}))
    allowed_modes = set(doc.get("decision_modes",{}))
    for eid, ex in doc.get("illustrative_examples",{}).items():
        cls = ex.get("classification")
        mode = ex.get("orientation")
        if cls and cls not in allowed_classes:
            errors.append(f"Exemple {eid}: classification inconnue {cls}")
        if mode and mode not in allowed_modes:
            errors.append(f"Exemple {eid}: orientation inconnue {mode}")
    return errors

def cmd_validate(args):
    doc = load(args.doctrine)
    errors = validate_internal(doc)
    if errors:
        print("INVALID")
        for e in errors:
            print("-", e)
        sys.exit(1)
    print("VALID")
    print("version:", doc["metadata"]["machine_version"])
    print("sha256:", sha256(args.doctrine))

def cmd_update(args):
    doctrine_path = Path(args.doctrine)
    doc = load(doctrine_path)
    update = load(args.update)

    current = doc["metadata"]["machine_version"]
    expected = update.get("base_version")
    if expected and expected != current:
        raise SystemExit(f"Refus: update prévu pour {expected}, doctrine courante {current}")

    old_doc = copy.deepcopy(doc)
    audit = []
    for change in update.get("changes", []):
        if "reason" not in change or not change["reason"].strip():
            raise SystemExit(f"Chaque changement doit contenir un 'reason': {change}")
        old = apply_change(doc, change)
        audit.append({
            "op": change["op"],
            "path": change["path"],
            "old": old,
            "new": change.get("value"),
            "reason": change["reason"]
        })

    new_version = bump_version(current, args.bump)
    doc["metadata"]["machine_version"] = new_version
    doc["metadata"]["last_updated"] = dt.date.today().isoformat()
    doc["metadata"].setdefault("revision_history", []).append({
        "version": new_version,
        "date": dt.date.today().isoformat(),
        "reason": update.get("reason", "Mise à jour doctrinale."),
        "changes": audit
    })

    errors = validate_internal(doc)
    if errors:
        print("Mise à jour refusée: doctrine invalide.")
        for e in errors:
            print("-", e)
        sys.exit(1)

    history_dir = doctrine_path.parent / "history"
    history_dir.mkdir(exist_ok=True)
    snapshot = history_dir / f"doctrine_{current}.json"
    if not snapshot.exists():
        dump(snapshot, old_doc)

    dump(doctrine_path, doc)
    print(f"UPDATED {current} -> {new_version}")
    print("sha256:", sha256(doctrine_path))

def cmd_context(args):
    doc = load(args.doctrine)
    errors = validate_internal(doc)
    if errors:
        raise SystemExit("Doctrine invalide; lancer validate.")
    context = {
        "doctrine_id": doc["metadata"]["doctrine_id"],
        "version": doc["metadata"]["machine_version"],
        "primary_rule": doc["purpose"]["primary_rule"],
        "principles": doc["principles"],
        "product_classes": doc["product_classes"],
        "decision_modes": doc["decision_modes"],
        "criteria": doc["criteria"],
        "cost_model": doc.get("cost_model"),
        "conservation_requirements": doc.get("conservation_requirements"),
        "traceability_requirements": doc.get("traceability_requirements"),
        "guardrails": doc["guardrails"],
        "decision_workflow": doc["decision_workflow"],
        "llm_research_protocol": doc["llm_research_protocol"]
    }
    out = Path(args.output)
    dump(out, context)
    print(out)

def cmd_checksum(args):
    print(sha256(args.doctrine))

def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(required=True)

    v = sub.add_parser("validate")
    v.add_argument("doctrine")
    v.set_defaults(func=cmd_validate)

    u = sub.add_parser("update")
    u.add_argument("doctrine")
    u.add_argument("update")
    u.add_argument("--bump", choices=["major","minor","patch"], default="minor")
    u.set_defaults(func=cmd_update)

    c = sub.add_parser("context")
    c.add_argument("doctrine")
    c.add_argument("--output", default="llm_context.json")
    c.set_defaults(func=cmd_context)

    h = sub.add_parser("checksum")
    h.add_argument("doctrine")
    h.set_defaults(func=cmd_checksum)

    args = p.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
