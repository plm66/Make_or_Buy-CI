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
import re
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

# Le conditionnement se lit dans la designation : la facture n'imprime pas le poids par
# ligne, elle imprime le prix unitaire du colis. `LEVURE 500G*5 HIRONDELLE 2,5KG` porte les
# deux, et c'est le total qui donne son sens au prix. Lire le premier donne 12,76 EUR/kg la
# ou le document imprime 2,552.
TAILLE = re.compile(r"(\d+(?:[.,]\d+)?)\s*(KG|KILOS?|G|GRS?)\b")
MULT_AVANT = re.compile(r"(\d+)\s*[*xX]\s*(\d+(?:[.,]\d+)?)\s*(KG|KILOS?|G|GRS?)\b")
MULT_APRES = re.compile(r"(\d+(?:[.,]\d+)?)\s*(KG|KILOS?|G|GRS?)\s*[*xX]\s*(\d+)\b")


def _grammes(valeur, unite):
    return float(valeur.replace(",", ".")) * (1000 if unite.startswith("K") else 1)


def poids_total_g(designation):
    """Poids total du conditionnement, en grammes, ou None si la designation se tait.

    Le maximum est retenu : quand une designation porte le sachet et le total, c'est le
    total. Un produit vendu a la piece n'a aucune taille dans son libelle, et rendre un
    chiffre devine ferait entrer une conversion inventee dans chaque recette qui l'utilise.
    """
    texte = (designation or "").upper()
    tailles = [_grammes(valeur, unite) for valeur, unite in TAILLE.findall(texte)]
    tailles += [_grammes(valeur, unite) * int(n) for n, valeur, unite in MULT_AVANT.findall(texte)]
    tailles += [_grammes(valeur, unite) * int(n) for valeur, unite, n in MULT_APRES.findall(texte)]
    return max(tailles) if tailles else None


# Le multiplicateur de colis s'ecrit en abrege fournisseur : BQ12, X30, 4/4, PLT, 5*100GRS.
# Il n'est pas lisible de facon fiable, et c'est lui qui produit les seuls ecarts mesures :
# sur les lignes ou la facture imprime son prix normalise, celles qui portent ce marqueur
# donnent 0 accord sur 4, celles qui ne le portent pas 24 sur 24.
MARQUEUR_COLIS = re.compile(r"\bBQ\d|\bX\d|\b\d+/\d\b|\b\d+\s*[*xX]\s*\d|\bPLT\b")


def prix_derive_au_kilo(ligne):
    """Le prix au kilo deduit de la designation seule, jamais du prix imprime.

    Expose separement pour que le test puisse confronter notre lecture au prix que la
    facture imprime : c'est le seul juge disponible, et il doit rester independant de ce
    qu'il juge.
    """
    designation = (ligne.get("designation") or "").upper()
    poids = poids_total_g(designation)
    if poids is None or MARQUEUR_COLIS.search(designation):
        return None
    prix, _ = _prix(ligne)
    return round(prix / (poids / 1000), 4) if prix else None


def prix_au_kilo(ligne):
    """Prix au kilo et sa provenance, ou None.

    La provenance compte. `IMPRIME_FACTURE` est le prix normalise imprime par le document
    lui-meme ; sa valeur n'est un prix au kilo que si la designation porte une masse, sinon
    elle est en EUR/L et l'unite n'est declaree nulle part. `DESIGNATION_SIMPLE` est notre
    lecture d'une designation sans abrege de colis.

    Une designation qui porte un abrege de colis ne donne aucun prix : le multiplicateur
    n'est pas lisible, et le prix du colis n'est pas un prix au kilo.
    """
    poids = poids_total_g(ligne.get("designation"))
    if poids is None:
        return None
    imprime = ligne.get("prix_unite_normalisee")
    if imprime is not None:
        return {"valeur": imprime, "source": "IMPRIME_FACTURE", "poids_g": poids}
    derive = prix_derive_au_kilo(ligne)
    if derive is None:
        return None
    return {"valeur": derive, "source": "DESIGNATION_SIMPLE", "poids_g": poids}


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