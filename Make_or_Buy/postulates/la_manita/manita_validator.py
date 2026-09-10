#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

FAMILIES=["SNACK","COLD_DRINK","COMPLEMENT","DESSERT","HOT_DRINK"]

def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def product_cost(p):
    # Canonical preference order. Adjust adapter if Make_or_Buy exposes a stronger field.
    for path in [
        ("decision","selected_effective_cost_eur"),
        ("manita","effective_cost_eur"),
        ("internal_production","avoidable_cost_total_eur"),
        ("internal_production","material_cost_eur"),
    ]:
        cur=p
        ok=True
        for k in path:
            if not isinstance(cur,dict) or k not in cur:
                ok=False; break
            cur=cur[k]
        if ok and isinstance(cur,(int,float)):
            return float(cur)
    # Legacy catalog adapter
    if isinstance(p.get("cost_eur"),(int,float)):
        return float(p["cost_eur"])
    return None

def family_of(p):
    return p.get("product",{}).get("family") or p.get("family")

def active(p):
    status=p.get("product",{}).get("status")
    if status is None:
        status=p.get("status","ACTIVE")
    return status=="ACTIVE"

def manita_eligible(p):
    m=p.get("manita")
    if isinstance(m,dict) and "eligible" in m:
        return bool(m["eligible"])
    return True

def roles(p):
    return p.get("manita",{}).get("economic_roles",[])

def validate(catalog, config, dietary=None):
    hard=config["cost_model"]["hard_max_bundle_cost_eur"]
    envelopes=config["family_cost_envelopes"]

    pools={f:[] for f in FAMILIES}
    missing_cost=[]
    over_family=[]
    role_counts={f:{} for f in FAMILIES}

    for p in catalog:
        f=family_of(p)
        if f not in pools or not active(p) or not manita_eligible(p):
            continue

        # Minimal dietary adapter
        if dietary=="VEGAN":
            vegan=p.get("dietary",{}).get("vegan")
            if vegan is None:
                vegan=p.get("diet",{}).get("vegan")
            if vegan is not True:
                continue
        if dietary=="VEGETARIAN":
            veg=p.get("dietary",{}).get("vegetarian")
            if veg is None:
                veg=p.get("diet",{}).get("vegetarian")
            if veg is not True:
                continue

        c=product_cost(p)
        if c is None:
            missing_cost.append(p.get("product",{}).get("id") or p.get("id"))
            continue

        cap=float(envelopes[f]["hard_max_eur"])
        if c > cap + 1e-9:
            over_family.append({
                "product_id":p.get("product",{}).get("id") or p.get("id"),
                "family":f,
                "cost_eur":round(c,4),
                "family_cap_eur":cap
            })
            continue

        pools[f].append((p,c))
        for r in roles(p):
            role_counts[f][r]=role_counts[f].get(r,0)+1

    blocking=[f for f in FAMILIES if not pools[f]]
    if blocking:
        return {
            "status":"DATA_INCOMPLETE" if missing_cost else "NO_VALID_BUNDLE",
            "dietary_filter":dietary,
            "blocking_families":blocking,
            "missing_cost_products":missing_cost,
            "over_family_cap_products":over_family,
            "family_counts":{f:len(pools[f]) for f in FAMILIES}
        }

    maxima={f:max(c for _,c in pools[f]) for f in FAMILIES}
    minima={f:min(c for _,c in pools[f]) for f in FAMILIES}
    worst=sum(maxima.values())
    best=sum(minima.values())

    status="VALID_BUNDLE" if worst <= hard + 1e-9 else "CATALOG_INVALID"
    return {
        "status":status,
        "dietary_filter":dietary,
        "best_case_bundle_cost_eur":round(best,4),
        "worst_case_bundle_cost_eur":round(worst,4),
        "hard_max_bundle_cost_eur":hard,
        "headroom_eur":round(hard-worst,4),
        "family_maxima_eur":{k:round(v,4) for k,v in maxima.items()},
        "family_counts":{f:len(pools[f]) for f in FAMILIES},
        "economic_role_counts":role_counts,
        "missing_cost_products":missing_cost,
        "over_family_cap_products":over_family
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--catalog",required=True)
    ap.add_argument("--config",default="manita.config.json")
    ap.add_argument("--dietary",choices=["VEGAN","VEGETARIAN"])
    args=ap.parse_args()
    catalog=load(args.catalog)
    if isinstance(catalog,dict) and "products" in catalog:
        catalog=catalog["products"]
    result=validate(catalog,load(args.config),args.dietary)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    if result["status"] in {"CATALOG_INVALID","DATA_INCOMPLETE","NO_VALID_BUNDLE"}:
        sys.exit(2)

if __name__=="__main__":
    main()
