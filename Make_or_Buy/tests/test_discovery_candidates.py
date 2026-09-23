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


def test_des013_rattache_au_catalogue_officiel():
    """DES-013 (Moelleux Chocolat Noisette Vegan) est formellement rapproché de la
    référence officielle '006107' du catalogue Traiteur de Paris, mais son allégation
    végane reste en quarantaine doctrinale car un catalogue fabricant n'est pas une
    fiche technique officielle (OFFICIAL_TECHNICAL_SHEET) au sens de product_tool.py.
    """
    des013 = next(c for c in DESSERT if c["candidate_id"] == "DES-013")
    assert des013["supplier_product_ref"] == "006107"
    assert des013["supplier_pack_units"] == 20
    assert des013["supplier_unit_weight_g"] == 90
    assert des013["catalogue_source"] == "data/supplier_products/traiteur_de_paris_catalogue_2026.json"
    assert des013["claim_status"] == "NOT_VALIDATED"
    assert "dietary.official_technical_sheet" in des013["missing_critical_fields"]


def test_lutosa_rosti_est_un_benchmark_indicatif():
    """GPO-001 (Rösti Lutosa 100g) est un benchmark public indicatif : son prix de référence
    est 0,235 €/pièce, mais sa base de taxe est UNKNOWN et son coût rendu est strictement null.
    Il ne peut donc pas prétendre être un coût rendu opérationnel.
    """
    gpo001 = next(o for o in OBSERVATIONS if o["observation_id"] == "GPO-001")
    assert gpo001["reference_price_eur_per_piece"] == 0.235
    assert gpo001["tax_basis"] == "UNKNOWN"
    assert gpo001["delivery_included"] is None
    assert gpo001["landed_cost_eur_per_piece"] is None


def test_aucun_candidat_de_recherche_nest_promu_en_produit_canonique():
    """Règle doctrinale fondamentale (consumer_rule) des jeux de découverte :
    'Do not import into canonical products, supplier master, price observations,
    or purchase authorization.'
    Aucune piste exploratoire ne doit figurer dans data/products/ tant qu'un arbitrage
    et un devis opérationnel réel n'existent pas.
    """
    fiches_canoniques = {p.stem for p in (ROOT / "data" / "products").glob("*.json")}
    for c in CANDIDATS:
        assert c["candidate_id"] not in fiches_canoniques
    for lead in SURPLUS:
        assert lead["lead_id"] not in fiches_canoniques


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
