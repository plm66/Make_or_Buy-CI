#!/usr/bin/env python3
"""Vue d'ensemble des factures METRO : ce qu'un article nous a coute, et comment il a bouge.

`serveur_factures.py` repond a « que dire de cette facture-ci ». Celle-ci repond a « que
dire des vingt ». Ce n'est pas la meme question : une facture isolee ne peut pas montrer
qu'un article a varie, et c'est la seule comparaison que ce depot puisse produire
aujourd'hui sans source exterieure.

Rien n'est decide ici. Les verdicts viennent de `comparaison_factures.verdicts`, le prix au
kilo de `prix_au_kilo`, le prix paye de `_prix`. Ce module agrege et rend.

La comparaison servie est celle d'un article avec lui-meme dans le temps. Elle ne demande
aucun rattachement : la cle est le numero d'article, qui survit au changement de libelle. La
couverture du rattachement borne la comparaison fournisseur, pas celle-ci.

Aucune colonne « meilleur fournisseur » : le depot ne porte aucun prix concurrent sur ces
articles, et une colonne vide sur toutes les lignes est du bruit, pas une information.

Usage: python3 rapport_factures.py rendre [--out chemin.html]
"""
import html
import sys
import tempfile
from pathlib import Path

RACINE = Path(__file__).resolve().parent
sys.path.insert(0, str(RACINE))

import comparaison_factures as cf  # noqa: E402


def agreger(achats, propositions):
    """Un enregistrement par article, du plus couteux au moins couteux.

    Le verdict est une propriete de la ligne, pas de l'article : un conditionnement illisible
    sur un seul achat suffit a la faire diverger. Les verdicts distincts sont donc tous
    rendus, jamais reduits au premier — reduire masquerait precisement la ligne qui coince.
    """
    verdict_par_ligne = {}
    for proposition in propositions:
        cle = (proposition["article"], proposition["facture"], proposition["designation"])
        verdict_par_ligne[cle] = proposition

    par_article = {}
    for ligne in achats:
        par_article.setdefault(ligne["article"], []).append(ligne)

    enregistrements = []
    for article, lignes in par_article.items():
        lignes = sorted(lignes, key=lambda l: (l["date_facture"], l["facture"]))
        prix = [p for p in (cf._prix(l)[0] for l in lignes) if p is not None]
        kilos = [k["valeur"] for k in (cf.prix_au_kilo(l) for l in lignes) if k]
        verdicts = []
        matiere = statut = None
        for ligne in lignes:
            proposition = verdict_par_ligne.get(
                (ligne["article"], ligne["facture"], ligne.get("designation")))
            if not proposition:
                continue
            if proposition["verdict"] not in verdicts:
                verdicts.append(proposition["verdict"])
            matiere = matiere or proposition.get("id_matiere")
            statut = statut or proposition.get("statut_rattachement")

        enregistrements.append({
            "article": article,
            "designation": lignes[-1].get("designation"),
            "achats": len(lignes),
            "depense_ht": round(sum(l["montant_ht"] for l in lignes), 2),
            "prix_min": min(prix) if prix else None,
            "prix_max": max(prix) if prix else None,
            # Un seul achat ne porte aucune dérive : rendre 0 % ferait lire une stabilité
            # mesurée là où rien n'a été mesuré. Deux achats au même prix, eux, disent
            # quelque chose — cette stabilité-là est un résultat.
            "dispersion_pct": (round(100 * (max(prix) / min(prix) - 1), 1)
                               if len(prix) > 1 and min(prix) else None),
            "promotions": sum(1 for l in lignes if l.get("promotion")),
            "remises_lues": sum(1 for l in lignes if l.get("prix_unitaire_paye") is not None),
            "eur_kg_min": min(kilos) if kilos else None,
            "eur_kg_max": max(kilos) if kilos else None,
            "id_matiere": matiere,
            "statut_rattachement": statut,
            "verdicts": verdicts,
            "premier_achat": lignes[0]["date_facture"],
            "dernier_achat": lignes[-1]["date_facture"],
        })
    enregistrements.sort(key=lambda e: -e["depense_ht"])
    return enregistrements


