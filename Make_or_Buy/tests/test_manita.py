"""Invariants de la composition de grilles à prix cible.

Une grille n'est pas un classement : `engine.compose_menus` rend les meilleures
combinaisons et peut réemployer le même article partout. Ici chaque produit sert une fois
et l'écart au prix cible est une contrainte, pas un score.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from make_or_buy.manita import compose_grille

COLONNES = ["A", "B"]


def catalogue(prix_a, prix_b, champ="sale_price_eur"):
    return ([{"id": f"a{i}", "name": f"A{i}", "family": "A", champ: p} for i, p in enumerate(prix_a)]
            + [{"id": f"b{i}", "name": f"B{i}", "family": "B", champ: p} for i, p in enumerate(prix_b)])


def test_aucun_produit_ne_sert_deux_fois():
    """C'est la contrainte structurante : une colonne place ses produits sur des lignes
    distinctes. Sans elle on obtient dix variantes d'une même ligne — ce que rend
    compose_menus, qui classe des combinaisons indépendantes.
    """
    grille, _ = compose_grille(catalogue([1, 2, 3], [4, 3, 2]), COLONNES,
                               lignes=3, cible=5.0, tolerance=0.0)
    assert len(grille) == 3
    vus = [i["id"] for ligne in grille for i in ligne["items"]]
    assert len(vus) == len(set(vus)), vus


def test_chaque_ligne_tient_dans_la_tolerance():
    """L'écart à la cible est une contrainte à satisfaire, jamais une valeur à maximiser.
    Casse si le score de compose_menus — qui récompense le dépassement — revient ici."""
    grille, _ = compose_grille(catalogue([1, 2, 3], [4, 3, 2]), COLONNES,
                               lignes=3, cible=5.0, tolerance=0.3)
    for ligne in grille:
        assert 5.0 <= ligne["total_eur"] <= 5.3, ligne["total_eur"]


def test_grille_courte_est_un_resultat_pas_une_erreur():
    """Une colonne trop pauvre rend une grille incomplète et dit combien il manque.
    Lever une exception cacherait l'information utile : le nombre de références à créer."""
    grille, manques = compose_grille(catalogue([1, 2], [4, 3]), COLONNES,
                                     lignes=10, cible=5.0, tolerance=0.0)
    assert len(grille) == 2
    assert manques == {"A": 8, "B": 8}, manques


def test_cible_inatteignable_rend_une_grille_vide():
    """Aucune combinaison ne tient : on rend zéro ligne, pas une ligne approximative.

    Le cas est réel — la ligne la moins chère du catalogue d'exemple vaut 10,10 € aux prix
    carte contre une cible de 5 €. Une manita à 5 € somme donc un autre prix que celui de
    la vitrine, et ce test protège le refus plutôt qu'un rapprochement silencieux.
    """
    grille, _ = compose_grille(catalogue([10, 12], [8, 9]), COLONNES,
                               lignes=2, cible=5.0, tolerance=0.5)
    assert grille == []


def test_le_champ_de_prix_est_choisi():
    """Le prix sommé n'est pas forcément celui de la vitrine : une formule valorise ses
    articles autrement. Casse si sale_price_eur redevient codé en dur."""
    cat = catalogue([1, 2], [4, 3], champ="reference_value_eur")
    assert compose_grille(cat, COLONNES, lignes=1, cible=5.0, tolerance=0.0)[0] == []
    grille, _ = compose_grille(cat, COLONNES, lignes=1, cible=5.0, tolerance=0.0,
                               champ_prix="reference_value_eur")
    assert grille and grille[0]["total_eur"] == 5.0


def test_adaptateur_pose_le_cout_ajuste_par_le_sourcing():
    """Le postulat veut le SELECTED_EFFECTIVE_PRODUCT_COST, pas le coût matière brut.

    Le format legacy expose les deux moitiés — coût interne et prix rendu — sans jamais
    le choix. L'adaptateur y dépose le coût effectivement retenu, sous le `cost_eur` que
    le validateur livré documente comme son point d'extension.
    """
    from make_or_buy.manita import adapte_pour_validateur
    catalogue = [{"id": "x"}, {"id": "y"}]
    adapte = adapte_pour_validateur(catalogue, lambda p: (0.42, "BUY") if p["id"] == "x" else (None, "UNDECIDED"))
    assert adapte[0]["cost_eur"] == 0.42
    assert "cost_eur" not in adapte[1], "un coût inconnu doit rester absent, jamais valoir zéro"
    assert catalogue == [{"id": "x"}, {"id": "y"}], "l'adaptateur ne mute pas son entrée"


def test_le_validateur_livre_refuse_plutot_que_de_fabriquer():
    """Contrat d'agent : DATA_INCOMPLETE quand un champ critique manque, jamais une
    décision inventée. Casse si l'adaptateur se met à combler les coûts absents."""
    import sys as _sys
    _sys.path.insert(0, str(ROOT / "postulates" / "la_manita"))
    from manita_validator import validate
    from make_or_buy.manita import adapte_pour_validateur
    import json
    config = json.loads((ROOT / "postulates" / "la_manita" / "manita.config.json").read_text(encoding="utf-8"))
    cat = [{"id": "s", "family": "SNACK"}]
    r = validate(adapte_pour_validateur(cat, lambda p: (None, "UNDECIDED")), config)
    assert r["status"] == "DATA_INCOMPLETE", r["status"]
    assert "s" in r["missing_cost_products"]


if __name__ == "__main__":
    for nom, fn in sorted(globals().items()):
        if nom.startswith("test_"):
            fn()
            print(f"OK  {nom}")
