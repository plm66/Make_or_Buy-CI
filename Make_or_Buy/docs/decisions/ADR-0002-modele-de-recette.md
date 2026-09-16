# ADR-0002 — Le modèle de recette : nomenclature à niveaux, et d'où viennent les recettes

- **Statut** : PROPOSED
- **Date** : 2026-09-12
- **Décide** : Philippe
- **Porte sur** : `schemas/product.canonical.schema.json`, `data/generics/` (famille `MATP`),
  `doctrine/doctrine.json` — `decision_modes`

## La demande

> « Donne-moi la composition et le poids de chaque ingrédient d'un opéra. »

L'application ne sait pas répondre. Le manque n'est pas une fonction absente, c'est une
couche de données qui n'existe pas.

## État des lieux

| couche | état |
|---|---|
| modèle de recette | inexistant |
| référentiel matières premières (`MATP`) | déclaré « phase 2 », **0 entrée** |
| coût matière | `internal_production.material_cost_eur`, **scalaire saisi à la main** |
| composition fournisseur | 52 des 59 fiches Bridor portent un pourcentage QUID, en texte libre non parsé |

`INTERNAL_RECIPE_DOCUMENTED` existe déjà comme niveau de preuve pour les allégations
alimentaires. La recette y est invoquée comme justificatif sans être stockée nulle part :
le dépôt s'appuie sur un document qu'il ne détient pas.

## Pourquoi une liste plate ne suffit pas

Un opéra n'est pas une liste d'ingrédients. C'est un assemblage de préparations :

```
Opéra
├── biscuit joconde        ── poudre d'amandes, œufs, sucre glace, farine, beurre
├── sirop d'imbibage café  ── eau, sucre, café
├── crème au beurre café   ── beurre, sucre, œufs, café
├── ganache chocolat       ── chocolat noir, crème
└── glaçage                ── chocolat, huile
```

Trois conséquences de cette forme :

1. **La même préparation sert plusieurs produits.** La crème au beurre de l'opéra est celle
   d'autres pâtisseries. La décrire une fois, la référencer partout — sinon un changement
   de recette se propage à la main et se perd.
2. **Le rendement se calcule par étage.** Un sirop perd à la cuisson, une ganache pas. Un
   poids de sortie n'est pas la somme des poids d'entrée.
3. **C'est l'étage où se décide MAKE ou BUY.**

Le troisième point est le plus important.

## Ce que ça change pour la mission

Aujourd'hui l'arbitrage MAKE / BUY / HYBRID s'applique **au produit**. `HYBRID_SIGNATURE`
existe comme classe, et son coût — `hybrid.avoidable_cost_eur` — est un nombre saisi à la
main. L'arbitrage *à l'intérieur* du produit n'existe pas.

Avec une nomenclature, il s'applique **au composant** : acheter le biscuit joconde et faire
la ganache, ou l'inverse. C'est littéralement ce que veut dire « aide à la fabrication
hybride » dans la mission. Sans nomenclature, HYBRID est une étiquette ; avec elle, c'est
un calcul.

## Ce que ça rend dérivable

Quatre données aujourd'hui **déclarées à la main** deviendraient calculées, donc auditables :

| donnée | aujourd'hui | avec nomenclature |
|---|---|---|
| `material_cost_eur` | scalaire saisi | Σ (poids × prix matière) par étage |
| `hybrid.avoidable_cost_eur` | scalaire saisi | Σ composants achetés + opérations internes |
| `composition_nature` (ADR-0001) | à déclarer | dérivée des ingrédients |
| allergènes | déclarés | dérivés des ingrédients |

C'est la raison de fond de cet ADR. La doctrine dit de ne jamais inventer un chiffre ; un
coût matière saisi à la main n'est pas inventé, mais il n'est pas non plus **rejouable** —
personne ne peut le recalculer ni voir ce qui a changé quand le prix du beurre bouge.

## Le piège, et la vraie décision

Demander à l'application la composition d'un opéra, c'est lui demander de **produire** une
recette. Si elle répond depuis la mémoire d'un modèle, elle fabrique un fait daté — ce que
la doctrine interdit.

