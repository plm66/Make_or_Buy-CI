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
       python3 comparaison_factures.py observations [--out chemin.json]
"""
import csv
import json
import re
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent
RELEVE = RACINE / "data/price_observations/metro_factures_2026-09-11.json"
RAPPORT = RACINE / "data/price_observations/metro_derive"
RATTACHEMENT = RACINE / "data/materials/rattachement_metro.csv"
MATIERES = RACINE / "data/materials/matieres_premieres.csv"

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

VOLUME = re.compile(r"(\d+(?:[.,]\d+)?)\s*(L|LITRES?|CL|ML)\b")
MULT_VOLUME_AVANT = re.compile(r"(\d+)\s*[*xX]\s*(\d+(?:[.,]\d+)?)\s*(L|LITRES?|CL|ML)\b")
MULT_VOLUME_APRES = re.compile(r"(\d+(?:[.,]\d+)?)\s*(L|LITRES?|CL|ML)\s*[*xX]\s*(\d+)\b")


def _grammes(valeur, unite):
    return float(valeur.replace(",", ".")) * (1000 if unite.startswith("K") else 1)


def _millilitres(valeur, unite):
    v = float(valeur.replace(",", "."))
    u = unite.upper()
    if u.startswith("L"):
        return v * 1000
    elif u.startswith("CL"):
        return v * 10
    return v


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


def poids_unite_facturee_g(ligne):
    """Ce que compte le colisage, en grammes.

    Le colisage ne compte pas toujours des pieces. `MC FARINE PANIF. T65 25KG` porte un
    colisage de 25 : l'unite facturee est le kilo, pas le sac. `BEURRE DX 500G` porte un
    colisage de 1 : l'unite facturee est la plaquette de 500 g. Sans cette division, la
    farine sortait a 0,03 EUR/kg, dix fois sous le prix de la matiere premiere agricole.
    """
    poids_pack = poids_total_g(ligne.get("designation"))
    if poids_pack is None:
        return None
    colisage = ligne.get("colisage") or 1
    if colisage <= 0:
        return None
    return poids_pack / colisage


def prix_derive_au_kilo(ligne):
    """Le prix au kilo deduit de la designation seule, jamais du prix imprime.

    Expose separement pour que le test puisse confronter notre lecture au prix que la
    facture imprime : c'est le seul juge disponible, et il doit rester independant de ce
    qu'il juge.
    """
    designation = (ligne.get("designation") or "").upper()
    poids = poids_unite_facturee_g(ligne)
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
    poids = poids_unite_facturee_g(ligne)
    if poids is None:
        return None
    imprime = ligne.get("prix_unite_normalisee")
    if imprime is not None:
        return {"valeur": imprime, "source": "IMPRIME_FACTURE", "poids_g": poids}
    derive = prix_derive_au_kilo(ligne)
    if derive is None:
        return None
    return {"valeur": derive, "source": "DESIGNATION_SIMPLE", "poids_g": poids}


def volume_total_ml(designation):
    """Volume total du conditionnement liquide en millilitres, ou None si muet."""
    texte = (designation or "").upper()
    volumes = [_millilitres(valeur, unite) for valeur, unite in VOLUME.findall(texte)]
    volumes += [_millilitres(valeur, unite) * int(n) for n, valeur, unite in MULT_VOLUME_AVANT.findall(texte)]
    volumes += [_millilitres(valeur, unite) * int(n) for valeur, unite, n in MULT_VOLUME_APRES.findall(texte)]
    return max(volumes) if volumes else None


def volume_unite_facturee_ml(ligne):
    """Volume de l'unite facturee en millilitres."""
    vol_pack = volume_total_ml(ligne.get("designation"))
    if vol_pack is None:
        return None
    colisage = ligne.get("colisage") or 1
    if colisage <= 0:
        return None
    # Si le colisage correspond aux litres du pack (ex: 5 pour 5L), l'unite est le litre (1000 mL)
    if abs(colisage - (vol_pack / 1000)) < 1e-4:
        return 1000.0
    return vol_pack


