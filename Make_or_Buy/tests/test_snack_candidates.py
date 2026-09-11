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


def test_la_forme_dun_candidat_est_uniforme():
    """Une clé absente et une clé à null ne se lisent pas pareil : la première oblige
    chaque lecteur à deviner laquelle il a reçue. Même défaut que la branche bloquante du
    validateur, corrigée pour la même raison."""
    obligatoires = {"candidate_id", "landed_cost_eur_per_piece", "effective_manita_cost_eur",
                    "reference_price_eur_per_piece", "registry_lead_id", "registry_supplier_id"}
    for c in DATA["candidates"]:
        assert obligatoires <= set(c), (c["candidate_id"], sorted(obligatoires - set(c)))


def test_un_prix_de_reference_nest_pas_un_prix_rendu():
    """Le registre d'achat range les deux sous un seul en-tête, « Reference / Landed
    €/piece ». Trier dessus ferait passer un tarif historique de 0,15 € pour un coût
    comptable. Deux champs, deux noms : le chiffre est conservé, il ne peut plus être lu
    comme une décision.
    """
    for c in DATA["candidates"]:
        if c.get("reference_price_eur_per_piece") is not None:
            assert c["landed_cost_eur_per_piece"] is None, c["candidate_id"]
            assert c["reference_price_basis"] == "HISTORICAL_NEEDS_CURRENT_QUOTE"


def test_chaque_candidat_pointe_vers_un_fournisseur_du_registre():
    """Un lead sans fournisseur homologué ne peut pas être commandé. Le lien vers le
    supplier master est ce qui rend le vivier actionnable plutôt qu'indicatif."""
    import json as _json
    index = _json.loads((ROOT / "data" / "suppliers" / "index.json").read_text(encoding="utf-8"))
    registre = {s["supplier_id"] for s in index["suppliers"]}
    fiches = {_json.loads(p.read_text(encoding="utf-8"))["procurement"]["registry_id"]
              for p in (ROOT / "data" / "suppliers").glob("*.json")
              if "procurement" in _json.loads(p.read_text(encoding="utf-8"))}
    assert len(registre) == 13
    for c in DATA["candidates"]:
        assert c.get("registry_supplier_id") in fiches, c["candidate_id"]


if __name__ == "__main__":
    for nom, fn in sorted(globals().items()):
        if nom.startswith("test_"):
            fn()
            print(f"OK  {nom}")
