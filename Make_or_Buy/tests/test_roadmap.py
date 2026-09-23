"""Invariants de la feuille de route et du README.

Un document qui annonce l'etat du depot vieillit plus vite que le depot. Personne ne le
relit pour verifier : on le lit pour savoir, et on le croit. Une feuille de route perimee
est donc pire qu'absente — elle fait decider sur un etat qui n'existe plus.

Ces tests rattachent chaque chiffre annonce a la donnee qui le porte. Le jour ou un geste
est chronometre ou une matiere ajoutee, c'est le document qui rougit, pas la mesure.
"""
import csv
import glob
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RACINE = ROOT.parent
ROADMAP = (ROOT / "docs" / "ROADMAP.md").read_text(encoding="utf-8")
ONBOARDING = (ROOT / "docs" / "ONBOARDING.md").read_text(encoding="utf-8")
README = (RACINE / "README.md").read_text(encoding="utf-8")


def _csv(p):
    return list(csv.DictReader(p.read_text(encoding="utf-8").splitlines(), delimiter=";"))


def _gabarits():
    return json.loads((ROOT / "params" / "operation_templates.json").read_text())["templates"]


def test_le_nombre_de_matieres_annonce_est_le_bon():
    """38 revient dans les deux documents. Ajouter une matiere sans les toucher ferait
    mentir la page d'accueil du depot."""
    reel = len(_csv(ROOT / "data" / "materials" / "matieres_premieres.csv"))
    for nom, doc in (("README", README), ("ROADMAP", ROADMAP)):
        assert f"**{reel}**" in doc or f"{reel} matieres" in doc or f"{reel} matières" in doc, (nom, reel)


def test_le_nombre_de_lignes_de_facture_est_le_bon():
    """384 lignes de prix reellement payes. Une nouvelle capture METRO change ce chiffre."""
    releves = sorted((ROOT / "data" / "price_observations").glob("metro_factures_*.json"))
    assert releves, "aucun releve de facture METRO"
    reel = sum(len(json.loads(p.read_text())["achats"]) for p in releves)
    assert str(reel) in ROADMAP and str(reel) in README, reel


def test_le_compte_de_rattachements_incertains_est_le_bon():
    """8 sur 24 sont A_VERIFIER. C'est un aveu, pas une statistique : chacun designe une
    propriete que le referentiel exige et que la facture ne dit pas. Le jour ou l'un se
    tranche, le document doit suivre — sinon l'aveu survit a sa raison."""
    lignes = _csv(ROOT / "data" / "materials" / "rattachement_metro.csv")
    a_verifier = [r for r in lignes if r["statut"] == "A_VERIFIER"]
    assert f"{len(a_verifier)} rattachements sur {len(lignes)}" in ROADMAP, (
        len(a_verifier), len(lignes))
    assert f"**{len(lignes)}**" in README, len(lignes)


def test_le_blocage_annonce_est_encore_le_blocage():
    """« 0 / 21 gestes chronometres » est la phrase qui porte toute la feuille de route.

    Le jour ou le premier geste est mesure, ce test rougit — et c'est exactement ce qu'on
    veut : le jalon 2 avance, les deux documents doivent le dire avant qu'on continue.
    """
    gestes = [o for g in _gabarits().values() for o in g["operations"]]
    chrono = [o for o in gestes if o["active_labor_minutes_per_batch"] is not None]
    assert f"{len(chrono)} / {len(gestes)}" in ROADMAP or \
           f"{len(chrono)}/{len(gestes)}" in ROADMAP, (len(chrono), len(gestes))
    assert f"**{len(chrono)} / {len(gestes)}**" in README, (len(chrono), len(gestes))


def test_chaque_gabarit_annonce_son_vrai_nombre_de_gestes():
    """Le tableau du jalon 2 sert de plan de chronometrage : on mesure ce qu'il liste.
    Un gabarit qui gagne un geste sans que le tableau bouge produit une mesure incomplete
    dont rien ne signale le trou."""
    for code, g in _gabarits().items():
        ligne = next((l for l in ROADMAP.splitlines() if l.startswith(f"| `{code}`")), None)
        assert ligne, f"{code} absent du tableau des gabarits"
        assert f"| {len(g['operations'])} |" in ligne, (code, len(g["operations"]), ligne)


def test_aucun_adr_accepte_tant_que_le_document_le_dit():
    """« 0 / 3 » borne le jalon 1. Accepter un ADR sans toucher la feuille de route
    laisserait croire que la composition reste a trancher alors qu'elle l'est."""
    adrs = sorted((ROOT / "docs" / "decisions").glob("ADR-*.md"))
    acceptes = [p for p in adrs
                if re.search(r"\*\*Statut\*\*\s*:\s*ACCEPTED", p.read_text(encoding="utf-8"))]
    assert f"{len(acceptes)} / {len(adrs)}" in ROADMAP, (len(acceptes), len(adrs))


