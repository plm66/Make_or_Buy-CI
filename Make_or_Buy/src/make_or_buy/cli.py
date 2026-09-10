from __future__ import annotations
import argparse, json
from pathlib import Path
from .engine import load_json, compose_menus, is_eligible
from .manita import compose_grille
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

    g = sub.add_parser("manita", help="Composer une grille colonnes × lignes à prix cible.")
    g.add_argument("--colonnes", nargs="+",
                   default=["SNACK","COMPLEMENT","COLD_DRINK","DESSERT","HOT_DRINK"])
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
