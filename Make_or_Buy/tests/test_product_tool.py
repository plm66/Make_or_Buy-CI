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
