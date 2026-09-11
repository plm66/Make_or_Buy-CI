from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from .engine import load_json, compose_menus, is_eligible, selected_cost
from .manita import compose_grille, adapte_pour_validateur
from .llm import build_context, ask_openai_compatible

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CATALOG = ROOT / "data" / "catalog.example.json"
DEFAULT_DOCTRINE = ROOT / "doctrine" / "doctrine.json"

def cmd_menu(args):
    catalog = load_json(args.catalog)
    result = compose_menus(
        catalog,
        diet=args.diet,
        price_tiers=args.tiers,
        max_food_cost_ratio=args.max_food_cost_ratio,
        top_n=args.top
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))

def cmd_manita_check(args):
    sys.path.insert(0, str(ROOT / "postulates" / "la_manita"))
    from manita_validator import validate
    catalog = adapte_pour_validateur(load_json(args.catalog), selected_cost)
    result = validate(catalog, load_json(args.config), args.dietary)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["status"] != "VALID_BUNDLE":
        raise SystemExit(2)

def cmd_manita(args):
    catalog = load_json(args.catalog)
    grille, manques = compose_grille(
        catalog, args.colonnes, lignes=args.lignes, cible=args.cible,
        tolerance=args.tolerance, champ_prix=args.champ_prix,
        eligible=lambda p: is_eligible(p, args.diet))
    print(json.dumps({"cible_eur": args.cible, "tolerance_eur": args.tolerance,
                      "lignes_demandees": args.lignes, "lignes_trouvees": len(grille),
                      "references_manquantes_par_colonne": manques,
                      "grille": grille}, ensure_ascii=False, indent=2))

def cmd_packet(args):
    context = build_context(args.doctrine, args.catalog, args.question)
    print(json.dumps(context, ensure_ascii=False, indent=2))

def cmd_ask(args):
    context = build_context(args.doctrine, args.catalog, args.question)
    print(ask_openai_compatible(context, model=args.model))

def main():
    p = argparse.ArgumentParser(prog="make-or-buy")
    sub = p.add_subparsers(required=True)

    m = sub.add_parser("menu", help="Composer des menus à partir du catalogue local.")
    m.add_argument("--diet", choices=["ANY","VEGETARIAN","VEGAN"], default="ANY")
    m.add_argument("--tiers", type=float, nargs="+", default=[5,7,9])
    m.add_argument("--max-food-cost-ratio", type=float, default=0.30)
    m.add_argument("--top", type=int, default=1)
    m.add_argument("--catalog", default=str(DEFAULT_CATALOG))
    m.set_defaults(func=cmd_menu)

    v = sub.add_parser("manita-check",
                       help="Valider un catalogue contre le postulat La Manita (pire cas, enveloppes).")
    v.add_argument("--catalog", default=str(DEFAULT_CATALOG))
    v.add_argument("--config", default=str(ROOT / "postulates" / "la_manita" / "manita.config.json"))
    v.add_argument("--dietary", choices=["VEGAN", "VEGETARIAN"])
    v.set_defaults(func=cmd_manita_check)

    g = sub.add_parser("manita", help="Composer une grille colonnes × lignes à prix cible.")
    g.add_argument("--colonnes", nargs="+",
                   default=["SNACK","GARNITURE","COLD_DRINK","DESSERT","HOT_DRINK"])
    g.add_argument("--lignes", type=int, default=10)
    g.add_argument("--cible", type=float, default=5.0)
    g.add_argument("--tolerance", type=float, default=0.5)
    g.add_argument("--champ-prix", dest="champ_prix", default="sale_price_eur")
    g.add_argument("--diet", choices=["ANY","VEGETARIAN","VEGAN"], default="ANY")
    g.add_argument("--catalog", default=str(DEFAULT_CATALOG))
    g.set_defaults(func=cmd_manita)

    q = sub.add_parser("packet", help="Créer le paquet JSON à envoyer à un LLM.")
    q.add_argument("question")
    q.add_argument("--catalog", default=str(DEFAULT_CATALOG))
    q.add_argument("--doctrine", default=str(DEFAULT_DOCTRINE))
    q.set_defaults(func=cmd_packet)

    a = sub.add_parser("ask", help="Interroger un endpoint OpenAI-compatible.")
    a.add_argument("question")
    a.add_argument("--model", default=None)
    a.add_argument("--catalog", default=str(DEFAULT_CATALOG))
    a.add_argument("--doctrine", default=str(DEFAULT_DOCTRINE))
    a.set_defaults(func=cmd_ask)

    args = p.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
