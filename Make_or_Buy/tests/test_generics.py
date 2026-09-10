"""Invariants du référentiel produits (data/generics/).

Deux axes : le SKU fournisseur et le produit générique auquel il se rattache. Ces tests
protègent le rattachement — c'est la seule chose que le référentiel apporte, et c'est ce
qui casse en silence quand un second catalogue arrive.
"""
import csv
import html
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GEN = ROOT / "data" / "generics"


def load(nom):
    with (GEN / nom).open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh, delimiter=";"))


def test_aucun_generique_orphelin():
    """Un SKU qui pointe vers un générique inexistant est invisible à l'axe 1.

    Casse dès qu'un catalogue est ajouté avec des id_generique inventés au lieu d'être
    repris de produits_generiques.csv — le mode d'échec attendu du second fournisseur.
    """
    connus = {r["id_generique"] for r in load("produits_generiques.csv")}
    cites = {r["id_generique"] for r in load("bridor_detail.csv")}
    assert cites - connus == set(), sorted(cites - connus)
    assert all(r["id_generique"] for r in load("bridor_detail.csv"))


def test_aucun_generique_sans_sku():
    """Un générique que plus aucun SKU ne référence est une entrée morte.

    Après une fusion de doublons, l'ancienne clé doit disparaître, pas rester vide.
    """
    detail = {r["id_generique"] for r in load("bridor_detail.csv")}
    orphelins = [r["id_generique"] for r in load("produits_generiques.csv")
                 if r["id_generique"] not in detail]
    assert orphelins == [], orphelins


def test_nb_refs_associees_dit_la_verite():
    """Le compteur est recalculable ; s'il diverge, c'est qu'il a été écrit à la main.

    C'est la donnée qui pourrit sans bruit : rien dans un CSV ne signale un compteur faux,
    et il sert à juger si la déduplication fonctionne.
    """
    reel = {}
    for r in load("bridor_detail.csv"):
        reel[r["id_generique"]] = reel.get(r["id_generique"], 0) + 1
    for r in load("produits_generiques.csv"):
        annonce = int(r["nb_refs_associees"])
        assert annonce == reel.get(r["id_generique"], 0), (r["id_generique"], annonce, reel)


def test_prefixe_de_cle_coherent_avec_la_famille():
    """`VIEN-CROI-50` doit vivre en famille VIEN. Sinon la clé ment sur son propre rangement."""
    for r in load("produits_generiques.csv"):
        assert r["id_generique"].startswith(r["famille"] + "-"), (r["id_generique"], r["famille"])


def test_familles_normalisees():
    """Codes, pas libellés — SCHEMA.md le dit et id_generique le fait déjà.

    La livraison initiale portait « Viennoiseries » en colonne et « VIEN- » dans la clé.
    """
    codes = {"PAIN", "VIEN", "PATI", "SNAC", "MATP", "EPIC"}
    for f in ["bridor_index.csv", "bridor_detail.csv", "produits_generiques.csv"]:
        vues = {r["famille"] for r in load(f)}
        assert vues <= codes, (f, sorted(vues - codes))


def test_aucune_entite_html():
    """`bun&#039;n&#039;roll` ne se rapproche d'aucun `bun'n'roll` d'un autre catalogue.

    Le scraping initial ne décodait pas les entités ; tout rattachement par nom échouait
    sur ces lignes. Casse si un futur import réintroduit le défaut.
    """
    for f in ["bridor_index.csv", "bridor_detail.csv", "produits_generiques.csv"]:
        for r in load(f):
            for champ, v in r.items():
                assert html.unescape(v) == v, (f, r.get("ref_sku") or r.get("id_generique"), champ, v)


def test_detail_est_un_sous_ensemble_de_lindex():
    """Une fiche détaillée décrit forcément une référence vue au catalogue."""
    idx = {r["ref_sku"] for r in load("bridor_index.csv")}
    det = {r["ref_sku"] for r in load("bridor_detail.csv")}
    assert det <= idx, sorted(det - idx)


if __name__ == "__main__":
    for nom, fn in sorted(globals().items()):
        if nom.startswith("test_"):
            fn()
            print(f"OK  {nom}")