def prix_derive_au_litre(ligne):
    """Prix au litre deduit de la designation seule."""
    designation = (ligne.get("designation") or "").upper()
    vol = volume_unite_facturee_ml(ligne)
    if vol is None or MARQUEUR_COLIS.search(designation):
        return None
    prix, _ = _prix(ligne)
    return round(prix / (vol / 1000), 4) if prix else None


def prix_au_litre(ligne):
    """Prix au litre et sa provenance, ou None."""
    vol = volume_unite_facturee_ml(ligne)
    if vol is None:
        return None
    imprime = ligne.get("prix_unite_normalisee")
    if imprime is not None and not MARQUEUR_COLIS.search((ligne.get("designation") or "").upper()):
        return {"valeur": imprime, "source": "IMPRIME_FACTURE", "volume_ml": vol}
    derive = prix_derive_au_litre(ligne)
    if derive is None:
        return None
    return {"valeur": derive, "source": "DESIGNATION_SIMPLE", "volume_ml": vol}


BOITE_CONSERVE = re.compile(r"\b4/4\b|\b5/1\b|\b1/2\b")
PIECE_COLIS = re.compile(r"\bPC\s*(\d+)?\b", re.I)
BARQUETTE = re.compile(r"\bBQ\s*(\d+)?\b", re.I)
CARTON = re.compile(r"\bCT\s*(\d+)?\b", re.I)


def prix_piece_ou_colis(ligne):
    """Prix unitaire a la boite, piece ou barquette."""
    designation = (ligne.get("designation") or "").upper()
    prix, _ = _prix(ligne)
    if prix is None:
        return None
    if BOITE_CONSERVE.search(designation):
        return {"valeur": round(prix, 4), "unite": "EUR/boite", "source": "BOITE_CONSERVE"}
    if PIECE_COLIS.search(designation):
        return {"valeur": round(prix, 4), "unite": "EUR/piece", "source": "PIECE_COLIS"}
    if BARQUETTE.search(designation):
        return {"valeur": round(prix, 4), "unite": "EUR/barquette", "source": "BARQUETTE"}
    if CARTON.search(designation) and ligne.get("prix_unite_normalisee"):
        return {"valeur": ligne["prix_unite_normalisee"], "unite": "EUR/kg", "source": "IMPRIME_FACTURE"}
    return None


def prix_normalise(ligne):
    """Prix ramene a l'unite standard (kg, L, boite, piece, barquette), ou None."""
    kilo = prix_au_kilo(ligne)
    if kilo is not None:
        return {"valeur": kilo["valeur"], "unite": "EUR/kg", "source": kilo["source"],
                "quantite": kilo["poids_g"] / 1000}
    litre = prix_au_litre(ligne)
    if litre is not None:
        return {"valeur": litre["valeur"], "unite": "EUR/L", "source": litre["source"],
                "quantite": litre["volume_ml"] / 1000}
    piece = prix_piece_ou_colis(ligne)
    if piece is not None:
        return {"valeur": piece["valeur"], "unite": piece["unite"], "source": piece["source"],
                "quantite": 1}
    imprime = ligne.get("prix_unite_normalisee")
    if imprime is not None:
        return {"valeur": imprime, "unite": "EUR/kg", "source": "IMPRIME_FACTURE", "quantite": None}
    return None


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


def observations_matiere(achats, rattachement, matieres):
    """Une observation de prix matiere par ligne de facture rattachee et convertible.

    La couche ne contient que des prix au kilo : une ligne sans conditionnement lisible, ou
    dont l'article n'est pas rattache, ne produit rien. Deviner la matiere par le libelle est
    ce que ce depot interdit, et un prix au colis n'est pas un prix au kilo.

    La reserve de rattachement et le statut de la matiere voyagent avec la valeur : un
    `A_VERIFIER` reste publiable, il ne reste pas consommable comme un `ACTIF`.
    """
    fiche = {r["article_metro"]: r for r in rattachement}
    observations = []
    for ligne in achats:
        lien = fiche.get(ligne["article"])
        if not lien:
            continue
        prix = prix_au_kilo(ligne)
        if prix is None:
            continue
        observations.append({
            "id_matiere": lien["id_matiere"],
            "date": ligne["date_facture"],
            "facture": ligne["facture"],
            "article_metro": ligne["article"],
            "depot": ligne.get("depot"),
            "designation": ligne.get("designation"),
            "prix_eur_par_kg": prix["valeur"],
            "source_prix": prix["source"],
            "poids_g": prix["poids_g"],
            "statut_rattachement": lien.get("statut"),
            "statut_matiere": (matieres.get(lien["id_matiere"]) or {}).get("statut"),
        })
    observations.sort(key=lambda o: (o["date"], o["facture"], o["article_metro"]))
    return observations


