#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

FAMILIES={"SNACK","COLD_DRINK","COMPLEMENT","DESSERT","HOT_DRINK"}
CLASSES={"STANDARDIZABLE","SUPPLIER_SUPERIOR","INHOUSE_SIGNATURE_ADVANTAGE","HYBRID_SIGNATURE"}
MODES={"MAKE","BUY","HYBRID","UNDECIDED"}

# Liste blanche, pas liste noire: la version precedente rejetait NONE et NOT_APPLICABLE,
# donc PARTIAL passait — et toute valeur future non prevue serait passee aussi. Une
# allegation vegan part en vitrine; c'est le seul controle du systeme dont l'erreur
# sort de l'ecran. La doctrine (traceability_requirements.vegan_products) demande une
# source capable de documenter composition, changements de recette et allergenes:
# une preuve partielle ne repond pas a ca.
PREUVES_VEGAN_SUFFISANTES={"SUPPLIER_DOCUMENTED","INTERNAL_RECIPE_DOCUMENTED"}

# Traduction du vocabulaire de preuve des leads fournisseurs (supplier_product.schema.json)
# vers celui de la fiche. Le critere qui tranche est celui que la doctrine nomme en premier
# dans traceability_requirements.vegan_products: la source doit pouvoir documenter les
# CHANGEMENTS DE RECETTE. Une fiche technique porte une version et une procedure d'alerte;
# une page produit et une mention d'emballage disent l'etat du jour et rien de l'apres.
EQUIVALENCE_PREUVES={
    "OFFICIAL_TECHNICAL_SHEET":"SUPPLIER_DOCUMENTED",
    "OFFICIAL_PRODUCT_PAGE":"PARTIAL",
    "LABEL":"PARTIAL",
    "NONE":"NONE",
    "UNKNOWN":"NONE",
}

def preuve_fiche(preuve_lead):
    """Preuve fournisseur traduite dans le vocabulaire de la fiche produit.
    Une valeur inconnue vaut NONE: une preuve non reconnue n'en est pas une."""
    return EQUIVALENCE_PREUVES.get(preuve_lead,"NONE")
SCHEMA_VERSION="2.0.0"
ROOT=Path(__file__).resolve().parent
DEFAULT_PARAMS=ROOT/"params"/"establishment.json"

# Postes de cout saisis a la main, par unite vendue. Le travail n'y figure pas: il se mesure
# par lot dans operations[], au niveau de qualification de chaque geste, et se ramene a
# l'unite par batch_size_units. Les taux vivent dans params/establishment.json, un seul endroit.
STATED_COST_FIELDS=["material_cost_eur","energy_cost_eur","packaging_cost_eur",
                    "cleaning_handling_cost_eur","expected_loss_cost_eur","other_avoidable_cost_eur"]

def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))

def load_params(path=None):
    p=Path(path or DEFAULT_PARAMS)
    return load(p) if p.exists() else {}

def labor_tiers(params):
    return ((params.get("labor") or {}).get("tiers")) or {}

def labor_cost(internal, params):
    """Cout main-d'oeuvre evitable par unite vendue, ou None si une donnee manque.

    Somme des gestes du lot, chacun valorise a son propre niveau de qualification,
    puis divise par la taille du lot. Seul le temps immobilise est facture: une infusion
    de 30 min surveillee en 1 min coute 1 min."""
    ops=internal.get("operations")
    batch=internal.get("batch_size_units")
    if not ops or not isinstance(batch,(int,float)) or batch<=0:
        return None
    tiers=labor_tiers(params)
    total=0.0
    for op in ops:
        rate=(tiers.get(op.get("labor_tier")) or {}).get("cost_per_minute_eur")
        minutes=op.get("active_labor_minutes_per_batch")
        if not isinstance(rate,(int,float)) or not isinstance(minutes,(int,float)):
            return None
        total+=minutes*rate
    return round(total/batch,4)

