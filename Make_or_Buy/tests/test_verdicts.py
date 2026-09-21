"""Invariants des verdicts par ligne : conserver, changer, arbitrer, écarter.

Le module propose, il ne commande pas. Une proposition n'a de valeur que si elle est
portée par un fait : une matière identifiée, un prix au kilo, et pour un changement, le
prix de l'alternative. Le verdict qui compte est celui qu'on refuse de rendre.

Ces invariants tiennent une seule règle dure, celle de `docs/SPEC_MODULE_FACTURES.md` :
`CHANGER` exige un prix alternatif aligné et daté. Tout le reste en découle.
"""
import json
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))

import comparaison_factures as cf  # noqa: E402

RELEVE = RACINE / "data/price_observations/metro_factures_2026-09-11.json"
RATTACHEMENT = RACINE / "data/materials/rattachement_metro.csv"
MATIERES = RACINE / "data/materials/matieres_premieres.csv"


def _lire():
    import csv
    achats = json.loads(RELEVE.read_text(encoding="utf-8"))["achats"]
    rattachement = list(csv.DictReader(RATTACHEMENT.read_text(encoding="utf-8").splitlines(),
                                       delimiter=";"))
    matieres = {m["id_matiere"]: m for m in csv.DictReader(
        MATIERES.read_text(encoding="utf-8").splitlines(), delimiter=";")}
    return achats, rattachement, matieres


def ligne(**kw):
    base = {"article": "2422798", "date_facture": "2026-07-27", "facture": "F1",
            "designation": "MC FARINE PANIF. T65 25KG", "colisage": 25,
            "prix_unitaire_ht": 0.75, "prix_unitaire_paye": None,
            "prix_unite_normalisee": None}
    base.update(kw)
    return base


def test_une_ligne_non_rattachee_ne_propose_ni_de_garder_ni_de_changer():
    """Sans rattachement, on ne sait pas de quoi parle la ligne. Proposer de garder le
    fournisseur serait une opinion sur un produit non identifié."""
    v = cf.verdict_ligne(ligne(article="7777777"), None)
    assert v["verdict"] == cf.NON_RATTACHE, v
    assert v["raison"] == "ARTICLE_ABSENT_DU_RATTACHEMENT", v
    assert v["id_matiere"] is None, v


def test_une_ligne_non_alimentaire_est_ecartee_et_pas_forcee_dans_le_referentiel():
    """Une casserole ne vise aucune matière. Le statut le dit, et la ligne est comptée à
    part plutôt que rattachée de force pour remplir une case."""
    casserole = ligne(article="0012476", designation="MP CASSEROLE INOX D28CM",
                      prix_unitaire_ht=42.87, colisage=1)
    lien = {"article_metro": "0012476", "id_matiere": "", "statut": "HORS_PERIMETRE"}
    v = cf.verdict_ligne(casserole, lien)
    assert v["verdict"] == cf.HORS_PERIMETRE, v
    assert v["raison"] == "NON_ALIMENTAIRE", v
    assert v["id_matiere"] is None, v


def test_une_reserve_ne_produit_pas_de_garder():
    """Un `A_VERIFIER` dit que le critère du référentiel n'est pas écrit sur la facture. La
    valeur est publiée, le verdict reste ouvert, et la réserve est lisible."""
    lien = {"article_metro": "2252104", "id_matiere": "MATP-BEUR-DOUX", "statut": "A_VERIFIER"}
    v = cf.verdict_ligne(ligne(article="2252104", designation="BEURRE DX 500G MA PAYSANNE",
                               prix_unitaire_ht=3.65, colisage=1), lien)
    assert v["verdict"] == cf.A_ARBITRER, v
    assert v["raison"] == "RESERVE_A_VERIFIER", v
    assert v["statut_rattachement"] == "A_VERIFIER", v


def test_un_conditionnement_illisible_ferme_la_proposition():
    """Sans prix au kilo, il n'y a rien à comparer. Le verdict le dit, et ne rend pas un
    prix de colis en le faisant passer pour un prix au kilo."""
    lien = {"article_metro": "0512202", "id_matiere": "MATP-FRUI-FRAI", "statut": "ACTIF"}
    v = cf.verdict_ligne(ligne(article="0512202", designation="FRAISE 500G BQ8",
                               prix_unitaire_ht=4.99, colisage=1), lien,
                         alternatives={"MATP-FRUI-FRAI": [{"prix_eur_par_kg": 2.0, "date": "2026-08-01"}]})
    assert v["verdict"] == cf.A_ARBITRER, v
    assert v["raison"] == "CONDITIONNEMENT_ILLISIBLE", v
    assert v["prix_eur_par_kg"] is None, v


