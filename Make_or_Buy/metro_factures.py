#!/usr/bin/env python3
"""Extrait les lignes d'achat des factures METRO PDF.

Une facture n'est pas un catalogue. Les prix lus ici sont ceux que nous avons
reellement payes, a une date reelle, pour une quantite reelle — des faits sur nous,
pas des references. C'est ce que `halalfs_tool.py` ne peut pas produire.

METRO est un cash & carry : la facture ne porte ni frais de livraison ni consigne,
donc le montant facture est le cout rendu au depot. Le cout de l'enlevement
(deplacement, temps) n'est porte par aucune de ces factures et reste a etablir.

Aucun rattachement a un id_matiere n'est fait ici : lire un prix et decider de quelle
matiere il s'agit sont deux operations distinctes, et la seconde n'est pas mecanique.

Usage: python3 metro_factures.py extraire [--write]
"""
import json
import re
import subprocess
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent
FACTURES = RACINE / "data/price_observations/metro"

# Le filigrane « Duplicata » traverse la page en diagonale. Sans -nodiag, pdftotext
# l'intercale dans les colonnes et casse 30 lignes sur 377 : la designation part sur
# une ligne, les nombres deux lignes plus bas.
PDFTOTEXT = ["pdftotext", "-layout", "-nodiag"]

# Ordre imprime : prix unitaire, colisage, quantite, montant. Le colisage est le
# nombre d'unites par colis (90 oeufs, 25 kg de farine), la quantite le nombre de colis.
ACHAT = re.compile(
    r"^\s{0,4}(?P<mm>[A-Z*]{0,3})\s*(?P<ean>\d{8,14})?\s*(?P<article>\d{7})\s+"
    r"(?P<designation>.+?)\s{2,}(?P<prix>\d+,\d{3})\s+(?P<colisage>\d+)\s+"
    r"(?P<qte>\d+)\s+(?P<montant>-?[\d ]+,\d{2})\s+(?P<tva>[A-Z])(?P<reste>.*)$")

# Article vendu au poids : une colonne de plus, et le montant vaut prix x poids.
AU_POIDS = re.compile(
    r"^\s{0,4}(?P<mm>[A-Z*]{0,3})\s*(?P<ean>\d{8,14})?\s*(?P<article>\d{7})\s+"
    r"(?P<designation>.+?)\s{2,}(?P<poids>\d+,\d{3})\s+(?P<prix>\d+,\d{3})\s+"
    r"(?P<qte>\d+)\s+(?P<montant>-?[\d ]+,\d{2})\s+(?P<tva>[A-Z])(?P<reste>.*)$")

UNITAIRE = re.compile(r"PRIX AU KG OU AU LITRE:\s*(\d+,\d+)")
RAYON = re.compile(r"^\*\*\*\s+(.+?)\s+Total:\s*([\d ]+,\d{2})")
NUMERO = re.compile(r"\((\d{3}-\d{5,6})\)")
DATE = re.compile(r"Date facture\s*:\s*(\d{2})-(\d{2})-(\d{4})")
DEPOT = re.compile(r"^METRO France\s+\S*\s*(METRO [A-Z0-9 ]+?)\s{2,}")
TOTAL = re.compile(r"Total H\.T\.\s*:\s*([\d ]+,\d{2})")
FIN_ARTICLES = re.compile(r"Nombre de colis\s*:")

# Une remise s'ecrit sans ligne article, montant suffixe d'un moins. Le sous-total de
# rayon l'ignore, le total de facture la deduit : c'est ce decalage qui la trahit.
REMISE = re.compile(r"^\s*(?P<libelle>[A-Za-zÀ-ÿ0-9' ]{6,60}?)\s+(?P<montant>[\d ]+,\d{2})-\s*$")

# « Offre Achetez Plus Payez Moins » porte sur l'article qui precede. « 3 pour 2 »
# porte sur un groupe : la rattacher a la derniere ligne ferait un faux prix paye.
REMISE_LIGNE = "Offre Achetez Plus Payez Moins"


def nombre(s):
    return float(s.replace(" ", "").replace(",", "."))


