# Fiche produit canonique

`schema_version: 2.0.0`. Chaque produit réel possède son propre fichier JSON dans `data/products/`.

## Blocs

### `product`
Identité stable du produit. `id` ne change pas lorsque le prix ou le fournisseur change.

### `commercial`
Prix de vente, valeur de référence, éligibilité bundle et paliers de prix.

### `dietary`
Régimes alimentaires, allergènes et niveau de preuve de l'allégation.
Une propriété `vegan=true` n'est pas suffisante : `claim_evidence` doit indiquer d'où vient la preuve.

Seuls `SUPPLIER_DOCUMENTED` et `INTERNAL_RECIPE_DOCUMENTED` valident une allégation vegan.
`PARTIAL` est refusé — le filtre est une liste blanche, donc toute valeur ajoutée plus tard
à l'énumération est refusée par défaut plutôt qu'acceptée par oubli. C'est le seul contrôle
du système dont l'erreur quitte l'écran pour aller en vitrine.

#### Équivalence avec les preuves fournisseur

Les leads fournisseurs (`supplier_product.schema.json`) parlent un autre vocabulaire. La
traduction :

| Preuve fournisseur | Vaut, côté fiche | Allégation vegan |
|---|---|---|
| `OFFICIAL_TECHNICAL_SHEET` | `SUPPLIER_DOCUMENTED` | **acceptée** |
| `OFFICIAL_PRODUCT_PAGE` | `PARTIAL` | refusée |
| `LABEL` | `PARTIAL` | refusée |
| `NONE`, `UNKNOWN`, toute valeur inconnue | `NONE` | refusée |

Le critère n'est pas le sérieux apparent de la source, c'est ce que la doctrine nomme en
premier dans `traceability_requirements.vegan_products` : la capacité à documenter les
**changements de recette**. Une fiche technique porte une version, une date et une
procédure d'alerte. Une page produit et une mention d'emballage disent l'état du jour et
rien de l'après — un fournisseur qui reformule en silence rend l'allégation fausse sans
que personne ne l'apprenne, et c'est ce risque-là qui sort de l'écran.

Conséquence pratique : le croissant végétal Vandemoortele 55973 et le cookie vegan Coup de
Pâtes 71376 sont tous deux en `OFFICIAL_PRODUCT_PAGE`. Ils ne peuvent pas porter
l'allégation tant que la fiche technique n'est pas au dossier. Ce n'est pas un blocage,
c'est un e-mail au fournisseur.

### `signature`
Classe doctrinale et opérations qui créent la différence client.
Pour un produit hybride, on décrit explicitement la marinade, le calibrage, l'assemblage ou la finition qui porte la signature.

### `internal_production`
Coût interne détaillé. Le champ déterminant est `avoidable_cost_total_eur`.
Il ne doit pas être confondu avec le seul coût matière.

Six postes sont saisis : matières, énergie, emballage, nettoyage/manutention, pertes, autres.
Le travail ne l'est pas — il se décrit geste par geste dans `operations[]` et se valorise
avec les taux de `params/establishment.json`. Le validateur recalcule la somme et refuse un
`avoidable_cost_total_eur` qui s'en écarte de plus d'un centime.

Conséquence voulue : réviser le taux périme les totaux de toutes les fiches, qui ressortent
alors en `INVALID`. C'est G006 — *réévaluer quand les salaires changent* — rendu mécanique.
Un `cost_status` à `VERIFIED` ou `ESTIMATED` que rien ne permet de recalculer est refusé.

### `external_sourcing`
Un produit peut avoir plusieurs sources fournisseurs. Chaque source conserve son prix rendu,
minimum de commande, délai, **durée de vie et durée résiduelle minimale à réception**,
qualité, traçabilité et fiabilité.

La conservation est portée par la source, pas par le produit : deux fournisseurs de la même
référence ne livrent pas la même DLC, et la durée résiduelle à réception est une propriété
de ce qui est livré. `supplier_specification.minimum_fields` de la doctrine l'exige au
niveau fournisseur.

### `stock_and_conservation`
Stockage, pertes et seuils de stock, plus la durée de vie de la production **interne**.
La conservation est un critère doctrinal autonome. Les durées de vie externes vivent
dans `external_sourcing.sources[]`, une par fournisseur.

### `decision_inputs`
Notes de 0 à 5 utilisées par la doctrine. `recommended_mode` reste MAKE, BUY, HYBRID ou UNDECIDED.

### `data_quality`
Toute donnée incertaine doit rester explicite. On conserve les champs critiques manquants,
les sources et la date de dernière revue.

## Unités

Coûts matière et postes annexes : **par unité vendue**. Prix fournisseurs : **par unité
vendue** aussi, jamais par colis ni par commande — `case_pack_units` et `minimum_order_units`
décrivent le conditionnement, pas l'unité des prix.

Le travail fait exception, parce qu'on ne chronomètre pas une production à l'unité : les
gestes se mesurent **par lot**, et `batch_size_units` les ramène à l'unité.

Chaque champ porte son unité dans son nom. Rien d'autre ne la portait, et l'écart entre les
deux lectures vaut la taille du lot : à 1,8 min par unité le cookie de `catalog.example.json`
sort en BUY, à 1,8 min par lot de 40 il reste MAKE. `labor_minutes`, `labor_minutes_per_unit`
et `labor_cost_eur` sont refusés par le validateur.