def _nombre(valeur, decimales=3, suffixe=""):
    return "—" if valeur is None else f"{valeur:.{decimales}f}{suffixe}"


def _ligne_html(e):
    fourchette = "—"
    if e["prix_min"] is not None:
        fourchette = (_nombre(e["prix_min"]) if e["prix_min"] == e["prix_max"]
                      else f"{e['prix_min']:.3f} → {e['prix_max']:.3f}")
    kilo = "—"
    if e["eur_kg_min"] is not None:
        kilo = (_nombre(e["eur_kg_min"]) if e["eur_kg_min"] == e["eur_kg_max"]
                else f"{e['eur_kg_min']:.3f} → {e['eur_kg_max']:.3f}")
    verdicts = "".join(f'<span class="v {html.escape(v)}">{html.escape(v)}</span>'
                       for v in e["verdicts"]) or "—"
    reserve = ('<span class="reserve">réserve</span>'
               if e["statut_rattachement"] == "A_VERIFIER" else "")
    return (
        "<tr>"
        f'<td class="mono">{html.escape(e["article"])}</td>'
        f'<td>{html.escape((e["designation"] or "").strip())}</td>'
        f'<td class="num">{e["achats"]}</td>'
        f'<td class="num">{e["depense_ht"]:.2f}</td>'
        f'<td class="num mono">{fourchette}</td>'
        f'<td class="num">{_nombre(e["dispersion_pct"], 1, " %")}</td>'
        f'<td class="num mono">{kilo}</td>'
        f'<td>{html.escape(e["id_matiere"] or "—")}{reserve}</td>'
        f"<td>{verdicts}</td>"
        "</tr>")


