#!/usr/bin/env python3
"""Dérive des prix payés, même article METRO, d'une facture à l'autre.

Trois comparaisons de prix existent dans ce dépôt, et les mélanger est la faute de la
maison. Celle-ci est la seule qui ne dépende d'aucune source externe : elle compare ce que
nous avons payé à ce que nous avons payé. Elle ne dit rien de ce que coûte le marché, rien
de ce qu'un fournisseur annonce, et rien du cout rendu : METRO est un cash & carry, le
montant facture est le cout au depot, sans enlevement.

La regle tenue ici est unique : pas de chiffre sans alignement declare. Le prix unitaire
imprime vaut pour un conditionnement precis. Si le colisage ou le poids facture ont bouge
entre deux factures, le prix unitaire ne mesure plus la meme chose, et la sortie porte
UNIT_GAP au lieu d'un delta qui se lirait comme une baisse.

Usage: python3 comparaison_factures.py derive [--article 2422798] [--top 10] [--write]
"""
import json
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent
RELEVE = RACINE / "data/price_observations/metro_factures_2026-09-11.json"
RAPPORT = RACINE / "data/price_observations/metro_derive"

ALIGNED = "ALIGNED"
UNIT_GAP = "UNIT_GAP"
PROMO_EXCLUDED = "PROMO_EXCLUDED"

# Un prix imprime est un tarif, pas toujours le montant paye : la remise de volume vit sur
# une autre ligne et `prix_unitaire_paye` ne vaut que si elle a ete lue. On le preferera
# toujours quand il existe, et on nomme le champ employe.
CHAMPS_PRIX = ("prix_unitaire_paye", "prix_unitaire_ht")


def _prix(ligne):
    for champ in CHAMPS_PRIX:
        if ligne.get(champ) is not None:
            return ligne[champ], champ
    return None, None


def _base(ligne):
    """Ce qui donne son sens au prix unitaire : le conditionnement facture."""
    return (ligne.get("colisage"), ligne.get("poids_facture_kg"))


def comparer(a, b):
    """Comparaison de deux observations du meme article, la plus ancienne en premier.

    La promotion est testee avant le conditionnement : une ligne en promotion ne porte pas
    le tarif, quelle que soit sa base, et le statut doit le dire avant toute autre chose.
    """
    prix_a, champ_a = _prix(a)
    prix_b, champ_b = _prix(b)
    statut, delta, pourcentage = ALIGNED, None, None

    if a.get("promotion") or b.get("promotion"):
        statut = PROMO_EXCLUDED
    elif _base(a) != _base(b):
        statut = UNIT_GAP
    elif prix_a is None or prix_b is None:
        statut = UNIT_GAP
    else:
        delta = round(prix_b - prix_a, 4)
        pourcentage = round(100 * delta / prix_a, 1) if prix_a else None

    comparaison = {
        "article": a["article"],
        "designation": a.get("designation"),
        "date_a": a["date_facture"], "facture_a": a["facture"],
        "date_b": b["date_facture"], "facture_b": b["facture"],
        "prix_a": prix_a, "prix_b": prix_b,
        "champ_prix": [champ_a, champ_b],
        "conditionnement_a": _base(a), "conditionnement_b": _base(b),
        "promotion_a": bool(a.get("promotion")), "promotion_b": bool(b.get("promotion")),
        "delta_eur": delta, "delta_pct": pourcentage, "statut": statut,
    }
    if statut == ALIGNED:
        # L'effet sur la depense de la facture la plus recente : c'est ce qui fait la
        # difference entre un pourcentage et un montant.
        unites = b.get("unites_facturees") or 0
        comparaison["effet_eur"] = round(delta * unites, 2) if unites else None
    else:
        comparaison["effet_eur"] = None
    return comparaison


