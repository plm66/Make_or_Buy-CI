# ADR-0003 — L'hybride se décide par composant, sur trois axes

- **Statut** : PROPOSED
- **Date** : 2026-09-12
- **Décide** : Philippe
- **Porte sur** : `doctrine/doctrine.json` — `product_classes.HYBRID_SIGNATURE`,
  `decision_modes` ; `src/make_or_buy/engine.py` — `selected_cost`

## Le cas

Une tarte aux cerises composée de :

| composant | provenance | ce qu'il apporte |
|---|---|---|
| cerises | fraîches, achetées en matière | ce que le client voit |
| pâte à tarte | surgelée, achetée | du travail supprimé, invisible |
| appareil ou finition | prêt à l'emploi, livré par un fournisseur | zéro geste restant |

Un seul produit, trois provenances, trois natures. C'est là que se fabrique la marge.

## Ce que le dépôt sait, et où il ne le sait pas ensemble

Trois vocabulaires existent, chacun dans son coin :

| axe | valeurs | où il vit aujourd'hui |
|---|---|---|
| mode d'approvisionnement | `MAKE`, `BUY` | `doctrine.decision_modes` |
| nature de composition | `FRESH_NATURAL`, `FROZEN_CLEAN`, `SUBSTITUTED` | ADR-0001, proposé |
| degré de transformation | `CRU`, `PAC`, `PRECUIT`, `CUIT`, `PRET_A_SERVIR` | `params/operation_templates.json` |

Aucun endroit ne les porte ensemble, et aucun ne les porte **par composant**.

Le troisième axe est le plus sous-estimé. Il porte déjà le nombre de gestes qui restent :

```
CRU            4 gestes
PAC            3 gestes
PRECUIT        3 gestes
CUIT           2 gestes
PRET_A_SERVIR  0 geste
```

« Le produit prêt à consommer livré par le fournisseur X » a donc déjà un nom dans le
dépôt : `PRET_A_SERVIR`, zéro geste.

## Le défaut

`doctrine.product_classes.HYBRID_SIGNATURE` définit l'hybride comme **une** base sourcée à
l'extérieur, plus une finition interne qui crée la signature. C'est un cas particulier à
deux composants. La tarte en compte trois, et un assemblage réel en compte davantage.

Côté moteur, `engine.py:52` :

```python
hybride = item.get("hybrid", {}).get("avoidable_cost_eur")
```

Un seul nombre, saisi à la main. L'hybride est une **étiquette portant un coût déclaré**,
pas une composition calculée. Personne ne peut savoir quel composant coûte quoi, ni
rejouer le calcul quand le prix d'un composant bouge, ni comparer deux façons de composer
le même produit.

C'est le même défaut que le coût matière saisi — non inventé, mais non rejouable.

## Ce que la trilogie rend calculable

Avec une composition par composant, trois choses qui sont aujourd'hui des opinions
deviennent des mesures :

1. **Le coût effectif** : Σ (coût des composants achetés) + Σ (opérations internes
   restantes × taux horaire). Le degré de transformation de chaque composant **donne** les
   gestes restants : c'est déjà tabulé.
2. **Le profil de composition** : la part de `FRESH_NATURAL`, `FROZEN_CLEAN` et
   `SUBSTITUTED` dans le produit fini, pondérée par les masses. L'arbitrage de mélange que
   demande la mission devient un calcul sur une nomenclature.
3. **La comparaison entre deux compositions du même produit** : acheter la pâte et faire
   l'appareil, ou l'inverse. Aujourd'hui il faudrait saisir deux coûts à la main et se
   fier au plus bas.

## La tension : mesurée, pas supposée

Hypothèse de départ : acheter du degré ferait gagner de la main-d'œuvre au prix d'une
composition dégradée. Mesure sur les 59 fiches Bridor, qui portent à la fois leur degré et
leur liste d'ingrédients.

| degré | fiches | au moins un additif | part | arôme | colorant |
|---|---|---|---|---|---|
| CRU | 5 | 5 | 100 % | 2 | 1 |
| PAC | 22 | 15 | 68 % | 11 | 2 |
| PRECUIT | 19 | 3 | **16 %** | 2 | 1 |
| CUIT | 5 | 5 | 100 % | 0 | 0 |
| PRET_A_SERVIR | 4 | 4 | 100 % | **4** | **4** |