def rendre(enregistrements, releve):
    total = sum(e["depense_ht"] for e in enregistrements)
    lignes = sum(e["achats"] for e in enregistrements)
    non_rattaches = [e for e in enregistrements if "NON_RATTACHE" in e["verdicts"]]
    bouges = [e for e in enregistrements
              if e["dispersion_pct"] is not None and e["dispersion_pct"] > 0]
    periode = releve.get("periode") or {}

    # Anti-bruit : une section ne s'affiche que si elle a quelque chose a dire. Les deux
    # ci-dessous sont peuplees sur les donnees actuelles, mais elles ne se rendent pas
    # vides le jour ou elles le seraient.
    section_bouges = ""
    if bouges:
        rangs = "".join(
            f"<tr><td class='mono'>{html.escape(e['article'])}</td>"
            f"<td>{html.escape((e['designation'] or '').strip())}</td>"
            f"<td class='num'>{e['achats']}</td>"
            f"<td class='num'>{e['depense_ht']:.2f}</td>"
            f"<td class='num mono'>{e['prix_min']:.3f} → {e['prix_max']:.3f}</td>"
            f"<td class='num fort'>{e['dispersion_pct']:.1f} %</td></tr>"
            for e in sorted(bouges, key=lambda e: -(e["dispersion_pct"] * e["depense_ht"]))[:25])
        section_bouges = f"""
  <h2>Articles dont le prix a bougé</h2>
  <p class="note">Le même article, chez le même fournisseur, à des dates différentes. Trié
  par dérive multipliée par la dépense : ce qui bouge beaucoup sur ce qu'on achète beaucoup.
  Le prix retenu est celui qui a été payé — la remise de volume vit sur une autre ligne que
  le tarif, et lire le tarif seul sous-estime la dérive.</p>
  <table><thead><tr><th>Article</th><th>Désignation</th><th class="num">Achats</th>
  <th class="num">Dépense HT</th><th class="num">Prix payé</th><th class="num">Dérive</th>
  </tr></thead><tbody>{rangs}</tbody></table>"""

    section_non_rattaches = ""
    if non_rattaches:
        rangs = "".join(
            f"<tr><td class='mono'>{html.escape(e['article'])}</td>"
            f"<td>{html.escape((e['designation'] or '').strip())}</td>"
            f"<td class='num'>{e['achats']}</td>"
            f"<td class='num'>{e['depense_ht']:.2f}</td></tr>"
            for e in non_rattaches)
        section_non_rattaches = f"""
  <h2>Articles non rattachés <span class="compte">{len(non_rattaches)}</span></h2>
  <p class="note">Énumérés, pas comptés : un compte ne dit pas quoi aller réparer. Le lien
  se pose dans <code>data/materials/rattachement_metro.csv</code>, avec sa note
  justificative. Cette liste ne dit pas lesquels sont des matières premières — le
  référentiel ne porte pas encore l'information, et le déduire du libellé est ce que
  <code>RATTACHEMENT.md</code> interdit. Le tri par dépense met en tête ceux qui comptent.</p>
  <table><thead><tr><th>Article</th><th>Désignation</th><th class="num">Achats</th>
  <th class="num">Dépense HT</th></tr></thead><tbody>{rangs}</tbody></table>"""

    corps = "".join(_ligne_html(e) for e in enregistrements)
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Factures METRO — vue d'ensemble</title>
<style>
  /* La taille de police suit la largeur : un ecran large rend de la place au lecteur au
     lieu de la laisser en marge. Tout le reste est en rem, donc ce reglage emporte la page. */
  html {{ font-size: clamp(16px, 0.5vw + 12px, 22px); }}
  :root {{ --encre:#1b1b1b; --gris:#6b6b6b; --trait:#dcdcdc; --fond:#faf9f7;
          --garder:#1f7a4d; --changer:#b3541e; --arbitrer:#8a6d1f;
          --hors:#6b6b6b; --non:#9b2226; }}
  * {{ box-sizing:border-box }}
  body {{ margin:0; padding:2.5rem 1rem; background:var(--fond); color:var(--encre);
         font:1rem/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
  main {{ max-width:min(78rem, 96vw); margin:0 auto }}
  h1 {{ font-size:1.6rem; margin:0 0 .3rem }}
  h2 {{ font-size:1.15rem; margin:2.5rem 0 .4rem }}
  p.sous {{ color:var(--gris); margin:0 0 1.6rem }}
  p.note {{ color:var(--gris); margin:0 0 .9rem; font-size:.9rem; max-width:62rem }}
  .chiffres {{ display:flex; gap:.5rem; flex-wrap:wrap; margin:1.2rem 0 }}
  .chiffre {{ border:1px solid var(--trait); border-radius:.6rem; padding:.5rem .8rem;
             background:#fff; font-size:.88rem }}
  .chiffre b {{ display:block; font-size:1.25rem; font-variant-numeric:tabular-nums }}
  .compte {{ font-size:.85rem; color:var(--gris); font-weight:400 }}
  table {{ border-collapse:collapse; width:100%; background:#fff; font-size:.88rem }}
  th, td {{ text-align:left; padding:.45rem .6rem; border-bottom:1px solid var(--trait);
           vertical-align:top }}
  th {{ font-weight:600; font-size:.8rem; text-transform:uppercase; letter-spacing:.04em;
       color:var(--gris) }}
  td.num, th.num {{ text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap }}
  td.mono {{ font-family:ui-monospace, SFMono-Regular, Menlo, monospace; white-space:nowrap }}
  td.fort {{ font-weight:600 }}
  .v {{ font-weight:600; font-size:.78rem; white-space:nowrap; margin-right:.3rem }}
  .v.GARDER {{ color:var(--garder) }} .v.CHANGER {{ color:var(--changer) }}
  .v.A_ARBITRER {{ color:var(--arbitrer) }} .v.HORS_PERIMETRE {{ color:var(--hors) }}
  .v.NON_RATTACHE {{ color:var(--non) }}
  .reserve {{ display:inline-block; margin-left:.35rem; padding:.05rem .4rem;
             border-radius:.25rem; background:#f6efdc; color:var(--arbitrer);
             font-size:.72rem; font-weight:600 }}
  .defilant {{ overflow-x:auto }}
  footer {{ margin:2.5rem 0 0; color:var(--gris); font-size:.85rem; max-width:62rem }}
  code {{ font-size:.92em }}
</style>
</head>
<body>
<main>
  <h1>Factures METRO — vue d'ensemble</h1>
  <p class="sous">{lignes} lignes d'achat, {len(enregistrements)} articles distincts,
  du {periode.get('debut', '—')} au {periode.get('fin', '—')}.</p>

  <div class="chiffres">
    <div class="chiffre"><b>{total:.2f} €</b>dépense HT</div>
    <div class="chiffre"><b>{len(enregistrements)}</b>articles</div>
    <div class="chiffre"><b>{len(bouges)}</b>dont le prix a bougé</div>
    <div class="chiffre"><b>{len(non_rattaches)}</b>non rattachés</div>
  </div>
{section_bouges}

  <h2>Tous les articles</h2>
  <p class="note">Un article par ligne, du plus coûteux au moins coûteux. La dérive est
  absente quand l'article n'a été acheté qu'une fois : il n'y a alors rien à comparer, et
  afficher 0 % ferait lire une stabilité que personne n'a mesurée.</p>
  <div class="defilant">
  <table><thead><tr><th>Article</th><th>Désignation</th><th class="num">Achats</th>
  <th class="num">Dépense HT</th><th class="num">Prix payé</th><th class="num">Dérive</th>
  <th class="num">EUR/kg</th><th>Matière</th><th>Proposition</th>
  </tr></thead><tbody>{corps}</tbody></table>
  </div>
{section_non_rattaches}

  <footer>
    Prix payés par nous, comparés entre eux. Ni un prix de référence, ni un prix catalogue,
    ni un coût rendu : METRO est un cash &amp; carry, le montant facturé est le coût au
    dépôt, et l'enlèvement n'est porté par aucune facture.
    Aucune colonne « meilleur fournisseur » : le dépôt ne porte aucun prix concurrent sur
    ces articles. Le verdict <b>CHANGER</b> exige un prix alternatif chiffré et daté.
    Source : <code>{html.escape(releve.get('dataset', '—'))}</code>,
    relevé du {html.escape(releve.get('observed_at', '—'))}.
  </footer>
</main>
</body>
</html>
"""


def main(argv):
    if len(argv) < 2 or argv[1] != "rendre":
        sys.exit(__doc__.strip().splitlines()[-1])

    achats, releve = cf.charger()
    rattachement, matieres = cf.charger_referentiels()
    enregistrements = agreger(achats, cf.verdicts(achats, rattachement, matieres))

    if "--out" in argv:
        sortie = Path(argv[argv.index("--out") + 1])
    else:
        sortie = Path(tempfile.gettempdir()) / f"rapport_factures_{releve.get('observed_at')}.html"
    sortie.write_text(rendre(enregistrements, releve), encoding="utf-8")

    total = sum(e["depense_ht"] for e in enregistrements)
    bouges = [e for e in enregistrements if e["dispersion_pct"]]
    print(f"{len(enregistrements)} articles, {sum(e['achats'] for e in enregistrements)} lignes, "
          f"{total:.2f} EUR HT")
    print(f"{len(bouges)} articles dont le prix a bouge, "
          f"{len([e for e in enregistrements if 'NON_RATTACHE' in e['verdicts']])} non rattaches")
    print(f"ecrit: {sortie}")


if __name__ == "__main__":
    main(sys.argv)
