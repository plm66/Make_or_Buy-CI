"""Invariants du moteur de composition.

Le test précédent affirmait qu'un menu vegan existe à 5, 7 et 9 €. Il ne tenait que parce
que `selected_cost` rendait le coût matière : les coûts réels sont deux à sept fois
supérieurs et aucun menu ne passe le ratio à ces paliers. Un test qui casse quand un
défaut est corrigé protégeait le défaut.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from make_or_buy.engine import compose_menus, selected_cost

CATALOGUE = json.loads((ROOT / "data" / "catalog.example.json").read_text(encoding="utf-8"))


def test_le_cout_matiere_nest_plus_une_reponse():
    """G002 : « Ne pas comparer le prix fournisseur au seul coût matière interne. »

    Un produit dont le coût complet évitable est inconnu rend None, jamais son coût
    matière. Casse si un repli silencieux réapparaît — c'est la dette qui sous-estimait
    tout coût interne et faisait sortir en MAKE des produits qui devaient être achetés.
    """
    produit = {"signature": {"class": "INHOUSE_SIGNATURE_ADVANTAGE"},
               "internal": {"possible": True, "material_cost_eur": 0.25,
                            "avoidable_cost_eur": None},
               "external": {"possible": False}}
    assert selected_cost(produit) == (None, "MAKE")


def test_le_cookie_de_la_doctrine_sort_en_buy():
    """`illustrative_examples.COOKIE` enseigne qu'un prix fournisseur supérieur au coût
    matière interne peut produire un coût total inférieur. Le moteur rendait MAKE : il
    inversait la leçon que son propre dépôt porte. Casse si l'inversion revient.
    """
    cookie = next(p for p in CATALOGUE if p["id"] == "dessert_cookie_vegan")
    cout, mode = selected_cost(cookie)
    assert cookie["internal"]["material_cost_eur"] < cookie["external"]["landed_cost_eur"]
    assert cookie["internal"]["avoidable_cost_eur"] > cookie["external"]["landed_cost_eur"]
    assert mode == "BUY" and cout == cookie["external"]["landed_cost_eur"]


def test_un_hybride_coute_la_somme_jamais_le_minimum():
    """Un hybride achète une base ET y ajoute du travail interne. Prendre min(interne,
    externe) en faisait le poste le moins cher du catalogue et biaisait le classement vers
    lui. Son coût est porté explicitement ou il est inconnu."""
    focaccia = next(p for p in CATALOGUE if p["signature"]["class"] == "HYBRID_SIGNATURE")
    cout, mode = selected_cost(focaccia)
    assert mode == "HYBRID"
    assert cout > focaccia["external"]["landed_cost_eur"]
    sans = {"signature": {"class": "HYBRID_SIGNATURE"},
            "internal": {"possible": True, "avoidable_cost_eur": 0.5},
            "external": {"possible": True, "landed_cost_eur": 0.4}}
    assert selected_cost(sans) == (None, "HYBRID")


def test_le_ratio_de_cout_matiere_est_une_contrainte_dure():
    """Aucun menu n'est rendu au-dessus du ratio, quel que soit son attrait par ailleurs.

    Aux coûts réels et au palier de 5 €, le catalogue d'exemple n'en produit aucun — c'est
    le signal honnête, pas une panne. Relever le palier en fait réapparaître.
    """
    serre = compose_menus(CATALOGUE, diet="VEGAN", price_tiers=[5], max_food_cost_ratio=0.30)
    assert serre[0]["menus"] == []

    large = compose_menus(CATALOGUE, diet="VEGAN", price_tiers=[5], max_food_cost_ratio=0.95)
    assert large[0]["menus"], "un ratio très permissif doit laisser passer quelque chose"
    for menu in large[0]["menus"]:
        assert menu["estimated_food_cost_ratio"] <= 0.95
        assert len({i["family"] for i in menu["items"]}) == len(menu["items"])


if __name__ == "__main__":
    for nom, fn in sorted(globals().items()):
        if nom.startswith("test_"):
            fn()
            print(f"OK  {nom}")
