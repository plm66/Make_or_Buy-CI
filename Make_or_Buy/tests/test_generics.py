"""Invariants du référentiel produits (data/generics/).

Deux axes : le SKU fournisseur et le produit générique auquel il se rattache. Ces tests
protègent le rattachement — c'est la seule chose que le référentiel apporte, et c'est ce
qui casse en silence quand un catalogue est ajouté.

Les fichiers sont découverts par convention `<fournisseur>_index.csv` / `_detail.csv`,
pour qu'un nouveau catalogue soit couvert sans toucher aux tests.
"""
import csv
import html
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GEN = ROOT / "data" / "generics"


def load(chemin):
    with Path(chemin).open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh, delimiter=";"))


def catalogues():
    return sorted(GEN.glob("*_detail.csv"))


def toutes_les_lignes():
    for f in list(catalogues()) + sorted(GEN.glob("*_index.csv")) + [GEN / "produits_generiques.csv"]:
        for r in load(f):
            yield f.name, r


def test_au_moins_un_catalogue():
    """Garde-fou des tests eux-mêmes : découverte par glob, donc un répertoire vide
    rendrait toutes les autres assertions vraies sans rien vérifier."""
    assert catalogues(), "aucun *_detail.csv dans data/generics/"


def test_aucun_generique_orphelin():
    """Un SKU qui pointe vers un générique inexistant est invisible à l'axe 1.

    Un id vide est licite — c'est un rattachement en attente d'arbitrage. Un id renseigné
    mais inconnu ne l'est pas : c'est le mode d'échec d'un catalogue collecté avec des
    identifiants inventés au lieu d'être repris de produits_generiques.csv.
    """
    connus = {r["id_generique"] for r in load(GEN / "produits_generiques.csv")}
    for f in catalogues():
        cites = {r["id_generique"] for r in load(f) if r["id_generique"]}
        assert cites <= connus, (f.name, sorted(cites - connus))


def test_rattachement_en_attente_porte_son_motif():
    """Un id_generique vide doit dire pourquoi, sinon c'est un oubli qu'on ne distingue
    plus d'une décision."""
    for f in catalogues():
        for r in load(f):
            if not r["id_generique"]:
                assert r.get("motif_nouveau", "").strip(), (f.name, r["ref_sku"])


def test_aucun_generique_sans_sku():
    """Un générique que plus aucun SKU ne référence, tous catalogues confondus, est mort.

    Après une fusion de doublons, l'ancienne clé doit disparaître, pas rester vide.
    """
    references = {r["id_generique"] for f in catalogues() for r in load(f) if r["id_generique"]}
    morts = [r["id_generique"] for r in load(GEN / "produits_generiques.csv")
             if r["id_generique"] not in references]
    assert morts == [], morts


def test_nb_refs_associees_dit_la_verite():
    """Le compteur porte sur TOUS les catalogues, et il est recalculable.

    C'est la mesure du regroupement inter-fournisseurs — la seule chose que l'axe générique
    apporte. Écrit à la main, il pourrit sans bruit : rien dans un CSV ne signale un
    compteur faux, et c'est lui qui sert à juger si la déduplication fonctionne.
    """
    reel = {}
    for f in catalogues():
        for r in load(f):
            if r["id_generique"]:
                reel[r["id_generique"]] = reel.get(r["id_generique"], 0) + 1
    for r in load(GEN / "produits_generiques.csv"):
        assert int(r["nb_refs_associees"]) == reel.get(r["id_generique"], 0), \
            (r["id_generique"], r["nb_refs_associees"], reel.get(r["id_generique"], 0))


def test_prefixe_de_cle_coherent_avec_la_famille():
    """`VIEN-CROI-50` doit vivre en famille VIEN. Sinon la clé ment sur son rangement."""
    for r in load(GEN / "produits_generiques.csv"):
        assert r["id_generique"].startswith(r["famille"] + "-"), (r["id_generique"], r["famille"])


def test_familles_normalisees():
    """Codes, pas libellés — SCHEMA.md le dit et id_generique le fait déjà.

    La livraison Bridor portait « Viennoiseries » en colonne et « VIEN- » dans la clé.
    """
    codes = {"PAIN", "VIEN", "PATI", "SNAC", "MATP", "EPIC"}
    for nom, r in toutes_les_lignes():
        assert r["famille"] in codes, (nom, r["famille"])


def test_technologie_normalisee():
    """CRU, PAC, PRECUIT… disent combien de gestes restent en interne : c'est le pont
    entre un catalogue fournisseur et le coût du travail. Une casse ou un accent de plus
    et le champ ne se regroupe plus."""
    valeurs = {"CRU", "PAC", "PRECUIT", "CUIT", "PRET_A_SERVIR", "NON_RENSEIGNE"}
    for f in catalogues():
        for r in load(f):
            assert r["technologie"] in valeurs, (f.name, r["ref_sku"], r["technologie"])


def test_aucune_entite_html():
    """`bun&#039;n&#039;roll` ne se rapproche d'aucun `bun'n'roll` d'un autre catalogue.

    Le premier scraping ne décodait pas les entités ; tout rattachement par nom échouait
    sur ces lignes. Casse si un futur import réintroduit le défaut.
    """
    for nom, r in toutes_les_lignes():
        for champ, v in r.items():
            assert html.unescape(v) == v, (nom, champ, v)


def test_detail_est_un_sous_ensemble_de_lindex():
    """Une fiche détaillée décrit forcément une référence vue au catalogue."""
    for f in catalogues():
        index = f.with_name(f.name.replace("_detail.csv", "_index.csv"))
        assert index.exists(), f"index manquant pour {f.name}"
        refs_index = {r["ref_sku"] for r in load(index)}
        refs_detail = {r["ref_sku"] for r in load(f)}
        assert refs_detail <= refs_index, (f.name, sorted(refs_detail - refs_index))


if __name__ == "__main__":
    for nom, fn in sorted(globals().items()):
        if nom.startswith("test_"):
            fn()
            print(f"OK  {nom}")