def test_une_alternative_moins_chere_et_datee_produit_un_changement():
    """Le seul cas où le dépôt propose de changer : une autre source, chiffrée, datée, et
    strictement moins chère. Le prix de l'alternative est attaché au verdict."""
    lien = {"article_metro": "2422798", "id_matiere": "MATP-FARI-T65", "statut": "ACTIF"}
    alternative = {"source_id": "autre_meunier", "prix_eur_par_kg": 0.62, "date": "2026-08-15"}
    v = cf.verdict_ligne(ligne(), lien, alternatives={"MATP-FARI-T65": [alternative]})
    assert v["verdict"] == cf.CHANGER, v
    assert v["raison"] == "ALTERNATIVE_MOINS_CHERE", v
    assert v["alternative"] == alternative, v


def test_une_alternative_plus_chere_ne_produit_pas_de_changement():
    """Comparer, c'est aussi constater qu'on achète déjà mieux. La proposition de garder
    devient alors motivée, et le dit."""
    lien = {"article_metro": "2422798", "id_matiere": "MATP-FARI-T65", "statut": "ACTIF"}
    v = cf.verdict_ligne(ligne(), lien,
                         alternatives={"MATP-FARI-T65": [{"prix_eur_par_kg": 0.99, "date": "2026-08-15"}]})
    assert v["verdict"] == cf.GARDER, v
    assert v["raison"] == "ALTERNATIVE_PLUS_CHEREE", v


def test_une_alternative_sans_prix_ne_produit_jamais_de_changement():
    """Le point d'honnêteté du module : un candidat sans prix, ou sans date, ne permet pas de
    trancher. Il ne doit pas non plus faire croire qu'on a comparé."""
    lien = {"article_metro": "2422798", "id_matiere": "MATP-FARI-T65", "statut": "ACTIF"}
    sans_prix = cf.verdict_ligne(ligne(), lien, alternatives={"MATP-FARI-T65": [
        {"source_id": "devis_en_attente", "prix_eur_par_kg": None, "date": "2026-08-15"}]})
    assert sans_prix["verdict"] == cf.GARDER, sans_prix
    assert sans_prix["raison"] == "AUCUNE_ALTERNATIVE_CHIFFREE", sans_prix
    sans_date = cf.verdict_ligne(ligne(), lien, alternatives={"MATP-FARI-T65": [
        {"source_id": "prix_sans_date", "prix_eur_par_kg": 0.10, "date": None}]})
    assert sans_date["verdict"] == cf.GARDER, sans_date


def test_le_nombre_de_verdicts_egale_le_nombre_de_lignes():
    """Une ligne muette serait un oubli. Les 384 lignes des 20 factures reçoivent toutes une
    proposition, y compris celles qu'on ne sait pas lire."""
    achats, rattachement, matieres = _lire()
    propositions = cf.verdicts(achats, rattachement, matieres)
    assert len(propositions) == len(achats), (len(propositions), len(achats))


def test_aucun_changement_sans_prix_alternatif_sur_les_donnees_reelles():
    """L'invariant qui tient tout le module, vérifié sur les vraies factures : sans prix
    concurrent dans le dépôt, aucun verdict de changement ne peut sortir."""
    achats, rattachement, matieres = _lire()
    propositions = cf.verdicts(achats, rattachement, matieres)
    changements = [v for v in propositions if v["verdict"] == cf.CHANGER]
    assert changements == [], changements
    garders = [v for v in propositions if v["verdict"] == cf.GARDER]
    assert all(v["prix_eur_par_kg"] for v in garders), garders[:3]
    assert all(v["statut_rattachement"] == "ACTIF" for v in garders), garders[:3]


if __name__ == "__main__":
    for nom, fn in sorted(globals().items()):
        if nom.startswith("test_"):
            fn()
            print(f"OK  {nom}")