#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

VALIDATOR_VERSION="1.6.0"

# Les familles sont declarees par le postulat. Les recopier ici en dur les dupliquerait
# hors de leur source, ce que P006 refuse pour la donnee produit et qui vaut autant pour
# la structure. Le litteral ne sert que de repli si le postulat n'est pas a cote.
FAMILIES_FALLBACK=["SNACK","COLD_DRINK","COMPLEMENT","DESSERT","HOT_DRINK"]

def families(postulate_path=None):
    p=Path(postulate_path or Path(__file__).resolve().parent/"la_manita.postulate.json")
    if not p.exists():
        return list(FAMILIES_FALLBACK)
    return [f["id"] for f in json.loads(p.read_text(encoding="utf-8"))["families"] if f.get("required")]

FAMILIES=families()

def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def _operations_cost(ops, tiers, batch):
    """Cout des gestes d'un lot ramene a l'unite, ou None si une donnee manque."""
    if not ops:
        return 0.0
    if not isinstance(batch,(int,float)) or batch<=0:
        return None
    total=0.0
    for op in ops:
        rate=((tiers or {}).get(op.get("labor_tier")) or {}).get("cost_per_minute_eur")
        minutes=op.get("active_labor_minutes_per_batch")
        if not isinstance(rate,(int,float)) or not isinstance(minutes,(int,float)):
            return None
        total+=minutes*rate
    return total/batch

def serving_unit_cost(p, base_cost, tiers=None):
    """(cout de l'unite Manita, motif d'echec) selon P014.

    AS_IS               le produit canonique tel quel
    PORTION             base x portion_ratio, plus les gestes de portionnage
    TRANSFORMED_SURPLUS le cout du produit source n'entre PAS: il n'est pas evitable en
                        renoncant a la transformation. Seuls les couts propres a la fiche
                        — matieres ajoutees et gestes — sont comptes, et ils sont deja
                        dans base_cost puisque la fiche EST le produit transforme.
    """
    su=(p.get("manita") or {}).get("serving_unit")
    if not su:
        return base_cost, None
    fige=su.get("effective_cost_eur")
    if isinstance(fige,(int,float)):
        return float(fige), None

    derivation=su.get("derivation")
    batch=(p.get("internal_production") or {}).get("batch_size_units")
    extra=_operations_cost(su.get("additional_operations"), tiers, batch)

    if derivation in (None,"AS_IS"):
        return base_cost, None
    if derivation=="PORTION":
        ratio=su.get("portion_ratio")
        if not isinstance(ratio,(int,float)) or not 0<ratio<=1:
            return None, "portion_ratio manquant ou hors ]0,1]"
        if base_cost is None:
            return None, "cout canonique inconnu, portion incalculable"
        if extra is None:
            return None, "gestes de portionnage non chiffrables (taux ou taille de lot)"
        return base_cost*ratio+extra, None
    if derivation=="TRANSFORMED_SURPLUS":
        if not su.get("source_product_id"):
            return None, "source_product_id obligatoire pour une transformation d'invendu"
        if su.get("source_state") not in ("DAY_OLD","SURPLUS"):
            return None, "source_state doit valoir DAY_OLD ou SURPLUS"
        if base_cost is None:
            return None, "couts propres a la transformation inconnus"
        # Contrat unique: la fiche EST le produit transforme, donc son avoidable_cost_total
        # porte deja matieres ajoutees, travail, energie et emballage de la transformation.
        # Y ajouter additional_operations comptait le travail deux fois.
        if su.get("additional_operations"):
            return None, ("additional_operations interdit en TRANSFORMED_SURPLUS: le coût "
                          "évitable de la fiche porte déjà la transformation, l'ajouter "
                          "compterait le travail deux fois")
        return base_cost, None
    return None, f"derivation inconnue: {derivation!r}"

def product_cost(p):
    # Canonical preference order. Adjust adapter if Make_or_Buy exposes a stronger field.
    for path in [
        ("decision","selected_effective_cost_eur"),
        ("manita","serving_unit","effective_cost_eur"),
        ("internal_production","avoidable_cost_total_eur"),
    ]:
        cur=p
        ok=True
        for k in path:
            if not isinstance(cur,dict) or k not in cur:
                ok=False; break
            cur=cur[k]
        if ok and isinstance(cur,(int,float)):
            return float(cur)
    # Un produit d'achat pur n'a pas de production interne: son cout est le prix rendu de
    # la source retenue. Sans cette branche, tout BUY ressortait DATA_INCOMPLETE alors que
    # son cout etait au dossier — et une Manita achete la plupart de ses colonnes.
    # Un BUY vaut le prix rendu de la source RETENUE. Prendre le minimum de toutes les
    # offres etait dangereux: le moins cher peut etre indisponible, hors zone, ou porter un
    # minimum de commande incompatible. Le minimum reste une metrique d'optimisation
    # (best_available_supplier_cost), jamais le cout comptable de la reference.
    sources=(p.get("external_sourcing") or {}).get("sources") or []
    retenues=[s for s in sources if s.get("selected") is True
              and isinstance(s.get("landed_cost_eur"),(int,float))]
    if len(retenues)==1:
        return float(retenues[0]["landed_cost_eur"])
    if len(retenues)>1:
        return None   # plusieurs sources retenues: ambigu, donc DATA_INCOMPLETE

    # Plus de repli sur internal_production.material_cost_eur. La config exige le
    # SELECTED_EFFECTIVE_PRODUCT_COST et interdit le coût matière quand un coût plus
    # complet existe; retomber dessus quand il manque revenait a fabriquer une decision
    # economique a partir d'un chiffre que la doctrine refuse (G002). L'absence rend None,
    # donc DATA_INCOMPLETE.

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