def test_le_compte_d_invariants_annonce_est_le_vrai():
    """Le README annonce un nombre de tests. C'est la seule metrique que le depot met en
    avant pour dire qu'il se verifie : elle doit se compter, pas s'estimer."""
    reel = sum(len(re.findall(r"^def (test_\w+)", Path(f).read_text(encoding="utf-8"), re.M))
               for f in glob.glob(str(ROOT / "tests" / "test_*.py")))
    assert f"**{reel}**" in README, reel


def test_le_moteur_ne_consomme_toujours_pas_les_prix_mesures():
    """Le jalon 4 annonce « l'instrument est fait, le branchement non ».

    La moitie faite se voit : comparaison_factures.py produit 69 observations de prix
    matiere. La moitie manquante ne se voit nulle part — c'est une absence, et une absence
    ne rougit jamais toute seule. Le jour ou quelqu'un branche ces observations sur le
    moteur, la feuille de route continuerait d'annoncer un blocage leve.

    Ce test transforme le branchement en evenement : il casse quand le cablage apparait,
    et force a relire le jalon avant de continuer.
    """
    module = "comparaison_factures"
    consommateurs = [ROOT / "product_tool.py", ROOT / "generics_tool.py"]
    consommateurs += sorted((ROOT / "src").rglob("*.py"))
    branches = [p.name for p in consommateurs
                if module in p.read_text(encoding="utf-8")]
    assert not branches, (
        "le moteur consomme desormais les prix mesures — mettre a jour le jalon 4", branches)
    assert "l'instrument est fait, le branchement non" in ROADMAP


def test_garder_n_est_jamais_rendu_sans_comparaison():
    """`GARDER` affirme qu'une alternative a ete confrontee et a perdu. Tant que la raison
    n'est pas `ALTERNATIVE_PLUS_CHERE`, la comparaison n'a pas eu lieu et le cas appartient a
    `NON_COMPARE`.

    La version precedente de cet invariant gardait l'affirmation inverse : elle verifiait que
    100 % des GARDER etaient *sans* comparaison, et demandait que la disparition du defaut
    soit remarquee. Elle a ete remarquee — le 2026-09-23, 32 GARDER sur 32 etaient sans
    comparaison et le cas comparé n'avait jamais ete atteint. Le verdict a ete scinde. Ce
    test garde desormais le sens du mot au lieu de compter ses occurrences fausses.
    """
    import sys
    sys.path.insert(0, str(ROOT))
    import comparaison_factures as cf
    achats, _ = cf.charger()
    rattachement, matieres = cf.charger_referentiels()
    verdicts = cf.verdicts(achats, rattachement, matieres, cf.charger_alternatives())
    garder = [v for v in verdicts if v["verdict"] == cf.GARDER]
    sans_comparaison = [v for v in garder if v.get("raison") != "ALTERNATIVE_PLUS_CHERE"]
    assert not sans_comparaison, (
        "un GARDER sans alternative chiffree : le mot a reglisse vers son ancien sens",
        sans_comparaison[:2])


def test_le_document_d_accueil_compte_juste_les_non_compares():
    """Le document annonce un nombre de lignes jamais confrontees. C'est une affirmation sur
    des donnees vivantes : elle bouge des qu'une alternative entre au catalogue, et un
    document qui garde l'ancien compte redevient le defaut qu'il denonce."""
    import sys
    sys.path.insert(0, str(ROOT))
    import comparaison_factures as cf
    achats, _ = cf.charger()
    rattachement, matieres = cf.charger_referentiels()
    verdicts = cf.verdicts(achats, rattachement, matieres, cf.charger_alternatives())
    non_compares = [v for v in verdicts if v["verdict"] == cf.NON_COMPARE]
    assert f"{len(non_compares)} lignes" in ONBOARDING, len(non_compares)


def test_les_liens_internes_pointent_vers_des_fichiers_reels():
    """Un lien mort dans la page d'accueil envoie le lecteur nulle part et ne casse rien.
    Ici il casse."""
    for doc, base in ((README, RACINE), (ROADMAP, ROOT / "docs"),
                      (ONBOARDING, ROOT / "docs")):
        for cible in re.findall(r"\]\((?!https?:)([^)#]+)\)", doc):
            assert (base / cible).exists(), (cible, str(base))


if __name__ == "__main__":
    for nom, fn in sorted(globals().items()):
        if nom.startswith("test_"):
            fn()
            print(f"OK  {nom}")
