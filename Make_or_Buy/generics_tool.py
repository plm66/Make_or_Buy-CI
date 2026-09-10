import re, unicodedata

def norm(s):
    s = unicodedata.normalize("NFD", (s or "").upper())
    return re.sub(r"[^A-Z0-9 ]", " ", "".join(c for c in s if unicodedata.category(c) != "Mn"))

# Le sale tranche avant la forme: un croissant au fromage est du snacking, pas une
# viennoiserie. BUN'N'ROLL est un nom de marque Bridor qu'aucune regle ne peut deduire —
# c'est un pain sale de snacking, inscrit explicitement.
SALE = (r"JAMBON|FROMAGE|EMMENTAL|CHEVRE|THON|POULET|SAUCISS|CHORIZO|LARDON|HOT DOG|"
        r"CROQ|MONSIEUR|PANIWICH|PIZZA|QUICHE|OLIVE|ROMARIN|CHARCUTIER|BUN.?N.?ROLL")

REGLES = [
 ("VIEN","croissants-fourres", r"CROISSANT.*(AMANDE|ABRICOT|PISTACHE|FRAMBOISE|FOURRE)|(AMANDE|ABRICOT).*CROISSANT"),
 ("VIEN","croissants",         r"\bCROISSANT"),
 ("VIEN","pains-au-chocolat",  r"PAIN\s*(AU)?\s*CHOCOLAT|CHOCOLATINE|SUISSE"),
 ("VIEN","pains-aux-raisins",  r"PAIN\s*(AUX?)?\s*RAISIN|ESCARGOT"),
 ("VIEN","autres-viennoiseries", r"BRIOCH|CHAUSSON|TORSADE|ROLL\b|TRESSE|KOUIGN|CRAMIQUE|BEIGNET|PAIN LAIT"),
 ("PATI","macarons",           r"MACARON"),
 ("PATI","pastel-de-nata",     r"PASTEL|NATA"),
 ("PATI","pates-feuilletees",  r"P\s?ATE (FEUILLET|LEVEE|BRISEE|SUCREE)|PLAQUE DE P"),
 ("PATI","patisserie-americaine", r"DONUT|MUFFIN|BROWNIE|COOKIE|CHEESECAKE|CARROT CAKE|BAGEL"),
 ("PATI","autres-patisseries", r"TARTE|ECLAIR|FLAN|MADELEINE|CAKE|MOELLEUX|FINANCIER|BOLA|CANEL|"
                               r"CHOU\b|MILLEFEUIL|TIRAMISU|CREME|ENTREMET|BUCHE|SABLE|GAUFRE|"
                               r"PANCAKE|CRUMBLE|CLAFOUTI|PARIS BREST|CADRE|BANDE FEUILLETEE|PRALINE"),
 ("PAIN","baguettes",          r"BAGUETT|FICELLE|FLUTE"),
 ("PAIN","petits-pains",       r"BOULE|PETIT PAIN|B\s?BREAK|NAVETTE|BUN\b|BURGER|BRETZEL"),
 ("PAIN","pains-a-partager",   r"FOCACCIA|FOUGASSE|CIABATTA|PAIN A PARTAGER|TOURTE"),
 ("PAIN","pains-sandwich",     r"SANDWICH|PANINI|WRAP|TORTILLA|PITA"),
 ("PAIN","autres-pains",       r"\bPAIN\b|MIX LOSANGE|CEREALIER|BATARD|COMPLET|RUSTIQUE"),
]

CODE = {"croissants":"CROI","croissants-fourres":"CROF","pains-au-chocolat":"PCHO",
        "pains-aux-raisins":"PRAI","autres-viennoiseries":"AUTR","macarons":"MACA",
        "pastel-de-nata":"PAST","pates-feuilletees":"PATE","autres-patisseries":"AUTR",
        "patisserie-americaine":"AMER","snacking":"TOUT","baguettes":"BAGU",
        "petits-pains":"PETI","pains-a-partager":"PPAR","pains-sandwich":"PSAN",
        "autres-pains":"AUTR"}

LIBELLE = {"CROI":"croissant","CROF":"croissant fourré","PCHO":"pain au chocolat",
           "PRAI":"pain aux raisins","AUTR":"autre","MACA":"macaron","PAST":"pastel de nata",
           "PATE":"pâte feuilletée","AMER":"pâtisserie américaine","TOUT":"snacking",
           "BAGU":"baguette","PETI":"petit pain","PPAR":"pain à partager","PSAN":"pain sandwich"}

