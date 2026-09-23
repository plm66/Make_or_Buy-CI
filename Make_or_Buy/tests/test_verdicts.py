"""Invariants des verdicts par ligne : conserver, changer, arbitrer, écarter.

Le module propose, il ne commande pas. Une proposition n'a de valeur que si elle est
portée par un fait : une matière identifiée, un prix au kilo, et pour un changement, le
prix de l'alternative. Le verdict qui compte est celui qu'on refuse de rendre.

Ces invariants tiennent une seule règle dure, celle de `docs/SPEC_MODULE_FACTURES.md` :
`CHANGER` exige un prix alternatif aligné et daté. Tout le reste en découle.
"""
import json
import re
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
    assert v["raison"] == "ALTERNATIVE_PLUS_CHERE", v


def test_une_alternative_sans_prix_ne_produit_jamais_de_changement():
    """Le point d'honnêteté du module : un candidat sans prix, ou sans date, ne permet pas de
    trancher. Il ne doit pas non plus faire croire qu'on a comparé — et c'est le verdict
    lui-même qui doit le dire, pas seulement sa raison. `GARDER` affirmait la comparaison
    dans le mot, en ne la portant que dans le champ d'à côté."""
    lien = {"article_metro": "2422798", "id_matiere": "MATP-FARI-T65", "statut": "ACTIF"}
    sans_prix = cf.verdict_ligne(ligne(), lien, alternatives={"MATP-FARI-T65": [
        {"source_id": "devis_en_attente", "prix_eur_par_kg": None, "date": "2026-08-15"}]})
    assert sans_prix["verdict"] == cf.NON_COMPARE, sans_prix
    assert sans_prix["raison"] == "AUCUNE_ALTERNATIVE_CHIFFREE", sans_prix
    sans_date = cf.verdict_ligne(ligne(), lien, alternatives={"MATP-FARI-T65": [
        {"source_id": "prix_sans_date", "prix_eur_par_kg": 0.10, "date": None}]})
    assert sans_date["verdict"] == cf.NON_COMPARE, sans_date


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
    non_compares = [v for v in propositions if v["verdict"] == cf.NON_COMPARE]
    assert all(v.get("prix_normalise") or v.get("prix_eur_par_kg") for v in non_compares), non_compares[:3]
    assert all(v["statut_rattachement"] == "ACTIF" for v in non_compares), non_compares[:3]
    # Sans alternative chargee, aucun GARDER ne peut sortir : il exige les deux termes d'une
    # comparaison. S'il en sort un, c'est que le verdict a reglisse vers l'ancien sens.
    assert [v for v in propositions if v["verdict"] == cf.GARDER] == []


def test_une_alternative_d_unite_differente_ne_produit_aucun_changement():
    """Une alternative en EUR/piece ne se compare pas a du EUR/kg ou EUR/L."""
    lien = {"article_metro": "2422798", "id_matiere": "MATP-FARI-T65", "statut": "ACTIF"}
    v = cf.verdict_ligne(ligne(), lien,
                         alternatives={"MATP-FARI-T65": [{"source_id": "autre", "prix_normalise": 0.10, "unite": "EUR/piece", "date": "2026-08-15"}]})
    assert v["verdict"] == cf.NON_COMPARE, v
    assert v["raison"] == "AUCUNE_ALTERNATIVE_CHIFFREE", v


def test_une_matiere_en_piece_exige_un_prix_piece():
    """MATP-OEUF-ENTI attend des pieces. Un conditionnement en kg est illisible pour elle."""
    lien = {"article_metro": "1234567", "id_matiere": "MATP-OEUF-ENTI", "statut": "ACTIF"}
    matiere = {"unite_achat": "piece"}
    v = cf.verdict_ligne(ligne(designation="MC OEUFS FRAIS 5KG", prix_unitaire_ht=15.0), lien, matiere=matiere)
    assert v["verdict"] == cf.A_ARBITRER, v
    assert v["raison"] == "CONDITIONNEMENT_ILLISIBLE", v


