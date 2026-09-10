import json
from pathlib import Path
from make_or_buy.engine import compose_menus

ROOT = Path(__file__).resolve().parents[1]

def test_vegan_three_tiers():
    catalog = json.loads((ROOT/"data"/"catalog.example.json").read_text(encoding="utf-8"))
    result = compose_menus(catalog, diet="VEGAN", price_tiers=[5,7,9])
    assert len(result) == 3
    assert all(x["diet"] == "VEGAN" for x in result)
    assert all(x["menus"] for x in result)
