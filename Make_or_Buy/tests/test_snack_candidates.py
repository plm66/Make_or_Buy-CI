"""Invariants du vivier de candidats snack BUY.

Le fichier est une passe de recherche fournisseur, pas une source de décision. Ces tests
protègent la seule chose qui compte : qu'aucun candidat ne prétende un coût qu'il n'a pas.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "data" / "supplier_products" / "snack_buy_candidates.json").read_text(encoding="utf-8"))


def test_aucun_candidat_ne_pretend_un_cout_effectif_non_calcule():
    """P022 et G002 : le prix rendu n'est pas le coût effectif. Un candidat qui annonce un
    effective_manita_cost_eur sans avoir chiffré sa remise en température fabriquerait la
    décision que tout le dispositif existe pour empêcher.
    """
    for c in DATA["candidates"]:
        if c.get("effective_manita_cost_eur") is not None:
            assert c.get("effective_cost_status") == "COMPUTED", (c["candidate_id"], c.get("effective_cost_status"))


def test_le_prix_a_la_piece_se_recalcule_depuis_le_colis():
    """Règle du dataset : ne pas faire confiance au prix unitaire affiché quand il
    contredit l'arithmétique du colis livré. On vérifie que la division tombe juste."""
    for c in DATA["candidates"]:
        piece, pack, prix = (c.get("landed_cost_eur_per_piece"),
                             c.get("pack_units"), c.get("delivered_pack_price_eur_ht"))
        if None in (piece, pack, prix):
            continue
        assert abs(piece - prix / pack) < 1e-4, (c["candidate_id"], piece, prix / pack)


def test_un_lead_sans_devis_na_pas_de_cout_rendu():
    """QUOTE_REQUIRED_IDF désigne une piste, pas un coût validé. Lui attribuer un prix
    rendu ferait entrer une estimation dans un arbitrage."""
    for c in DATA["candidates"]:
        if c.get("status") == "QUOTE_REQUIRED_IDF":
            assert c.get("landed_cost_eur_per_piece") is None, c["candidate_id"]


def test_une_base_seule_est_un_hybride_pas_un_achat():
    """Un pain à burger n'est pas un snack : il faut le garnir. Le classer BUY ferait
    passer son prix rendu pour le coût du produit fini."""
    for c in DATA["candidates"]:
        if c.get("candidate_type") == "BASE_ONLY":
            assert c.get("sourcing_mode") == "HYBRID", c["candidate_id"]


if __name__ == "__main__":
    for nom, fn in sorted(globals().items()):
        if nom.startswith("test_"):
            fn()
            print(f"OK  {nom}")