def charger_referentiels():
    rattachement = list(csv.DictReader(RATTACHEMENT.read_text(encoding="utf-8").splitlines(),
                                       delimiter=";"))
    matieres = {m["id_matiere"]: m for m in csv.DictReader(
        MATIERES.read_text(encoding="utf-8").splitlines(), delimiter=";")}
    return rattachement, matieres


GARDER = "GARDER"
CHANGER = "CHANGER"
A_ARBITRER = "A_ARBITRER"
HORS_PERIMETRE = "HORS_PERIMETRE"
NON_RATTACHE = "NON_RATTACHE"

# `GARDER` portait deux cas que rien ne distinguait a la lecture : une alternative chiffree
# existait et perdait, ou aucune n'existait. Mesure du 2026-09-23 : 32 `GARDER` sur 32 etaient
# le second cas, et le premier n'a jamais ete atteint une seule fois depuis que le verdict
# existe. Le mot affirmait donc une comparaison qui n'avait jamais eu lieu — et dix `CHANGER`
# reels autour de lui rendaient l'inference naturelle : un lecteur en deduit que les `GARDER`
# ont ete confrontes et ont gagne. `NON_COMPARE` prend ce second cas, `GARDER` ne dit plus
# que ce qu'il prouve.
NON_COMPARE = "NON_COMPARE"

# Une ligne non alimentaire ne vise aucune matiere et ne doit jamais y etre forcee. Le
# statut existe dans le rattachement pour le dire ; le vocabulaire reste celui de
# `RATTACHEMENT.md`, qui distingue deja « le referentiel ne couvre pas » d'un oubli.
STATUT_HORS_PERIMETRE = "HORS_PERIMETRE"


def _alternative_unite(opt):
    """Determine l'unite de l'alternative de marche."""
    if opt.get("unite"):
        return opt["unite"]
    if opt.get("prix_eur_par_kg") is not None:
        return "EUR/kg"
    if opt.get("prix_au_litre") is not None:
        return "EUR/L"
    if opt.get("prix_piece") is not None:
        return "EUR/piece"
    return None


def _valeur_alternative(opt):
    """Valeur numerique du prix de l'alternative."""
    if opt.get("prix_eur_par_kg") is not None:
        return opt["prix_eur_par_kg"]
    if opt.get("prix_au_litre") is not None:
        return opt["prix_au_litre"]
    if opt.get("prix_normalise") is not None:
        return opt["prix_normalise"]
    return None


def _alternative_moins_chere(prix, options, unite_cible=None):
    """L'option la moins chere, chiffree, datee et de meme unite que la ligne.

    Une option sans prix ne compte pas : elle ne permet pas de trancher, et un verdict de
    changement sans prix serait une opinion. Une option d'une unite differente est ecartee.
    """
    if prix is None or not options:
        return None
    chiffrees = []
    for o in options:
        if not o.get("date"):
            continue
        u = _alternative_unite(o)
        if unite_cible and u != unite_cible:
            continue
        v = _valeur_alternative(o)
        if v is not None:
            chiffrees.append((v, o))
    if not chiffrees:
        return None
    meilleure_val, meilleure_opt = min(chiffrees, key=lambda t: t[0])
    return meilleure_opt if meilleure_val < prix else None