def validate_operations(internal, params):
    e=[]
    ops=internal.get("operations")
    if not ops: return e
    # Un lot pas encore mesure est une ignorance legitime: labor_cost rend None, et le
    # controle cost_status VERIFIED/ESTIMATED refusera un cout annonce mais incalculable.
    # Seule une valeur presente et absurde est une erreur ici.
    batch=internal.get("batch_size_units")
    if batch is not None and (not isinstance(batch,(int,float)) or batch<=0):
        e.append(f"batch_size_units={batch!r} invalide: nombre > 0, c'est le diviseur vers l'unite")
    connus=labor_tiers(params)
    for n,op in enumerate(ops):
        ref=f"operations[{n}]" + (f" ({op['task']})" if op.get("task") else "")
        if not op.get("task"): e.append(f"{ref}: task obligatoire")
        act=op.get("active_labor_minutes_per_batch")
        if not isinstance(act,(int,float)) or act<0:
            e.append(f"{ref}: active_labor_minutes_per_batch obligatoire, >= 0")
        tier=op.get("labor_tier")
        if tier not in connus:
            e.append(f"{ref}: labor_tier {tier!r} inconnu; disponibles: {', '.join(sorted(connus)) or 'aucun'}")
        el=op.get("elapsed_minutes_per_batch")
        if isinstance(el,(int,float)) and isinstance(act,(int,float)) and el<act:
            e.append(f"{ref}: elapsed_minutes_per_batch={el} < active_labor_minutes_per_batch={act}; "
                     "le temps ecoule ne peut pas etre inferieur au temps immobilise")
    return e

def active_minutes_per_unit(internal):
    """Minutes immobilisees par unite, tous niveaux confondus, pour le format legacy."""
    ops=internal.get("operations"); batch=internal.get("batch_size_units")
    if not ops or not isinstance(batch,(int,float)) or batch<=0: return None
    mins=[op.get("active_labor_minutes_per_batch") for op in ops]
    if not all(isinstance(m,(int,float)) for m in mins): return None
    return round(sum(mins)/batch,4)

def operations_summary(internal):
    """(minutes immobilisees, minutes ecoulees) du lot, ou None si non renseigne.
    L'ecart des deux est la capacite liberee au sens de P004: du temps qualifie
    disponible pendant qu'une pate leve ou qu'une infusion repose."""
    ops=internal.get("operations")
    if not ops: return None
    act=[op.get("active_labor_minutes_per_batch") for op in ops]
    if not all(isinstance(m,(int,float)) for m in act): return None
    ela=[op.get("elapsed_minutes_per_batch") if isinstance(op.get("elapsed_minutes_per_batch"),(int,float))
         else op.get("active_labor_minutes_per_batch") for op in ops]
    return round(sum(act),4), round(sum(ela),4)

def engine_blockers(doc):
    """Champs sans lesquels la compilation inventerait un chiffre au lieu de constater une absence.
    Le cout n'y figure pas: il echoue deja ferme (selected_cost rend None, le menu est ecarte)."""
    b=[]
    if doc["commercial"].get("sale_price_eur") is None: b.append("commercial.sale_price_eur")
    if doc["signature"].get("customer_value_score") is None: b.append("signature.customer_value_score")
    return b

