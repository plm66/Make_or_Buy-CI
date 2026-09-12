"""Garde-fous pour les jeux de découverte Manita non opérationnels."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))

def test_candidates_research_only_and_not_achetables():
    supplier_rows = load("data/suppliers/index.json")["suppliers"]
    suppliers = {s["supplier_id"] for s in supplier_rows}
    suppliers_meta = {s["supplier_id"]: s for s in supplier_rows}
    for rel in (
        "data/research/supplier_candidates/garniture_discovery_candidates.json",
        "data/research/supplier_candidates/dessert_discovery_candidates.json",
    ):
        data = load(rel)
        assert data["data_status"] == "RESEARCH_ONLY_NOT_OPERATIONALLY_VALIDATED"
        assert data["schema_ref"] == "schemas/research_discovery_candidate_dataset.schema.json"
        ids = [c["candidate_id"] for c in data["candidates"]]
        assert len(ids) == len(set(ids))
        for c in data["candidates"]:
            assert c["supplier_id"] in suppliers
            assert c["procurement_registry_id"].startswith("SUP-")
            assert c["operational_purchase_authorized"] is False
            assert c["source_evidence"]
            assert c["cost_components"]["selected_effective_product_cost_eur"] is None
            assert c["supplier_entry_status"] == suppliers_meta[c["supplier_id"]]["entry_status"]
            assert c["purchase_channel"] == suppliers_meta[c["supplier_id"]]["purchase_channel"]
            for evidence in c["source_evidence"]:
                assert evidence["evidence_status"] in {"EXACT_PRODUCT_PAGE", "CATEGORY_PAGE"}
            if "raw_imported_dietary_claim_unvalidated" in c:
                assert c["claim_status"] == "NOT_VALIDATED"

def test_surplus_leads_research_only():
    data = load("data/research/supplier_candidates/dessert_internal_transformed_surplus_leads.json")
    assert data["data_status"] == "RESEARCH_ONLY_NOT_OPERATIONALLY_VALIDATED"
    assert data["schema_ref"] == "schemas/research_transformed_surplus_leads_dataset.schema.json"
    for lead in data["leads"]:
        assert lead["candidate_track"] == "TRANSFORMED_SURPLUS"
        assert lead["selected_effective_product_cost_eur"] is None

def test_benchmarks_ne_sont_pas_des_observations_operationnelles():
    for rel in (
        "data/research/garniture_public_benchmarks.json",
        "data/research/dessert_public_benchmarks.json",
    ):
        data = load(rel)
        assert data["data_status"] == "RESEARCH_ONLY_NOT_OPERATIONALLY_VALIDATED"
        assert data["schema_ref"] == "schemas/research_public_price_benchmark_dataset.schema.json"
        ids = [o["observation_id"] for o in data["observations"]]
        assert len(ids) == len(set(ids))
        for o in data["observations"]:
            assert o["landed_cost_eur_per_piece"] is None
            assert o["source_url_status"]
    dessert = load("data/research/dessert_public_benchmarks.json")
    for o in dessert["observations"][:2]:
        assert o["source_url"] is None
        assert o["source_url_status"] == "MISMATCHED_DO_NOT_USE"


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"OK  {name}")
