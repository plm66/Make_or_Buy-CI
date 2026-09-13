#!/usr/bin/env python3
"""Relevé de catalogue Halal Food Service — PrestaShop, sans dépendance ni navigateur.

PrestaShop 1.7 sert ses pages de catégorie en JSON sur `?ajax=1`, sans clé de webservice
et sans authentification. On n'a donc ni à gratter du HTML ni à piloter un navigateur.

    python3 halalfs_tool.py capture 577-promotions
    python3 halalfs_tool.py refresh  577-promotions

`capture` écrit un relevé daté. `refresh` le rejoue et rend le différentiel : références
apparues, disparues, et prix ayant bougé. Aucune des deux ne décide quoi que ce soit.
"""
import argparse
import json
import re
import sys
import time
import urllib.request
from datetime import date
from pathlib import Path

RACINE = Path(__file__).resolve().parent
SORTIE = RACINE / "data" / "price_observations"
BASE = "https://halalfs.com"
SOURCE = "halal_food_service"
UA = "Mozilla/5.0 (compatible; Make_or_Buy/1.0)"

# Champs repris tels quels du JSON PrestaShop. On n'en invente aucun et on n'en dérive
# aucun: la normalisation est un travail séparé, qui doit pouvoir se rejouer sur le brut.
CHAMPS = ("id_product", "reference", "name", "category_name", "price_amount",
          "regular_price_amount", "unit_price", "has_discount", "discount_percentage",
          "discount_type", "tax_name", "rate", "link", "active")


def _json(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def base_de_taxe(categorie):
    """HT ou TTC, lu dans la configuration du site — jamais déduit du prix.

    `display_prices_tax_incl` dit si les prix affichés incluent la taxe. La politique de
    capture interdit d'inférer une base de taxe ; ici le site la déclare, on la lit.
    """
    req = urllib.request.Request(f"{BASE}/{categorie}", headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        html = r.read().decode("utf-8", "replace")
    m = re.search(r'"display_prices_tax_incl"\s*:\s*(true|false)', html)
    if not m:
        return "UNKNOWN"
    return "TTC" if m.group(1) == "true" else "HT"


def capturer(categorie, pause=1.0):
    premier = _json(f"{BASE}/{categorie}?ajax=1")
    pages = premier["pagination"]["pages_count"]
    attendu = premier["pagination"]["total_items"]
    produits = list(premier["products"])
    for p in range(2, pages + 1):
        time.sleep(pause)                      # une page par seconde: on ne martèle pas
        produits += _json(f"{BASE}/{categorie}?ajax=1&page={p}")["products"]

    releves = []
    for x in produits:
        r = {c: x.get(c) for c in CHAMPS}
        r["price_source_id"] = SOURCE
        releves.append(r)

    doc = {
        "dataset": "HALALFS_CATEGORY_CAPTURE",
        "version": "1.0.0",
        "price_source_id": SOURCE,
        "category": categorie,
        "observed_at": date.today().isoformat(),
        "capture_method": "PUBLIC_WEB",
        "source_api": "PrestaShop ?ajax=1 — public, sans clé ni compte",
        "tax_basis": base_de_taxe(categorie),
        "tax_basis_evidence": "prestashop.configuration.display_prices_tax_incl",
        "pagination_declared_total": attendu,
        "pages_fetched": pages,
        "data_status": "RAW_UNMATCHED_NOT_OPERATIONALLY_VALIDATED",
        "consumer_rule": (
            "Prix catalogue affiché. Ce n'est pas un coût rendu : les conditions de "
            "livraison et le franco ne sont pas portés par cette API. Aucun rattachement "
            "à un id_matiere n'est établi ici."),
        "products": releves,
    }
    return doc


def _chemin(categorie, jour):
    return SORTIE / f"halalfs_{categorie.replace('/', '_')}_{jour}.json"


def cmd_capture(args):
    doc = capturer(args.categorie)
    SORTIE.mkdir(parents=True, exist_ok=True)
    p = _chemin(args.categorie, doc["observed_at"])
    p.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    n, attendu = len(doc["products"]), doc["pagination_declared_total"]
    print(f"{n} produits sur {attendu} annoncés, {doc['pages_fetched']} pages, "
          f"taxe {doc['tax_basis']}")
    if n != attendu:
        print(f"  ECART: {attendu - n} produit(s) annoncé(s) non ramené(s)")
    print(f"  écrit {p.relative_to(RACINE)}")
    return 0 if n == attendu else 1


def cmd_refresh(args):
    anciens = sorted(SORTIE.glob(f"halalfs_{args.categorie.replace('/', '_')}_*.json"))
    if not anciens:
        print("aucun relevé antérieur: lancer `capture` d'abord")
        return 1
    avant = json.loads(anciens[-1].read_text(encoding="utf-8"))
    apres = capturer(args.categorie)

    par_ref = lambda d: {x["reference"] or x["id_product"]: x for x in d["products"]}
    a, b = par_ref(avant), par_ref(apres)
    apparues = sorted(set(b) - set(a))
    disparues = sorted(set(a) - set(b))
    bouges = [(k, a[k]["price_amount"], b[k]["price_amount"]) for k in set(a) & set(b)
              if a[k]["price_amount"] != b[k]["price_amount"]]

    print(f"référence: {anciens[-1].name} ({avant['observed_at']}) "
          f"-> {apres['observed_at']}")
    print(f"  {len(apparues)} apparue(s), {len(disparues)} disparue(s), "
          f"{len(bouges)} prix modifié(s)")
    for k in apparues[:10]:
        print(f"    + {k:10} {b[k]['name'][:48]:48} {b[k]['price_amount']}")
    for k in disparues[:10]:
        print(f"    - {k:10} {a[k]['name'][:48]}")
    for k, va, vb in sorted(bouges, key=lambda t: -abs(t[2] - t[1]))[:10]:
        print(f"    ~ {k:10} {b[k]['name'][:40]:40} {va} -> {vb}")

    if args.write:
        SORTIE.mkdir(parents=True, exist_ok=True)
        p = _chemin(args.categorie, apres["observed_at"])
        p.write_text(json.dumps(apres, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"  écrit {p.relative_to(RACINE)}")
    else:
        print("  (relevé non écrit — ajouter --write)")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sous = ap.add_subparsers(dest="cmd", required=True)
    c = sous.add_parser("capture", help="relève une catégorie et écrit un fichier daté")
    c.add_argument("categorie", help="segment d'URL, ex. 577-promotions")
    c.set_defaults(fn=cmd_capture)
    r = sous.add_parser("refresh", help="rejoue et rend le différentiel")
    r.add_argument("categorie")
    r.add_argument("--write", action="store_true", help="écrit aussi le nouveau relevé")
    r.set_defaults(fn=cmd_refresh)
    args = ap.parse_args()
    sys.exit(args.fn(args))


if __name__ == "__main__":
    main()
