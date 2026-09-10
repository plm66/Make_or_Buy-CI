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


def test_lesperance_ne_decide_daucune_admission():
    """P013 révisé en 1.4.0 : les enveloppes familiales somment au plafond dur, donc elles
    garantissent seules le pire cas. Une porte d'admission par espérance n'ajouterait rien.

    Casse si le statut se remet à dépendre de l'espérance — c'est l'arbitrage d'Alex, et
    l'inverse rendrait le verdict indéfini entre postulat, config et validateur (P019).
    """
    import sys as _sys, json as _json
    _sys.path.insert(0, str(ROOT / "postulates" / "la_manita"))
    from manita_validator import validate
    config = _json.loads((ROOT / "postulates" / "la_manita" / "manita.config.json").read_text(encoding="utf-8"))
    config = _json.loads(_json.dumps(config))
    for f in config["family_cost_envelopes"]:
        config["family_cost_envelopes"][f]["hard_max_eur"] = 5.0
    cat = [{"id": f"{fam}{i}", "family": fam, "cost_eur": c}
           for fam in config["family_cost_envelopes"] for i, c in ((0, 0.10), (1, 0.60))]
    r = validate(cat, config)
    assert r["expected_bundle_cost_eur"] == 1.75 <= 1.75      # espérance saine
    assert r["worst_case_bundle_cost_eur"] == 3.0             # pire cas hors plafond
    assert r["status"] == "CATALOG_INVALID", r["status"]      # c'est le pire cas qui tranche


def test_lesperance_nest_exploitable_quau_dessus_du_volume():
    """Les directives interdisent de raisonner en moyenne sous le volume minimal. Le
    validateur ne pouvait pas l'appliquer, faute d'entrée de volume. Il le rend désormais."""
    import sys as _sys, json as _json
    _sys.path.insert(0, str(ROOT / "postulates" / "la_manita"))
    from manita_validator import validate
    config = _json.loads((ROOT / "postulates" / "la_manita" / "manita.config.json").read_text(encoding="utf-8"))
    seuil = config["expected_value_model"]["min_daily_bundles_for_averaging"]
    cat = [{"id": f, "family": f, "cost_eur": 0.10} for f in config["family_cost_envelopes"]]
    assert validate(cat, config)["expected_cost_usable"] is None
    assert validate(cat, config, daily_bundles=seuil - 1)["expected_cost_usable"] is False
    assert validate(cat, config, daily_bundles=seuil)["expected_cost_usable"] is True


def test_les_controles_non_implementes_sont_annonces():
    """P020 : un contrôle déclaré sans implémentation se lit comme un contrôle passé.
    Le validateur doit les nommer dans chaque sortie."""
    import sys as _sys, json as _json
    _sys.path.insert(0, str(ROOT / "postulates" / "la_manita"))
    from manita_validator import validate
    config = _json.loads((ROOT / "postulates" / "la_manita" / "manita.config.json").read_text(encoding="utf-8"))
    r = validate([], config)
    assert "dynamic_slots_resolvable" in r["checks_not_implemented"]
    assert "attachment_offset_measured_or_absent" in r["checks_not_implemented"]


def test_lenveloppe_familiale_est_la_seule_regle_par_article():
    """Revue Alex 1.3.0 : le plafond absolu par article est retiré, redondant.

    Pour FULL_MATRIX la règle est `product_cost <= hard_cap[family]`, rien d'autre. Un
    multiplicateur du type 1,5 × enveloppe autoriserait précisément le produit que
    l'enveloppe existe pour interdire. Casse si un second plafond réapparaît.
    """
    import sys as _sys, json as _json
    _sys.path.insert(0, str(ROOT / "postulates" / "la_manita"))
    from manita_validator import validate
    config = _json.loads((ROOT / "postulates" / "la_manita" / "manita.config.json").read_text(encoding="utf-8"))
    assert "per_item_absolute_cap_eur" not in config["expected_value_model"]

    cap = config["family_cost_envelopes"]["SNACK"]["hard_max_eur"]
    r = validate([{"id": "juste_dessus", "family": "SNACK", "cost_eur": cap + 0.01}], config)
    assert r["over_family_cap_products"][0]["product_id"] == "juste_dessus"
    assert "SNACK" in r["blocking_families"]


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


def test_une_reference_sous_le_maximum_est_gratuite():
    """P017 : le budget de pire cas consommé vaut max(0, coût − maximum de la famille).

    C'est ce qui réconcilie la cible de dix références avec P012 : une famille peut passer
    de 3 à 10 sans dégrader le worst case, tant que les nouvelles restent sous son maximum.
    Casse si l'admission redevient facturée au coût absolu du candidat.
    """
    from make_or_buy.manita import budget_incremental
    assert budget_incremental(0.60, 0.72) == 0.0      # sous le max : gratuit
    assert budget_incremental(0.72, 0.72) == 0.0      # au max : gratuit
    assert budget_incremental(0.73, 0.72) == 0.01     # un centime au-dessus : un centime
    assert budget_incremental(0.45, 0.30) == 0.15     # attractif mais cher en budget


