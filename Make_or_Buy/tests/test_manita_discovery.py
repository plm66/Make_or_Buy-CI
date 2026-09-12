"""Garde-fous pour les jeux de découverte Manita non opérationnels."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))

def validate_schema(value, schema, path="$"):
    if "const" in schema and value != schema["const"]:
        raise AssertionError(f"{path}: expected const {schema['const']!r}, got {value!r}")
    if "enum" in schema and value not in schema["enum"]:
        raise AssertionError(f"{path}: value outside enum")
    expected = schema.get("type")
    if expected:
        expected = expected if isinstance(expected, list) else [expected]
        ok = any((t == "null" and value is None) or (t == "string" and isinstance(value, str)) or (t == "object" and isinstance(value, dict)) or (t == "array" and isinstance(value, list)) or (t == "number" and isinstance(value, (int, float)) and not isinstance(value, bool)) or (t == "integer" and isinstance(value, int) and not isinstance(value, bool)) for t in expected)
        if not ok: raise AssertionError(f"{path}: type mismatch")
    if "oneOf" in schema:
        matches = 0
        for branch in schema["oneOf"]:
            try: validate_schema(value, branch, path)
            except AssertionError: continue
            matches += 1
        if matches != 1: raise AssertionError(f"{path}: oneOf matched {matches} branches")
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value: raise AssertionError(f"{path}: missing {key}")
        for key, child in schema.get("properties", {}).items():
            if key in value: validate_schema(value[key], child, f"{path}.{key}")
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0): raise AssertionError(f"{path}: too few items")
        if "items" in schema:
            for i, item in enumerate(value): validate_schema(item, schema["items"], f"{path}[{i}]")
    if "if" in schema:
        condition=True
        try: validate_schema(value, schema["if"], path)
        except AssertionError: condition=False
        if condition and "then" in schema: validate_schema(value, schema["then"], path)

def test_schema_refs_resolve_and_validate_without_dependency():
    pairs = [
        ("data/research/supplier_candidates/garniture_discovery_candidates.json", "schemas/research_discovery_candidate_dataset.schema.json"),
        ("data/research/supplier_candidates/dessert_discovery_candidates.json", "schemas/research_discovery_candidate_dataset.schema.json"),
        ("data/research/supplier_candidates/dessert_internal_transformed_surplus_leads.json", "schemas/research_transformed_surplus_leads_dataset.schema.json"),
        ("data/research/garniture_public_benchmarks.json", "schemas/research_public_price_benchmark_dataset.schema.json"),
        ("data/research/dessert_public_benchmarks.json", "schemas/research_public_price_benchmark_dataset.schema.json"),
    ]
    for payload, schema in pairs:
        data, schema_data = load(payload), load(schema)
        assert data["schema_ref"] == schema
        validate_schema(data, schema_data)

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
        assert data["allowed_candidate_tracks"]
        assert data["schema_ref"] == "schemas/research_discovery_candidate_dataset.schema.json"
        assert len(data["candidates"]) == 30
        ids = [c["candidate_id"] for c in data["candidates"]]
        assert len(ids) == len(set(ids))
        for c in data["candidates"]:
            assert c["supplier_id"] in suppliers
            assert c["procurement_registry_id"].startswith("SUP-")
            assert c["operational_purchase_authorized"] is False
            assert c["source_evidence"]
            assert c["cost_components"]["selected_effective_product_cost_eur"] is None
            supplier = load(f"data/suppliers/{c['supplier_id']}.json")
            assert c["supplier_entry_status"] == supplier["procurement"]["entry_status"]
            assert c["purchase_channel"] == supplier["procurement"]["purchase_channel"]
            assert c["procurement_registry_id"] == supplier["procurement"]["registry_id"]
            assert c["candidate_track"] in data["allowed_candidate_tracks"]
            assert c["landed_cost_eur_per_piece"] is None
            for evidence in c["source_evidence"]:
                assert evidence["evidence_status"] in {"EXACT_PRODUCT_PAGE", "CATEGORY_PAGE"}
            if c["dietary"].get("vegan") is True:
                assert c["dietary"].get("vegan_evidence") in {"SUPPLIER_DOCUMENTED", "INTERNAL_RECIPE_DOCUMENTED"}
            if "raw_imported_dietary_claim_unvalidated" in c:
                assert c["claim_status"] == "NOT_VALIDATED"

def test_surplus_leads_research_only():
    data = load("data/research/supplier_candidates/dessert_internal_transformed_surplus_leads.json")
    assert data["data_status"] == "RESEARCH_ONLY_NOT_OPERATIONALLY_VALIDATED"
    assert data["schema_ref"] == "schemas/research_transformed_surplus_leads_dataset.schema.json"
    assert len(data["leads"]) == 5
    for lead in data["leads"]:
        assert lead["candidate_track"] == "TRANSFORMED_SURPLUS"
        assert lead["source_state"] in {"DAY_OLD", "SURPLUS"}
        assert "source_product_id" in lead
        assert lead["selected_effective_product_cost_eur"] is None

def test_benchmarks_ne_sont_pas_des_observations_operationnelles():
    for rel in (
        "data/research/garniture_public_benchmarks.json",
        "data/research/dessert_public_benchmarks.json",
    ):
        data = load(rel)
        assert data["data_status"] == "RESEARCH_ONLY_NOT_OPERATIONALLY_VALIDATED"
        assert data["schema_ref"] == "schemas/research_public_price_benchmark_dataset.schema.json"
        assert len(data["observations"]) == 6
        ids = [o["observation_id"] for o in data["observations"]]
        assert len(ids) == len(set(ids))
        for o in data["observations"]:
            assert o["landed_cost_eur_per_piece"] is None
            assert o["source_url_status"]
    dessert = load("data/research/dessert_public_benchmarks.json")
    for o in (o for o in dessert["observations"] if o["observation_id"] in {"DPO-001", "DPO-002"}):
        assert o["source_url"] is None
        assert o["source_url_status"] == "MISMATCHED_DO_NOT_USE"


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"OK  {name}")
