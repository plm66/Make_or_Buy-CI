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


def test_lesperance_admet_ce_que_le_pire_cas_refuse():
    """P013 : le pire cas somme les maxima des cinq familles à la fois — un adversaire,
    pas un client. L'admission se juge sur l'espérance, le pire cas restant rendu.

    Le verdict est celui du validateur du postulat : une seconde implémentation ici
    pourrait diverger de la normative.
    """
    import sys as _sys, json as _json
    _sys.path.insert(0, str(ROOT / "postulates" / "la_manita"))
    from manita_validator import validate
    config = _json.loads((ROOT / "postulates" / "la_manita" / "manita.config.json").read_text(encoding="utf-8"))
    config = _json.loads(_json.dumps(config))
    for f in config["family_cost_envelopes"]:
        config["family_cost_envelopes"][f]["hard_max_eur"] = 1.0
    cat = [{"id": f"{fam}{i}", "family": fam, "cost_eur": c}
           for fam in config["family_cost_envelopes"] for i, c in ((0, 0.10), (1, 0.60))]
    r = validate(cat, config)
    assert r["worst_case_bundle_cost_eur"] == 3.0 and r["worst_case_bundle_cost_eur"] > 1.75
    assert r["expected_bundle_cost_eur"] == 1.75
    assert r["status"] == "VALID_BUNDLE", r


def test_le_plafond_par_article_bloque_la_dilution():
    """Garde contre l'usage détourné de P013. Sans plafond par article, une référence hors
    budget serait admise en la noyant dans une moyenne — ce que P011 interdit. Une
    espérance saine ne rachète pas un article aberrant."""
    import sys as _sys, json as _json
    _sys.path.insert(0, str(ROOT / "postulates" / "la_manita"))
    from manita_validator import validate
    config = _json.loads((ROOT / "postulates" / "la_manita" / "manita.config.json").read_text(encoding="utf-8"))
    cap = config["expected_value_model"]["per_item_absolute_cap_eur"]
    cat = [{"id": "aberrant", "family": "SNACK", "cost_eur": cap + 0.5}]
    r = validate(cat, config)
    assert r["over_item_cap_products"] and r["over_item_cap_products"][0]["product_id"] == "aberrant"


def test_la_ponderation_deplace_lesperance_vers_le_produit_choisi():
    """L'espérance uniforme suppose un client indifférent. Il ne l'est pas.

    Le validateur du postulat ne sait calculer que l'uniforme, faute de ventes observées.
    `bornes_du_panier` porte le cas pondéré, qui existera le jour où la caisse mesurera la
    distribution réelle — et c'est ce jour-là que l'espérance dérivera vers le maximum si
    un produit devient un carton.
    """
    from make_or_buy.manita import bornes_du_panier
    par_fam = {"A": [0.20, 0.80]}
    assert bornes_du_panier(par_fam)[1] == 0.50                      # uniforme
    assert bornes_du_panier(par_fam, poids={"A": [9, 1]})[1] == 0.26  # le pas cher domine
    assert bornes_du_panier(par_fam, poids={"A": [1, 9]})[1] == 0.74  # le cher domine
    assert bornes_du_panier(par_fam)[2] == 0.80                      # pire cas inchangé


if __name__ == "__main__":
    for nom, fn in sorted(globals().items()):
        if nom.startswith("test_"):
            fn()
            print(f"OK  {nom}")