def derive(achats):
    """Toutes les comparaisons consecutives du meme article, ordonnees dans le temps.

    La cle est le numero d'article METRO. Deux libelles proches sont deux produits
    differents : un rapprochement par le nom est ce que ce depot interdit.
    """
    par_article = {}
    for ligne in achats:
        par_article.setdefault(ligne["article"], []).append(ligne)

    comparaisons = []
    for lignes in par_article.values():
        lignes = sorted(lignes, key=lambda l: (l["date_facture"], l["facture"]))
        for a, b in zip(lignes, lignes[1:]):
            comparaisons.append(comparer(a, b))
    return comparaisons


def charger(chemin=RELEVE):
    releve = json.loads(Path(chemin).read_text(encoding="utf-8"))
    return releve["achats"], releve


def rapport(comparaisons, releve):
    """Le rapport est un artefact date : il dit sur quoi il a ete produit, et ce qu'il
    n'autorise pas."""
    statuts = {}
    for c in comparaisons:
        statuts[c["statut"]] = statuts.get(c["statut"], 0) + 1
    return {
        "dataset": "METRO_INVOICE_PRICE_MOVEMENTS",
        "version": "1.0.0",
        "price_source_id": releve.get("price_source_id"),
        "source_dataset": releve.get("dataset"),
        "source_observed_at": releve.get("observed_at"),
        "periode": releve.get("periode"),
        "comparaisons": len(comparaisons),
        "statuts": statuts,
        "value_status": "PAID_PRICES_ONLY",
        "consumer_rule": (
            "Prix payes par nous, compares entre eux. Ni un prix de reference, ni un prix "
            "catalogue, ni un cout rendu : l'enlevement du cash & carry n'est porte par "
            "aucune facture. Un statut autre qu'ALIGNED signifie qu'aucun delta n'a ete "
            "calcule, et le trou est volontaire."
        ),
        "mouvements": comparaisons,
    }


def _table(comparaisons, top):
    """Mouvements les plus couteux, puis les plus frequents. Un statut sans chiffre reste
    visible : c'est une mesure qu'on n'a pas pu faire, pas une absence de mouvement."""
    avec = [c for c in comparaisons if c["delta_eur"] is not None]
    avec.sort(key=lambda c: abs(c.get("effet_eur") or 0), reverse=True)
    print(f"{len(comparaisons)} comparaisons, {len(avec)} avec un chiffre\n")
    print(f"{'article':9} {'de':10} {'a':10} {'prix':>13} {'delta':>8} {'effet EUR':>10}  designation")
    for c in avec[:top]:
        print(f"{c['article']:9} {c['date_a']:10} {c['date_b']:10} "
              f"{c['prix_a']:>6}->{c['prix_b']:<6} {c['delta_eur']:>8.4f} "
              f"{c.get('effet_eur') or 0:>10.2f}  {(c['designation'] or '')[:34]}")
    bloques = [c for c in comparaisons if c["delta_eur"] is None]
    if bloques:
        par_statut = {}
        for c in bloques:
            par_statut.setdefault(c["statut"], []).append(c)
        print("\nsans chiffre, par raison :")
        for statut, lot in sorted(par_statut.items()):
            print(f"  {statut:14} {len(lot):>3}   ex. {lot[0]['article']} {(lot[0]['designation'] or '')[:30]}")


def main(argv):
    if len(argv) < 2 or argv[1] != "derive":
        sys.exit(__doc__.strip().splitlines()[-1])

    achats, releve = charger()
    comparaisons = derive(achats)
    if "--article" in argv:
        cible = argv[argv.index("--article") + 1]
        comparaisons = [c for c in comparaisons if c["article"] == cible]
    top = int(argv[argv.index("--top") + 1]) if "--top" in argv else 10

    _table(comparaisons, top)
    if "--write" in argv:
        sortie = RAPPORT.parent / f"{RAPPORT.name}_{releve.get('observed_at')}.json"
        sortie.write_text(json.dumps(rapport(comparaisons, releve), ensure_ascii=False, indent=1),
                          encoding="utf-8")
        print(f"\necrit {sortie.relative_to(RACINE)}")


if __name__ == "__main__":
    main(sys.argv)