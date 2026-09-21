"""Invariants du JavaScript des pages.

Le dépôt juge son Python et laissait son JavaScript sans juge. La page a été livrée avec
deux `const nonLues` dans la même portée — une erreur de *parsing*, donc le `<script>`
entier rejeté, aucun écouteur lié, et un dépôt de PDF qui ne faisait rien. Les 188
invariants sont restés verts : ils sont tous en Python, aucun ne lisait ce fichier.

Le juge est `node --check`. Une première version tentait un scanner de portées en Python
pur, pour ne dépendre d'aucun binaire ; confronté à la page cassée, il ne la voyait pas —
il prenait le `"` du littéral `/[&<>"']/` pour une ouverture de chaîne et aveuglait la
moitié du fichier. Un juge qui rend vert sur ce qu'il n'a pas lu est pire que pas de juge,
et c'est le défaut même que cette suite est censée fermer. Il a été retiré.

`node` n'est pas une dépendance du projet (`pyproject.toml` : `dependencies = []`). Son
absence est donc déclarée, jamais verte — et cette limite est réelle : le défaut jumeau de
la page était un essai qui se déclarait ignoré à chaque exécution parce que son chemin
était mort.
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))

PAGES = sorted((RACINE / "web").glob("*.html"))


def _scripts(page):
    return re.findall(r"<script>(.*?)</script>", page.read_text(encoding="utf-8"), re.S)


def test_le_script_de_chaque_page_se_parse():
    """Une erreur de syntaxe ne casse pas une fonction, elle annule le script entier : la
    page s'affiche intacte et ne répond à rien. C'est l'échec le plus silencieux qu'une page
    puisse produire, et aucun essai Python ne peut le voir."""
    if not shutil.which("node"):
        print("      (ignoré : node absent, le JS des pages n'a été parsé par personne)")
        return
    for page in PAGES:
        for numero, js in enumerate(_scripts(page)):
            resultat = subprocess.run(["node", "--check", "-"], input=js,
                                      capture_output=True, text=True)
            assert resultat.returncode == 0, (
                f"{page.name}, script {numero} : "
                f"{' | '.join(resultat.stderr.strip().splitlines()[:3])}")


def test_chaque_page_porte_un_script_a_juger():
    """Sans ce contrôle, une page sans `<script>` — ou un `web/` vide — rendrait l'essai
    ci-dessus vert sur zéro ligne lue. Le vert indistinguable du vide, encore."""
    assert PAGES, "aucune page dans web/ : cette suite ne juge rien"
    for page in PAGES:
        assert _scripts(page), f"{page.name} ne porte aucun bloc <script> à parser"


if __name__ == "__main__":
    for nom, fn in sorted(globals().items()):
        if nom.startswith("test_"):
            fn()
            print(f"OK  {nom}")
