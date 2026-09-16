"""Invariants de la dérive des prix payés, même article, d'une facture à l'autre.

Un prix payé n'est pas un prix de référence : il vaut pour un conditionnement, une date et
un dépôt. Comparer deux prix unitaires sans vérifier que le conditionnement n'a pas bougé
produit un chiffre qui a l'air d'un fait et n'en est pas un. C'est le défaut de la maison :
le nombre est exact, il porte juste un autre sens que celui qu'on lui prête.

Ces invariants tiennent la seule règle qui compte ici : pas de chiffre sans alignement
déclaré. Quand la base de comparaison a changé ou qu'une promotion s'en mêle, la sortie
porte un statut et un trou, jamais un delta.
"""
import json
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))

import comparaison_factures as cf  # noqa: E402


def ligne(**kw):
    base = {
        "facture": "001-000001", "date_facture": "2026-01-10", "depot": "METRO PARIS12",
        "ean": "3000000000001", "article": "1234567", "designation": "FARINE T65 25KG",
        "prix_unitaire_ht": 1.0, "colisage": 1, "quantite": 1, "poids_facture_kg": None,
        "unites_facturees": 1, "montant_ht": 1.0, "code_tva": "B", "promotion": False,
        "remise_ht": None, "prix_unitaire_paye": None, "prix_unite_normalisee": None,
        "controle_arithmetique": "OK",
    }
    base.update(kw)
    return base


def test_deux_observations_du_meme_article_sont_comparees_et_datees():
    """Le cas normal : même conditionnement, aucune promotion, deux dates. Le delta existe
    et la comparaison dit de quand à quand."""
    achats = [
        ligne(date_facture="2026-01-10", facture="001", prix_unitaire_ht=1.0),
        ligne(date_facture="2026-03-05", facture="002", prix_unitaire_ht=1.2),
    ]
    (c,) = cf.derive(achats)
    assert c["statut"] == cf.ALIGNED, c
    assert c["date_a"] == "2026-01-10" and c["date_b"] == "2026-03-05", c
    assert round(c["delta_eur"], 4) == 0.2, c
    assert round(c["delta_pct"], 1) == 20.0, c


def test_une_seule_observation_ne_donne_aucune_comparaison():
    """Un article vu une fois ne dérive pas : il est constaté. Rendre une comparaison avec
    lui-même fabriquerait un zéro qui se lirait comme une stabilité mesurée."""
    achats = [ligne(date_facture="2026-01-10")]
    assert cf.derive(achats) == []


def test_un_changement_de_conditionnement_interdit_le_chiffre():
    """Deux catalogues vendent le même produit à des formats différents. Si le colisage
    change entre deux factures, le prix unitaire ne mesure plus la même chose : la sortie
    doit porter UNIT_GAP et aucun delta."""
    achats = [
        ligne(date_facture="2026-01-10", colisage=12, prix_unitaire_ht=1.0),
        ligne(date_facture="2026-03-05", colisage=24, prix_unitaire_ht=0.6),
    ]
    (c,) = cf.derive(achats)
    assert c["statut"] == cf.UNIT_GAP, c
    assert c["delta_eur"] is None and c["delta_pct"] is None, c


def test_un_article_vendu_au_poids_change_de_base_si_le_poids_change():
    """Pour un article vendu au poids, la base n'est pas le colisage mais le poids facturé.
    Le champ null d'un côté et rempli de l'autre est déjà un changement de base."""
    achats = [
        ligne(date_facture="2026-01-10", colisage=None, poids_facture_kg=5.0),
        ligne(date_facture="2026-03-05", colisage=1, poids_facture_kg=None),
    ]
    (c,) = cf.derive(achats)
    assert c["statut"] == cf.UNIT_GAP, c


def test_une_promotion_de_l_un_des_deux_cotes_exclut_la_comparaison():
    """Une ligne en promotion ne porte pas le tarif. Le prix affiché y côtoie une remise qui
    vit sur une autre ligne, et `prix_unitaire_paye` reste nul tant qu'aucune remise n'a été
    lue. Comparer ce prix à un prix normal mesurerait la promotion, pas la dérive."""
    achats = [
        ligne(date_facture="2026-01-10", promotion=True, prix_unitaire_ht=1.0),
        ligne(date_facture="2026-03-05", promotion=False, prix_unitaire_ht=1.2),
    ]
    (c,) = cf.derive(achats)
    assert c["statut"] == cf.PROMO_EXCLUDED, c
    assert c["delta_eur"] is None and c["delta_pct"] is None, c