def verdict_ligne(ligne, lien, matiere=None, alternatives=None):
    """Ce que le depot propose pour une ligne, et pourquoi.

    L'ordre des tests porte le sens : le rattachement d'abord, parce qu'une ligne dont on ne
    sait pas de quoi elle parle ne se compare a rien. La reserve ensuite, parce qu'un
    `A_VERIFIER` publie sa valeur sans etre consommable comme un `ACTIF`.
    """
    prix_kilo = prix_au_kilo(ligne)
    norm = prix_normalise(ligne)
    prix_valeur = norm["valeur"] if norm else None

    verdict = {
        "article": ligne.get("article"),
        "designation": ligne.get("designation"),
        "date": ligne.get("date_facture"),
        "facture": ligne.get("facture"),
        "prix_eur_par_kg": prix_kilo["valeur"] if prix_kilo else None,
        "prix_normalise": prix_valeur,
        "unite": norm["unite"] if norm else None,
        "source_prix": norm["source"] if norm else None,
        "id_matiere": (lien or {}).get("id_matiere") or None,
        "statut_rattachement": (lien or {}).get("statut"),
        "statut_matiere": (matiere or {}).get("statut"),
        "alternative": None,
    }

    if not (lien or {}).get("id_matiere"):
        if (lien or {}).get("statut") == STATUT_HORS_PERIMETRE:
            note = ((lien or {}).get("note") or "").lower()
            raison_hors = "REVENTE_DIRECTE" if "revente" in note else "NON_ALIMENTAIRE"
            # Un article hors fabrication peut etre confronte a une alternative grossiste directe
            options_article = (alternatives or {}).get(ligne.get("article")) or []
            if options_article and prix_valeur is not None:
                unite_ligne = norm["unite"] if norm else None
                chiffrees_meme_unite = [
                    o for o in options_article
                    if _valeur_alternative(o) is not None and o.get("date") and (_alternative_unite(o) == unite_ligne)
                ]
                meilleure = _alternative_moins_chere(prix_valeur, options_article, unite_cible=unite_ligne)
                if meilleure:
                    verdict.update(verdict=CHANGER, raison="ALTERNATIVE_MOINS_CHERE", alternative=meilleure)
                    return verdict
                elif chiffrees_meme_unite:
                    verdict.update(verdict=GARDER, raison="ALTERNATIVE_PLUS_CHERE")
                    return verdict
            verdict.update(verdict=HORS_PERIMETRE, raison=raison_hors)
        else:
            verdict.update(verdict=NON_RATTACHE, raison="ARTICLE_ABSENT_DU_RATTACHEMENT")
        return verdict

    # Unite attendue pour la matiere premiere
    unite_attendue = (matiere or {}).get("unite_achat")
    if not unite_attendue:
        id_mat = (lien.get("id_matiere") or "")
        if id_mat.startswith("MATP-LIQU") or "HUIL" in id_mat or id_mat.startswith("MATP-LAIT"):
            unite_attendue = "L"
        elif id_mat in ("MATP-OEUF-ENTI", "MATP-AROM-VAGO"):
            unite_attendue = "piece"
        else:
            unite_attendue = "kg"

    if unite_attendue == "kg" and (prix_kilo is None or (norm and norm.get("unite") != "EUR/kg")):
        verdict.update(verdict=A_ARBITRER, raison="CONDITIONNEMENT_ILLISIBLE")
        return verdict
    elif unite_attendue == "L" and (prix_au_litre(ligne) is None or (norm and norm.get("unite") != "EUR/L")):
        verdict.update(verdict=A_ARBITRER, raison="CONDITIONNEMENT_ILLISIBLE")
        return verdict
    elif unite_attendue == "piece" and (norm is None or norm.get("unite") != "EUR/piece"):
        verdict.update(verdict=A_ARBITRER, raison="CONDITIONNEMENT_ILLISIBLE")
        return verdict
    elif prix_valeur is None:
        verdict.update(verdict=A_ARBITRER, raison="CONDITIONNEMENT_ILLISIBLE")
        return verdict

    if lien.get("statut") == "A_VERIFIER":
        verdict.update(verdict=A_ARBITRER, raison="RESERVE_A_VERIFIER")
        return verdict

    unite_ligne = norm["unite"] if norm else None
    options = (alternatives or {}).get(lien["id_matiere"]) or (alternatives or {}).get(ligne.get("article")) or []
    chiffrees_meme_unite = [
        o for o in options
        if _valeur_alternative(o) is not None and o.get("date") and (_alternative_unite(o) == unite_ligne)
    ]
    meilleure = _alternative_moins_chere(prix_valeur, options, unite_cible=unite_ligne)
    if meilleure:
        verdict.update(verdict=CHANGER, raison="ALTERNATIVE_MOINS_CHERE", alternative=meilleure)
    elif chiffrees_meme_unite:
        verdict.update(verdict=GARDER, raison="ALTERNATIVE_PLUS_CHERE")
    else:
        verdict.update(verdict=NON_COMPARE, raison="AUCUNE_ALTERNATIVE_CHIFFREE")
    return verdict