def controle(prix, unites, montant):
    """Le montant facture doit valoir le prix unitaire fois le nombre d'unites.

    Le prix unitaire est imprime a trois decimales, donc arrondi : sur 50 kg de farine
    l'ecart legitime atteint 2,5 centimes. La tolerance suit le nombre d'unites au lieu
    d'etre un forfait, sinon les grosses lignes sortent fausses et les petites laissent
    passer de vraies erreurs de colonne.
    """
    return abs(montant - prix * unites) <= unites * 0.0005 + 0.011


def extraire_facture(pdf):
    texte = subprocess.run([*PDFTOTEXT, str(pdf), "-"],
                           capture_output=True, text=True, check=True).stdout
    lignes = texte.splitlines()

    entete = {"fichier": pdf.name, "numero": None, "date_facture": None,
              "depot": None, "total_ht_declare": None}
    for l in lignes:
        if entete["numero"] is None and (m := NUMERO.search(l)):
            entete["numero"] = m.group(1)
        if entete["date_facture"] is None and (m := DATE.search(l)):
            entete["date_facture"] = f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
        if entete["depot"] is None and (m := DEPOT.search(l)):
            entete["depot"] = m.group(1).strip()
        if m := TOTAL.search(l):
            entete["total_ht_declare"] = nombre(m.group(1))

    achats, remises, rayon, non_lues = [], [], None, []
    for i, l in enumerate(lignes):
        if FIN_ARTICLES.search(l):
            break
        if (m := REMISE.match(l)) and not ACHAT.match(l) and not AU_POIDS.match(l):
            precedent = achats[-1] if achats else None
            montant = -nombre(m.group("montant"))
            libelle = m.group("libelle").strip()
            sur_ligne = libelle.startswith(REMISE_LIGNE) and precedent is not None
            remises.append({
                "facture": entete["numero"], "libelle": libelle, "montant_ht": montant,
                "rayon": rayon,
                "apres_article": precedent["article"] if precedent else None,
                "portee": "LIGNE_PRECEDENTE" if sur_ligne else "GROUPE_NON_ATTRIBUE",
            })
            if sur_ligne:
                precedent["remise_ht"] = montant
                precedent["prix_unitaire_paye"] = round(
                    (precedent["montant_ht"] + montant) / precedent["unites_facturees"], 4)
            continue
        if m := RAYON.match(l.strip()):
            rayon = m.group(1)
            continue
        m, au_poids = ACHAT.match(l), False
        if not m:
            m, au_poids = AU_POIDS.match(l), True
        if not m:
            if re.match(r"^\s*\S*\s*(\d{8,14} )?\d{7} [A-Z*]", l):
                non_lues.append(l.strip()[:100])
            continue

        g = m.groupdict()
        prix, montant = nombre(g["prix"]), nombre(g["montant"])
        poids = nombre(g["poids"]) if au_poids else None
        colisage = None if au_poids else int(g["colisage"])
        qte = int(g["qte"])
        unites = poids * qte if au_poids else colisage * qte

        # Le prix au kg n'est imprime qu'a la ligne suivante, et seulement quand le
        # conditionnement n'est pas deja une unite de mesure.
        norme = None
        if i + 1 < len(lignes) and (u := UNITAIRE.search(lignes[i + 1])):
            norme = nombre(u.group(1))

        achats.append({
            "facture": entete["numero"], "date_facture": entete["date_facture"],
            "depot": entete["depot"], "rayon": rayon,
            # L'EAN manque sur certains articles METRO (croissants crus). Le numero
            # d'article, lui, est toujours la : c'est lui la cle stable.
            "ean": g["ean"], "article": g["article"],
            "designation": g["designation"].strip(),
            "prix_unitaire_ht": prix, "colisage": colisage, "quantite": qte,
            "poids_facture_kg": poids, "unites_facturees": round(unites, 3),
            "montant_ht": montant, "code_tva": g["tva"],
            "promotion": "P" in g["reste"],
            "remise_ht": None,
            # Le prix imprime est celui du tarif, pas forcement celui paye : une remise
            # de volume s'applique apres coup. Ce champ ne vaut que si remise_ht est lu.
            "prix_unitaire_paye": None,
            "prix_unite_normalisee": norme,
            "controle_arithmetique": "OK" if controle(prix, unites, montant) else "ECART",
        })

    return entete, achats, remises, non_lues


