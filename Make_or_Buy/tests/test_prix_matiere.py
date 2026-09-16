"""Invariants de la couche de prix matière tirée des factures.

`data/materials/SCHEMA.md` déclare les prix matière « dans une couche datée à construire ».
Aujourd'hui les factures METRO sont le seul gisement de prix réels sur des matières
identifiées : 24 articles rattachés, dont 16 convertibles en euros par kilo.

Une observation porte une matière, une date, une facture, un prix au kilo et la provenance
de ce prix. Elle ne porte un prix que si ce prix existe : une ligne sans conditionnement
lisible, ou sans rattachement, ne produit rien. Un trou déclaré vaut mieux qu'un chiffre
crédible, et cette couche est destinée à nourrir des décisions de coût.

La réserve de rattachement voyage avec l'observation. Un `A_VERIFIER` dit que le critère
du référentiel n'est pas écrit sur la facture : la valeur reste publiée, mais elle ne peut
pas être consommée comme un `ACTIF`.
"""
import csv
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
    achats = json.loads(RELEVE.read_text(encoding="utf-8"))["achats"]
    rattachement = list(csv.DictReader(RATTACHEMENT.read_text(encoding="utf-8").splitlines(),
                                       delimiter=";"))
    matieres = {m["id_matiere"]: m for m in csv.DictReader(
        MATIERES.read_text(encoding="utf-8").splitlines(), delimiter=";")}
    return achats, rattachement, matieres


def test_une_observation_porte_matiere_date_prix_et_provenance():
    """Le minimum consommable : de quoi savoir quelle matière, quand, à quel prix, et d'où
    vient ce prix."""
    achats = [{"article": "2422798", "date_facture": "2026-07-27", "facture": "032-018364",
               "depot": "METRO PARIS12", "designation": "MC FARINE PANIF. T65 25KG",
               "prix_unitaire_ht": 18.0, "prix_unitaire_paye": None,
               "prix_unite_normalisee": None}]
    rattachement = [{"article_metro": "2422798", "id_matiere": "MATP-FARI-T65",
                     "statut": "ACTIF"}]
    (o,) = cf.observations_matiere(achats, rattachement, {"MATP-FARI-T65": {}})
    assert o["id_matiere"] == "MATP-FARI-T65", o
    assert o["date"] == "2026-07-27" and o["facture"] == "032-018364", o
    assert o["prix_eur_par_kg"] == 0.72, o
    assert o["source_prix"] == "DESIGNATION_SIMPLE", o


def test_aucune_observation_sans_prix_au_kilo_lisible():
    """Une ligne dont le conditionnement est illisible ou absent ne produit rien. La couche
    ne doit pas contenir de valeur qui serait en réalité un prix au colis ou au litre."""
    achats = [
        {"article": "0012476", "date_facture": "2026-07-27", "facture": "F1", "depot": None,
         "designation": "MP CASSEROLE INOX D28CM", "prix_unitaire_ht": 42.87,
         "prix_unitaire_paye": None, "prix_unite_normalisee": None},
        {"article": "0512202", "date_facture": "2026-07-27", "facture": "F1", "depot": None,
         "designation": "FRAISE 500G BQ8 C1 BEBELGIQUE", "prix_unitaire_ht": 4.99,
         "prix_unitaire_paye": None, "prix_unite_normalisee": None},
    ]
    rattachement = [{"article_metro": "0012476", "id_matiere": "MATP-X", "statut": "ACTIF"},
                    {"article_metro": "0512202", "id_matiere": "MATP-FRUI-FRAI", "statut": "ACTIF"}]
    assert cf.observations_matiere(achats, rattachement, {}) == []


def test_aucune_observation_sans_rattachement():
    """Un article non rattaché ne sait pas de quelle matière il parle. Le deviner par le
    libellé est ce que le dépôt interdit ; la ligne est donc écartée, pas rapprochée."""
    achats = [{"article": "9999999", "date_facture": "2026-07-27", "facture": "F1",
               "depot": None, "designation": "SUCRE GLACE 1KG", "prix_unitaire_ht": 1.5,
               "prix_unitaire_paye": None, "prix_unite_normalisee": None}]
    assert cf.observations_matiere(achats, [], {}) == []