def validate(catalog, config, dietary=None, labor_tiers=None, daily_bundles=None,
             apply_family_caps=True):
    hard=config["cost_model"]["hard_max_bundle_cost_eur"]
    envelopes=config["family_cost_envelopes"]
    # 1.3.0: le plafond absolu par article est retire, redondant avec les enveloppes.
    # Pour FULL_MATRIX la regle est simplement product_cost <= hard_cap[family].

    pools={f:[] for f in FAMILIES}
    missing_cost=[]
    over_family=[]
    unresolved=[]
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

        c, motif = serving_unit_cost(p, product_cost(p), labor_tiers)
        if motif:
            unresolved.append({"product_id":p.get("product",{}).get("id") or p.get("id"),
                               "family":f, "reason":motif})
            continue
        if c is None:
            missing_cost.append(p.get("product",{}).get("id") or p.get("id"))
            continue

        cap=float(envelopes[f]["hard_max_eur"])
        # P016: M_f se recalcule a chaque modification du catalogue. Filtrer sur d'anciens
        # plafonds avant de recalculer les maxima empeche le budget de se recalibrer — les
        # references qui justifieraient une autre allocation sont exclues d'avance.
        # apply_family_caps=False est le mode CONCEPTION: il rend les maxima reels.
        if apply_family_caps and c > cap + 1e-9:
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
    result={
        "validator_version":VALIDATOR_VERSION,
        "status":None,
        "dietary_filter":dietary,
        "blocking_families":blocking,
        "best_case_bundle_cost_eur":None,
        "worst_case_bundle_cost_eur":None,
        "expected_bundle_cost_eur":None,
        "hard_max_bundle_cost_eur":hard,
        "headroom_eur":None,
        "family_maxima_eur":{},
        "family_counts":{f:len(pools[f]) for f in FAMILIES},
        "economic_role_counts":role_counts,
        "missing_cost_products":missing_cost,
        "over_family_cap_products":over_family,
        "admission_budget_eur":None,
        "free_budget_eur":None,
        "overrun_attributable_to":[],
        "serving_unit_unresolved":unresolved,
        "daily_bundles":daily_bundles,
        "expected_cost_usable":None,
        "family_caps_applied":apply_family_caps,
        "required_envelope_vector_eur":None,
        "checks_not_implemented":[
            "all_exposed_products_active_or_substitutable",
            "dynamic_slots_resolvable",
            "attachment_offset_measured_or_absent",
            "economic_role_portfolio_sufficient"
        ]
    }
    if blocking:
        result["status"]="DATA_INCOMPLETE" if missing_cost else "NO_VALID_BUNDLE"
        return result

    maxima={f:max(c for _,c in pools[f]) for f in FAMILIES}
    minima={f:min(c for _,c in pools[f]) for f in FAMILIES}
    worst=sum(maxima.values())
    best=sum(minima.values())
    # P013 revise en 1.4.0: les enveloppes familiales garantissent elles-memes le pire cas,
    # puisque leur somme ne depasse pas le plafond. L'admission reste donc adossee au pire
    # cas; l'esperance mesure la performance probable et ne decide de rien. Elle n'est
    # exploitable qu'au-dessus du volume journalier minimal — en dessous, la moyenne d'une
    # journee n'est pas une mesure.
    expected=sum(sum(c for _,c in pools[f])/len(pools[f]) for f in FAMILIES)
    volume_min=(config.get("expected_value_model") or {}).get("min_daily_bundles_for_averaging")
    usable=None if daily_bundles is None or volume_min is None else daily_bundles>=volume_min

    # P016: M_f est le max des references ADMISES; le budget d'admission est leur somme,
    # recalculee a chaque modification du catalogue. Un depassement doit nommer les
    # references responsables, pas renvoyer a une enveloppe theorique.
    budget=worst
    libre=round(hard-budget,4)
    attribue=[]
    if budget > hard + 1e-9:
        for f in sorted(FAMILIES, key=lambda x: maxima[x], reverse=True):
            porteur=max(pools[f], key=lambda t: t[1])[0]
            attribue.append({
                "family":f,
                "product_id":porteur.get("product",{}).get("id") or porteur.get("id"),
                "cost_eur":round(maxima[f],4),
                "family_cap_eur":float(envelopes[f]["hard_max_eur"]),
                "budget_freed_if_removed_eur":round(
                    maxima[f]-max([c for _,c in pools[f] if c < maxima[f]] or [0.0]),4)
            })

    result.update({
        "status":"VALID_BUNDLE" if worst <= hard + 1e-9 else "CATALOG_INVALID",
        "expected_cost_usable":usable,
        "expected_vs_target_eur":round(expected-(config["cost_model"]["target_bundle_cost_eur"]),4),
        "admission_budget_eur":round(budget,4),
        "required_envelope_vector_eur":{k:round(v,4) for k,v in maxima.items()},
        "free_budget_eur":libre,
        "overrun_attributable_to":attribue,
        "best_case_bundle_cost_eur":round(best,4),
        "worst_case_bundle_cost_eur":round(worst,4),
        "expected_bundle_cost_eur":round(expected,4),
        "headroom_eur":round(hard-expected,4),
        "family_maxima_eur":{k:round(v,4) for k,v in maxima.items()}
    })
    return result

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