## Le travail : `operations[]`

Une entrée par geste, chacun à son propre niveau de qualification.

```json
"operations": [
  {"task": "weigh_dried_hibiscus",  "active_labor_minutes_per_batch": 2,
   "elapsed_minutes_per_batch": 2,  "labor_tier": "apprentice"},
  {"task": "infusion_monitoring",   "active_labor_minutes_per_batch": 1,
   "elapsed_minutes_per_batch": 30, "labor_tier": "apprentice"},
  {"task": "filter_and_bottle",     "active_labor_minutes_per_batch": 4,
   "elapsed_minutes_per_batch": 4,  "labor_tier": "apprentice"}
]
```

Deux règles portent tout le modèle.

**On facture le temps humain réellement immobilisé.** Une infusion de 30 minutes surveillée
en 1 minute coûte 1 minute. Les 29 autres ne disparaissent pas : c'est de la capacité
disponible, la valeur que P004 demande de compter. Sur ce bissap, confondre les deux
multiplie le coût du travail par 5,1.

**On paie au niveau de qualification minimal raisonnablement nécessaire.** Une pesée facturée
au tarif d'un boulanger qualifié fait pencher l'arbitrage vers BUY pour une raison qui
n'existe pas. `labor_tier` est une clé de `params.labor.tiers` ; un niveau inconnu est refusé,
jamais traité comme zéro.

Coût du travail par unité = Σ (minutes immobilisées × taux du niveau) ÷ `batch_size_units`.

### Gabarits par technologie

`params/operation_templates.json` donne, pour chaque technologie fournisseur, **quels
gestes restent en interne** :

```bash
python3 product_tool.py operations CRU
```

| Technologie | Gestes internes |
|---|---|
| `CRU` | mise en plaque, pousse, cuisson, défournement |
| `PAC` | mise en plaque, cuisson, défournement |
| `PRECUIT` | mise en plaque, finition de cuisson, défournement |
| `CUIT` | décongélation, dressage |
| `PRET_A_SERVIR` | aucun |

Les minutes sont à `null` et le restent : le gabarit dit quels gestes, jamais combien de
temps. On chronomètre **une fois par technologie**, pas une fois par produit — cinq mesures
couvrent les 130 SKU du référentiel. Une minute pré-remplie serait un coût inventé, et un
test le refuse.

La pousse et la décongélation portent le même motif que l'infusion du bissap : temps écoulé
long, temps immobilisé réduit à la surveillance. Un modèle qui les compterait comme du
travail externaliserait tout ce qui lève, repose ou fermente.

Un lot pas encore mesuré (`batch_size_units: null`) reste une fiche valide : le coût devient
simplement incalculable, et un `cost_status` annoncé `VERIFIED` ou `ESTIMATED` est alors refusé.

## Paramètres d'établissement

`params/establishment.json` porte ce qui ne dépend ni d'une règle durable ni d'un produit :
le coût de la minute de travail. Un seul endroit, sinon le taux est gravé dans chaque fiche
et une révision de salaire impose de toutes les rouvrir — sans garantie qu'elles portent le
même taux.

```json
"labor": { "tiers": {
  "apprentice":             { "cost_per_minute_eur": 0.16 },
  "production_assistant":   { "cost_per_minute_eur": 0.25 },
  "qualified_baker_pastry": { "cost_per_minute_eur": 0.36 }
}}
```

Trois niveaux plutôt que deux : la hiérarchie économique du travail est assez différente pour
déplacer réellement un arbitrage Make-or-Buy.

## Commandes

Voir ce qu'il reste à remplir, par famille et par fiche :

```bash
python3 product_tool.py status data/products
```

`PRÊT` signifie exactement « `compile` l'accepterait ». La commande affiche aussi, pour chaque
fiche chronométrée, le temps immobilisé, le temps écoulé et l'écart des deux — la capacité
libérée au sens de P004.

Valider un produit :

```bash
python3 product_tool.py validate data/products/bissap_maison.json
```

Valider tout le répertoire :

```bash
python3 product_tool.py validate data/products
```

Compiler les fiches canoniques actives vers le catalogue utilisé par le moteur actuel :

```bash
python3 product_tool.py compile data/products --output data/catalog.generated.json
```

Cette étape permet de faire évoluer progressivement le moteur sans casser la version existante.

Une fiche `ACTIVE` dont le prix de vente ou la valeur client reste inconnu est **ignorée avec
son motif**, jamais compilée avec un zéro. Un coût inconnu échoue déjà fermé — le moteur
écarte le menu ; un prix à zéro échouerait ouvert, en produisant un score faux sans signal.

## Migration 1.0.0 → 2.0.0

Format cassant. Une fiche `1.0.0` est refusée plutôt que mal interprétée.

| Champ | 1.0.0 | 2.0.0 |
|---|---|---|
| `internal_production.labor_cost_eur` | montant saisi | supprimé |
| `internal_production.labor_minutes` | unité non définie | supprimé |
| — | — | `operations[]`, un geste par entrée, avec son niveau |
| `params.labor.cost_per_minute_eur` | taux unique | `params.labor.tiers.*` |
| `stock_and_conservation.external_shelf_life_hours` | par produit | `sources[].shelf_life_hours` |
| `stock_and_conservation.minimum_residual_shelf_life_hours_at_delivery` | par produit | `sources[].minimum_residual_shelf_life_hours_at_delivery` |
