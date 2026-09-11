from __future__ import annotations
from dataclasses import dataclass
from itertools import product
from pathlib import Path
import json

DEFAULT_FAMILIES = ["SNACK","COLD_DRINK","GARNITURE","DESSERT","HOT_DRINK"]

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
    """(coût complet évitable, mode) du produit, ou (None, mode) si la donnée manque.

    Logique normative — La Manita config, cost_metric SELECTED_EFFECTIVE_PRODUCT_COST :

        MAKE    avoidable_cost_eur                    coût complet évitable interne
        BUY     external.landed_cost_eur              prix rendu de la source retenue
        HYBRID  composants achetés + opérations internes évitables

    Aucun repli sur le coût matière. Il a longtemps servi de valeur par défaut et c'était
    la dette G002 : comparer un prix fournisseur au seul coût matière interne est
    exactement ce que la doctrine interdit en G002, et ça sous-estimait le coût interne
    d'un facteur 2 à 7. Une donnée absente rend None, ce qui remonte en DATA_INCOMPLETE
    plutôt qu'en décision fabriquée.
    """
    cls = item["signature"]["class"]
    i = item.get("internal", {})
    e = item.get("external", {})
    interne = i.get("avoidable_cost_eur") if i.get("possible") else None
    externe = e.get("landed_cost_eur") if e.get("possible") else None
    interne = interne if isinstance(interne, (int, float)) else None
    externe = externe if isinstance(externe, (int, float)) else None

    if cls == "INHOUSE_SIGNATURE_ADVANTAGE":
        return interne, "MAKE"
    if cls == "SUPPLIER_SUPERIOR":
        return externe, "BUY"
    if cls == "HYBRID_SIGNATURE":
        # Un hybride achète une base ET y ajoute du travail interne: son coût est la somme,
        # jamais le minimum. Prendre min() faisait de l'hybride le poste le moins cher du
        # catalogue et biaisait tout le classement vers lui.
        hybride = item.get("hybrid", {}).get("avoidable_cost_eur")
        return (hybride if isinstance(hybride, (int, float)) else None), "HYBRID"

    candidats = [(c, m) for c, m in ((interne, "MAKE"), (externe, "BUY")) if c is not None]
    return min(candidats, default=(None, "UNDECIDED"), key=lambda x: x[0])


def menu_score(items, target_price, hard_max_cost_ratio=0.35, target_cost_ratio=0.30,
               prefer_signature=True):
    """Score d'un panier, ou None s'il dépasse le plafond dur.

    Deux ratios, deux rôles. Le postulat La Manita les sépare explicitement
    (`hard_max_bundle_cost_ratio` 0.35, `target_bundle_cost_ratio` 0.30) : le premier
    rejette, le second oriente. Les défauts reprennent ces valeurs sans importer le
    postulat — le moteur reste générique, l'appelant impose sa norme.
    """
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
    # Avant fix: le seuil de rejet valait 0.30, la *cible*. Toute la bande 30-35 %
    # que le postulat declare admissible etait supprimee, dont le panier reellement
    # source a 1,5462 EUR (30,9 % a 5 EUR). Le moteur refusait la bonne reponse.
    if ratio > hard_max_cost_ratio:
        return None

    perceived_discount = max(sale_value - target_price, 0)
    # Score favorise valeur perçue, marge et identité.
    score = perceived_discount * 2.0 + (1-ratio) * 5.0 + (signature if prefer_signature else 0) * 0.15
    return {
        "target_price_eur": target_price,
        "estimated_cost_eur": round(total_cost,2),
        "estimated_food_cost_ratio": round(ratio,3),
        "within_target_ratio": ratio <= target_cost_ratio,
        "estimated_reference_value_eur": round(sale_value,2),
        "estimated_customer_saving_eur": round(perceived_discount,2),
        "score": round(score,3),
        "items": rows
    }

def compose_menus(catalog, diet="ANY", price_tiers=(5,7,9), families=None,
                  hard_max_cost_ratio=0.35, target_cost_ratio=0.30,
                  prefer_signature=True, top_n=1):
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
            s = menu_score(combo, tier, hard_max_cost_ratio, target_cost_ratio,
                           prefer_signature)
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
