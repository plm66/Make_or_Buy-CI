#!/usr/bin/env python3
"""Import du registre d'achat vers le supplier master JSON.

Le registre est livré en xlsx. Un classeur ne se diffe pas, ne se teste pas et ne se relit
pas en revue : le JSON est la source de vérité du dépôt, le xlsx un véhicule de livraison.
Cette commande est rejouable, donc l'édition peut rester dans Excel sans que les deux
divergent — il suffit de la relancer.

    python3 suppliers_tool.py import-registry Procurement_Supplier_Registry_La_Manita_v1.xlsx

Lecture xlsx sans dépendance : un classeur est un zip de XML.
"""
from __future__ import annotations
import argparse, json, re, sys, zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parent
SUPPLIERS = ROOT / "data" / "suppliers"
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def _col(ref):
    n = 0
    for c in re.match(r"[A-Z]+", ref).group():
        n = n * 26 + ord(c) - 64
    return n - 1


def lire_classeur(path):
    """{nom de feuille: [[cellule]]} — les feuilles sont rendues telles quelles."""
    z = zipfile.ZipFile(path)
    partages = []
    if "xl/sharedStrings.xml" in z.namelist():
        for si in ET.fromstring(z.read("xl/sharedStrings.xml")):
            partages.append("".join(t.text or "" for t in si.iter(NS + "t")))
    rels = {r.get("Id"): r.get("Target").lstrip("/")
            for r in ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))}
    feuilles = {}
    for sh in ET.fromstring(z.read("xl/workbook.xml")).iter(NS + "sheet"):
        cible = rels[sh.get("{http://schemas.openxmlformats.org/officeDocument/2006/"
                            "relationships}id")]
        lignes = []
        for row in ET.fromstring(z.read(cible if cible.startswith("xl/")
                                        else "xl/" + cible)).iter(NS + "row"):
            vals = {}
            for c in row.iter(NS + "c"):
                v = c.find(NS + "v")
                if v is None:
                    isn = c.find(NS + "is")
                    txt = "".join(t.text or "" for t in isn.iter(NS + "t")) if isn is not None else ""
                else:
                    txt = partages[int(v.text)] if c.get("t") == "s" else (v.text or "")
                vals[_col(c.get("r"))] = txt.strip()
            lignes.append([vals.get(i, "") for i in range(max(vals) + 1 if vals else 0)])
        feuilles[sh.get("name")] = lignes
    return feuilles


def _liste(cellule):
    return [x.strip() for x in re.split(r"[;,]", cellule) if x.strip()]


def _nombre(cellule):
    try:
        return float(cellule)
    except (TypeError, ValueError):
        return None


def _identifiant(sup_id, nom):
    """Identifiant de fichier stable, aligné sur les fiches déjà au dépôt."""
    connus = {"SUP-CDP": "coup_de_pates", "SUP-TG": "transgourmet", "SUP-VDM": "vandemoortele",
              "SUP-TDP": "traiteur_de_paris", "SUP-TIP": "tipiak_restauration"}
    if sup_id in connus:
        return connus[sup_id]
    return re.sub(r"[^a-z0-9]+", "_", nom.lower()).strip("_")


def importer(classeur):
    feuilles = lire_classeur(classeur)
    lignes = [r + [""] * 20 for r in feuilles["Supplier Master"][1:] if any(x.strip() for x in r)]
    ecrits, fusionnes = [], []
    for r in lignes:
        sid = _identifiant(r[0], r[1])
        chemin = SUPPLIERS / f"{sid}.json"
        # Les fiches existantes portent official_sources, research_policy et
        # doctrine_relevance, absents du classeur: on ajoute sans jamais ecraser.
        fiche = json.loads(chemin.read_text(encoding="utf-8")) if chemin.exists() else {
            "supplier_id": sid, "name": r[1], "entity_type": r[5] or "UNKNOWN",
            "market": [], "coverage": {}, "capabilities": {}, "product_families": [],
            "official_sources": [], "data_quality": {}}
        if chemin.exists():
            fusionnes.append(sid)
        fiche["procurement"] = {
            "registry_id": r[0],
            "entry_status": r[2],
            "purchase_channel": r[3],
            "priority": r[4],
            "strategic_role": r[7] or None,
            "idf_delivery": r[8],
            "moq_franco_eur_ht": _nombre(r[9]),
            "price_access": r[10],
            "frozen_capability": r[11] or None,
            "vegan_capability": r[12] or None,
            "traceability_level": r[13] or None,
            "qualification_evidence": r[14] or None,
            "next_action": r[15] or None,
            "buyer_owner": r[18] or None,
            "notes": r[19] or None,
            "last_verified": r[17] or None,
        }
        if not fiche.get("product_families") and r[6]:
            fiche["product_families"] = _liste(r[6])
        if r[16] and not any(s.get("url") == r[16] for s in fiche.get("official_sources", [])):
            fiche.setdefault("official_sources", []).append(
                {"url": r[16], "source_type": "SUPPLIER_SITE", "verified_at": r[17] or None,
                 "notes": "Source officielle déclarée au registre d'achat."})
        chemin.write_text(json.dumps(fiche, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        ecrits.append((sid, r[2], r[3]))

    index = {"schema_version": "2.0.0",
             "generated_from": Path(classeur).name,
             "generated_at": max((r[17] for r in lignes if r[17]), default=None),
             "suppliers": [{"supplier_id": s, "entry_status": st, "purchase_channel": ch}
                           for s, st, ch in sorted(ecrits)]}
    (SUPPLIERS / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n",
                                          encoding="utf-8")

    crit = [{"criterion": r[0], "mandatory": r[1], "collect": r[2], "decision_rule": r[3]}
            for r in feuilles["Qualification"][1:] if any(x.strip() for x in r)]
    (SUPPLIERS / "qualification_criteria.json").write_text(
        json.dumps({"schema_version": "1.0.0", "criteria": crit}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")

    print(f"{len(ecrits)} fournisseurs écrits ({len(fusionnes)} fusionnés avec une fiche existante)")
    print(f"{len(crit)} critères de qualification -> qualification_criteria.json")
    return ecrits


def main():
    ap = argparse.ArgumentParser(prog="suppliers_tool")
    sp = ap.add_subparsers(required=True)
    i = sp.add_parser("import-registry", help="Importer le registre d'achat xlsx.")
    i.add_argument("classeur")
    i.set_defaults(func=lambda a: importer(a.classeur))
    a = ap.parse_args(); a.func(a)


if __name__ == "__main__":
    main()
