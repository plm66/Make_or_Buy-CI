from __future__ import annotations
import json, os, urllib.request
from pathlib import Path

def build_context(doctrine_path, catalog_path, user_question):
    doctrine = json.loads(Path(doctrine_path).read_text(encoding="utf-8"))
    catalog = json.loads(Path(catalog_path).read_text(encoding="utf-8"))
    return {
        "instruction": (
            "Réponds en appliquant strictement la doctrine Make or Buy. "
            "Sépare les faits, estimations et hypothèses. "
            "Pour toute recommandation, indique les contraintes dominantes et le niveau de confiance."
        ),
        "doctrine": doctrine,
        "catalog": catalog,
        "question": user_question
    }

def ask_openai_compatible(context, model=None):
    base = os.environ.get("LLM_BASE_URL","").rstrip("/")
    key = os.environ.get("LLM_API_KEY","")
    model = model or os.environ.get("LLM_MODEL","")
    if not base or not model:
        raise RuntimeError("Définir LLM_BASE_URL et LLM_MODEL. LLM_API_KEY si le fournisseur l'exige.")
    body = {
        "model": model,
        "messages": [
            {"role":"system","content":"Tu es un moteur de décision de sourcing et de composition de menus pour une boulangerie."},
            {"role":"user","content":json.dumps(context, ensure_ascii=False)}
        ],
        "temperature":0.2
    }
    req = urllib.request.Request(
        base + "/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type":"application/json", **({"Authorization":f"Bearer {key}"} if key else {})},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.loads(r.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]
