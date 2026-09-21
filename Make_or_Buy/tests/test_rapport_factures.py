"""Invariants de la vue d'ensemble des factures.

La vue agrège, elle ne décide pas : les verdicts, le prix au kilo et le prix payé viennent
tous de `comparaison_factures`. Ce qui doit être vrai ici porte donc sur l'agrégation — ne
perdre aucun article, ne pas inventer de dérive, et lire le bon prix.

Le relevé servi est un artefact daté (`metro_factures_2026-09-11.json`) : les chiffres figés
ci-dessous ne bougeront pas sous un nouvel arrivage, qui produirait un autre fichier.
"""
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))

import comparaison_factures as cf  # noqa: E402
import rapport_factures as rf  # noqa: E402

BEURRE = "2252104"


def _corpus():
    achats, releve = cf.charger()
    rattachement, matieres = cf.charger_referentiels()
    return achats, releve, rf.agreger(achats, cf.verdicts(achats, rattachement, matieres))


def test_la_derive_lit_le_prix_paye_et_non_le_tarif():
    """Le tarif imprimé survit intact à côté d'un montant qui ne lui correspond plus : la
    remise de volume vit sur une autre ligne, et `prix_unitaire_paye` la porte. Lire
    `prix_unitaire_ht` seul sous-estime la dérive du beurre d'un tiers — 15,3 % au lieu de
    22,5 sur le poste le plus cher des vingt factures. C'est G002 à l'étage du relevé.

    L'écart entre les deux chiffres est ce que ce test protège : s'ils se rejoignent, c'est
    que le mauvais champ est relu.
    """
    achats, _, enregistrements = _corpus()
    beurre = next(e for e in enregistrements if e["article"] == BEURRE)
    assert beurre["achats"] == 16, beurre["achats"]
    assert beurre["remises_lues"] == 4, beurre["remises_lues"]
    assert beurre["dispersion_pct"] == 22.5, beurre["dispersion_pct"]

    tarifs = [l["prix_unitaire_ht"] for l in achats if l["article"] == BEURRE]
    tarif_seul = round(100 * (max(tarifs) / min(tarifs) - 1), 1)
    assert tarif_seul == 15.3, tarif_seul
    assert beurre["dispersion_pct"] > tarif_seul, (
        "la dérive payée doit dépasser la dérive tarifaire tant que des remises existent")


def test_un_article_achete_une_seule_fois_ne_porte_aucune_derive():
    """Rendre 0 % ferait lire une stabilité mesurée là où rien n'a été comparé. Deux achats
    au même prix disent quelque chose ; un seul achat ne dit rien, et le dire quand même est
    la façon la plus discrète de fabriquer une donnée."""
    _, _, enregistrements = _corpus()
    uniques = [e for e in enregistrements if e["achats"] == 1]
    assert uniques, "aucun article acheté une seule fois : le corpus a changé de nature"
    assert all(e["dispersion_pct"] is None for e in uniques), (
        [e["article"] for e in uniques if e["dispersion_pct"] is not None])

    stables = [e for e in enregistrements
               if e["achats"] > 1 and e["dispersion_pct"] == 0]
    assert stables, "une stabilité mesurée doit rester distinguable d'une absence de mesure"


def test_la_vue_porte_tous_les_articles_pas_seulement_les_rattaches():
    """La comparaison servie est celle d'un article avec lui-même : elle ne demande aucun
    rattachement. Restreindre la vue aux articles rattachés ferait passer la couverture du
    référentiel pour une limite de la mesure, alors qu'elle ne borne que la comparaison
    fournisseur."""
    achats, _, enregistrements = _corpus()
    assert len(enregistrements) == len({l["article"] for l in achats})
    rattachement, _ = cf.charger_referentiels()
    assert len(enregistrements) > len(rattachement), (
        "la vue doit dépasser le périmètre du rattachement")


def test_aucune_ligne_ni_aucun_euro_ne_se_perd_dans_l_agregation():
    """Un total qui ne retombe pas sur ses pieds est un total faux, et rien ne le signale :
    une ligne perdue ressemble à une ligne qui n'existait pas."""
    achats, _, enregistrements = _corpus()
    assert sum(e["achats"] for e in enregistrements) == len(achats)
    attendu = round(sum(l["montant_ht"] for l in achats), 2)
    obtenu = round(sum(e["depense_ht"] for e in enregistrements), 2)
    assert abs(obtenu - attendu) < 0.01, (obtenu, attendu)


def test_les_verdicts_divergents_d_un_article_sont_tous_rendus():
    """Le verdict est une propriété de la ligne : un conditionnement illisible sur un seul
    achat suffit à le faire diverger. Réduire au premier masquerait précisément la ligne qui
    coince — et c'est cette liste-là qui dit quoi aller mesurer."""
    _, _, enregistrements = _corpus()
    assert all(e["verdicts"] for e in enregistrements), "un article sans verdict est un oubli"
    assert all(len(e["verdicts"]) == len(set(e["verdicts"])) for e in enregistrements)
    divergents = [e for e in enregistrements if len(e["verdicts"]) > 1]
    assert all(e["achats"] > 1 for e in divergents), (
        "un article acheté une fois ne peut pas porter deux verdicts")


if __name__ == "__main__":
    for nom, fn in sorted(globals().items()):
        if nom.startswith("test_"):
            fn()
            print(f"OK  {nom}")
