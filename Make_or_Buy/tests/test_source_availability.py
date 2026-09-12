"""Invariants de l'audit d'accessibilité des sources de prix.

Le registre classe une source `ACTIVE_PUBLIC` ; l'audit dit ce qu'on a vu, à une date.
Les deux ne disent pas la même chose et ne doivent pas être confondus — une classification
est une décision, une accessibilité est un fait daté. Ces tests protègent la couverture de
l'audit et l'honnêteté de sa méthode.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _lire(*parts):
    return json.loads(ROOT.joinpath(*parts).read_text(encoding="utf-8"))


AUDIT = _lire("data", "price_observations", "source_availability_2026-09-12.json")
REGISTRE = _lire("data", "supplier_price_sources", "supplier_price_sources.registry.json")


def test_laudit_couvre_toutes_les_sources_declarees_actives():
    """Une source publique non auditée est une source qu'on croit disponible sans l'avoir
    vérifiée. C'est exactement l'état d'où sort cet audit : six sources déclarées
    publiques, dont une injoignable.
    """
    actives = {s["price_source_id"] for s in REGISTRE["sources"]
               if s["source_status"] == "ACTIVE_PUBLIC"}
    auditees = {s["price_source_id"] for s in AUDIT["sources"]}
    assert actives <= auditees, sorted(actives - auditees)


def test_une_source_injoignable_est_signalee_comme_divergente():
    """Le registre continuerait sinon d'annoncer une source active que rien n'atteint. La
    divergence doit être portée par la donnée, pas seulement par un commentaire.
    """
    for s in AUDIT["sources"]:
        if not s["reachable"]:
            assert s["matches_registry"] is False, s["price_source_id"]
            assert s.get("registry_correction_needed"), s["price_source_id"]


def test_une_divergence_nomme_la_correction_attendue():
    """Constater un écart sans dire ce qu'il faut corriger laisse le registre en l'état.
    Un audit qui ne débouche sur rien n'a mesuré que du temps.
    """
    for s in AUDIT["sources"]:
        if s["matches_registry"] is False:
            assert s.get("registry_correction_needed"), s["price_source_id"]


def test_laudit_declare_les_limites_de_sa_methode():
    """Un rapport sans limites déclarées se lit comme une preuve. Celui-ci a été produit en
    faisant résumer des pages marchandes par un modèle, qui s'est contredit sur une source :
    la méthode doit se dénoncer elle-même, sinon ses résultats passeront pour mesurés.
    """
    assert AUDIT["method"] == "PAGE_READ_BY_MODEL"
    assert len(AUDIT["method_limits"]) >= 2


def test_aucun_prix_ne_sort_de_cet_audit():
    """L'audit porte sur l'accessibilité, jamais sur les montants. Un prix capté par
    lecture de prose entrerait dans le dépôt avec l'autorité d'une observation datée sans
    en avoir la fiabilité — la contradiction relevée sur aj_foods suffit à l'interdire.
    """
    interdit = ("price_eur", "prix_eur", "case_price_eur", "price_per_piece_eur",
                "landed_cost_eur_per_piece", "displayed_price_eur")
    for s in AUDIT["sources"]:
        for champ in s:
            assert champ not in interdit, (s["price_source_id"], champ)


def test_aucune_base_de_taxe_nest_inferee():
    """« Do not infer HT/TTC status. Store UNKNOWN » — price_capture_policy. Aucune des six
    sources ne l'indique ; l'audit doit le constater plutôt que de trancher.
    """
    for s in AUDIT["sources"]:
        assert s["tax_basis_stated"] is False, s["price_source_id"]


if __name__ == "__main__":
    for nom, fn in sorted(globals().items()):
        if nom.startswith("test_"):
            fn()
            print(f"OK  {nom}")
