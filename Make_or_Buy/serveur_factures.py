#!/usr/bin/env python3
"""Page locale pour deposer une facture METRO et lire ce que le depot en propose.

Le serveur ne sert que cette page, sur localhost, et n'envoie rien a l'exterieur. Le PDF
depose est ecrit dans un dossier temporaire, jamais dans `data/`, et rien du depot n'est
modifie : la page est une vue, pas une seconde implementation.

L'extraction est celle de `metro_factures.py`, les verdicts ceux de `comparaison_factures.py`.
Le contrat est dans `docs/SPEC_MODULE_FACTURES.md`, et il tient en une phrase : le verdict
CHANGER exige un prix alternatif chiffre et date, sinon la ligne est declaree a arbitrer.

Usage: python3 serveur_factures.py [--port 8770] [--ouvrir]
"""
import argparse
import json
import shutil
import sys
import tempfile
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

RACINE = Path(__file__).resolve().parent
PAGE = RACINE / "web" / "factures.html"
sys.path.insert(0, str(RACINE))

import comparaison_factures as cf  # noqa: E402
import metro_factures as mf  # noqa: E402


def analyse_achats(achats, entete, rattachement, matieres, alternatives=None):
    """Une proposition par ligne extraite, et le compte par verdict."""
    propositions = cf.verdicts(achats, rattachement, matieres, alternatives)
    comptes = {}
    for proposition in propositions:
        comptes[proposition["verdict"]] = comptes.get(proposition["verdict"], 0) + 1
    return {
        "entete": entete,
        "lignes": len(achats),
        "comptes": comptes,
        "propositions": propositions,
    }


def analyser(pdf, travail=None):
    """Extrait un PDF depose et rend une proposition par ligne extraite.

    Une erreur de lecture rend un message, pas une exception : la page doit pouvoir dire
    ce qui s'est passe au lieu de tomber.
    """
    if not shutil.which("pdftotext"):
        return {"erreur": "pdftotext est absent (paquet poppler). Sans lui, aucune facture ne se lit."}

    dossier = Path(travail or tempfile.mkdtemp(prefix="factures-"))
    dossier.mkdir(parents=True, exist_ok=True)
    copie = dossier / Path(pdf).name
    # Le serveur depose deja le PDF dans le dossier de travail : recopier un fichier sur
    # lui-meme leve SameFileError, et c'est exactement le chemin qu'emprunte la page.
    if Path(pdf).resolve() != copie.resolve():
        shutil.copyfile(pdf, copie)

    try:
        entete, achats, remises, non_lues = mf.extraire_facture(copie)
    except Exception as erreur:  # pdftotext refuse un fichier qui n'est pas un PDF
        return {"erreur": f"lecture impossible : {type(erreur).__name__}"}

    if not achats:
        return {"entete": entete, "lignes": 0, "comptes": {}, "propositions": [],
                "lignes_non_lues": non_lues,
                "avertissement": "aucune ligne d'achat lue dans ce document"}

    rattachement, matieres = cf.charger_referentiels()
    alternatives = cf.charger_alternatives()
    resultat = analyse_achats(achats, entete, rattachement, matieres, alternatives)
    resultat["remises"] = len(remises)
    resultat["lignes_non_lues"] = non_lues
    return resultat


class Handler(BaseHTTPRequestHandler):
    server_version = "factures"

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._envoyer(200, "text/html; charset=utf-8", PAGE.read_bytes())
        else:
            self._envoyer(404, "text/plain; charset=utf-8", b"chemin inconnu")

    def do_POST(self):
        if self.path != "/analyser":
            self._envoyer(404, "text/plain; charset=utf-8", b"chemin inconnu")
            return
        taille = int(self.headers.get("Content-Length") or 0)
        if taille <= 0:
            self._envoyer(400, "application/json", json.dumps({"erreur": "corps vide"}).encode())
            return
        donnees = self.rfile.read(taille)
        # Le dossier temporaire porte tout le travail et disparait apres la reponse.
        with tempfile.TemporaryDirectory(prefix="factures-") as dossier:
            pdf = Path(dossier) / "facture.pdf"
            pdf.write_bytes(donnees)
            resultat = analyser(pdf, dossier)
        self._envoyer(200, "application/json; charset=utf-8",
                      json.dumps(resultat, ensure_ascii=False).encode("utf-8"))

    def _envoyer(self, code, type_contenu, corps):
        self.send_response(code)
        self.send_header("Content-Type", type_contenu)
        self.send_header("Content-Length", str(len(corps)))
        self.end_headers()
        self.wfile.write(corps)

    def log_message(self, format, *args):
        print(f"  {self.address_string()} {format % args}")


def main():
    parseur = argparse.ArgumentParser(description=__doc__)
    parseur.add_argument("--port", type=int, default=8770)
    parseur.add_argument("--ouvrir", action="store_true", help="ouvre la page dans le navigateur")
    options = parseur.parse_args()

    if not PAGE.exists():
        sys.exit(f"page absente : {PAGE}")

    serveur = ThreadingHTTPServer(("127.0.0.1", options.port), Handler)
    adresse = f"http://127.0.0.1:{options.port}/"
    print(f"page locale : {adresse}  (Ctrl+C pour arreter)")
    if options.ouvrir:
        webbrowser.open(adresse)
    try:
        serveur.serve_forever()
    except KeyboardInterrupt:
        print("\narret")


if __name__ == "__main__":
    main()
