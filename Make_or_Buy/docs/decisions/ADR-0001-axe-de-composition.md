# ADR-0001 — L'axe de composition : frais et naturel, surgelé, chimique

- **Statut** : PROPOSED
- **Date** : 2026-09-12
- **Décide** : Philippe
- **Porte sur** : `doctrine/doctrine.json` — `criteria`, `guardrails`, `product_classes`

## Contexte

La mission de l'application est double, et seule la première moitié est aujourd'hui
outillée :

1. une base de données pour la décision de choix de produits — MAKE, BUY, HYBRID ;
2. une aide à la **fabrication hybride**, avec une proposition d'arbitrage sur le mélange
   intelligent du frais et du naturel avec le surgelé et le chimique.

La seconde n'a aucune existence normative. Ni critère, ni garde-fou, ni attribut produit.

## Le problème

La doctrine pondère huit critères dont la somme fait 1,00. Aucun ne mesure ce dont est
fait un produit.

| critère | poids | ce qu'il mesure |
|---|---|---|
| `CUSTOMER_INDIFFERENCE` | 0,20 | le client verrait-il la différence |
| `LABOR_SAVING` | 0,20 | temps qualifié supprimé |
| `SUPPLIER_QUALITY` | 0,15 | qualité et **régularité** |
| `AVOIDABLE_COST` | 0,15 | coût qui disparaît |
| `PURCHASING_STOCK_SIMPLIFICATION` | 0,10 | achats et stock |
| `CONSERVATION_LOSS` | 0,10 | pertes |
| `TRACEABILITY_INCIDENT` | 0,05 | traçabilité |
| `SUPPLIER_RISK` | 0,05 | risque fournisseur |

`SUPPLIER_QUALITY` semble proche mais ne l'est pas. Il demande « le produit externe est-il
au moins aussi bon et aussi régulier ? ». Un entremets industriel aromatisé à la vanilline
est régulier, bon, et marque fort. La régularité est même l'argument de vente de
l'aromatisation artificielle.

**Conséquence.** Le moteur peut rendre `BUY` sur un produit dont le seul défaut est sa
composition. Le refus humain qui suivrait serait hors doctrine : non tracé, non rejouable,
invisible dans l'arbitrage. C'est précisément le défaut que ce dépôt existe pour empêcher —
une décision qui ne remonte à aucune règle nommée.

## Ce que « chimique » doit vouloir dire pour être mesurable

« Chimique » ne peut pas rester un mot de conversation : tout ingrédient est chimique. La
définition qui rend l'axe opérant :

> Un composant est **substitutif** lorsqu'un additif ou un arôme y remplace un ingrédient
> qu'une recette fraîche contiendrait — vanilline pour la vanille, arôme fraise pour la
> fraise, colorant pour le fruit, texturant pour la crème.

Ce qui se mesure alors n'est pas une opinion mais une liste d'ingrédients. Et nous en
collectons déjà : `ingredients` et `allergenes_declares` dans les catalogues génériques,
les descriptions du catalogue Traiteur de Paris, les fiches techniques fournisseur.

Trois natures distinctes, non ordonnées en qualité :

| nature | définition | exemple |
|---|---|---|
| `FRESH_NATURAL` | ingrédients bruts, pas de substitutif | crème, œufs, fruits frais |
| `FROZEN_CLEAN` | surgelé, sans composant substitutif | pâte surgelée pur beurre |
| `SUBSTITUTED` | porte au moins un composant substitutif | arôme, colorant, texturant |

Le surgelé n'est **pas** un défaut de composition. Le confondre avec le chimique serait la
première erreur : un croissant surgelé pur beurre est du `FROZEN_CLEAN`, une crème
pâtissière en poudre aromatisée est du `SUBSTITUTED` même préparée le matin même.

## Options

### A — Un neuvième critère pondéré `COMPOSITION_INTEGRITY`

Les huit poids somment à 1,00 : en ajouter un impose de tous les rebaisser.

Défaut de fond : une pondération se **compense**. À 0,10, un produit substitué et bon
marché gagne sur les 0,90 restants. L'axe disparaît là où il comptait.

### B — Un garde-fou `G007`, donc un veto

Certaines compositions sont inadmissibles quel que soit le score, par famille et par rôle.
Un veto ne se compense pas. C'est le régime déjà retenu pour G002.

Défaut : binaire. Ne dit rien du mélange intelligent, seulement de l'interdit.

### C — Un attribut produit à niveaux de preuve, sur le modèle des allégations

`composition_nature` porté par la fiche, avec le niveau de preuve qui l'établit —
`SUPPLIER_DOCUMENTED`, `INTERNAL_RECIPE_DOCUMENTED`, `PARTIAL`, `NONE` — exactement comme
`vegan` aujourd'hui. Une allégation sans preuve ne vaut rien : une recette change sans que
l'étiquette suive.

Permet l'arbitrage de mélange : un panier, une gamme ou une vitrine peuvent viser une part
minimale de `FRESH_NATURAL` et une part maximale de `SUBSTITUTED`, par famille.

### D — Rien : jugement d'acheteur, hors système

Cohérent seulement si l'on renonce à la seconde moitié de la mission.

## Recommandation

**C comme socle, B comme plancher.** Les deux, pas l'un ou l'autre.

C porte le mélange — c'est ce que demande « l'arbitrage sur le mélange intelligent ». Un
axe de mélange a besoin de proportions, pas d'un interdit.

B porte ce qui ne se négocie pas. Sans lui, C reste une préférence qu'un écart de prix
suffit à faire céder.

A est à écarter : une pondération transforme un refus en prix. Elle répond à « combien
d'euros vaut l'absence d'arôme artificiel », question à laquelle personne ici ne veut
répondre.

## Ce que la décision engage

- La doctrine suit le .docx humain : `doctrine/doctrine.json` ne se modifie pas ici. Cet
  ADR alimente la version suivante du document.
- Le schéma canonique gagne un champ et son niveau de preuve — il en porte déjà 90.
- La collecte change : `ingredients` devient une donnée de décision, pas une information
  d'allergène. Les passes de sourcing doivent la relever, ce que les briefs GARNITURE et
  DESSERT ne demandent pas aujourd'hui.
- Le référentiel porte déjà `Clean Label` comme label fournisseur. Un label déclaré par un
  fournisseur n'est pas une preuve de composition : à traiter en `PARTIAL`.

## Questions ouvertes

- Les seuils de mélange par famille ne sont pas fixés et ne peuvent pas l'être tant qu'on
  n'a pas de listes d'ingrédients sur les candidats réels.
- Le cas des auxiliaires technologiques — améliorants de panification, enzymes — n'est pas
  tranché par la définition ci-dessus : ils ne substituent pas un ingrédient, ils modifient
  un procédé.