**L'hypothèse est fausse telle qu'énoncée.** Le degré ne prédit pas la présence d'additifs :
PRECUIT est à 16 %, CRU à 100 %.

Ce que la mesure montre est plus étroit. Sur les quatre références `PRET_A_SERVIR`, les
quatre portent un arôme **et** un colorant. Sur les cinq `CRU`, ce qu'on trouve est surtout
de l'émulsifiant — cinq sur cinq — et l'arôme n'apparaît que deux fois.

L'émulsifiant est un auxiliaire de procédé dans une pâte feuilletée : il ne remplace aucun
ingrédient. L'arôme et le colorant, si. Le signal n'est donc pas « le degré amène des
additifs » mais « le degré amène des **substitutifs** », et il ne se voit qu'en appliquant
la distinction d'ADR-0001 entre substitutif et auxiliaire technologique.

**Limite.** Quatre références `PRET_A_SERVIR` et cinq `CRU` sur un seul catalogue. C'est un
indice qui oriente la collecte, pas une loi. La mesure est à refaire quand les listes
d'ingrédients couvriront plusieurs fournisseurs — Coup de Pâtes en porte zéro aujourd'hui.

Conséquence si l'indice se confirme : le composant qui supprime le plus de gestes est aussi
celui qu'il faut examiner le plus, et un gain de marge obtenu en substituant ce que le
client venait chercher se paie en réputation — un coût que le calcul ne voit pas.

C'est pour cette raison que l'axe de composition d'ADR-0001 doit être un **plancher** et non
une pondération. Une pondération y répondrait par un prix ; un plancher dit où l'arbitrage
s'arrête.

## Où se décide quoi

P007 et P008 donnent déjà la règle, sans pouvoir l'appliquer faute de composants :

| composant | règle | conséquence |
|---|---|---|
| visible, porte la signature | reste interne, ou acheté en matière brute | la cerise s'achète fraîche, elle ne se délègue pas transformée |
| invisible, coûteux en travail | s'achète | la pâte surgelée supprime du travail que personne ne voit |
| invisible, peu coûteux en travail | indifférent, tranché au coût | |

La marge vient de la deuxième ligne. La réputation se perd sur la première.

## Options

### A — Composition par composant dans la fiche produit

Le produit porte une liste de composants, chacun avec sa référence — matière `MATP`,
préparation interne, ou produit fournisseur — son mode, sa nature, son degré et sa masse.
Le coût et le profil de composition se calculent.

C'est la nomenclature d'ADR-0002 avec, sur chaque ligne, le mode et le degré.

### B — Garder le coût hybride saisi, ajouter seulement le profil de composition

Moins de travail. On saurait de quoi le produit est fait sans savoir ce que chaque partie
coûte, donc sans pouvoir comparer deux compositions. La moitié du bénéfice pour presque
autant de saisie.

### C — Garder l'hybride tel quel

Renoncer à la trilogie.

## Recommandation

**A**, et cet ADR ne s'implémente pas avant ADR-0002 : sans nomenclature, il n'y a pas de
composant à qualifier. L'ordre reste `MATP`, puis nomenclature, puis mode et degré par
ligne.

Deux conséquences à assumer :

- `HYBRID_SIGNATURE` cesse d'être une classe à deux composants. La définition doctrinale
  doit se généraliser à N composants, ce qui passe par le .docx.
- `selected_cost` cesse de lire `hybrid.avoidable_cost_eur`. Le champ ne disparaît pas tout
  de suite : il devient une valeur de repli explicite tant que la nomenclature n'existe
  pas, avec le statut qui le dit — jamais un repli silencieux, c'est la leçon de G002.

## Questions ouvertes

- Le taux horaire manque toujours. Le degré de transformation donne les gestes, pas leur
  prix : `operation_templates.json` porte volontairement des minutes nulles.
- La pondération du profil de composition — par masse, par coût, ou par visibilité au
  client — n'est pas tranchée. Par masse est le plus simple et le plus faux : trente
  grammes d'appareil substitué se voient plus que deux cents grammes de pâte propre.
- Un composant acheté peut lui-même être composite. La profondeur de nomenclature qu'on
  accepte de suivre chez un fournisseur n'est pas décidée, et elle bute vite sur ce qu'il
  accepte de déclarer.
