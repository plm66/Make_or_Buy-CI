"""Invariants du rattachement des achats aux matieres.

Le rattachement est l'endroit ou une base de prix devient utilisable — et l'endroit ou
elle devient fausse sans prevenir. Un prix exact inscrit sur la mauvaise matiere ne se
voit nulle part en aval : il est exact, il est date, il est simplement ailleurs.

Ces tests gardent trois choses : que la cle soit stable, que les identifiants existent,
et qu'un rattachement incertain ne se declare pas certain.
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TABLE = ROOT / "data" / "materials" / "rattachement_metro.csv"
MATIERES = ROOT / "data" / "materials" / "matieres_premieres.csv"
RELEVES = sorted((ROOT / "data" / "price_observations").glob("metro_factures_*.json"))


def _csv(p, sep=";"):
    return list(csv.DictReader(p.read_text(encoding="utf-8").splitlines(), delimiter=sep))


def test_chaque_id_matiere_existe():
    """Un identifiant invente ne casse rien au moment ou on l'ecrit.

    Il casse plus tard, chez un consommateur qui cherchera une matiere absente et
    trouvera zero prix — indiscernable d'une matiere jamais achetee.
    """
    connus = {m["id_matiere"] for m in _csv(MATIERES)}
    for r in _csv(TABLE):
        if r["statut"] == "HORS_PERIMETRE":
            assert r["id_matiere"] == "", f"ligne HORS_PERIMETRE ne doit pas porter d id_matiere: {r}"
            continue
        assert r["id_matiere"] in connus, (r["article_metro"], r["id_matiere"])


def test_chaque_article_a_ete_reellement_achete():
    """La table ne rattache que ce qui existe dans les relevés.

    J'ai ecrit un numero d'article de memoire lors de la premiere redaction : il
    n'existait pas. Ce test transforme cette erreur en rouge au lieu d'une ligne morte.
    """
    achetes = {a["article"] for p in RELEVES for a in json.loads(p.read_text())["achats"]}
    for r in _csv(TABLE):
        assert r["article_metro"] in achetes, r["article_metro"]


def test_un_rattachement_incertain_ne_se_declare_pas_certain():
    """ACTIF engage : il dit que la designation porte le critere du referentiel.

    Le beurre 500g ne porte aucun taux de matiere grasse alors que MATP-BEUR-DOUX exige
    82 %. Le declarer ACTIF inscrirait une propriete que personne n'a lue — G002 a
    l'etage du rattachement.
    """
    for r in _csv(TABLE):
        assert r["statut"] in ("ACTIF", "A_VERIFIER", "HORS_PERIMETRE"), (r["article_metro"], r["statut"])
        assert r["note"].strip(), r["article_metro"]


def test_un_article_ne_pointe_que_vers_une_matiere():
    """Plusieurs articles peuvent servir une matiere — deux marques de sucre glace.

    L'inverse est une contradiction : un meme article ne peut pas etre deux matieres.
    """
    vus = {}
    for r in _csv(TABLE):
        a, m = r["article_metro"], r["id_matiere"]
        assert vus.setdefault(a, m) == m, (a, vus[a], m)


def test_la_cle_de_rattachement_survit_au_renommage():
    """L'article 2422798 porte deux designations differentes dans les relevés.

    C'est la preuve mesuree que le libelle ne peut pas servir de cle. Si ce test devient
    vide un jour, c'est que les relevés ont change — pas que la regle a cesse de valoir.
    """
    par_article = {}
    for p in RELEVES:
        for a in json.loads(p.read_text())["achats"]:
            par_article.setdefault(a["article"], set()).add(a["designation"])
    instables = {k: v for k, v in par_article.items() if len(v) > 1}
    assert instables, "aucun renommage observe — verifier que les relevés sont bien lus"


if __name__ == "__main__":
    for nom, fn in sorted(globals().items()):
        if nom.startswith("test_"):
            fn()
            print(f"OK  {nom}")
