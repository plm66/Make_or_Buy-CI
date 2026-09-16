"""Invariants de la fiche produit 2.0.0.

Chaque test protège une règle, pas une valeur de sortie : il doit casser si quelqu'un
« simplifie » la logique, pas si un prix d'exemple change.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import product_tool as pt

TAUX = {"labor": {"tiers": {
    "apprentice": {"cost_per_minute_eur": 0.16},
    "production_assistant": {"cost_per_minute_eur": 0.25},
    "qualified_baker_pastry": {"cost_per_minute_eur": 0.36},
}}}


def fiche_complete():
    """Fiche saisie de bout en bout : postes matière, lot chronométré, prix connu, 2 sources."""
    d = json.loads((ROOT / "data" / "product.template.json").read_text(encoding="utf-8"))
    d["product"].update(id="probe", name="Probe", family="DESSERT", status="ACTIVE")
    d["commercial"]["sale_price_eur"] = 2.0
    d["signature"]["class"] = "STANDARDIZABLE"
    d["signature"]["customer_value_score"] = 2.5
    d["dietary"].update(vegan=True, vegetarian=True, claim_evidence="INTERNAL_RECIPE_DOCUMENTED")
    d["internal_production"].update(
        possible=True, cost_status="VERIFIED", batch_size_units=40,
        material_cost_eur=0.25, energy_cost_eur=0.02, packaging_cost_eur=0.03,
        cleaning_handling_cost_eur=0.01, expected_loss_cost_eur=0.02,
        other_avoidable_cost_eur=0.0,
        operations=[
            {"task": "pesee_melange", "active_labor_minutes_per_batch": 20,
             "elapsed_minutes_per_batch": 20, "labor_tier": "apprentice"},
            {"task": "faconnage_cuisson", "active_labor_minutes_per_batch": 30,
             "elapsed_minutes_per_batch": 45, "labor_tier": "qualified_baker_pastry"},
        ],
        # 0.33 saisi + (20 x 0.16 + 30 x 0.36) / 40 = 0.33 + 0.35
        avoidable_cost_total_eur=0.68,
    )
    d["external_sourcing"] = {"possible": True, "sources": [
        {"source_id": "cher_longue_dlc", "supplier_name": "A", "data_status": "VERIFIED",
         "landed_cost_eur": 0.52, "shelf_life_hours": 720},
        {"source_id": "moins_cher_dlc_courte", "supplier_name": "B", "data_status": "VERIFIED",
         "landed_cost_eur": 0.38, "shelf_life_hours": 96},
    ]}
    d["decision_inputs"]["recommended_mode"] = "BUY"
    d["data_quality"].update(confidence="HIGH", missing_critical_fields=[])
    return d


def test_chaque_geste_est_paye_a_son_niveau():
    """Un geste d'apprenti ne coûte pas un geste de boulanger qualifié.

    Casse si le moteur retombe sur un taux unique : ici 50 minutes valorisées à un seul
    niveau donneraient 0,20 ou 0,45 €/unité, jamais 0,35.
    """
    i = fiche_complete()["internal_production"]
    assert pt.labor_cost(i, TAUX) == 0.35


def test_temps_ecoule_nest_pas_du_temps_immobilise():
    """Une infusion de 30 min surveillée en 1 min coûte 1 min, pas 30.

    C'est la règle qui sépare ce modèle d'un chronomètre : on facture le temps humain
    réellement immobilisé. L'écart est de la capacité libérée au sens de P004, pas du coût.
    """
    i = fiche_complete()["internal_production"]
    facture = pt.labor_cost(i, TAUX)
    i_elapsed = json.loads(json.dumps(i))
    for op in i_elapsed["operations"]:
        op["active_labor_minutes_per_batch"] = op["elapsed_minutes_per_batch"]
    assert pt.labor_cost(i_elapsed, TAUX) > facture


def test_elapsed_inferieur_a_active_est_refuse():
    """Le temps écoulé ne peut pas être inférieur au temps immobilisé — saisie inversée."""
    doc = fiche_complete()
    doc["internal_production"]["operations"][0]["elapsed_minutes_per_batch"] = 5  # actif = 20
    errs = pt.validate_product(doc, TAUX)
    assert any("elapsed_minutes_per_batch" in e for e in errs), errs


def test_niveau_inconnu_est_refuse():
    """Un labor_tier absent de params ne doit pas valoir zéro en silence."""
    doc = fiche_complete()
    doc["internal_production"]["operations"][0]["labor_tier"] = "chef_etoile"
    errs = pt.validate_product(doc, TAUX)
    assert any("chef_etoile" in e for e in errs), errs


def test_revision_dun_taux_perime_les_totaux():
    """G006 : une révision de salaire doit forcer la réévaluation des décisions.

    Les taux vivant dans params/, le total d'une fiche cesse d'être recalculable dès qu'un
    niveau bouge — et le validateur le dit. Casse si le coût du travail redevient un montant
    saisi par produit : le taux serait gravé N fois et une révision passerait inaperçue.
    """
    doc = fiche_complete()
    assert pt.validate_product(doc, TAUX) == []

    hausse = json.loads(json.dumps(TAUX))
    hausse["labor"]["tiers"]["apprentice"]["cost_per_minute_eur"] = 0.25
    errs = pt.validate_product(doc, hausse)
    assert any("avoidable_cost_total_eur" in e for e in errs), errs


def test_cout_annonce_verifie_doit_etre_recalculable():
    """Un `cost_status: VERIFIED` que rien ne permet de recalculer est un statut qui ment."""
    errs = pt.validate_product(fiche_complete(), {})  # aucun taux connu
    assert any("non recalculable" in e for e in errs), errs


def test_lot_non_mesure_reste_une_ignorance_legitime():
    """Connaître les gestes sans avoir mesuré la taille du lot est un état de savoir valide.

    La fiche existe pour consigner le partiel sans l'inventer : le coût devient simplement
    incalculable. Casse si batch_size_units redevient obligatoire dès qu'il y a des gestes.
    """
    doc = fiche_complete()
    doc["internal_production"]["batch_size_units"] = None
    doc["internal_production"]["cost_status"] = "UNKNOWN"
    doc["internal_production"]["avoidable_cost_total_eur"] = None
    doc["data_quality"].update(confidence="MEDIUM",
                               missing_critical_fields=["internal_production.batch_size_units"])
    assert pt.validate_product(doc, TAUX) == []
    assert pt.labor_cost(doc["internal_production"], TAUX) is None


def test_preuve_vegan_doit_etre_documentee():
    """Une allégation vegan est le seul contrôle dont l'erreur sort de l'écran.

    Le filtre est une liste blanche, pas une liste noire : la version précédente
    rejetait NONE et NOT_APPLICABLE, donc PARTIAL passait — et n'importe quelle valeur
    ajoutée plus tard à l'enum serait passée aussi. Casse si quelqu'un ré-énumère les
    valeurs interdites au lieu des valeurs suffisantes.
    """
    for insuffisante in ["PARTIAL", "NONE", "NOT_APPLICABLE", "VALEUR_AJOUTEE_PLUS_TARD"]:
        doc = fiche_complete()
        doc["dietary"]["claim_evidence"] = insuffisante
        errs = pt.validate_product(doc, TAUX)
        assert any("vegan" in e for e in errs), (insuffisante, errs)

    for suffisante in ["SUPPLIER_DOCUMENTED", "INTERNAL_RECIPE_DOCUMENTED"]:
        doc = fiche_complete()
        doc["dietary"]["claim_evidence"] = suffisante
        assert pt.validate_product(doc, TAUX) == []


def test_capacite_liberee_est_restituee():
    """L'écart entre temps écoulé et temps immobilisé est une valeur, pas un résidu.

    P004 demande de compter le temps qualifié libéré. Il est calculé depuis toujours
    et n'apparaissait nulle part. Casse si operations_summary cesse de rendre les deux
    totaux séparément.
    """
    i = fiche_complete()["internal_production"]
    actif, ecoule = pt.operations_summary(i)
    assert (actif, ecoule) == (50, 65)          # 20+30 immobilisées, 20+45 écoulées
    assert ecoule - actif == 15                 # capacité libérée par lot


def test_status_distingue_pret_et_incomplet():
    """`status` sert à savoir s'il reste quelque chose à faire sur une fiche.

    PRÊT signifie exactement « compile l'accepterait ». Casse si les deux critères
    divergent — l'utilisateur verrait PRÊT sur une fiche que compile ignore.
    """
    assert pt.fiche_status(fiche_complete(), TAUX)[0] == "PRET"

    sans_prix = fiche_complete()
    sans_prix["commercial"]["sale_price_eur"] = None
    etat, details = pt.fiche_status(sans_prix, TAUX)
    assert etat == "INCOMPLET"
    assert any("sale_price_eur" in d for d in details), details


def test_seule_la_fiche_technique_porte_une_allegation_vegan():
    """Traduction des preuves fournisseur vers le vocabulaire de la fiche.

    Le critère est celui que la doctrine nomme en premier pour les produits vegan : la
    source doit pouvoir documenter les *changements de recette*. Une fiche technique porte
    une version et une procédure d'alerte ; une page produit et une mention d'emballage
    disent l'état du jour et rien de l'après — un fournisseur qui reformule en silence
    rend l'allégation fausse sans que personne ne l'apprenne.

    Casse si une page produit redevient une preuve suffisante.
    """
    assert pt.preuve_fiche("OFFICIAL_TECHNICAL_SHEET") in pt.PREUVES_VEGAN_SUFFISANTES
    for insuffisante in ["OFFICIAL_PRODUCT_PAGE", "LABEL", "NONE", "UNKNOWN", "INVENTE"]:
        assert pt.preuve_fiche(insuffisante) not in pt.PREUVES_VEGAN_SUFFISANTES, insuffisante


def test_les_gabarits_ne_portent_aucune_minute():
    """Un gabarit donne les gestes, jamais leur durée.

    C'est la garde qui empêche la technologie de fabriquer un coût : elle dit quels gestes
    restent en interne, et rien sur le temps qu'ils prennent. Une minute pré-remplie ici
    se propagerait dans avoidable_cost_total_eur sans que personne ne l'ait mesurée —
    exactement ce que la doctrine interdit.
    """
    for techno in pt.load_templates():
        for op in pt.operations_pour(techno):
            assert op["active_labor_minutes_per_batch"] is None, (techno, op["task"])
            assert op["elapsed_minutes_per_batch"] is None, (techno, op["task"])


def test_chaque_technologie_du_catalogue_a_son_gabarit():
    """Une technologie vue dans un catalogue mais sans gabarit laisse un produit sans
    moyen de décrire son travail résiduel. NON_RENSEIGNE fait exception : par définition
    on ne sait pas quels gestes restent."""
    import csv
    vues = set()
    for f in sorted((ROOT / "data" / "generics").glob("*_detail.csv")):
        with f.open(encoding="utf-8") as fh:
            vues |= {r["technologie"] for r in csv.DictReader(fh, delimiter=";")}
    manquantes = vues - set(pt.load_templates()) - {"NON_RENSEIGNE"}
    assert manquantes == set(), manquantes


def test_l_axe_de_transformation_a_ses_deux_extremites():
    """Acheter plus de transformation, c'est acheter moins de gestes.

    L'axe allait de CRU — pâte crue *achetée* — à PRET_A_SERVIR. Il lui manquait le bout
    où l'on n'achète aucune transformation : le référentiel des matières premières
    décrivait des farines et des beurres qu'aucun gabarit ne savait consommer, donc
    aucune fiche ne pouvait chiffrer un MAKE parti de la matière.

    Sans ce test, la même extrémité peut disparaître à la prochaine réécriture du fichier
    et le manque redeviendrait invisible : rien d'autre ne casse quand elle s'en va.
    """
    gabarits = pt.load_templates()
    assert "MATP" in gabarits, "aucun gabarit ne part des matières premières"
    gestes = {t: len(pt.operations_pour(t)) for t in gabarits}
    assert gestes["MATP"] > max(v for t, v in gestes.items() if t != "MATP"), gestes
    assert gestes.get("PRET_A_SERVIR") == 0, gestes


def test_les_niveaux_des_gabarits_existent():
    """Un labor_tier de gabarit absent de params rendrait incalculable toute fiche
    construite dessus — et le refus n'apparaîtrait qu'au moment du calcul du coût."""
    connus = set(pt.labor_tiers(pt.load_params()))
    assert connus, "params/establishment.json ne porte aucun niveau"
    for techno in pt.load_templates():
        for op in pt.operations_pour(techno):
            assert op["labor_tier"] in connus, (techno, op["task"], op["labor_tier"])


def test_prix_inconnu_nest_pas_compile_en_zero():
    """Un prix inconnu vaut « inconnu », jamais 0 €.

    Le coût échoue fermé (menu écarté) ; un prix à 0 échouerait ouvert — le menu serait
    retenu avec une valeur de référence et un score faux, sans aucun signal.
    """
    doc = fiche_complete()
    doc["commercial"]["sale_price_eur"] = None
    assert pt.engine_blockers(doc) == ["commercial.sale_price_eur"]


def test_dlc_vient_de_la_source_retenue():
    """La conservation est une propriété du fournisseur, pas du produit (P005).

    Deux sources de la même référence ont deux DLC. Le catalogue compilé doit porter celle
    de la source effectivement retenue, sinon la doctrine arbitre sur la DLC d'un
    fournisseur qu'on n'achète pas.
    """
    legacy = pt.canonical_to_legacy(fiche_complete())
    assert legacy["external"]["landed_cost_eur"] == 0.38   # source la moins chère
    assert legacy["external"]["shelf_life_hours"] == 96    # ...et SA durée de vie, pas 720
    assert legacy["internal"]["labor_minutes"] == 1.25     # (20 + 30) / 40, immobilisé seul


def test_champs_de_travail_perimes_sont_refuses():
    """Trois formats de saisie du travail se sont succédé. Les deux premiers doivent être
    rejetés, pas silencieusement ignorés : un montant par produit gravait le taux, et un
    `labor_minutes` sans unité valait un facteur égal à la taille du lot."""
    for perime, valeur in [("labor_cost_eur", 0.81), ("labor_minutes", 1.8),
                           ("labor_minutes_per_unit", 1.8)]:
        doc = fiche_complete()
        doc["internal_production"][perime] = valeur
        errs = pt.validate_product(doc, TAUX)
        assert any(perime in e for e in errs), (perime, errs)


def test_fiche_v1_est_refusee():
    """Format cassant : une fiche 1.0.0 est rejetée, pas mal interprétée."""
    doc = fiche_complete()
    doc["schema_version"] = "1.0.0"
    errs = pt.validate_product(doc, TAUX)
    assert any("schema_version" in e for e in errs), errs


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"OK  {name}")