def charger_alternatives(chemin=None):
    """Charge les alternatives de marche chiffrees et datees.

    Lit `data/price_observations/alternatives_marche.json` s'il existe.
    """
    fichier = Path(chemin) if chemin else (RACINE / "data/price_observations/alternatives_marche.json")
    if fichier.exists():
        donnees = json.loads(fichier.read_text(encoding="utf-8"))
        return donnees.get("alternatives", {})
    return {}


def verdicts(achats, rattachement, matieres, alternatives=None):
    """Une proposition par ligne recue, sans exception : une ligne muette serait un oubli."""
    fiche = {r["article_metro"]: r for r in rattachement}
    return [verdict_ligne(ligne, fiche.get(ligne["article"]),
                          (matieres or {}).get((fiche.get(ligne["article"]) or {}).get("id_matiere")),
                          alternatives)
            for ligne in achats]


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


def _enveloppe_observations(observations, releve):
    statuts = {}
    for o in observations:
        statuts[o["statut_rattachement"]] = statuts.get(o["statut_rattachement"], 0) + 1
    return {
        "dataset": "MATERIAL_PRICE_OBSERVATIONS",
        "version": "1.0.0",
        "source_dataset": releve.get("dataset"),
        "source_observed_at": releve.get("observed_at"),
        "price_source_id": releve.get("price_source_id"),
        "observations": len(observations),
        "statuts_rattachement": statuts,
        "value_status": "PAID_PRICES_PER_KG",
        "consumer_rule": (
            "Prix payes ramenes au kilo, par matiere et par date. Le kilo vient du document "
            "quand la facture imprime son prix normalise, de la designation sinon. Un "
            "rattachement A_VERIFIER publie sa valeur et garde sa reserve : le critere du "
            "referentiel n'est pas ecrit sur la facture, et cette reserve doit suivre la "
            "valeur jusqu'a la decision de cout."
        ),
        "observations_detail": observations,
    }


def _table_observations(observations):
    par_matiere = {}
    for o in observations:
        par_matiere.setdefault(o["id_matiere"], []).append(o)
    print(f"{len(observations)} observations sur {len(par_matiere)} matieres\n")
    print(f"{'matiere':16} {'obs':>3} {'EUR/kg min':>10} {'max':>8}  rattachement")
    for matiere, lot in sorted(par_matiere.items()):
        prix = [o["prix_eur_par_kg"] for o in lot]
        reserves = {o["statut_rattachement"] for o in lot}
        print(f"{matiere:16} {len(lot):>3} {min(prix):>10.3f} {max(prix):>8.3f}  {'/'.join(sorted(reserves))}")


def main(argv):
    if len(argv) < 2 or argv[1] not in ("derive", "observations"):
        sys.exit(__doc__.strip().splitlines()[-1])

    achats, releve = charger()

    if argv[1] == "observations":
        rattachement, matieres = charger_referentiels()
        observations = observations_matiere(achats, rattachement, matieres)
        _table_observations(observations)
        if "--out" in argv:
            # Aucun chemin par defaut : l'emplacement de la couche est une decision, pas un
            # defaut choisi par l'outil.
            sortie = Path(argv[argv.index("--out") + 1])
            sortie.write_text(
                json.dumps(_enveloppe_observations(observations, releve),
                           ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"\necrit {sortie}")
        return

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