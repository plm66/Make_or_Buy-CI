"""Invariants du harnais de test.

Le projet n'a pas de framework : la convention est `python3 tests/test_*.py`, et chaque
fichier se termine par le bloc qui parcourt ses propres fonctions. Deux fichiers ne
l'avaient pas — `test_metro_factures.py` et `test_rattachement.py` sortaient en 0 sans rien
exécuter, et douze invariants sur cent trente-trois ne tournaient pas sous la commande
documentée. C'est le défaut de la maison sous sa forme la plus discrète : un compte vert
ne dit rien de ce qui n'a pas été lancé.

Ces deux tests tiennent la convention. Le premier la vérifie sur le texte, le second
l'exécute — un bloc peut exister et n'appeler aucune fonction.
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FICHIERS = sorted(ROOT.glob("test_*.py"))
MOI = Path(__file__).resolve().name

GARDE = re.compile(r'^if __name__ == "__main__":', re.M)
DECLARE = re.compile(r"^def test_", re.M)
IMPRIME = re.compile(r"^OK  test_", re.M)


def test_chaque_fichier_porte_son_bloc_dexecution():
    """Un fichier sans bloc d'exécution est un fichier mort sous la convention du projet :
    il se lance, il sort en zéro, et rien de ce qu'il déclare n'est vérifié. Rien ne le
    signalait — le vert était indistinguable du vide.
    """
    manquants = [f.name for f in FICHIERS if not GARDE.search(f.read_text(encoding="utf-8"))]
    assert not manquants, manquants


def test_chaque_fichier_annonce_tous_ses_tests():
    """Un bloc d'exécution peut exister et n'appeler qu'une partie des fonctions — un filtre
    trop étroit, un `if` de trop. On lance donc chaque fichier et on compte les `OK`
    imprimés : ils doivent égaler les fonctions déclarées.
    """
    for f in FICHIERS:
        if f.name == MOI:
            continue
        declares = len(DECLARE.findall(f.read_text(encoding="utf-8")))
        # -B n'empeche que l'ECRITURE du bytecode, jamais sa lecture : un .pyc deja sur
        # le disque est relu malgre lui. Mesure faite : cache perime present, avec et sans
        # -B, la regression passe au vert dans les deux cas. Ce qui vaut ici est donc
        # preventif — aucun .pyc n'est jamais ecrit, donc aucun ne peut perimer. Guerir un
        # cache deja pose demande de le supprimer, et c'est une autre commande.
        #
        # Python valide son cache sur
        # (mtime, taille) ; inverser deux chaines de meme longueur ne change ni l'une ni
        # l'autre, et un .pyc perime passe pour frais. Mesure du 21-09 : un cache date de
        # 15:48 servait CHAMPS_PRIX inverse alors que le disque et HEAD portaient le bon
        # ordre. Ce jour-la il a fait rougir du code sain — l'inverse est la vraie alerte,
        # et elle est verifiee : cache perime present, le garde G002 passe au vert sur la
        # regression meme qu'il surveille.
        out = subprocess.run([sys.executable, "-B", str(f)], capture_output=True, text=True)
        assert out.returncode == 0, (f.name, out.stderr[-400:])
        imprimes = len(IMPRIME.findall(out.stdout))
        assert imprimes == declares, (f.name, imprimes, declares)


if __name__ == "__main__":
    for nom, fn in sorted(globals().items()):
        if nom.startswith("test_"):
            fn()
            print(f"OK  {nom}")
