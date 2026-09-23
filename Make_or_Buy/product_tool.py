#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

FAMILIES={"SNACK","COLD_DRINK","GARNITURE","DESSERT","HOT_DRINK"}
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
DEFAULT_TEMPLATES=ROOT/"params"/"operation_templates.json"

# Postes de cout saisis a la main, par unite vendue. Le travail n'y figure pas: il se mesure
# par lot dans operations[], au niveau de qualification de chaque geste, et se ramene a
# l'unite par batch_size_units. Les taux vivent dans params/establishment.json, un seul endroit.
STATED_COST_FIELDS=["material_cost_eur","energy_cost_eur","packaging_cost_eur",
                    "cleaning_handling_cost_eur","expected_loss_cost_eur","other_avoidable_cost_eur"]

ANCIENNES_FICHES_INTERDITES={
    "pommes_anna_60g":"manque devis grossiste et coût rendu opérationnel",
    "moelleux_chocolat_noisette_vegan_90g":"manque devis grossiste et fiche technique officielle pour allégation végane",
    "croissant_aux_amandes_surplus_j1":"manque protocole de recette mesuré et chiffrage des coûts évitables",
}

EXPLORATOIRE_KW=("supplier_candidates","discovery","surplus_leads","benchmarks","research_only")

def research_candidate_refs(root_path=None):
    """Références fournisseurs identifiées dans les passes de recherche exploratoire.
    Ces références ne peuvent être intégrées dans le catalogue canonique sans
    preuve opérationnelle indépendante (devis vérifié, coût rendu non nul)."""
    base=Path(root_path or ROOT)
    refs=set()
    for nom in ("garniture_discovery_candidates.json","dessert_discovery_candidates.json"):
        p=base/"data"/"research"/"supplier_candidates"/nom
        if p.exists():
            try:
                data=json.loads(p.read_text(encoding="utf-8"))
                for c in data.get("candidates",[]):
                    r=c.get("supplier_product_ref")
                    if r: refs.add(str(r))
            except Exception:
                pass
    return refs