def classe(nom):
    """(famille, categorie) derivees de l'intitule, ou (None, None)."""
    n = norm(nom)
    if re.search(SALE, n): return "SNAC", "snacking"
    for fam, cat, pat in REGLES:
        if re.search(pat, n): return fam, cat
    return None, None

def poids(v):
    m = re.search(r"(\d+)", str(v) or "")
    return int(m.group(1)) if m else None

def cle(fam, cat, nom, p):
    """Nature x classe de format. Le grammage n'entre pas dans la cle: deux catalogues
    vendent le meme produit a des formats differents et ne se rejoindraient jamais."""
    code = CODE[cat]
    if code == "MACA":
        # 12 g petit four et 55-100 g dessert sont deux natures, pas deux formats.
        return f"{fam}-MACA-" + ("PETITFOUR" if p and p < 30 else "DESSERT")
    k = f"{fam}-{code}"
    return k + "-MINI" if re.search(r"\bMINI\b", norm(nom)) else k

# ---------------------------------------------------------------- outillage

import argparse, collections, csv, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
GENERICS = ROOT / "data" / "generics"

def load(p):
    with Path(p).open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh, delimiter=";"))

def save(p, rows, champs=None):
    with Path(p).open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=champs or list(rows[0]), delimiter=";", extrasaction="ignore")
        w.writeheader(); w.writerows(rows)

def libelle(k):
    parts = k.split("-")
    nom = LIBELLE.get(parts[1], parts[1].lower())
    if len(parts) < 3: return nom
    return "mini " + nom if parts[2] == "MINI" else f"{nom} {parts[2].lower()}"

def cmd_rebuild(args):
    """Rederive famille, categorie et id_generique depuis les intitules, puis reconstruit
    le referentiel generique. A rejouer apres chaque import de catalogue: la categorie
    d'un collecteur reprend le vocabulaire de son fournisseur et n'est pas comparable."""
    rep = Path(args.directory)
    skus, echecs = [], []
    for f in sorted(rep.glob("*_detail.csv")):
        rows = load(f)
        for r in rows:
            fam, cat = classe(r["nom_commercial"])
            if fam is None:
                echecs.append((f.name, r["ref_sku"], r["nom_commercial"])); continue
            p = poids(r["poids_unitaire"])
            r["famille"], r["categorie"] = fam, cat
            r["id_generique"] = cle(fam, cat, r["nom_commercial"], p)
            skus.append((f.name.split("_detail")[0], r, p))
        if not echecs: save(f, rows)

    if echecs:
        for nom, ref, intitule in echecs:
            print(f"NON CLASSE {nom} {ref} — {intitule}", file=sys.stderr)
        print(f"{len(echecs)} intitulés hors règles: enrichir REGLES avant de reconstruire",
              file=sys.stderr)
        sys.exit(1)

    for f in sorted(rep.glob("*_index.csv")):
        rows = load(f)
        for r in rows:
            fam, cat = classe(r["nom_commercial"])
            if fam: r["famille"], r["categorie"] = fam, cat
        save(f, rows)

    par_cle = collections.defaultdict(list)
    for src, r, p in skus:
        par_cle[r["id_generique"]].append((src, r, p))
    gen = []
    for k, membres in sorted(par_cle.items()):
        ps = sorted(p for _, _, p in membres if p)
        gen.append({"id_generique": k, "famille": membres[0][1]["famille"],
                    "categorie": membres[0][1]["categorie"], "nom_normalise": libelle(k),
                    "poids_min_g": ps[0] if ps else "", "poids_max_g": ps[-1] if ps else "",
                    "nb_refs_associees": len(membres),
                    "nb_fournisseurs": len({src for src, _, _ in membres})})
    save(rep / "produits_generiques.csv", gen,
         ["id_generique","famille","categorie","nom_normalise","poids_min_g","poids_max_g",
          "nb_refs_associees","nb_fournisseurs"])
    inter = [g for g in gen if g["nb_fournisseurs"] > 1]
    print(f"{len(skus)} SKU, {len(gen)} génériques, {len(inter)} inter-fournisseurs "
          f"({sum(g['nb_refs_associees'] for g in inter)}/{len(skus)} SKU)")

def main():
    ap = argparse.ArgumentParser(prog="generics_tool")
    sp = ap.add_subparsers(required=True)
    r = sp.add_parser("rebuild", help="Redérive les catégories depuis les intitulés et reconstruit le référentiel.")
    r.add_argument("directory", nargs="?", default=str(GENERICS))
    r.set_defaults(func=cmd_rebuild)
    a = ap.parse_args(); a.func(a)

if __name__ == "__main__":
    main()
