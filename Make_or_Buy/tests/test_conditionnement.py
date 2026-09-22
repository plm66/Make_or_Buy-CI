"""Invariants du conditionnement lu dans une désignation fournisseur.

Le prix unitaire d'une facture vaut pour un conditionnement précis. Sans lui, un prix ne se
compare à rien : `LEVURE 500G*5 HIRONDELLE 2,5KG` porte le poids du sachet ET le poids
total, et lire le premier donne 12,76 EUR/kg là où la facture imprime 2,552.

Le garde-fou est le document lui-même : certaines lignes METRO portent, sur la ligne
suivante du PDF, le prix unitaire normalisé que l'extracteur a déjà relevé dans
`prix_unite_normalisee`. Quand cette valeur existe, elle juge notre lecture. Un désaccord
est une erreur de notre côté, jamais de son côté.

Un conditionnement illisible ne devient pas un chiffre : la lecture rend None, et l'appelant
déclare le trou.
"""
import json
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))

import comparaison_factures as cf  # noqa: E402

RELEVE = RACINE / "data/price_observations/metro_factures_2026-09-11.json"


def test_le_poids_total_prime_sur_le_poids_du_sachet():
    """Le cas qui a produit 12 nombres faux : deux poids dans la désignation, le sachet et
    le total. C'est le total qui donne son sens au prix unitaire imprime."""
    assert cf.poids_total_g("LEVURE 500G*5 HIRONDELLE 2,5KG") == 2500
    assert cf.poids_total_g("ARO CHOCO NOIR 5*100GRS") == 500


def test_un_multiplicateur_se_calcule():
    """`2X2,5KG` et `5*100GRS` n'écrivent pas le total, ils l'impliquent."""
    assert cf.poids_total_g("MEL 7 GRAINES 2X2,5KG CT B/PAT") == 5000
    assert cf.poids_total_g("CHOCOLAT 5*100GRS") == 500


def test_un_poids_simple_se_lit_tel_quel():
    """Le cas courant : un seul poids, en kilos ou en grammes."""
    assert cf.poids_total_g("MC FARINE PANIF. T65 25KG") == 25000
    assert cf.poids_total_g("BEURRE DX 500G MA PAYSANNE") == 500
    assert cf.poids_total_g("GROS SEL TRAD SAC 10KG") == 10000


def test_sans_taille_dans_la_designation_aucun_poids():
    """Un produit vendu à la pièce n'a pas de poids dans son libellé. Rendre un chiffre
    inventé ferait entrer une conversion devinée dans chaque recette qui l'utilise."""
    assert cf.poids_total_g("MP CASSEROLE INOX D28CM") is None
    assert cf.poids_total_g("200 SAC COURT 1 BAGUETTE") is None


def test_un_volume_n_est_pas_un_poids():
    """`33CL` et `1L` sont des volumes. Les confondre avec une masse produirait des EUR/kg
    qui seraient en réalité des EUR/L, le défaut que le dépôt traque."""
    assert cf.poids_total_g("COCA SANS SUCRES 33CL") is None
    assert cf.poids_total_g("PREPA TIRAMISU MASCAR. 1L GALB") is None


def test_le_prix_au_kilo_exige_un_poids_connu():
    """Pas de poids, pas de prix au kilo. Le trou est déclaré, jamais comblé par le prix du
    colis qui, lui, existe toujours."""
    assert cf.prix_au_kilo({"designation": "MP CASSEROLE INOX D28CM", "prix_unitaire_ht": 42.87}) is None
    beurre = cf.prix_au_kilo({"designation": "BEURRE DX 500G MA PAYSANNE", "prix_unitaire_ht": 3.65})
    assert beurre == {"valeur": 7.3, "source": "DESIGNATION_SIMPLE", "poids_g": 500}, beurre


def test_un_volume_n_a_pas_de_prix_au_kilo_meme_imprime():
    """`prix_unite_normalisee` existe pour des boissons, où il vaut des EUR/L. Sans masse
    dans la désignation, l'unité n'est déclarée nulle part, donc le champ ne peut pas servir
    de prix au kilo."""
    coca = {"designation": "COCA SANS SUCRES 33CL", "prix_unitaire_ht": 0.522,
            "prix_unite_normalisee": 1.582}
    assert cf.prix_au_kilo(coca) is None


def test_un_abrege_de_colis_interdit_le_prix_au_kilo():
    """BQ12, X30, 4/4, PLT : le multiplicateur de colis s'écrit en abrégé fournisseur et
    n'est pas lisible. C'est la cause unique des quatre écarts mesurés contre le prix
    imprimé. Sans prix imprimé, la ligne ne donne donc rien."""
    fraise = {"designation": "FRAISE 500G BQ8 C1 BEBELGIQUE", "prix_unitaire_ht": 4.99,
              "prix_unite_normalisee": None}
    assert cf.prix_au_kilo(fraise) is None
    assert cf.prix_derive_au_kilo(fraise) is None
    fraise_imprimee = dict(fraise, prix_unite_normalisee=1.248)
    assert cf.prix_au_kilo(fraise_imprimee)["source"] == "IMPRIME_FACTURE"


