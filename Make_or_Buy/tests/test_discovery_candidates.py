"""Invariants des passes de sourcing GARNITURE et DESSERT.

Soixante candidats fournisseur, cinq pistes de transformation d'invendu, douze relevés de
prix publics. Aucun de ces fichiers ne décide quoi que ce soit : ce sont des pistes datées.
Ces tests protègent la seule chose qui compte à ce stade — qu'aucune piste ne prétende un
prix ou un coût qu'elle n'a pas, et qu'aucune ne désigne un fournisseur sous un nom que le
registre ignore.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _lire(*parts):
    return json.loads(ROOT.joinpath(*parts).read_text(encoding="utf-8"))


def _contenu(doc, cle):
    return doc[cle] if isinstance(doc, dict) else doc


GARNITURE = _contenu(_lire("data", "research", "supplier_candidates", "garniture_discovery_candidates.json"), "candidates")
DESSERT = _contenu(_lire("data", "research", "supplier_candidates", "dessert_discovery_candidates.json"), "candidates")
SURPLUS = _contenu(_lire("data", "research", "supplier_candidates", "dessert_internal_transformed_surplus_leads.json"), "leads")
OBSERVATIONS = [o for nom in ("garniture", "dessert")
                for o in _lire("data", "research", f"{nom}_public_benchmarks.json")["observations"]]

CANDIDATS = GARNITURE + DESSERT
FICHES = {s["supplier_id"]: s for s in _lire("data", "suppliers", "index.json")["suppliers"]}
SOURCES = {s["price_source_id"]: s for s in
           _lire("data", "supplier_price_sources", "supplier_price_sources.registry.json")["sources"]}

VOIES = {"GARNITURE": {"READY_PORTION_HEAT", "COOKED_BULK_PORTIONABLE", "DRY_HIGH_YIELD"},
         "DESSERT": {"READY_TO_SERVE", "THAW_ONLY"}}


def test_aucun_candidat_naffirme_un_cout_effectif():
    """G002 et P022 : le prix rendu n'est pas le coût effectif. Un candidat qui annonce un
    coût sans avoir chiffré sa remise en température, son portionnage et ses pertes
    fabriquerait la décision que tout le dispositif existe pour empêcher.
    """
    for c in CANDIDATS:
        composants = c["cost_components"]
        if composants.get("selected_effective_product_cost_eur") is not None:
            assert composants.get("effective_cost_status") == "COMPUTED", c["candidate_id"]
    for lead in SURPLUS:
        assert lead.get("selected_effective_product_cost_eur") is None or \
            lead.get("effective_cost_status") == "COMPUTED", lead["lead_id"]


def test_un_candidat_sans_devis_na_pas_de_prix_rendu():
    """`QUOTE_REQUIRED` désigne une piste, pas un prix. Lui attribuer un coût rendu ferait
    entrer une estimation dans un arbitrage — les soixante candidats viennent de catalogues
    dont les prix sont sous compte professionnel.
    """
    for c in CANDIDATS:
        if c.get("price_status") == "QUOTE_REQUIRED":
            assert c.get("landed_cost_eur_per_piece") is None, c["candidate_id"]
            assert c["cost_components"].get("landed_cost_eur_per_piece") is None, c["candidate_id"]


def test_chaque_candidat_pointe_vers_une_fiche_fournisseur():
    """Une piste sans fournisseur homologué ne peut pas être commandée. Le lien vers le
    supplier master est ce qui rend le vivier actionnable plutôt qu'indicatif.
    """
    for c in CANDIDATS:
        assert c.get("supplier_id") in FICHES, c["candidate_id"]


def test_un_fabricant_ne_peut_pas_porter_un_prix_rendu():
    """Sept fiches sur treize sont `MANUFACTURER_REFERENCE` / `DISTRIBUTOR_REQUIRED` :
    sourçables, pas commandables. Trente-trois des soixante candidats en viennent. Leur
    prix catalogue n'est pas un prix rendu — il suppose un distributeur qui n'est pas
    encore identifié, et le traiter comme rendu sous-estimerait la voie BUY.
    """
    for c in CANDIDATS:
        fiche = FICHES[c["supplier_id"]]
        if fiche.get("entry_status") == "MANUFACTURER_REFERENCE":
            assert c.get("landed_cost_eur_per_piece") is None, c["candidate_id"]


def test_toute_observation_cite_une_source_enregistree():
    """La livraison est arrivée avec `AJ_FOODS` et `FOODOMARKET` en majuscules, alors que
    le registre porte `aj_foods` et `foodomarket`. Deux graphies pour une entité, et plus
    aucun prix relevé ne rejoint la source qui le pratique. Rien ne l'attrapait : les
    invariants de la couche prix ne couvraient que les jobs de capture, pas les relevés.
    """
    for o in OBSERVATIONS:
        assert o["price_source_id"] in SOURCES, o["observation_id"]



def test_le_prix_piece_se_recalcule_depuis_le_colis():
    """« Ne jamais se fier au prix unitaire affiché quand l'arithmétique du colis en donne
    un autre » — `price_capture_policy`. Trois relevés portaient un prix arrondi à deux
    décimales, dont un à 0,97 € pour un calcul à 0,9656 € : un demi-centime sur une
    enveloppe DESSERT de 0,20 €, soit deux pour cent du budget de la famille.
    """
    for o in OBSERVATIONS:
        colis, unites, piece = o.get("case_price_eur"), o.get("unit_count"), o.get("price_per_piece_eur")
        if None in (colis, unites, piece) or not unites:
            continue
        assert abs(piece - colis / unites) < 1e-4, (o["observation_id"], piece, colis / unites)



def test_les_voies_declarees_appartiennent_au_vocabulaire_des_briefs():
    """Chaque voie dit quel travail interne reste à payer. Une voie inventée en cours de
    route rendrait ce travail invisible au moment de calculer le coût effectif.
    """
    for c in CANDIDATS:
        assert c["candidate_track"] in VOIES[c["family"]], (c["candidate_id"], c["candidate_track"])
    for lead in SURPLUS:
        assert lead["candidate_track"] == "TRANSFORMED_SURPLUS", lead["lead_id"]


def test_une_transformation_dinvendu_declare_son_etat_source():
    """Le validateur exige `source_state` valant DAY_OLD ou SURPLUS : c'est ce qui justifie
    que le coût du produit source n'entre pas dans le coût du dessert. Sans cet état, la
    dérivation deviendrait un moyen de faire disparaître un coût de production réel.
    """
    for lead in SURPLUS:
        assert lead.get("source_state") in ("DAY_OLD", "SURPLUS"), lead["lead_id"]


CATALOGUE = _lire("data", "supplier_products", "traiteur_de_paris_catalogue_2026.json")


def test_un_catalogue_fabricant_ne_porte_aucun_prix():
    """Traiteur de Paris est `MANUFACTURER_REFERENCE / DISTRIBUTOR_REQUIRED` : son
    catalogue publie la gamme, pas les tarifs. Soixante-dix pages ne contiennent pas un
    seul euro. Si un champ de prix y apparaissait un jour, il viendrait d'ailleurs que du
    catalogue et se ferait passer pour une donnée constatée.
    """
    fiche = FICHES[CATALOGUE["registry_supplier_id"]]
    assert fiche["entry_status"] == "MANUFACTURER_REFERENCE", fiche
    assert CATALOGUE["price_status"] == "NO_PRICE_PUBLISHED"
    interdit = re.compile(r"price|cost|eur|tarif|prix", re.I)
    for r in CATALOGUE["references"]:
        for champ in r:
            assert not interdit.search(champ), (r["supplier_product_ref"], champ)


def test_tout_candidat_rattache_pointe_vers_une_reference_reelle():
    """Le rapprochement s'est fait sur les noms, entre un intitulé relevé sur le web et
    celui du catalogue fabricant. Une référence inventée ferait passer une piste pour
    documentée alors qu'elle ne le serait pas.
    """
    connues = {r["supplier_product_ref"] for r in CATALOGUE["references"]}
    for c in DESSERT:
        if c.get("catalogue_source"):
            assert c["supplier_product_ref"] in connues, c["candidate_id"]


def test_les_donnees_reprises_du_catalogue_sont_fideles():
    """Un rapprochement qui recopie de travers vaut moins qu'une absence : il porte
    l'autorité du catalogue sans en avoir le contenu.
    """
    par_ref = {r["supplier_product_ref"]: r for r in CATALOGUE["references"]}
    for c in DESSERT:
        if not c.get("catalogue_source"):
            continue
        r = par_ref[c["supplier_product_ref"]]
        for champ_c, champ_r in (("supplier_pack_units", "pack_units"),
                                 ("supplier_unit_weight_g", "unit_weight_g")):
            if c.get(champ_c) is not None and r[champ_r] is not None:
                assert float(c[champ_c]) == float(r[champ_r]), (c["candidate_id"], champ_c)


import sys
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import product_tool as pt


def test_une_allegation_du_catalogue_declare_sa_preuve():
    """Une allégation végane sans source documentée ne vaut rien — une recette change sans
    que l'étiquette suive. Le catalogue fabricant est une pièce officielle : il doit le
    dire, pour que la preuve reste traçable jusqu'à la fiche produit.
    """
    for r in CATALOGUE["references"]:
        if r["claims"]:
            assert r["claims_evidence"] == "OFFICIAL_MANUFACTURER_CATALOGUE", r["supplier_product_ref"]


POMMES_ANNA_FIXTURE = {
    "schema_version": "2.0.0",
    "product": {
        "id": "pommes_anna_60g",
        "name": "Pommes de terre Anna 60 g",
        "family": "GARNITURE",
        "subcategory": "pommes_de_terre",
        "status": "DRAFT",
        "description": "Garniture individuelle portionnée surgelée 60 g.",
        "unit": "piece",
        "serving_size_g": 60,
        "serving_size_ml": None,
    },
    "commercial": {"sale_price_eur": 1.20, "price_status": "ESTIMATED"},
    "dietary": {"vegan": None, "vegetarian": True, "allergens": [], "claim_evidence": "NONE"},
    "signature": {"class": "STANDARDIZABLE", "signature_operations": []},
    "internal_production": {"possible": False, "cost_status": "NOT_APPLICABLE", "operations": []},
    "external_sourcing": {
        "possible": True,
        "sources": [
            {
                "source_id": "coup_de_pates_832909",
                "supplier_id": "coup_de_pates",
                "supplier_name": "Coup de Pâtes",
                "supplier_product_ref": "832909",
                "data_status": "QUOTE_REQUIRED",
                "landed_cost_eur": None,
                "pack_size_units": 40,
            }
        ],
    },
    "stock_and_conservation": {"storage_mode": "FROZEN", "after_opening_shelf_life_hours": 48},
    "decision_inputs": {"recommended_mode": "BUY"},
    "data_quality": {
        "confidence": "MEDIUM",
        "missing_critical_fields": ["external_sourcing.sources[0].landed_cost_eur", "dietary.vegan"],
        "sources": ["data/research/supplier_candidates/garniture_discovery_candidates.json"],
    },
}

MOELLEUX_VEGAN_FIXTURE = {
    "schema_version": "2.0.0",
    "product": {
        "id": "moelleux_chocolat_noisette_vegan_90g",
        "name": "Moelleux Chocolat Noisette Vegan 90 g",
        "family": "DESSERT",
        "subcategory": "moelleux_individuels",
        "status": "DRAFT",
        "description": "Moelleux individuel vegan 90 g surgelé.",
        "unit": "piece",
        "serving_size_g": 90,
        "serving_size_ml": None,
    },
    "commercial": {"sale_price_eur": 3.20, "price_status": "ESTIMATED"},
    "dietary": {
        "vegan": True,
        "vegetarian": True,
        "allergens": ["fruits_a_coque", "soja"],
        "claim_evidence": "SUPPLIER_DOCUMENTED",
    },
    "signature": {"class": "STANDARDIZABLE", "signature_operations": []},
    "internal_production": {"possible": False, "cost_status": "NOT_APPLICABLE", "operations": []},
    "external_sourcing": {
        "possible": True,
        "sources": [
            {
                "source_id": "traiteur_de_paris_006107",
                "supplier_id": "traiteur_de_paris",
                "supplier_name": "Traiteur de Paris",
                "supplier_product_ref": "006107",
                "data_status": "QUOTE_REQUIRED",
                "landed_cost_eur": None,
                "pack_size_units": 20,
            }
        ],
    },
    "stock_and_conservation": {"storage_mode": "FROZEN", "after_opening_shelf_life_hours": 120},
    "decision_inputs": {"recommended_mode": "BUY"},
    "data_quality": {
        "confidence": "HIGH",
        "missing_critical_fields": ["external_sourcing.sources[0].landed_cost_eur"],
        "sources": [
            "data/supplier_products/traiteur_de_paris_catalogue_2026.json",
            "data/research/supplier_candidates/dessert_discovery_candidates.json",
        ],
    },
}

CROISSANT_AMANDES_FIXTURE = {
    "schema_version": "2.0.0",
    "product": {
        "id": "croissant_aux_amandes_surplus_j1",
        "name": "Croissant aux amandes sur surplus J-1",
        "family": "DESSERT",
        "subcategory": "viennoiserie_transformee",
        "status": "DRAFT",
        "description": "Croissant aux amandes préparé sur surplus J-1.",
        "unit": "piece",
        "serving_size_g": 95,
        "serving_size_ml": None,
    },
    "commercial": {"sale_price_eur": 2.20, "price_status": "ESTIMATED"},
    "dietary": {
        "vegan": False,
        "vegetarian": True,
        "allergens": ["gluten", "lait", "oeufs", "fruits_a_coque"],
        "claim_evidence": "INTERNAL_RECIPE_DOCUMENTED",
    },
    "signature": {
        "class": "INHOUSE_SIGNATURE_ADVANTAGE",
        "signature_operations": ["siropage", "garnissage_amande", "cuisson"],
        "notes": "Valorisation anti-gaspillage de surplus.",
    },
    "internal_production": {
        "possible": True,
        "cost_status": "UNKNOWN",
        "material_cost_eur": None,
        "operations": [],
        "avoidable_cost_total_eur": None,
    },
    "external_sourcing": {"possible": False, "sources": []},
    "stock_and_conservation": {"storage_mode": "AMBIENT", "internal_shelf_life_hours": 24},
    "decision_inputs": {"recommended_mode": "MAKE"},
    "data_quality": {
        "confidence": "MEDIUM",
        "missing_critical_fields": ["internal_production.material_cost_eur"],
        "sources": [
            "data/research/supplier_candidates/dessert_internal_transformed_surplus_leads.json"
        ],
    },
}


def test_critere_1_chacune_des_trois_anciennes_fiches_est_rejetee():
    """Critère 1 : Chacune des trois anciennes fiches réintroduites sans preuve
    opérationnelle doit être formellement rejetée par le contrôle d'étanchéité.
    """
    errs_pommes = pt.verifier_admissibilite_sourcing(POMMES_ANNA_FIXTURE)
    assert any("832909" in e or "recherche exploratoire" in e for e in errs_pommes), errs_pommes

    errs_moelleux = pt.verifier_admissibilite_sourcing(MOELLEUX_VEGAN_FIXTURE)
    assert any("006107" in e or "recherche exploratoire" in e for e in errs_moelleux), errs_moelleux

    errs_croissant = pt.verifier_admissibilite_sourcing(CROISSANT_AMANDES_FIXTURE)
    assert any("surplus" in e or "recherche exploratoire" in e for e in errs_croissant), errs_croissant


def test_critere_2_changer_nom_fiche_ne_contourne_pas_le_controle():
    """Critère 2 : Renommer l'identifiant ou l'intitulé d'une fiche ne permet pas de
    contourner le contrôle. L'analyse inspecte le contenu (références fournisseur,
    opérations de surplus, et sources de provenance).
    """
    pommes_renommees = json.loads(json.dumps(POMMES_ANNA_FIXTURE))
    pommes_renommees["product"]["id"] = "garniture_anonyme_deluxe"
    pommes_renommees["product"]["name"] = "Garniture de pommes secrète"
    errs = pt.verifier_admissibilite_sourcing(pommes_renommees)
    assert any("832909" in e for e in errs), errs

    croissant_renomme = json.loads(json.dumps(CROISSANT_AMANDES_FIXTURE))
    croissant_renomme["product"]["id"] = "viennoiserie_recyclee"
    croissant_renomme["product"]["name"] = "Viennoiserie recyclée"
    errs_c = pt.verifier_admissibilite_sourcing(croissant_renomme)
    assert any("surplus" in e or "recherche exploratoire" in e for e in errs_c), errs_c


def test_critere_3_supprimer_sources_ne_contourne_pas_le_controle():
    """Critère 3 : Supprimer ou vider data_quality.sources ne permet pas de contourner
    le contrôle. La référence fournisseur issue de la recherche ou l'absence de recette
    mesurée bloque immédiatement la fiche.
    """
    pommes_sans_sources = json.loads(json.dumps(POMMES_ANNA_FIXTURE))
    pommes_sans_sources["data_quality"]["sources"] = []
    errs = pt.verifier_admissibilite_sourcing(pommes_sans_sources)
    assert any("832909" in e or "sources manquant" in e for e in errs), errs

    moelleux_sans_sources = json.loads(json.dumps(MOELLEUX_VEGAN_FIXTURE))
    moelleux_sans_sources["data_quality"].pop("sources", None)
    errs_m = pt.verifier_admissibilite_sourcing(moelleux_sans_sources)
    assert any("006107" in e or "sources manquant" in e for e in errs_m), errs_m


def test_critere_4_fiche_avec_justificatifs_requis_peut_etre_acceptee():
    """Critère 4 : Une fiche canonique portant une référence issue de la recherche (832909)
    ou valorisant un surplus DOIT pouvoir être acceptée si elle s'accompagne de ses
    justificatifs opérationnels réels (devis grossiste vérifié, coût rendu > 0,
    recette chronométrée et coûts complets calculés).
    """
    # 4a. Promotion légitime BUY sur Coup de Pâtes 832909
    pommes_validees = json.loads(json.dumps(POMMES_ANNA_FIXTURE))
    pommes_validees["data_quality"]["sources"] = [
        "Contrat cadre Coup de Pâtes 2026-09",
        "Bon de livraison vérifié #4412"
    ]
    pommes_validees["data_quality"]["confidence"] = "HIGH"
    pommes_validees["data_quality"]["missing_critical_fields"] = []
    pommes_validees["external_sourcing"]["sources"][0]["data_status"] = "VERIFIED"
    pommes_validees["external_sourcing"]["sources"][0]["landed_cost_eur"] = 0.285
    assert pt.verifier_admissibilite_sourcing(pommes_validees) == []

    # 4b. Promotion légitime MAKE sur croissant aux amandes
    croissant_valide = json.loads(json.dumps(CROISSANT_AMANDES_FIXTURE))
    croissant_valide["data_quality"]["sources"] = [
        "Protocole atelier Manita v1.2",
        "Mesure laboratoire 2026-09"
    ]
    croissant_valide["data_quality"]["confidence"] = "HIGH"
    croissant_valide["data_quality"]["missing_critical_fields"] = []
    croissant_valide["internal_production"]["operations"] = [
        {"task": "siropage", "active_labor_minutes_per_batch": 4, "elapsed_minutes_per_batch": 4, "labor_tier": "apprentice"},
        {"task": "dressage", "active_labor_minutes_per_batch": 6, "elapsed_minutes_per_batch": 6, "labor_tier": "apprentice"},
    ]
    croissant_valide["internal_production"]["material_cost_eur"] = 0.35
    croissant_valide["internal_production"]["avoidable_cost_total_eur"] = 0.51
    croissant_valide["internal_production"]["cost_status"] = "VERIFIED"
    croissant_valide["internal_production"]["batch_size_units"] = 20
    assert pt.verifier_admissibilite_sourcing(croissant_valide) == []


def test_critere_5_des013_quarantaine_vegan_maintenue():
    """Critère 5 : DES-013 est rattaché à sa référence officielle 006107, mais conserve
    strictement sa quarantaine végane (claim_status: NOT_VALIDATED, official_technical_sheet
    manquante) tant que la fiche technique officielle n'a pas été obtenue.
    """
    des013 = next(c for c in DESSERT if c["candidate_id"] == "DES-013")
    assert des013["supplier_product_ref"] == "006107"
    assert des013["supplier_pack_units"] == 20
    assert des013["supplier_unit_weight_g"] == 90
    assert des013["catalogue_source"] == "data/supplier_products/traiteur_de_paris_catalogue_2026.json"
    assert des013["claim_status"] == "NOT_VALIDATED"
    assert "dietary.official_technical_sheet" in des013["missing_critical_fields"]
    assert des013["dietary"]["vegan"] is None


def test_critere_6_gpo001_reste_benchmark_indicatif():
    """Critère 6 : GPO-001 (Rösti Lutosa 100g) est un benchmark public indicatif : son prix
    de référence est 0,235 €/pièce, mais sa base de taxe est UNKNOWN et son coût rendu est
    strictement null. Il ne prétend donc pas être un coût rendu validé opérationnellement.
    """
    gpo001 = next(o for o in OBSERVATIONS if o["observation_id"] == "GPO-001")
    assert gpo001["reference_price_eur_per_piece"] == 0.235
    assert gpo001["tax_basis"] == "UNKNOWN"
    assert gpo001["delivery_included"] is None
    assert gpo001["landed_cost_eur_per_piece"] is None


def test_fiches_existantes_respectent_l_etancheite_sourcing():
    """Toutes les fiches présentes dans data/products/ doivent satisfaire sans exception
    le contrôle d'étanchéité entre recherche exploratoire et catalogue canonique.
    """
    for p in (ROOT / "data" / "products").glob("*.json"):
        doc = json.loads(p.read_text(encoding="utf-8"))
        errs = pt.verifier_admissibilite_sourcing(doc)
        assert errs == [], f"{p.name} échoue au contrôle d'étanchéité: {errs}"


if __name__ == "__main__":
    for nom, fn in sorted(globals().items()):
        if nom.startswith("test_"):
            fn()
            print(f"OK  {nom}")


# Deux invariants de la livraison d'origine ne sont pas repris ici.
#
# test_toute_observation_passe_le_schema appliquait supplier_price_observation.schema.json
# aux benchmarks de recherche. Le depot a depuis separe les deux : un relevé fournisseur et
# un benchmark public n'ont ni le meme schema ni le meme statut, et les confondre est la
# frontiere que la PR #2 a justement posee. Les benchmarks se valident contre
# research_public_price_benchmark_dataset.schema.json, verifie par test_manita_discovery.
#
# test_une_observation_de_source_non_promue_ne_porte_pas_de_fournisseur verifiait qu'un
# benchmark laisse supplier_id a null. test_benchmarks_ne_sont_pas_des_observations_
# operationnelles garde la meme regle plus en amont : un benchmark ne porte aucun
# landed_cost_eur_per_piece, donc rien a attribuer a un fournisseur.