def verifier_admissibilite_sourcing(doc, refs_recherche=None):
    """Contrôle d'étanchéité entre la recherche exploratoire et le catalogue opérationnel.
    Une fiche canonique ne peut être justifiée uniquement par un jeu de données
    marqué RESEARCH_ONLY_NOT_OPERATIONALLY_VALIDATED, ni porter une référence
    fournisseur issue de la recherche sans preuve opérationnelle indépendante
    (devis vérifié, conditions d'achat et fiche technique requise)."""
    e=[]
    dq=doc.get("data_quality",{})
    sources=dq.get("sources")
    if sources is None:
        e.append("data_quality.sources manquant")
        sources=[]

    # 1. Vérification de la justification par les sources
    sources_exploratoires=[
        s for s in sources if any(kw in str(s).lower() for kw in EXPLORATOIRE_KW)
    ]
    sources_operationnelles=[
        s for s in sources if s not in sources_exploratoires
    ]
    if sources_exploratoires and not sources_operationnelles:
        e.append(
            "fiche justifiée uniquement par un jeu de données de recherche exploratoire "
            f"({', '.join(sources_exploratoires)}) sans justificatif opérationnel indépendant"
        )

    # 2. Vérification des références fournisseurs issues de la recherche
    connues=refs_recherche if refs_recherche is not None else research_candidate_refs()
    ext=doc.get("external_sourcing",{})
    for src in ext.get("sources",[]):
        ref=str(src.get("supplier_product_ref") or "")
        if ref and ref in connues:
            statut=src.get("data_status")
            cout=src.get("landed_cost_eur")
            if statut!="VERIFIED" or not isinstance(cout,(int,float)) or cout<=0:
                e.append(
                    f"source {src.get('source_id')}: référence fournisseur {ref!r} issue de la recherche "
                    f"sans preuve opérationnelle indépendante (attendu data_status='VERIFIED' et landed_cost_eur>0, "
                    f"reçu status={statut!r}, landed_cost={cout!r})"
                )
            if doc.get("dietary",{}).get("vegan") is True:
                ev=doc.get("dietary",{}).get("claim_evidence")
                if ev!="SUPPLIER_DOCUMENTED" or "dietary.official_technical_sheet" in dq.get("missing_critical_fields",[]):
                    e.append(
                        f"référence {ref!r} avec allégation vegan: fiche technique officielle (OFFICIAL_TECHNICAL_SHEET) "
                        "requise pour promotion canonique"
                    )

    # 3. Vérification des fiches internes ou dérivées de surplus
    ip=doc.get("internal_production",{})
    if ip.get("possible"):
        desc=(doc.get("product",{}).get("description") or "").lower()
        notes=(doc.get("signature",{}).get("notes") or "").lower()
        spec=(doc.get("signature",{}).get("proprietary_specification") or "").lower()
        pid=doc.get("product",{}).get("id","")
        est_surplus=any("surplus" in t or "invendu" in t for t in (desc,notes,spec,pid))
        if est_surplus or pid=="croissant_aux_amandes_surplus_j1":
            ops=ip.get("operations") or []
            mat=ip.get("material_cost_eur")
            tot=ip.get("avoidable_cost_total_eur")
            if not ops or not isinstance(mat,(int,float)) or not isinstance(tot,(int,float)):
                e.append(
                    "valorisation de surplus/interne sans protocole de recette mesuré "
                    "(operations[], material_cost_eur et avoidable_cost_total_eur requis)"
                )

    # 4. Interdiction explicite des 3 anciennes fiches tant que les justificatifs manquent
    pid=doc.get("product",{}).get("id")
    if pid in ANCIENNES_FICHES_INTERDITES:
        if pid=="pommes_anna_60g":
            sources_ext=ext.get("sources",[])
            valide=any(s.get("data_status")=="VERIFIED" and isinstance(s.get("landed_cost_eur"),(int,float)) and s.get("landed_cost_eur")>0 for s in sources_ext)
            if not valide:
                e.append(f"fiche interdite {pid}: {ANCIENNES_FICHES_INTERDITES[pid]}")
        elif pid=="moelleux_chocolat_noisette_vegan_90g":
            sources_ext=ext.get("sources",[])
            valide_cout=any(s.get("data_status")=="VERIFIED" and isinstance(s.get("landed_cost_eur"),(int,float)) and s.get("landed_cost_eur")>0 for s in sources_ext)
            valide_ft=doc.get("dietary",{}).get("claim_evidence")=="SUPPLIER_DOCUMENTED" and "dietary.official_technical_sheet" not in dq.get("missing_critical_fields",[])
            if not (valide_cout and valide_ft):
                e.append(f"fiche interdite {pid}: {ANCIENNES_FICHES_INTERDITES[pid]}")
        elif pid=="croissant_aux_amandes_surplus_j1":
            valide_ops=bool(ip.get("operations"))
            valide_cout=isinstance(ip.get("avoidable_cost_total_eur"),(int,float)) and ip.get("avoidable_cost_total_eur")>0
            if not (valide_ops and valide_cout):
                e.append(f"fiche interdite {pid}: {ANCIENNES_FICHES_INTERDITES[pid]}")

    return e

def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))

def load_params(path=None):
    p=Path(path or DEFAULT_PARAMS)
    return load(p) if p.exists() else {}

def load_templates(path=None):
    p=Path(path or DEFAULT_TEMPLATES)
    return (load(p).get("templates") or {}) if p.exists() else {}

def operations_pour(technologie, path=None):
    """Gestes qui restent en interne pour une technologie fournisseur, minutes a null.

    La technologie dit QUELS gestes restent, jamais combien de temps: on chronometre une
    fois par technologie et pas une fois par produit. Des minutes pre-remplies ici
    seraient un cout invente, ce que la doctrine interdit."""
    t=load_templates(path).get(technologie)
    return None if t is None else t["operations"]

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

def gestes_supplementaires(techno_make, techno_buy, equivalences=None, path=None):
    """Gestes que techno_make execute et que techno_buy n'execute pas, et l'inverse.

    Acheter de la transformation, c'est acheter des gestes. Partir de la farine au lieu
    d'une pate crue en ajoute six et en retire un: c'est la, et seulement la, que vit
    l'ecart de main-d'oeuvre entre faire et acheter.

    `equivalences` nomme les gestes que les deux voies executent sous des noms differents
    — l'appret du gabarit MATIERES est la pousse du CRU. Sans cette table le meme geste compterait
    deux fois et l'ecart serait surestime; avec elle, l'assimilation reste visible au lieu
    d'etre codee en dur.
    """
    eq = equivalences or {}
    mk = {o["task"]: o["labor_tier"] for o in operations_pour(techno_make, path)}
    by = {o["task"]: o["labor_tier"] for o in operations_pour(techno_buy, path)}
    en_plus = {t: n for t, n in mk.items() if eq.get(t, t) not in by}
    en_moins = {t: n for t, n in by.items() if t not in {eq.get(x, x) for x in mk}}
    return en_plus, en_moins

