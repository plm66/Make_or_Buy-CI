# MANITA_GARNITURE_DISCOVERY — instruction de recherche

Passe de sourcing pour la colonne **GARNITURE**, anciennement COMPLEMENT. Même discipline
que la passe snack : aucun prix inventé, aucun coût effectif annoncé sans son calcul.

## Ce qui change par rapport à une recherche « féculents en barquette »

Trois voies, pas une. Elles ne demandent pas le même travail interne et ne visent donc pas
le même prix rendu.

| Voie | Type | Travail interne restant | Priorité |
|---|---|---|---|
| **A** | `READY_PORTION` | réchauffage seulement | 1 |
| **B** | `COOKED_BULK_PORTIONABLE` | réchauffage + portionnage | 2 |
| **C** | `DRY_HIGH_YIELD` | cuisson + portionnage + conservation | 3 |

La cible de 0,15-0,30 € rendu pièce ne vaut **que pour la voie A**. Pour B, viser plus bas :
le portionnage reste à payer. Pour C, viser plus bas encore : cuisson, main-d'œuvre,
refroidissement, portionnage et emballage reviennent tous dans le coût effectif — c'est G002
qui s'applique de nouveau.

## Familles recherchées

pomme de terre · riz · pâtes · couscous et semoule · boulgour · quinoa · lentilles et
légumes secs · mélanges céréaliers

## Fournisseurs, par ordre

1. **Coup de Pâtes** — catégorie `GARNITURES` explicite, dont des individuels déjà portionnés
2. **Transgourmet** — grossiste, DIRECT, `ADMITTED_CONDITIONAL`
3. **Sysco France** — DIRECT, `ADMITTED_CONDITIONAL`
4. **Domafrais / France Frais** — DIRECT, `ADMITTED_CONDITIONAL`
5. **Tipiak Restauration** — `MANUFACTURER_REFERENCE`, voie C uniquement

Rappel du registre : Tipiak est un **fabricant**, non commandable en direct. Son offre
`Accompagnements céréaliers` est du sec en 1 à 4,5 kg avec rendement après réhydratation —
c'est de la voie C, pas des barquettes finies. Ses références sont sourçables, leur prix
rendu suppose un distributeur.

## Grammage : ne rien imposer

**Ne pas fixer 120-180 g.** Une pomme de terre Anna individuelle fait 60 g. Dans un panier
qui porte déjà quatre autres éléments, 70 à 120 g de garniture peut être plus cohérent
qu'une portion de restauration classique. Relever le grammage réel, ne pas filtrer dessus.

## Calcul exigé pour chaque candidat

```
prix rendu
+ remise en température
+ main-d'œuvre de portionnage
+ emballage
+ pertes attendues
= SELECTED_EFFECTIVE_PRODUCT_COST
```

**Ne jamais classer sur le coût matière brut.** C'est la dette G002, fermée dans le moteur
le 2026-09-11 : le coût matière sous-estimait le coût interne d'un facteur deux à sept.

L'emballage est une variable de design du panier, pas un attribut du produit — relever ce
que le fournisseur conditionne, sans présumer qu'une barquette individuelle scellée sera
nécessaire. Voir `packaging_model` dans `manita.config.json`.

## Interdits

- Déduire un prix pièce d'un prix au kilo sans le grammage réel de la portion
- Confondre **pâte feuilletée** et **pâtes alimentaires** — le référentiel porte `PATI-PATE`
  pour la première, le faux ami est avéré
- Annoncer un `effective_manita_cost_eur` sans avoir chiffré le travail restant
- Traiter un prix catalogue fabricant comme un prix rendu : sans distributeur identifié,
  c'est `QUOTE_REQUIRED`
- Extrapoler une allégation alimentaire depuis une absence d'ingrédient

## Livrable

30 candidats au format de `data/supplier_products/snack_buy_candidates.json`, avec
`candidate_track` valant `READY_PORTION`, `COOKED_BULK_PORTIONABLE` ou `DRY_HIGH_YIELD`,
`registry_supplier_id` pointant vers une fiche de `data/suppliers/`, et
`landed_cost_eur_per_piece` à `null` tant qu'un devis courant n'existe pas — le prix
historique vivant séparément en `reference_price_eur_per_piece`.
