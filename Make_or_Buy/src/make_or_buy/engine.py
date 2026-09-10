from __future__ import annotations
from dataclasses import dataclass
from itertools import product
from pathlib import Path
import json

DEFAULT_FAMILIES = ["SNACK","COLD_DRINK","COMPLEMENT","DESSERT","HOT_DRINK"]

def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def is_eligible(item, diet):
    if diet == "ANY":
        return True
    if diet == "VEGAN":
        return bool(item.get("diet",{}).get("vegan"))
    if diet == "VEGETARIAN":
        return bool(item.get("diet",{}).get("vegetarian"))
    return False

def selected_cost(item):
    """
    Estimation simple de coût opérationnel retenu.
    Ce moteur est volontairement conservateur: il compare d'abord coûts connus.
    La doctrine reste prioritaire sur une décision automatique.
    """
    cls = item["signature"]["class"]
    i = item.get("internal",{})
    e = item.get("external",{})

    if cls == "INHOUSE_SIGNATURE_ADVANTAGE" and i.get("possible"):
        return i.get("material_cost_eur"), "MAKE"
    if cls == "SUPPLIER_SUPERIOR" and e.get("possible"):
        return e.get("landed_cost_eur"), "BUY"
    if cls == "HYBRID_SIGNATURE":
        # Faute d'un coût hybride détaillé, prendre le meilleur coût disponible et signaler HYBRID.
        vals = [v for v in [i.get("material_cost_eur"), e.get("landed_cost_eur")] if isinstance(v,(int,float))]
        return (min(vals) if vals else None), "HYBRID"

    vals = []
    if i.get("possible") and isinstance(i.get("material_cost_eur"),(int,float)):
        vals.append((i["material_cost_eur"],"MAKE"))
    if e.get("possible") and isinstance(e.get("landed_cost_eur"),(int,float)):
        vals.append((e["landed_cost_eur"],"BUY"))
    return min(vals, default=(None,"UNDECIDED"), key=lambda x:x[0])

def menu_score(items, target_price, max_food_cost_ratio=0.30, prefer_signature=True):
    rows = []
    total_cost = 0.0
    sale_value = 0.0
    signature = 0.0
    for item in items:
        c, mode = selected_cost(item)
        if c is None:
            return None
        total_cost += c
        sale_value += float(item.get("sale_price_eur",0))
        signature += float(item.get("signature",{}).get("customer_value_score",0))
        rows.append({"id":item["id"],"name":item["name"],"family":item["family"],"cost_eur":round(c,3),"mode":mode})

    ratio = total_cost / target_price if target_price else 999
    if ratio > max_food_cost_ratio:
        return None

    perceived_discount = max(sale_value - target_price, 0)
    # Score favorise valeur perçue, marge et identité.
    score = perceived_discount * 2.0 + (1-ratio) * 5.0 + (signature if prefer_signature else 0) * 0.15
    return {
        "target_price_eur": target_price,
        "estimated_cost_eur": round(total_cost,2),
        "estimated_food_cost_ratio": round(ratio,3),
        "estimated_reference_value_eur": round(sale_value,2),
        "estimated_customer_saving_eur": round(perceived_discount,2),
        "score": round(score,3),
        "items": rows
    }

def compose_menus(catalog, diet="ANY", price_tiers=(5,7,9), families=None,
                  max_food_cost_ratio=0.30, prefer_signature=True, top_n=1):
    families = families or DEFAULT_FAMILIES
    pools = []
    for family in families:
        eligible = [x for x in catalog if x["family"] == family and is_eligible(x,diet)]
        if not eligible:
            raise ValueError(f"Aucun produit éligible pour {family} / {diet}")
        pools.append(eligible)

    results = []
    for tier in price_tiers:
        candidates = []
        for combo in product(*pools):
            s = menu_score(combo, tier, max_food_cost_ratio, prefer_signature)
            if s:
                candidates.append(s)
        candidates.sort(key=lambda x:x["score"], reverse=True)
        results.append({
            "price_tier_eur": tier,
            "diet": diet,
            "menus": candidates[:top_n],
            "candidate_count": len(candidates)
        })
    return results