def test_aucun_chiffre_ne_sort_sans_alignement():
    """L'invariant qui tient tous les autres : un delta n'existe que si le statut dit
    ALIGNED. Une baisse de prix qui est en réalité un changement de format est le piège que
    ce test ferme."""
    achats = [
        ligne(date_facture="2026-01-10", prix_unitaire_ht=2.0),
        ligne(date_facture="2026-02-01", prix_unitaire_ht=1.0, colisage=6),
        ligne(date_facture="2026-03-01", prix_unitaire_ht=1.1, promotion=True),
        ligne(date_facture="2026-04-01", prix_unitaire_ht=1.15),
    ]
    for c in cf.derive(achats):
        if c["statut"] != cf.ALIGNED:
            assert c["delta_eur"] is None, c
            assert c["delta_pct"] is None, c


def test_le_prix_paye_prime_sur_le_prix_imprime_quand_il_existe():
    """`prix_unitaire_ht` est le tarif imprimé, `prix_unitaire_paye` le montant après remise.
    Le champ utilisé doit être nommé dans la comparaison, sinon on ne sait pas ce qu'on
    compare."""
    achats = [
        ligne(date_facture="2026-01-10", prix_unitaire_ht=1.0, prix_unitaire_paye=None),
        ligne(date_facture="2026-03-05", prix_unitaire_ht=1.2, prix_unitaire_paye=1.05,
              remise_ht=-0.15),
    ]
    (c,) = cf.derive(achats)
    assert c["champ_prix"] == ["prix_unitaire_ht", "prix_unitaire_paye"], c
    assert round(c["prix_b"], 4) == 1.05, c
    assert c["statut"] == cf.ALIGNED, c


def test_les_comparaisons_sont_ordonnees_par_date():
    """Une dérive se lit dans l'ordre du temps. Une comparaison qui remonte le temps se
    lirait comme une hausse quand c'est une baisse."""
    achats = [
        ligne(date_facture="2026-05-01", prix_unitaire_ht=3.0),
        ligne(date_facture="2026-01-10", prix_unitaire_ht=1.0),
        ligne(date_facture="2026-03-05", prix_unitaire_ht=2.0),
    ]
    comparaisons = cf.derive(achats)
    assert [c["date_a"] for c in comparaisons] == ["2026-01-10", "2026-03-05"], comparaisons
    assert [c["date_b"] for c in comparaisons] == ["2026-03-05", "2026-05-01"], comparaisons


def test_trois_observations_donnent_deux_comparaisons_consecutives():
    """On compare chaque observation à la précédente, pas toutes à la première : un article
    qui monte puis redescend doit montrer les deux mouvements."""
    achats = [
        ligne(date_facture="2026-01-10", prix_unitaire_ht=1.0),
        ligne(date_facture="2026-03-05", prix_unitaire_ht=1.5),
        ligne(date_facture="2026-05-01", prix_unitaire_ht=1.25),
    ]
    comparaisons = cf.derive(achats)
    assert len(comparaisons) == 2, comparaisons
    assert [round(c["delta_eur"], 2) for c in comparaisons] == [0.5, -0.25]


def test_deux_articles_ne_se_comparent_pas_entre_eux():
    """La clé est l'article METRO, jamais la désignation : deux libellés proches sont deux
    produits différents, et un rapprochement par le nom est ce que le dépôt interdit."""
    achats = [
        ligne(article="1111111", designation="CROISSANT PAC 60G", prix_unitaire_ht=0.4),
        ligne(article="2222222", designation="CROISSANT PAC 60G", prix_unitaire_ht=0.9,
              date_facture="2026-03-05"),
    ]
    assert cf.derive(achats) == []


if __name__ == "__main__":
    for nom, fn in sorted(globals().items()):
        if nom.startswith("test_"):
            fn()
            print(f"OK  {nom}")