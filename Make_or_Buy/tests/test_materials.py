"""Invariants du référentiel matières premières.

C'est l'étage le plus bas : une erreur ici se propage dans chaque recette qui référence la
matière, et plus rien ne dit d'où elle vient. Ces tests protègent trois choses — que le
référentiel ne porte aucun fait daté, qu'aucune conversion ne soit devinée, et que l'axe de
composition reste utilisable.
"""
import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FICHIER = ROOT / "data" / "materials" / "matieres_premieres.csv"

with FICHIER.open(encoding="utf-8") as f:
    MATIERES = list(csv.DictReader(f, delimiter=";"))

PAR_ID = {m["id_matiere"]: m for m in MATIERES}
NATURES = {"FRESH_NATURAL", "FROZEN_CLEAN", "SUBSTITUTED", "UNDECIDED"}
CATEGORIES = {"farines", "matieres-grasses", "sucres", "oeufs", "laits-cremes", "chocolats",
              "fruits-secs", "aromes", "levures-agents", "sels", "liquides"}


def test_le_referentiel_ne_porte_aucun_prix():
    """Un prix est un fait daté qui bouge, l'identité d'une matière ne bouge pas. Les mêler
    ferait de chaque relevé de prix une modification du référentiel, et on ne saurait plus
    quel prix a servi à une décision passée. Même séparation que `price_source` contre
    `supplier`, et que `reference_price` contre `landed_cost`.
    """
    interdit = re.compile(r"prix|price|cost|cout|co[ûu]t|eur|tarif", re.I)
    for champ in MATIERES[0]:
        assert not interdit.search(champ), champ


def test_aucune_conversion_nest_devinee():
    """Une masse volumique inventée se propage dans chaque recette qui utilise la matière,
    et plus rien ne dit qu'elle a été devinée. Vide et TO_VERIFY est plus utile qu'un
    chiffre crédible.
    """
    for m in MATIERES:
        g = m["grammes_par_unite_achat"]
        if g == "":
            assert m["statut"] == "TO_VERIFY", m["id_matiere"]
        else:
            assert float(g) > 0, m["id_matiere"]
            assert m["statut"] == "ACTIF", m["id_matiere"]


def test_une_matiere_substituee_nomme_ce_quelle_remplace():
    """Sans cette cible, on saurait qu'une matière est substituée sans pouvoir proposer
    l'alternative — l'axe de composition deviendrait un constat au lieu d'un arbitrage.
    """
    for m in MATIERES:
        if m["composition_nature"] == "SUBSTITUTED":
            cible = m["substitut_de"]
            assert cible in PAR_ID, (m["id_matiere"], cible)
            assert PAR_ID[cible]["composition_nature"] != "SUBSTITUTED", (m["id_matiere"], cible)


def test_seule_une_matiere_substituee_porte_une_cible():
    """Un beurre qui prétendrait remplacer quelque chose brouillerait la lecture de l'axe :
    la colonne ne se lit que dans un sens.
    """
    for m in MATIERES:
        if m["composition_nature"] != "SUBSTITUTED":
            assert m["substitut_de"] == "", (m["id_matiere"], m["substitut_de"])


def test_le_vocabulaire_est_celui_de_la_doctrine():
    """Les natures viennent d'ADR-0001 et les catégories sont une liste fermée. Une valeur
    inventée en cours de saisie ne se regrouperait avec rien.
    """
    for m in MATIERES:
        assert m["composition_nature"] in NATURES, (m["id_matiere"], m["composition_nature"])
        assert m["categorie"] in CATEGORIES, (m["id_matiere"], m["categorie"])
        assert m["unite_achat"] in ("kg", "L", "piece"), (m["id_matiere"], m["unite_achat"])
        assert m["statut"] in ("ACTIF", "TO_VERIFY"), (m["id_matiere"], m["statut"])


def test_les_identifiants_sont_uniques_et_prefixes():
    """Deux matières sous un même identifiant, et une recette sur deux référence la
    mauvaise sans que rien ne le signale.
    """
    ids = [m["id_matiere"] for m in MATIERES]
    assert len(ids) == len(set(ids)), [i for i in ids if ids.count(i) > 1]
    for i in ids:
        assert re.fullmatch(r"MATP-[A-Z]{4}-[A-Z0-9]{2,4}", i), i


def test_une_nature_definitionnelle_ne_vaut_pas_pour_un_sku():
    """La nature d'une matière générique découle de sa définition. Elle ne se transmet pas
    à une référence fournisseur : un beurre concentré peut porter un émulsifiant. Le
    référentiel doit le dire, sans quoi un SKU hériterait d'une preuve qu'il n'a pas.
    """
    for m in MATIERES:
        assert m["preuve_composition"] == "DEFINITIONAL", m["id_matiere"]


if __name__ == "__main__":
    for nom, fn in sorted(globals().items()):
        if nom.startswith("test_"):
            fn()
            print(f"OK  {nom}")
