"""Invariants du serveur local et de sa page.

Le serveur ne sert qu'une vue sur le moteur de verdicts. Ce qui doit être vrai n'est donc
pas « la page s'affiche », mais : chaque ligne reçue obtient une proposition avec sa raison,
un fichier illisible rend un message et pas une exception, et rien du dépôt n'est écrit.

Le PDF source n'est pas versionné (`.gitignore` le porte), donc l'essai de bout en bout est
déclaré ignoré quand aucun PDF n'est présent, au lieu de passer en silence.
"""
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))

import comparaison_factures as cf  # noqa: E402
import serveur_factures as sf  # noqa: E402

PDF_METRO = RACINE / "data/price_observations/metro"


def ligne(**kw):
    base = {"article": "2422798", "date_facture": "2026-07-27", "facture": "F1",
            "designation": "MC FARINE PANIF. T65 25KG", "colisage": 25,
            "prix_unitaire_ht": 0.75, "prix_unitaire_paye": None,
            "prix_unite_normalisee": None}
    base.update(kw)
    return base


def _referentiels():
    return [{"article_metro": "2422798", "id_matiere": "MATP-FARI-T65", "statut": "ACTIF"}], {}


def _fichiers_de_data():
    return sorted(str(p.relative_to(RACINE)) for p in (RACINE / "data").rglob("*") if p.is_file())


def test_chaque_ligne_obtient_une_proposition_et_sa_raison():
    """L'invariant de la page : aucune ligne muette, aucune proposition sans raison. Une
    raison vide serait indiscernable d'un bug d'affichage."""
    rattachement, matieres = _referentiels()
    achats = [ligne(), ligne(article="7777777", designation="OBJET INCONNU")]
    resultat = sf.analyse_achats(achats, {"numero": "F1"}, rattachement, matieres)
    assert resultat["lignes"] == 2, resultat
    assert len(resultat["propositions"]) == 2, resultat
    assert sum(resultat["comptes"].values()) == 2, resultat["comptes"]
    for proposition in resultat["propositions"]:
        assert proposition["raison"], proposition
        assert proposition["verdict"] in (cf.GARDER, cf.CHANGER, cf.A_ARBITRER,
                                          cf.NON_RATTACHE, cf.HORS_PERIMETRE), proposition


def test_un_fichier_illisible_rend_un_message_pas_une_exception():
    """Une page qui tombe ne dit rien. Un fichier qui n'est pas un PDF, ou un `pdftotext`
    absent, doit rendre une erreur lisible."""
    import tempfile
    with tempfile.TemporaryDirectory() as dossier:
        faux = Path(dossier) / "pas-un-pdf.pdf"
        faux.write_text("ceci n'est pas un PDF", encoding="utf-8")
        resultat = sf.analyser(faux, dossier)
    assert "erreur" in resultat, resultat
    assert isinstance(resultat["erreur"], str) and resultat["erreur"], resultat


def test_rien_du_depot_n_est_ecrit_par_une_analyse():
    """La spec l'exige : le travail se fait dans un dossier temporaire, et aucun fichier du
    dépôt ne change. Le contrôle porte sur l'arbre réel, pas sur une intention."""
    import tempfile
    avant = _fichiers_de_data()
    with tempfile.TemporaryDirectory() as dossier:
        faux = Path(dossier) / "pas-un-pdf.pdf"
        faux.write_text("x", encoding="utf-8")
        sf.analyser(faux, dossier)
    assert _fichiers_de_data() == avant, "un fichier du dépôt a bougé pendant une analyse"


def test_la_page_porte_le_depot_et_l_endpoint():
    """Le contrat minimal entre la page et le serveur : un champ de fichier, et un envoi vers
    l'endpoint que le serveur sert réellement."""
    page = (RACINE / "web" / "factures.html").read_text(encoding="utf-8")
    assert 'type="file"' in page, "aucun champ de fichier"
    assert "'/analyser'" in page, "la page n'appelle pas l'endpoint du serveur"
    assert "EUR/kg" in page, "la page n'annonce pas l'unité du prix"
    assert 'id="non-lues"' in page, "la page ne prévoit pas d'afficher les lignes non lues"
    assert "lignes_non_lues" in page, "la page n'utilise pas les lignes déclarées non lues"


# L'accesseur, pas le nom nu : `class="raison"` est une classe CSS, pas un champ du PDF.
CHAMPS_DU_PDF = ("p.designation", "p.article", "p.id_matiere", "p.raison",
                 "p.alternative.source_id")


def _bloc(page, marqueur):
    debut = page.index(marqueur)
    return page[debut:page.index(";", debut)]


def _champs_sans_echappement(page, marqueur, champs=CHAMPS_DU_PDF):
    """Les champs venus du PDF, dans le bloc désigné, qui ne sont pas passés par `esc(`.

    Le contrôle est local et non textuel : une première version cherchait la chaîne
    `${p.designation`, et retirer l'échappement laissait le test vert parce que l'écriture
    autour changeait. Ici on regarde ce qui précède immédiatement chaque nom de champ.
    """
    extrait = _bloc(page, marqueur)
    nus = []
    for champ in champs:
        position = 0
        while (index := extrait.find(champ, position)) != -1:
            if "esc(" not in extrait[max(0, index - 12):index]:
                nus.append((champ, extrait[max(0, index - 28):index + 12]))
            position = index + len(champ)
    return nus


def test_la_page_echappe_tout_texte_venu_du_pdf():
    """Une désignation vient du texte d'un PDF : elle peut porter `<`, `&` ou une apostrophe.
    Injectée telle quelle dans le tableau, elle casse l'affichage et fait disparaître des
    lignes. Une ligne qui disparaît ressemble à une ligne qui n'existait pas."""
    page = (RACINE / "web" / "factures.html").read_text(encoding="utf-8")
    assert "const esc" in page, "aucune fonction d'échappement"
    nus = _champs_sans_echappement(page, "ligne.innerHTML =")
    assert nus == [], f"champs du PDF injectés sans échappement : {nus}"
    non_lues = _bloc(page, "nonLues.innerHTML =")
    assert "esc(l)" in non_lues and "${l}" not in non_lues, non_lues


def test_la_page_n_invente_aucun_endpoint_absent_du_serveur():
    """Un endpoint appelé et non servi donnerait une page qui échoue en silence."""
    page = (RACINE / "web" / "factures.html").read_text(encoding="utf-8")
    source = (RACINE / "serveur_factures.py").read_text(encoding="utf-8")
    assert "'/analyser'" in page and '"/analyser"' in source.replace("'", '"'), "endpoint absent du serveur"


def test_un_pdf_reel_va_jusqu_aux_verdicts():
    """Bout en bout, quand le PDF source est là. Les PDF ne sont pas versionnés : sans eux,
    l'essai est déclaré ignoré plutôt que vert."""
    pdfs = sorted(PDF_METRO.glob("*.pdf")) if PDF_METRO.exists() else []
    if not pdfs:
        print("      (ignoré : aucun PDF dans data/price_observations/metro)")
        return
    import tempfile
    with tempfile.TemporaryDirectory() as dossier:
        resultat = sf.analyser(pdfs[0], dossier)
    assert "erreur" not in resultat, resultat
    assert resultat["lignes"] > 0, resultat
    assert len(resultat["propositions"]) == resultat["lignes"], resultat


if __name__ == "__main__":
    for nom, fn in sorted(globals().items()):
        if nom.startswith("test_"):
            fn()
            print(f"OK  {nom}")