# Rattachement croisé Coup de Pâtes → génériques Bridor

**Date de collecte :** 2026-09-10
**Fournisseur testé :** Coup de Pâtes (shop.coupdepates.fr, pages produit publiques)
**Table de vérité :** les 27 génériques existants (axe 1) — Viennoiserie, Pâtisserie, Snacking

## Méthode

- Index de 605 références vues dans les 4 catégories ciblées : VIENNOISERIE (c/022, 195 réf.), PÂTISSERIE (c/010, 243), VIENNOISERIE-PÂTISSERIE-AMÉRICAINE (c/056, 73, classés PATI), SNACKING (c/019, 94) → `coup_de_pates_index.csv`. Les madeleines Coup de Pâtes sont classées par le fournisseur lui-même en VIENNOISERIE (c/022) — la famille du CSV est celle de la navigation fournisseur.
- 71 fiches détaillées collectées sur les pages produit officielles, en privilégiant les natures a priori rattachables (croissants, pains au chocolat, pains aux raisins, chaussons, briochettes, macarons, pastéis de nata, brioches feuilletées, breizh roll, croques) → `coup_de_pates_detail.csv`.
- Rattachement strict : **nature + garniture + grammage**. Un conditionnement, une gamme (Sélection, Secrets du Fournil, D'Hubert…) ou un argument marketing ne crée pas un générique différent.

## Résultat

| Indicateur | Valeur |
|---|---|
| SKU détaillés | 71 |
| **Rattachés à un générique EXISTANT** | **6 (8,5 %)** |
| NOUVEAU (générique proposé) | 65 |
| Cas douteux arbitrés | 9 |

### Les 6 rattachements réussis

| Réf. Cdp | Produit | Générique |
|---|---|---|
| 25960 | MINI PAIN CHOCOLAT 2 BARRES PRÉPOUSSÉ 25G | VIEN-PAIN-25 |
| 25004 | MINI PAIN CHOCOLAT 2 BARRES SÉLECTION PRÉPOUSSÉ 25G | VIEN-PAIN-25 |
| 70651 | MINI PAIN CHOCOLAT D'HUBERT PRÉPOUSSÉ 25G | VIEN-PAIN-25 |
| 25958 | MINI PAIN RAISIN PRÉPOUSSÉ 30G | VIEN-PAIN-30 |
| 25003 | MINI PAIN RAISIN SÉLECTION PRÉPOUSSÉ 30G | VIEN-PAIN-30 |
| 25144 | BRIOCHETTE BOULE 60G | VIEN-AUTR-60 |

C'est le résultat central du test, mesuré **sur l'échantillon détaillé de 71 SKU** (tiré volontairement dans les zones de recouvrement a priori ; le taux sur le catalogue complet serait plus faible encore). Les deux fournisseurs couvrent des zones de gamme différentes : Bridor (assortiment artisanal traditionnel) et Coup de Pâtes (gastro-professionnel large) partagent les natures de base, mais presque jamais le même grammage exact.

### Pourquoi 65 NOUVEAU — motifs dominants

1. **Croissants et pains au chocolat** : Coup de Pâtes travaille en 25–30g (mini) et 60–90g (standard) ; les génériques Bridor couvrent 40/50g (croissant) et 25/28/150g (pain au chocolat). Aucun croisement.
2. **Macarons** : les macarons Coup de Pâtes sont des macarons individuels dessert de 55 à 100g ; le générique PATI-MACA-12 est un macaron de 12g type petit-four. Nature proche, grammage et usage différents.
3. **Pastel de nata** : Coup de Pâtes propose un format unique à 66g ; les génériques sont à 35/50/60g (écart 66 vs 60 = cas douteux ci-dessous).
4. **Natures absentes de la table Bridor** : donuts, cookies, muffins, brownies, madeleines classiques, millefeuilles, quiches, croques, feuilletés salés, bretzels — aucun générique d'aucun grammage n'existe côté Bridor.

## Cas douteux (règle stricte appliquée, à arbitrer)

| Réf. | Situation | Décision appliquée |
|---|---|---|
| 28113 | Croissant aux amandes 85g vs VIEN-CROI-90b (90g) / VIEN-CROI-95 (95g) | NOUVEAU — grammage différent |
| 25130 | Chausson pomme 100g vs VIEN-AUTR-105 (105g) | NOUVEAU — écart 5g |
| 25115 | Chausson pomme Isigny 100g vs VIEN-AUTR-105 (105g) | NOUVEAU — écart 5g |
| 70667 | Brioche feuilletée 300g vs VIEN-AUTR-295 (295g) | NOUVEAU — écart 5g |
| 27156 | Pastel de nata 66g vs PATI-PAST-60 (60g) | NOUVEAU — écart 6g |
| 840821 | Mini pain chocolat 30g vs VIEN-PAIN-28 (28g) | NOUVEAU — écart 2g |
| 71358 | Breizh roll jambon-fromage 150g vs VIEN-AUTR-85 / SNAC-TOUT-85 (85g) | NOUVEAU — même nature, grammage très différent |
| 70652 | Fiche officielle contradictoire : intitulé « CRU », pictogramme « PRÉPOUSSÉ » | technologie = NON_RENSEIGNE |
| 835314 | Fiche officielle contradictoire : intitulé « CUIT », pictogramme « PRÉCUIT » | technologie = NON_RENSEIGNE |

Les écarts ≤ 6g (chausson, brioche feuilletée, pastel, mini pain chocolat) désignent probablement le même produit marché des deux côtés : si une tolérance de grammage (± 5-10 %) est validée dans le référentiel, ces 6 rattachements deviennent possibles et le taux passerait de 8,5 % à ~17 %.

## Champs non publiés par Coup de Pâtes (hors compte pro)

- **Prix : `price_access=ACCOUNT_REQUIRED`** — les tarifs sont réservés aux clients connectés ; aucune valeur de prix n'a été collectée ni estimée.
- Ingrédients, DDM, colis/palette, usine de provenance : non publiés sur les pages produit publiques → `n.d.` (jamais déduits).
- Allergènes : déclarés « Présence de / Traces de » sur la fiche officielle, normalisés en noms courts (gluten, œufs, lait, soja, fruits à coque, sésame…).
- `poids_colis_kg` est calculé mécaniquement (`poids_unitaire × unités_par_colis`), ce n'est pas un poids carton publié par le fournisseur.
- Statut : tout produit vu au catalogue est noté ACTIF (présence catalogue ≠ disponibilité de livraison confirmée).
- Labels : uniquement ceux portés par l'intitulé officiel (BIO, AOP, Pur beurre, Halal, Végétarien, Vegan). Aucun statut vegan/végétarien déduit d'un argument de catégorie.

## Fichiers livrés

- `coup_de_pates_index.csv` — 605 références vues dans les 3 familles (périmètre étendu aux 4 catégories les couvrant).
- `coup_de_pates_detail.csv` — 71 fiches détaillées, 22 colonnes conformes au schéma.
- `rattachement.md` — ce rapport.