def test_revente_directe_distinguee_de_non_alimentaire():
    """Une boisson ou fruit de revente sort en REVENTE_DIRECTE, pas NON_ALIMENTAIRE."""
    lien_revente = {"article_metro": "2694164", "id_matiere": "", "statut": "HORS_PERIMETRE", "note": "boisson revente directe"}
    v = cf.verdict_ligne(ligne(article="2694164", designation="PEPSI REGULAR SLIM 33CL"), lien_revente)
    assert v["verdict"] == cf.HORS_PERIMETRE, v
    assert v["raison"] == "REVENTE_DIRECTE", v


def test_revente_directe_peut_confronter_une_alternative_grossiste():
    """Un article de revente peut etre compare par son numero d'article."""
    lien = {"article_metro": "2694164", "id_matiere": "", "statut": "HORS_PERIMETRE", "note": "boisson revente directe"}
    l = ligne(article="2694164", designation="PEPSI REGULAR SLIM 33CL", prix_unitaire_ht=0.454,
              colisage=24, prix_unite_normalisee=1.376)
    alt = {"source_id": "halal_food_service", "prix_normalise": 1.150, "unite": "EUR/L", "date": "2026-09-13"}
    v = cf.verdict_ligne(l, lien, alternatives={"2694164": [alt]})
    assert v["verdict"] == cf.CHANGER, v
    assert v["raison"] == "ALTERNATIVE_MOINS_CHERE", v
    assert v["alternative"] == alt, v


def test_toutes_les_alternatives_de_marche_citent_une_source_enregistree():
    """Toute source d'alternative doit exister dans supplier_price_sources.registry.json."""
    registre_sources = json.loads((RACINE / "data/supplier_price_sources/supplier_price_sources.registry.json").read_text())
    sources_connues = {s["price_source_id"] for s in registre_sources["sources"]}
    alternatives = cf.charger_alternatives()
    for cle, liste in alternatives.items():
        for alt in liste:
            assert alt["source_id"] in sources_connues, (cle, alt["source_id"])


def test_tout_code_sorti_en_json_est_declare_au_glossaire():
    """`GLOSSAIRE.md` pose sa regle en tete : « tout code qui entre dans une donnee ou un
    schema figure ici avant d'etre ecrit. Un code absent du glossaire est un code invente. »

    Les sept verdicts et leurs raisons ont vecu non declares jusqu'au 2026-09-23, et c'est
    exactement la ou `GARDER` a pu deriver : personne n'avait jamais eu a ecrire sa
    definition, donc personne n'avait bute sur le fait qu'il affirmait une comparaison
    jamais faite. Ecrire la definition est ce qui revele le mensonge du nom.

    Rien ne tenait cette regle. Ce test la tient.
    """
    source = (RACINE / "comparaison_factures.py").read_text(encoding="utf-8")
    glossaire = (RACINE / "docs" / "GLOSSAIRE.md").read_text(encoding="utf-8")

    # Constantes de module en MAJUSCULES affectees a une chaine : ce sont les codes qui
    # sortent. Les chemins et les tuples de configuration n'en sont pas.
    constantes = set(re.findall(r'^([A-Z][A-Z_]+)\s*=\s*"([A-Z_]+)"', source, re.M))
    raisons = set(re.findall(r'raison="([A-Z_]+)"', source))

    codes = {valeur for _, valeur in constantes} | raisons
    assert codes, "aucun code detecte : le detecteur est casse, pas le glossaire"

    # Une mention en prose ne vaut pas declaration : le glossaire definit dans des tableaux,
    # et c'est la definition qu'on exige. Chercher le code n'importe ou laisserait passer un
    # code seulement cite — par exemple dans le paragraphe qui raconte pourquoi il existe.
    declares = {c for ligne_glo in glossaire.splitlines() if ligne_glo.startswith("|")
                for c in codes if f"`{c}`" in ligne_glo}

    absents = sorted(codes - declares)
    assert not absents, (
        f"codes sortis en JSON et non definis dans un tableau de GLOSSAIRE.md : {absents}. "
        "Un code absent du glossaire est un code invente.")


if __name__ == "__main__":
    for nom, fn in sorted(globals().items()):
        if nom.startswith("test_"):
            fn()
            print(f"OK  {nom}")