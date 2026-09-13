"""Invariants des relevés de catalogue Halal Food Service.

La source expose une API PrestaShop publique : la capture est fiable, donc la tentation
est de la croire complète et opérationnelle. Ces tests protègent les deux illusions —
qu'un relevé partiel passe pour exhaustif, et qu'un prix catalogue passe pour un coût rendu.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RELEVES = sorted((ROOT / "data" / "price_observations").glob("halalfs_*.json"))


def _lire(p):
    return json.loads(p.read_text(encoding="utf-8"))


def test_au_moins_un_releve():
    """Garde-fou des tests eux-mêmes : découverte par glob, donc zéro fichier rendrait
    tous les autres verts sans rien vérifier."""
    assert RELEVES, "aucun halalfs_*.json dans data/price_observations/"


def test_le_releve_est_complet_ou_le_dit():
    """La pagination annonce un total. Ramener moins et se taire ferait passer un relevé
    tronqué pour le catalogue entier — c'est exactement ce qui rend une couverture
    inaffirmable chez les autres sources.
    """
    for p in RELEVES:
        d = _lire(p)
        assert len(d["products"]) == d["pagination_declared_total"], (
            p.name, len(d["products"]), d["pagination_declared_total"])


def test_la_base_de_taxe_est_lue_jamais_deduite():
    """« Do not infer HT/TTC status » — price_capture_policy. Cette source est la seule des
    six auditées à la déclarer : elle doit citer où elle l'a lue, sinon on ne distinguera
    plus une lecture d'une supposition.
    """
    for p in RELEVES:
        d = _lire(p)
        assert d["tax_basis"] in ("HT", "TTC", "UNKNOWN"), (p.name, d["tax_basis"])
        if d["tax_basis"] != "UNKNOWN":
            assert d["tax_basis_evidence"], p.name


def test_aucun_cout_rendu_nest_affirme():
    """Un prix catalogue n'est pas un coût rendu : l'API ne porte ni conditions de
    livraison ni franco. Un champ de coût rendu ici se ferait passer pour constaté.
    """
    interdit = re.compile(r"landed|rendu|delivered", re.I)
    for p in RELEVES:
        d = _lire(p)
        for champ in d["products"][0]:
            assert not interdit.search(champ), (p.name, champ)
        assert d["data_status"] == "RAW_UNMATCHED_NOT_OPERATIONALLY_VALIDATED", p.name


def test_chaque_produit_porte_une_cle_de_deduplication():
    """`refresh` compare deux relevés par référence. Sans clé stable, un produit renommé
    passerait pour une disparition suivie d'une apparition, et tout différentiel mentirait.
    """
    for p in RELEVES:
        d = _lire(p)
        cles = [x["reference"] or x["id_product"] for x in d["products"]]
        assert all(cles), p.name
        assert len(cles) == len(set(cles)), (p.name, len(cles) - len(set(cles)))


def test_une_categorie_promotions_ne_presume_pas_de_remise():
    """Les 72 produits de `577-promotions` portent tous `has_discount: false`. La promotion
    tient à l'appartenance à la catégorie, pas à un flag PrestaShop. Déduire une remise de
    l'un ou de l'autre inventerait un écart de prix.
    """
    for p in RELEVES:
        d = _lire(p)
        for x in d["products"]:
            if x["has_discount"]:
                assert x["discount_type"] and x["regular_price_amount"] is not None, (
                    p.name, x["reference"])


if __name__ == "__main__":
    for nom, fn in sorted(globals().items()):
        if nom.startswith("test_"):
            fn()
            print(f"OK  {nom}")