def validate_product(doc, params=None):
    e=[]
    params=params or {}
    for section in ["schema_version","product","commercial","dietary","signature","internal_production","external_sourcing","stock_and_conservation","decision_inputs","data_quality"]:
        if section not in doc: e.append(f"section manquante: {section}")
    if e: return e
    if doc["schema_version"]!=SCHEMA_VERSION: e.append(f"schema_version doit valoir {SCHEMA_VERSION}")
    p=doc["product"]
    if p.get("family") not in FAMILIES: e.append("product.family invalide")
    if not p.get("id"): e.append("product.id obligatoire")
    s=doc["signature"]
    if s.get("class") not in CLASSES: e.append("signature.class invalide")
    d=doc["decision_inputs"]
    if d.get("recommended_mode") not in MODES: e.append("decision_inputs.recommended_mode invalide")

    # Logical checks
    i=doc["internal_production"]
    x=doc["external_sourcing"]
    if not i.get("possible") and d.get("recommended_mode")=="MAKE":
        e.append("incohérence: MAKE alors que internal_production.possible=false")
    if not x.get("possible") and d.get("recommended_mode")=="BUY":
        e.append("incohérence: BUY alors que external_sourcing.possible=false")
    if s.get("class")=="HYBRID_SIGNATURE" and not s.get("signature_operations"):
        e.append("un HYBRID_SIGNATURE doit documenter signature_operations")

    # Recontrole du cout complet evitable. La main-d'oeuvre vient du taux d'etablissement,
    # donc une revision de salaire perime les totaux de toutes les fiches et les fait
    # ressortir ici: c'est G006 ("reevaluer quand les salaires changent") rendu mecanique.
    for perime,remplacant in [("labor_cost_eur","operations[] + params.labor.tiers"),
                              ("labor_minutes","operations[]"),
                              ("labor_minutes_per_unit","operations[]")]:
        if perime in i: e.append(f"{perime} n'est plus saisi: remplace par {remplacant}")
    e+=validate_operations(i,params)
    stated_vals=[i.get(k) for k in STATED_COST_FIELDS]
    lab=labor_cost(i,params)
    if lab is not None and all(isinstance(v,(int,float)) for v in stated_vals):
        calc=round(sum(stated_vals)+lab,4)
        stated=i.get("avoidable_cost_total_eur")
        if stated is None:
            e.append(f"avoidable_cost_total_eur manquant; total calculable={calc}")
        elif abs(stated-calc)>0.01:
            e.append(f"avoidable_cost_total_eur={stated} incohérent; calcul={calc} "
                     f"(travail {lab} €/unité sur {len(i.get('operations') or [])} opérations "
                     f"pour un lot de {i.get('batch_size_units')})")
    elif i.get("cost_status") in {"VERIFIED","ESTIMATED"}:
        # Un cout annonce verifie ou estime doit etre recalculable, sinon le statut ment.
        manque=[k for k in STATED_COST_FIELDS if not isinstance(i.get(k),(int,float))]
        if lab is None: manque.append("operations[], batch_size_units ou les taux params.labor.tiers")
        e.append(f"cost_status={i.get('cost_status')} mais total non recalculable; manque: {', '.join(manque)}")

    # Vegan claim evidence
    diet=doc["dietary"]
    if diet.get("vegan") is True and diet.get("claim_evidence") not in PREUVES_VEGAN_SUFFISANTES:
        e.append(f"allégation vegan avec claim_evidence={diet.get('claim_evidence')!r}: "
                 f"preuve insuffisante, attendu {' ou '.join(sorted(PREUVES_VEGAN_SUFFISANTES))}")

    # Missing fields must be explicit when confidence is not HIGH
    dq=doc["data_quality"]
    if dq.get("confidence")!="HIGH" and not dq.get("missing_critical_fields"):
        e.append("confidence LOW/MEDIUM exige missing_critical_fields explicite")
    return e

def canonical_to_legacy(doc):
    i=doc["internal_production"]; ext=doc["external_sourcing"]
    best=None
    sources=ext.get("sources",[])
    valid=[s for s in sources if isinstance(s.get("landed_cost_eur"),(int,float))]
    if valid: best=min(valid,key=lambda s:s["landed_cost_eur"])
    cons=doc["stock_and_conservation"]
    return {
      "id":doc["product"]["id"],
      "name":doc["product"]["name"],
      "family":doc["product"]["family"],
      "diet":{
        "vegan":doc["dietary"].get("vegan"),
        "vegetarian":doc["dietary"].get("vegetarian"),
        "allergens":doc["dietary"].get("allergens",[])
      },
      "sale_price_eur":doc["commercial"]["sale_price_eur"],
      "internal":{
        "possible":i.get("possible",False),
        "material_cost_eur":i.get("avoidable_cost_total_eur") if i.get("avoidable_cost_total_eur") is not None else i.get("material_cost_eur"),
        "labor_minutes":active_minutes_per_unit(i),
        "shelf_life_hours":cons.get("internal_shelf_life_hours"),
        "traceability_score":None
      },
      "external":{
        "possible":ext.get("possible",False),
        "landed_cost_eur":best.get("landed_cost_eur") if best else None,
        "shelf_life_hours":best.get("shelf_life_hours") if best else None,
        "traceability_score":best.get("traceability_score") if best else None,
        "supplier_quality_score":best.get("quality_score") if best else None
      },
      "signature":{
        "class":doc["signature"]["class"],
        "customer_value_score":doc["signature"]["customer_value_score"],
        "notes":doc["signature"].get("notes") or ""
      }
    }

def cmd_validate(args):
    files=[]
    p=Path(args.path)
    if p.is_dir(): files=sorted(p.glob("*.json"))
    else: files=[p]
    params=load_params()
    failed=False
    for f in files:
        doc=load(f); errors=validate_product(doc,params)
        if errors:
            failed=True; print(f"INVALID {f}")
            for e in errors: print(" -",e)
        else: print(f"VALID   {f}")
    if failed: sys.exit(1)