def minutes_avant_bascule(cout_matiere_eur, prix_achat_eur, lot_unites, gestes, params):
    """Minutes immobilisees par lot que le MAKE peut absorber avant que le BUY ne gagne.

    Ce n'est pas un arbitrage, c'est une cible de mesure. Personne n'a chronometre les
    gestes, donc `avoidable_cost_eur` est nul et `selected_cost` rend DATA_INCOMPLETE —
    correctement. Cette fonction repond a l'autre question: combien de minutes peut-on
    se permettre avant que la reponse ne bascule.

    Elle prend en entree un cout matiere et un prix d'achat, ce qui la place a un doigt
    de G002. La difference tient a ce qu'elle en fait: G002 interdit de *conclure* d'une
    comparaison matiere contre prix fournisseur. Ici on ne conclut pas, on calcule ce qui
    manque pour pouvoir conclure. Lire le resultat comme une victoire du MAKE refait
    exactement la faute.

    Un resultat negatif dit que la matiere seule depasse deja le prix d'achat: aucune
    quantite de travail gratuit ne sauve le MAKE.
    """
    if not isinstance(lot_unites, (int, float)) or lot_unites <= 0 or not gestes:
        return None
    tiers = labor_tiers(params)
    taux = [(tiers.get(n) or {}).get("cost_per_minute_eur") for n in gestes.values()]
    if not all(isinstance(t, (int, float)) and t > 0 for t in taux):
        return None
    for v in (cout_matiere_eur, prix_achat_eur):
        if not isinstance(v, (int, float)):
            return None
    # Moyenne des niveaux impliques: le lot ne dit pas comment les minutes se repartissent
    # entre les gestes. Un chronometrage geste par geste rendrait cette moyenne inutile —
    # et c'est le but, cette fonction sert avant la mesure, pas apres.
    moyen = sum(taux) / len(taux)
    return round((prix_achat_eur - cout_matiere_eur) * lot_unites / moyen, 1)

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
    e += verifier_admissibilite_sourcing(doc)
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
        # Le champ porte le cout complet evitable et rien d'autre. Il s'appelait
        # material_cost_eur et contenait deja ce total: un nom qui ment sur son contenu
        # fait qu'un lecteur du moteur reintroduit G002 de bonne foi.
        "avoidable_cost_eur":i.get("avoidable_cost_total_eur"),
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

FAMILLES_MOTEUR=["SNACK","COLD_DRINK","GARNITURE","DESSERT","HOT_DRINK"]

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

def cmd_operations(args):
    ops=operations_pour(args.technologie)
    if ops is None:
        connues=", ".join(sorted(load_templates())) or "aucune"
        print(f"technologie {args.technologie!r} sans gabarit; connues: {connues}", file=sys.stderr)
        sys.exit(1)
    print(json.dumps({"operations":ops}, ensure_ascii=False, indent=2))
    if ops:
        print(f"\n{len(ops)} gestes, minutes à chronométrer une fois pour toute la technologie "
              f"{args.technologie}.", file=sys.stderr)
    else:
        print(f"\nAucun geste interne: {args.technologie} est un BUY sans travail résiduel.",
              file=sys.stderr)

def main():
    ap=argparse.ArgumentParser(prog="product_tool")
    sp=ap.add_subparsers(required=True)
    v=sp.add_parser("validate"); v.add_argument("path"); v.set_defaults(func=cmd_validate)
    c=sp.add_parser("compile"); c.add_argument("directory"); c.add_argument("--output",default="data/catalog.generated.json"); c.set_defaults(func=cmd_compile)
    o=sp.add_parser("operations",help="Gabarit d'opérations internes pour une technologie fournisseur.")
    o.add_argument("technologie")
    o.set_defaults(func=cmd_operations)
    st=sp.add_parser("status",help="Avancement du remplissage, par famille et par fiche.")
    st.add_argument("path",nargs="?",default="data/products"); st.set_defaults(func=cmd_status)
    a=ap.parse_args(); a.func(a)
if __name__=="__main__": main()