def test_le_colisage_compte_parfois_des_kilos_pas_des_pieces():
    """`MC FARINE PANIF. T65 25KG` porte un colisage de 25 : l'unité facturée est le kilo,
    pas le sac, et la facture imprime alors 0,75 EUR/kg. Diviser par le poids du sac au lieu
    du poids de l'unité facturée donnait 0,03 EUR/kg, dix fois sous le prix de la matière
    première agricole, et rien ne le signalait."""
    farine = {"designation": "MC FARINE PANIF. T65 25KG", "colisage": 25,
              "prix_unitaire_ht": 0.75, "prix_unite_normalisee": None}
    assert cf.poids_unite_facturee_g(farine) == 1000
    assert cf.prix_au_kilo(farine)["valeur"] == 0.75
    beurre = {"designation": "BEURRE DX 500G MA PAYSANNE", "colisage": 1,
              "prix_unitaire_ht": 3.65, "prix_unite_normalisee": None}
    assert cf.poids_unite_facturee_g(beurre) == 500


def test_le_prix_imprime_par_la_facture_confirme_la_lecture():
    """Le seul juge disponible, et il est dans le document. Sur les lignes où METRO imprime
    son propre prix normalisé, notre déduction doit tomber juste. Le test vérifie aussi que
    le sous-ensemble n'est pas vide, sans quoi il passerait sans rien vérifier."""
    achats = json.loads(RELEVE.read_text(encoding="utf-8"))["achats"]
    juges = 0
    for x in achats:
        if x["prix_unite_normalisee"] is None:
            continue
        notre = cf.prix_derive_au_kilo(x)
        if notre is None:
            continue
        juges += 1
        imprime = x["prix_unite_normalisee"]
        assert abs(notre - imprime) <= 0.02 * imprime, (
            x["article"], x["designation"], cf.poids_total_g(x["designation"]), notre, imprime)
    assert juges >= 10, f"seulement {juges} lignes jugées, le test ne prouve presque rien"


def test_un_volume_liquide_se_lit_en_millilitres():
    """`5L`, `33CL` et `50CL` sont convertis en millilitres."""
    assert cf.volume_total_ml("MAUREL HLE TOURNESOL 5L") == 5000
    assert cf.volume_total_ml("CAPRISUN MANG PASSION 33CL") == 330
    assert cf.volume_total_ml("CRISTALI 50CL PET") == 500
    assert cf.volume_total_ml("CREME UHT 35% 1L BK MC") == 1000


def test_le_prix_au_litre_exige_un_volume_connu():
    """Sans volume lisible, aucun prix au litre n'est rendu."""
    assert cf.prix_au_litre({"designation": "MP CASSEROLE INOX D28CM", "prix_unitaire_ht": 42.87}) is None
    creme = cf.prix_au_litre({"designation": "PREPA TIRAMISU MASCAR. 1L GALB", "prix_unitaire_ht": 7.95, "colisage": 1})
    assert creme == {"valeur": 7.95, "source": "DESIGNATION_SIMPLE", "volume_ml": 1000}, creme


def test_le_prix_imprime_confirme_la_lecture_au_litre():
    """Sur les boissons ou METRO imprime EUR/L, notre lecture s'aligne sur le document."""
    pepsi = {"designation": "PEPSI REGULAR SLIM 33CL", "prix_unitaire_ht": 0.454,
             "prix_unite_normalisee": 1.376, "colisage": 24}
    assert cf.prix_au_litre(pepsi)["valeur"] == 1.376
    cristali = {"designation": "CRISTALI 50CL PET", "prix_unitaire_ht": 0.128,
                "prix_unite_normalisee": 0.256, "colisage": 24}
    assert cf.prix_au_litre(cristali)["valeur"] == 0.256


def test_prix_normalise_distingue_kilo_et_litre():
    """La fonction unifiee porte l'unite exacte : EUR/kg pour solide, EUR/L pour liquide."""
    beurre = cf.prix_normalise({"designation": "BEURRE DX 500G MA PAYSANNE", "prix_unitaire_ht": 3.65})
    assert beurre["unite"] == "EUR/kg"
    assert beurre["valeur"] == 7.3
    huile = cf.prix_normalise({"designation": "MAUREL HLE TOURNESOL 5L", "prix_unitaire_ht": 1.998, "colisage": 5})
    assert huile["unite"] == "EUR/L"
    assert huile["valeur"] == 1.998


def test_les_boites_et_pieces_ont_leur_unite():
    """Les boites (4/4) et pieces (PC) portent leur unite EUR/boite ou EUR/piece."""
    abricot = cf.prix_normalise({"designation": "METRO CHEF OREIL. ABRICOT 4/4", "prix_unitaire_ht": 2.758, "colisage": 6})
    assert abricot["unite"] == "EUR/boite"
    assert abricot["valeur"] == 2.758
    melon = cf.prix_normalise({"designation": "MELON DINO BOLLO PC6 ES ESPAGNE", "prix_unitaire_ht": 2.69, "colisage": 1})
    assert melon["unite"] == "EUR/piece"
    assert melon["valeur"] == 2.69


if __name__ == "__main__":
    for nom, fn in sorted(globals().items()):
        if nom.startswith("test_"):
            fn()
            print(f"OK  {nom}")