def test_la_valeur_dadmission_ne_renvoie_pas_linfini():
    """Une référence gratuite n'a pas de ratio valeur/budget : elle s'admet sur sa seule
    valeur. Renvoyer l'infini la ferait gagner tous les classements sans rien dire de son
    intérêt réel."""
    from make_or_buy.manita import valeur_admission
    assert valeur_admission(10.0, 0.60, 0.72) is None
    assert valeur_admission(3.0, 0.75, 0.72) == 100.0   # 3 de valeur pour 0,03 de budget


def test_le_plafond_article_de_la_matrice_contrainte_se_calcule():
    """En CONSTRAINED_MATRIX le plafond d'un article n'est pas fixé : c'est ce qui reste du
    budget une fois les autres familles servies au moins cher. Un produit cher devient
    admissible avec certaines combinaisons seulement."""
    from make_or_buy.manita import plafond_article_matrice_contrainte
    r = plafond_article_matrice_contrainte({"A": [0.20, 0.60], "B": [0.10], "C": [0.05]}, 1.75)
    assert r["A"] == 1.60   # 1,75 − (0,10 + 0,05)
    assert r["B"] == 1.50   # 1,75 − (0,20 + 0,05)
    assert plafond_article_matrice_contrainte({"A": [0.2], "B": []}, 1.75) is None


def test_un_depassement_nomme_les_references_responsables():
    """Alex : le validateur doit rendre les références responsables, pas renvoyer à des
    enveloppes théoriques. Sans ça on raisonne sur un vecteur et pas sur un catalogue."""
    import sys as _sys, json as _json
    _sys.path.insert(0, str(ROOT / "postulates" / "la_manita"))
    from manita_validator import validate
    config = _json.loads((ROOT / "postulates" / "la_manita" / "manita.config.json").read_text(encoding="utf-8"))
    config = _json.loads(_json.dumps(config))
    for f in config["family_cost_envelopes"]:
        config["family_cost_envelopes"][f]["hard_max_eur"] = 5.0   # rien n'est exclu
    cat = [{"id": f"{fam}{i}", "family": fam, "cost_eur": c}
           for fam in config["family_cost_envelopes"] for i, c in ((0, 0.10), (1, 0.90))]
    r = validate(cat, config)
    assert r["admission_budget_eur"] == 4.5 and r["admission_budget_eur"] > 1.75
    assert len(r["overrun_attributable_to"]) == 5
    premier = r["overrun_attributable_to"][0]
    assert premier["cost_eur"] == 0.9
    assert premier["budget_freed_if_removed_eur"] == 0.8   # retomberait sur la 0,10


def test_une_portion_coute_sa_fraction_plus_le_portionnage():
    """P014 : une tranche de cake n'est pas un cake. Le coût se dérive du produit
    canonique par la règle de sa dérivation, jamais re-saisi.

    Bug corrigé en 1.4.0 : product_cost cherchait manita.effective_cost_eur alors que le
    schéma pose manita.serving_unit.effective_cost_eur — tous les coûts de portions
    étaient donc faux ou absents.
    """
    import sys as _sys
    _sys.path.insert(0, str(ROOT / "postulates" / "la_manita"))
    from manita_validator import serving_unit_cost
    taux = {"apprentice": {"cost_per_minute_eur": 0.16}}
    cake = {"internal_production": {"batch_size_units": 12},
            "manita": {"serving_unit": {
                "derivation": "PORTION", "portion_ratio": 1/12,
                "additional_operations": [{"task": "trancher",
                                           "active_labor_minutes_per_batch": 6,
                                           "labor_tier": "apprentice"}]}}}
    cout, motif = serving_unit_cost(cake, base_cost=6.00, tiers=taux)
    assert motif is None
    assert round(cout, 4) == round(6.00/12 + 6*0.16/12, 4) == 0.58


def test_une_transformation_dinvendu_ne_reimpute_pas_le_source():
    """Le croissant aux amandes est fait sur le croissant de la veille. Le coût du
    croissant n'entre pas : il n'est pas évitable en renonçant à la transformation, il a
    déjà été fabriqué et payé. C'est P003 et G003 de la doctrine.

    La règle est protégée par l'exigence de source_product_id et source_state : sans eux
    on ne peut pas distinguer une transformation d'invendu d'une fabrication normale.
    """
    import sys as _sys
    _sys.path.insert(0, str(ROOT / "postulates" / "la_manita"))
    from manita_validator import serving_unit_cost
    taux = {"production_assistant": {"cost_per_minute_eur": 0.25}}
    fiche = {"internal_production": {"batch_size_units": 20},
             "manita": {"serving_unit": {
                 "derivation": "TRANSFORMED_SURPLUS",
                 "source_product_id": "croissant_nature", "source_state": "DAY_OLD",
                 "additional_operations": [{"task": "garnir_repasser",
                                            "active_labor_minutes_per_batch": 20,
                                            "labor_tier": "production_assistant"}]}}}
    cout, motif = serving_unit_cost(fiche, base_cost=0.18, tiers=taux)   # 0,18 = crème d'amande
    assert motif is None and round(cout, 4) == round(0.18 + 20*0.25/20, 4) == 0.43

    sans_source = {"manita": {"serving_unit": {"derivation": "TRANSFORMED_SURPLUS"}}}
    assert serving_unit_cost(sans_source, 0.18, taux)[0] is None


if __name__ == "__main__":
    for nom, fn in sorted(globals().items()):
        if nom.startswith("test_"):
            fn()
            print(f"OK  {nom}")