Trois couches, pas deux, et c'est leur comparaison qui est le travail :

| couche | nature | traitement | ce qu'on en a |
|---|---|---|---|
| l'opéra **standard** | référence de métier | sourcée et citée, jamais un fait sur nous | rien |
| les opéras **des autres** | produits observés et achetables | faits datés sur le marché | 1 140 références catalogue, dont 52 fiches Bridor avec pourcentages QUID |
| **le nôtre** | un fait sur la boulangerie | saisi une fois, daté, versionné ; fait autorité pour le coût | rien |

La couche du milieu existe déjà : le référentiel construit pour le sourcing est aussi le
corpus de comparaison pour la conception. Un même fichier sert deux usages qu'on n'avait
pas identifiés comme liés.

Le travail est de considérer le standard, le comparer à ce que fabriquent les autres, et
concevoir le nôtre à partir de cet écart.

C'est la troisième fois que cette distinction se présente dans ce dépôt :

- `price_source` n'est pas `supplier` — on capture un prix sans acheter
- `reference_price_eur_per_piece` n'est pas `landed_cost_eur_per_piece` — un historique
  n'est pas un devis
- une recette de référence n'est pas la recette de la maison

Le motif est constant : **une référence n'est pas un fait sur nous.** Les deux doivent
coexister dans le modèle, jamais dans le même champ.

Une recette de référence a pourtant une vraie utilité : proposer un point de départ, et
mesurer l'écart entre la pratique de la maison et la pratique du métier. Elle doit donc
exister, marquée comme telle, avec sa source.

## Options de modélisation

### A — Nomenclature à niveaux, préparations partagées

`preparations` devient une entité de premier rang, référencée par les produits et par
d'autres préparations. Un produit porte une liste de lignes `(référence, quantité, unité)`
où la référence est soit une matière première `MATP`, soit une préparation.

Coût : il faut le référentiel `MATP` avec des prix, aujourd'hui vide.
Gain : tout le reste en découle, y compris l'arbitrage par composant.

### B — Liste plate d'ingrédients par produit

Chaque produit porte ses ingrédients finaux, sans sous-préparations.

Coût : faible. Répond à la question posée telle qu'elle est posée.
Perte : la crème au beurre est ressaisie à chaque produit, l'arbitrage par composant reste
impossible, et le rendement par étage ne se calcule pas. C'est-à-dire qu'on renonce à la
fabrication hybride.

### C — Rien, et importer la composition depuis les fiches fournisseur

Utiliser les 52 QUID Bridor déjà collectés.

Portée : produits *achetés* seulement. Ne dit rien de ce qu'on fabrique, donc ne sert ni au
coût MAKE ni à l'arbitrage. Utile, mais ce n'est pas la même question.

## Recommandation

**A**, et l'ordre des travaux importe plus que le modèle.

Le référentiel `MATP` d'abord : sans prix matière, une nomenclature calcule zéro. C'est
aussi la donnée la plus stable — la farine, le beurre et le sucre ne changent pas de
définition, et leurs prix sont accessibles.

Puis les préparations de la maison, saisies une fois. Puis les produits qui les assemblent.

B est un piège : il répond à la question du jour et ferme la moitié de la mission. Le
surcoût de A sur B tient au seul référentiel `MATP`, qu'il faudra de toute façon pour
chiffrer un coût matière rejouable.

## Questions ouvertes

- Les recettes de la maison n'existent aujourd'hui sous aucune forme numérique. Leur saisie
  est un travail humain que rien n'automatise, et c'est le vrai coût de cette décision.
- Le prix matière est une donnée mouvante. Faut-il figer le coût d'une recette à une date,
  ou le recalculer à chaque interrogation ? Les deux se défendent et n'ont pas la même
  conséquence sur la traçabilité d'une décision passée.
- Le rendement et les pertes par étage se mesurent en production. Tant qu'ils ne sont pas
  mesurés, un coût matière calculé reste une estimation — à marquer comme telle, jamais à
  présenter comme constatée.