def extraire(ecrire=False):
    pdfs = sorted(FACTURES.glob("*.pdf"))
    if not pdfs:
        sys.exit(f"aucun PDF dans {FACTURES}")

    tous, toutes_remises, entetes, non_lues = [], [], [], []
    for pdf in pdfs:
        e, a, r, nl = extraire_facture(pdf)
        somme = round(sum(x["montant_ht"] for x in a) + sum(x["montant_ht"] for x in r), 2)
        e["total_ht_calcule"] = somme
        e["lignes"] = len(a)
        # Un total qui ne retombe pas sur la somme des lignes signale une ligne perdue
        # ou mal decoupee. C'est le seul controle qui voit ce que la regex n'a pas vu.
        e["total_concorde"] = abs(somme - (e["total_ht_declare"] or -1)) <= 0.02
        e["remises"] = len(r)
        entetes.append(e)
        tous.extend(a)
        toutes_remises.extend(r)
        non_lues.extend((pdf.name, l) for l in nl)

    ecarts = [a for a in tous if a["controle_arithmetique"] == "ECART"]
    discordants = [e for e in entetes if not e["total_concorde"]]
    dates = sorted(e["date_facture"] for e in entetes if e["date_facture"])

    sortie = {
        "dataset": "METRO_INVOICE_EXTRACTION",
        "version": "1.0.0",
        "price_source_id": "metro_france",
        "observed_at": max(dates) if dates else None,
        "periode": {"debut": dates[0] if dates else None, "fin": dates[-1] if dates else None},
        "capture_method": "PDF_FACTURE_CLIENT",
        "source_api": "aucune — factures telechargees par l'exploitant depuis son espace client",
        "tax_basis": "HT",
        "tax_basis_evidence": "mention « Total H.T. » et « Montant hors T.V.A. » en pied de facture",
        "factures": len(entetes),
        "lignes_extraites": len(tous),
        "remises_extraites": len(toutes_remises),
        "lignes_non_lues": [{"fichier": f, "ligne": l} for f, l in non_lues],
        "lignes_en_ecart": len(ecarts),
        "factures_discordantes": [e["fichier"] for e in discordants],
        "data_status": "INVOICED_ACTUAL_UNMATCHED",
        "consumer_rule": (
            "Prix reellement payes, pas des prix catalogue. METRO etant un cash & carry, "
            "la facture ne porte ni livraison ni consigne : le montant est le cout rendu "
            "au depot. Le cout de l'enlevement n'y figure pas et reste a etablir ailleurs. "
            "Aucun rattachement a un id_matiere n'est etabli ici."
        ),
        "entetes": entetes,
        "achats": tous,
        "remises": toutes_remises,
    }

    print(f"{len(entetes)} factures, {len(tous)} lignes, "
          f"{dates[0] if dates else '?'} → {dates[-1] if dates else '?'}")
    attribuees = [r for r in toutes_remises if r["portee"] == "LIGNE_PRECEDENTE"]
    print(f"  controle arithmetique : {len(tous) - len(ecarts)}/{len(tous)} OK")
    print(f"  remises               : {len(toutes_remises)} "
          f"({len(attribuees)} rattachees a une ligne, "
          f"{len(toutes_remises) - len(attribuees)} a un groupe), "
          f"{round(sum(r['montant_ht'] for r in toutes_remises), 2)} EUR")
    print(f"  totaux concordants    : {len(entetes) - len(discordants)}/{len(entetes)}")
    for e in discordants:
        print(f"    ECART {e['fichier']}: declare {e['total_ht_declare']} "
              f"calcule {e['total_ht_calcule']}")
    for f, l in non_lues:
        print(f"    NON LUE {f}: {l}")

    if ecrire:
        cible = RACINE / f"data/price_observations/metro_factures_{sortie['observed_at']}.json"
        cible.write_text(json.dumps(sortie, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"ecrit: {cible.relative_to(RACINE)}")
    else:
        print("  (--write pour ecrire le JSON)")
    return sortie


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] != "extraire":
        sys.exit(__doc__)
    extraire("--write" in sys.argv)
