"""Composition de grilles à prix cible.

Une grille est un tableau colonnes × lignes où chaque cellule est un produit distinct et
où le total des prix de chaque ligne se tient au voisinage d'une cible. Le cas d'usage
d'origine est la manita — 5 colonnes, 10 lignes, 5 € — mais rien ici n'est spécifique à
cette configuration.

Distinct de `engine.compose_menus`, qui classe des combinaisons indépendantes en
maximisant l'écart au prix cible. Ici l'écart est une contrainte, pas un score.
"""
from __future__ import annotations


# Le prix sommé n'est pas forcément celui de la vitrine. Une ligne à 5 € composée de cinq
# prix carte est structurellement hors d'atteinte — le minimum du catalogue d'exemple est
# de 10,10 €. Une grille à prix cible somme le prix-en-formule, qui est un autre champ.
CHAMP_PRIX_DEFAUT = "sale_price_eur"


def prix(item, champ=CHAMP_PRIX_DEFAUT):
    v = item.get(champ)
    return float(v) if isinstance(v, (int, float)) else 0.0


def _cherche(pools, index, somme, cible, tolerance, choix, champ):
    """Descente en profondeur sur les colonnes, élaguée par les bornes du reste.

    À chaque colonne on connaît le total minimal et maximal encore atteignable : si même
    le moins cher fait dépasser, ou si même le plus cher n'atteint pas la cible, la
    branche est morte. C'est ce qui rend l'exhaustif praticable — sans élagage on
    énumère le produit cartésien des colonnes."""
    if index == len(pools):
        return list(choix) if cible <= somme <= cible + tolerance else None

    reste = pools[index + 1:]
    mini = sum(prix(p[0], champ) for p in reste if p)
    maxi = sum(prix(p[-1], champ) for p in reste if p)

    for item in pools[index]:
        s = somme + prix(item, champ)
        if s + mini > cible + tolerance:
            break            # colonne triée: tous les suivants sont pires
        if s + maxi < cible:
            continue
        choix.append(item)
        trouve = _cherche(pools, index + 1, s, cible, tolerance, choix, champ)
        choix.pop()
        if trouve:
            return trouve
    return None


def compose_grille(catalogue, colonnes, lignes=10, cible=5.0, tolerance=0.5, eligible=None,
                   champ_prix=CHAMP_PRIX_DEFAUT):
    """Grille de `lignes` lignes, une cellule par colonne, chaque produit employé une fois.

    Rend (grille, manques) : les lignes trouvées, et les colonnes qui n'avaient pas assez
    de produits distincts pour aller au bout. Une grille courte est un résultat, pas une
    erreur — elle dit combien de références manquent.
    """
    dispo = {c: sorted((p for p in catalogue
                        if p.get("family") == c and (eligible is None or eligible(p))),
                       key=lambda i: prix(i, champ_prix))
             for c in colonnes}
    manques = {c: lignes - len(v) for c, v in dispo.items() if len(v) < lignes}

    grille = []
    for _ in range(lignes):
        pools = [dispo[c] for c in colonnes]
        if any(not p for p in pools):
            break
        ligne = _cherche(pools, 0, 0.0, cible, tolerance, [], champ_prix)
        if ligne is None:
            break
        grille.append({"total_eur": round(sum(prix(i, champ_prix) for i in ligne), 2),
                       "items": [{"id": i["id"], "name": i["name"], "family": i["family"],
                                  champ_prix: prix(i, champ_prix)} for i in ligne]})
        for c, item in zip(colonnes, ligne):
            dispo[c].remove(item)
    return grille, manques


# --------------------------------------------------- pont vers le validateur du postulat

def adapte_pour_validateur(catalogue, cout_effectif):
    """Catalogue legacy augmenté du coût que le postulat veut voir.

    `manita.config.json` demande le SELECTED_EFFECTIVE_PRODUCT_COST — le coût ajusté par
    le sourcing, pas le coût matière brut. Le format legacy expose les deux moitiés
    (`internal.material_cost_eur`, `external.landed_cost_eur`) sans jamais le choix ; c'est
    `engine.selected_cost` qui tranche. Le validateur livré lit un `cost_eur` de haut
    niveau, documenté comme son point d'extension : on l'y dépose sans le modifier.

    Un coût inconnu reste absent plutôt que nul — le validateur rend alors
    DATA_INCOMPLETE, ce que le contrat d'agent exige au lieu d'une décision fabriquée.
    """
    adapte = []
    for produit in catalogue:
        cout, _ = cout_effectif(produit)
        copie = dict(produit)
        if isinstance(cout, (int, float)):
            copie["cost_eur"] = cout
        adapte.append(copie)
    return adapte