def test_la_reserve_de_rattachement_voyage_avec_l_observation():
    """Un rattachement `A_VERIFIER` dit que le critère du référentiel n'est pas écrit sur la
    facture. La valeur reste publiée, mais la réserve doit être lisible par le
    consommateur, sinon un beurre à taux inconnu deviendrait un beurre doux 82 %."""
    achats = [{"article": "2252104", "date_facture": "2026-07-27", "facture": "F1",
               "depot": None, "designation": "BEURRE DX 500G MA PAYSANNE",
               "prix_unitaire_ht": 3.65, "prix_unitaire_paye": None,
               "prix_unite_normalisee": None}]
    rattachement = [{"article_metro": "2252104", "id_matiere": "MATP-BEUR-DOUX",
                     "statut": "A_VERIFIER"}]
    (o,) = cf.observations_matiere(achats, rattachement, {"MATP-BEUR-DOUX": {"statut": "ACTIF"}})
    assert o["statut_rattachement"] == "A_VERIFIER", o
    assert o["statut_matiere"] == "ACTIF", o


def test_le_prix_paye_prime_sur_le_prix_imprime_dans_la_couche():
    """Le tarif imprimé n'est pas le montant payé. Quand la remise a été lue, c'est elle qui
    décide du prix publié, et la provenance le nomme."""
    achats = [{"article": "2422798", "date_facture": "2026-07-27", "facture": "F1",
               "depot": None, "designation": "MC FARINE PANIF. T65 25KG",
               "prix_unitaire_ht": 18.0, "prix_unitaire_paye": 17.0,
               "prix_unite_normalisee": None}]
    rattachement = [{"article_metro": "2422798", "id_matiere": "MATP-FARI-T65", "statut": "ACTIF"}]
    (o,) = cf.observations_matiere(achats, rattachement, {})
    assert o["prix_eur_par_kg"] == 0.68, o


def test_les_observations_sont_ordonnees_et_dates():
    """Une couche de prix se lit dans le temps. Le tri porte sur la date puis la facture,
    sans quoi deux observations du même jour sortiraient dans un ordre instable."""
    achats = [
        {"article": "2422798", "date_facture": "2026-09-11", "facture": "F2", "depot": None,
         "designation": "MC FARINE PANIF. T65 25KG", "prix_unitaire_ht": 20.0,
         "prix_unitaire_paye": None, "prix_unite_normalisee": None},
        {"article": "2422798", "date_facture": "2026-07-27", "facture": "F1", "depot": None,
         "designation": "MC FARINE PANIFICAT T65 25KG", "prix_unitaire_ht": 18.0,
         "prix_unitaire_paye": None, "prix_unite_normalisee": None},
    ]
    rattachement = [{"article_metro": "2422798", "id_matiere": "MATP-FARI-T65", "statut": "ACTIF"}]
    observations = cf.observations_matiere(achats, rattachement, {})
    assert [o["date"] for o in observations] == ["2026-07-27", "2026-09-11"], observations


def test_la_couche_reelle_ne_contient_aucun_prix_manquant():
    """L'invariant qui tient les autres sur les données réelles : toute observation publiée
    porte un prix au kilo strictement positif et une hypothèse de provenance nommée."""
    achats, rattachement, matieres = _lire()
    observations = cf.observations_matiere(achats, rattachement, matieres)
    assert len(observations) >= 60, len(observations)
    for o in observations:
        assert o["prix_eur_par_kg"] and o["prix_eur_par_kg"] > 0, o
        assert o["source_prix"] in ("IMPRIME_FACTURE", "DESIGNATION_SIMPLE"), o
        assert o["statut_rattachement"] in ("ACTIF", "A_VERIFIER"), o
    matieres_touchees = {o["id_matiere"] for o in observations}
    # 24 articles rattaches, mais 12 matieres distinctes : plusieurs articles portent la
    # meme matiere (deux farines, deux sucres semoule, trois chocolats).
    assert len(matieres_touchees) >= 12, matieres_touchees


def test_aucun_prix_matiere_invraisemblable_ne_passe():
    """`RATTACHEMENT.md` pose la règle : un prix compatible ne prouve rien, il ne sert qu'à
    écarter. Un plancher de vraisemblance attrape ce que l'oracle ne voit pas, puisque les
    lignes vendues au kilo n'impriment aucun prix normalisé. C'est ce contrôle qui a exposé
    une farine T65 à 0,03 EUR/kg, dix fois sous le prix agricole de la céréale."""
    achats, rattachement, matieres = _lire()
    observations = cf.observations_matiere(achats, rattachement, matieres)
    for o in observations:
        assert o["prix_eur_par_kg"] >= 0.10, o
        assert o["prix_eur_par_kg"] <= 500, o
    farine = [o["prix_eur_par_kg"] for o in observations if o["id_matiere"] == "MATP-FARI-T65"]
    assert farine, "aucune observation de farine, le contrôle ne porte sur rien"
    assert min(farine) >= 0.30, farine


if __name__ == "__main__":
    for nom, fn in sorted(globals().items()):
        if nom.startswith("test_"):
            fn()
            print(f"OK  {nom}")