def cmd_compile(args):
    p=Path(args.directory)
    params=load_params()
    out=[]; failures=[]; skipped=[]
    for f in sorted(p.glob("*.json")):
        doc=load(f); errors=validate_product(doc,params)
        if errors:
            failures.append((f,errors)); continue
        if doc["product"].get("status")!="ACTIVE":
            skipped.append((f,f"status={doc['product'].get('status')}")); continue
        blockers=engine_blockers(doc)
        if blockers:
            skipped.append((f,"inconnu: "+", ".join(blockers))); continue
        out.append(canonical_to_legacy(doc))
    if failures:
        for f,errs in failures:
            print(f"INVALID {f}", file=sys.stderr)
            for e in errs: print(" -",e,file=sys.stderr)
        sys.exit(1)
    for f,reason in skipped:
        print(f"IGNORE  {f} — {reason}", file=sys.stderr)
    Path(args.output).write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"{len(out)} produits compilés, {len(skipped)} ignorés -> {args.output}")

FAMILLES_MOTEUR=["SNACK","COLD_DRINK","COMPLEMENT","DESSERT","HOT_DRINK"]

def fiche_status(doc, params):
    """(etat, details) d'une fiche: INVALIDE, INCOMPLET ou PRET pour le moteur."""
    errors=validate_product(doc,params)
    if errors: return "INVALIDE", errors
    blockers=engine_blockers(doc)
    if doc["product"].get("status")!="ACTIVE":
        return "INCOMPLET", [f"status={doc['product'].get('status')}"]
    if blockers: return "INCOMPLET", [f"{b} inconnu" for b in blockers]
    return "PRET", []

def cmd_status(args):
    p=Path(args.path)
    params=load_params()
    files=sorted(p.glob("*.json")) if p.is_dir() else [p]
    if not files:
        print(f"aucune fiche dans {p}"); return

    lignes=[]
    for f in files:
        doc=load(f)
        etat,details=fiche_status(doc,params)
        lignes.append((doc,etat,details,f))

    print(f"{'FAMILLE':14} {'PRÊTES':>7}  FICHES")
    par_famille={}
    for doc,etat,_,_ in lignes:
        par_famille.setdefault(doc["product"].get("family"),[]).append((doc,etat))
    for fam in FAMILLES_MOTEUR:
        fiches=par_famille.get(fam,[])
        prets=sum(1 for _,e in fiches if e=="PRET")
        noms=", ".join(d["product"]["id"] for d,_ in fiches) or "—"
        print(f"{fam:14} {prets:>3}/{len(fiches):<3}  {noms}")
    inconnues=set(par_famille)-set(FAMILLES_MOTEUR)
    for fam in sorted(inconnues):
        print(f"{str(fam):14} {'?':>7}  famille hors moteur")

    manquantes=[f for f in FAMILLES_MOTEUR if not par_famille.get(f)]
    if manquantes:
        print(f"\nLe moteur compose un menu par famille: {len(manquantes)} sans aucune fiche "
              f"({', '.join(manquantes)}). Aucun menu possible tant qu'il en manque une.")

    for doc,etat,details,f in lignes:
        pr=doc["product"]
        print(f"\n{pr['id']:28} {pr.get('family',''):12} {etat}")
        for d in details: print(f"  - {d}")
        for champ in doc["data_quality"].get("missing_critical_fields") or []:
            print(f"  · à mesurer: {champ}")
        i=doc["internal_production"]
        somme=operations_summary(i)
        if somme:
            act,ela=somme
            print(f"  travail: {act} min immobilisées / {ela} min écoulées "
                  f"-> {round(ela-act,4)} min de capacité libérée par lot")
            cout=labor_cost(i,params)
            batch=i.get("batch_size_units")
            print(f"  coût du travail: {cout} €/unité (lot de {batch})" if cout is not None
                  else "  coût du travail: incalculable (lot non mesuré ou taux manquant)")

def main():
    ap=argparse.ArgumentParser(prog="product_tool")
    sp=ap.add_subparsers(required=True)
    v=sp.add_parser("validate"); v.add_argument("path"); v.set_defaults(func=cmd_validate)
    c=sp.add_parser("compile"); c.add_argument("directory"); c.add_argument("--output",default="data/catalog.generated.json"); c.set_defaults(func=cmd_compile)
    st=sp.add_parser("status",help="Avancement du remplissage, par famille et par fiche.")
    st.add_argument("path",nargs="?",default="data/products"); st.set_defaults(func=cmd_status)
    a=ap.parse_args(); a.func(a)
if __name__=="__main__": main()
