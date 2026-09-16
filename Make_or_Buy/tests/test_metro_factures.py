"""Invariants des factures METRO.

Une facture inspire plus confiance qu'un catalogue, et c'est ce qui la rend dangereuse :
on la lit sans la verifier. Ces tests protegent trois illusions.

La premiere est que le prix imprime soit le prix paye. Une remise de volume s'ecrit sur
la ligne suivante, hors du sous-total de rayon : le tarif affiche survit intact a cote
d'un montant qui ne lui correspond plus. C'est G002 a l'etage du releve — comparer un
prix de reference en croyant comparer un fait.

La deuxieme est qu'une lecture reussie soit une lecture complete. Le filigrane diagonal
et les articles sans EAN font disparaitre des lignes sans rien casser.

La troisieme est qu'un montant facture soit un cout rendu. METRO est un cash & carry :
l'enlevement est reel, il n'est simplement sur aucune de ces factures.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RELEVES = sorted((ROOT / "data" / "price_observations").glob("metro_factures_*.json"))


def _lire(p):
    return json.loads(p.read_text(encoding="utf-8"))


def test_au_moins_un_releve():
    """Decouverte par glob : zero fichier rendrait tous les autres tests verts a vide."""
    assert RELEVES, "aucun metro_factures_*.json dans data/price_observations/"


def test_chaque_facture_se_boucle():
    """Le seul controle qui voie ce que la regex n'a pas vu.

    Les lignes lues plus les remises doivent retomber sur le Total H.T. imprime. Une
    colonne mal decoupee passe l'arithmetique de sa propre ligne mais casse ici ; une
    ligne perdue ne casse que ici. Sans ce test, les 30 lignes mangees par le filigrane
    et les croissants crus sans EAN seraient partis en silence.
    """
    for p in RELEVES:
        d = _lire(p)
        for e in d["entetes"]:
            # Recalcule depuis les lignes plutot que de relire total_concorde : croire
            # le booleen que le parseur a ecrit ferait un test qui confirme le parseur
            # au lieu de le contredire.
            somme = round(sum(a["montant_ht"] for a in d["achats"]
                              if a["facture"] == e["numero"])
                          + sum(r["montant_ht"] for r in d["remises"]
                                if r["facture"] == e["numero"]), 2)
            assert abs(somme - e["total_ht_declare"]) <= 0.02, (
                p.name, e["fichier"], e["total_ht_declare"], somme)


def test_chaque_ligne_verifie_son_propre_montant():
    """Prix unitaire fois unites facturees doit valoir le montant.

    Si les colonnes glissent d'un cran — et elles glissent, le colisage et la quantite
    sont voisins et tous deux entiers — l'egalite tombe. C'est ce qui distingue une
    lecture d'une coincidence.
    """
    for p in RELEVES:
        for a in _lire(p)["achats"]:
            assert a["controle_arithmetique"] == "OK", (p.name, a["designation"])


def test_le_prix_imprime_n_est_pas_declare_paye_sans_preuve():
    """Une ligne remisee doit porter un prix paye distinct du tarif, et lui seul.

    Le beurre facture 3,320 a ete paye 3,120 : un consommateur qui lit prix_unitaire_ht
    surestime de 6 %. Symetriquement, fabriquer un prix_unitaire_paye sur une ligne sans
    remise inventerait une precision qu'on n'a pas.
    """
    for p in RELEVES:
        for a in _lire(p)["achats"]:
            if a["remise_ht"] is None:
                assert a["prix_unitaire_paye"] is None, (p.name, a["designation"])
            else:
                assert a["prix_unitaire_paye"] < a["prix_unitaire_ht"], (
                    p.name, a["designation"])


def test_une_remise_de_groupe_n_est_rattachee_a_aucune_ligne():
    """« 3 pour 2 soumis a panachage » porte sur trois articles.

    La rattacher a la derniere ligne lue — la seule que le parseur ait sous la main —
    lui ferait porter toute la remise et produirait un prix paye faux sur elle, et trop
    eleve sur les deux autres. Une attribution qu'on ne sait pas faire doit rester nulle.
    """
    for p in RELEVES:
        d = _lire(p)
        groupes = {r["apres_article"] for r in d["remises"]
                   if r["portee"] == "GROUPE_NON_ATTRIBUE"}
        for a in d["achats"]:
            if a["article"] in groupes:
                assert a["prix_unitaire_paye"] is None, (p.name, a["designation"])


def test_le_releve_ne_pretend_pas_au_cout_rendu():
    """METRO est un cash & carry : la facture ne porte ni livraison ni consigne.

    Le montant est donc le cout au depot, pas le cout rendu a la boulangerie. Le
    deplacement existe et coute ; il n'est sur aucune facture. Un consommateur qui prend
    ce montant pour un landed cost refait G002 une fois de plus.
    """
    for p in RELEVES:
        d = _lire(p)
        assert d["data_status"] == "INVOICED_ACTUAL_UNMATCHED", p.name
        assert "enlevement" in d["consumer_rule"], p.name
        assert "id_matiere" in d["consumer_rule"], p.name


def test_aucune_ligne_article_n_est_abandonnee_en_silence():
    """Une ligne que le parseur voit commencer mais ne sait pas finir doit etre nommee.

    Le compte de lignes lues ne dit rien de celles qui manquent : c'est exactement la
    forme « un compte n'est pas un finding ».
    """
    for p in RELEVES:
        assert _lire(p)["lignes_non_lues"] == [], (p.name, _lire(p)["lignes_non_lues"])


if __name__ == "__main__":
    for nom, fn in sorted(globals().items()):
        if nom.startswith("test_"):
            fn()
            print(f"OK  {nom}")
