# Make_or_Buy

Rendre **exécutable et auditable** la doctrine d'arbitrage fabriquer / acheter d'une
boulangerie. Chaque décision `MAKE`, `BUY` ou `HYBRID` se trace à une règle durable nommée,
un fait daté et une incertitude déclarée.

Ce n'est pas un générateur de menus. C'est une **base de décision sur le choix des produits**,
et un outil d'arbitrage sur la fabrication hybride : le mélange raisonné du frais et du naturel
avec le surgelé et le substitué.

> Le code Python vit dans [`Make_or_Buy/`](Make_or_Buy/). Ce dossier racine ne porte que les
> règles de collaboration.

---

## Les trois axes, qui ne se confondent pas

Un produit se décrit sur trois questions indépendantes. Les mélanger est l'erreur que le
dépôt a payée le plus cher.

| axe | question | valeurs |
|---|---|---|
| **approvisionnement** | qui fait ? | `MAKE` · `BUY` · `HYBRID` |
| **composition** | de quoi c'est fait ? | `FRESH_NATURAL` · `FROZEN_CLEAN` · `SUBSTITUTED` |
| **transformation** | ce qu'il reste à faire | `MATIERES` (9 gestes) → `PRET_A_SERVIR` (0) |

Un surgelé peut être irréprochable de composition. Un produit frais peut être bourré
d'arômes. Le froid n'est pas un défaut ; la substitution en est un, quand elle n'est pas
choisie.

---

## Où en est le projet

| | |
|---|---|
| matières premières au référentiel | **38** |
| prix réellement payés, relevés sur facture | **384 lignes**, mars → septembre 2026 |
| articles rattachés à une matière | **24** (15 lus, 9 à vérifier) |
| fournisseurs au registre | **13** |
| invariants exécutables | **190** |
| **gestes chronométrés** | **0 / 21** ← le blocage |
| **produits arbitrables** | **0** |

Le moteur, la doctrine et le référentiel sont complets. Aucun produit n'est encore
arbitrable, parce que le coût complet évitable d'une fabrication interne exige des minutes
que personne n'a mesurées.

**→ [La feuille de route](Make_or_Buy/docs/ROADMAP.md)** dit dans quel ordre lever ça.

---

## Ce que le dépôt sait déjà faire

```bash
cd Make_or_Buy

product_tool.py status                      # fiches produit, ce qui manque à chacune
generics_tool.py rebuild                    # référentiel générique, clés dérivées
metro_factures.py extraire --write          # lire les factures PDF, contrôler l'arithmétique
halalfs_tool.py capture <categorie>         # relever un catalogue PrestaShop public
doctrine_tool.py validate                   # doctrine versionnée, empreinte sha256
make-or-buy manita-check                    # valider un panier contre le postulat
```

Tests sans framework, un fichier par domaine :

```bash
python3 tests/test_harness.py               # les 188 invariants
```

---

## Les quatre couches, et ce qui fait autorité

| | rôle | autorité |
|---|---|---|
| `doctrine/` | comment décider — 8 principes, G001–G006 | normative, suit un document humain |
| `postulates/` | modules commerciaux, dont La Manita | normative, versionnée par deltas |
| `data/` | sur quoi décider — faits datés | faits, jamais des règles |
| `src/`, `*_tool.py` | application des règles | implémentation, corrigeable |

`data/research/` est à part : des pistes, jamais une autorisation d'achat.

---

## À lire avant de contribuer

| document | pourquoi |
|---|---|
| [`docs/GLOSSAIRE.md`](Make_or_Buy/docs/GLOSSAIRE.md) | un terme, un sens, un référent anglais. Un code absent du glossaire est un code inventé. |
| [`docs/decisions/`](Make_or_Buy/docs/decisions/) | les trois ADR ouverts : composition, recette, hybride par composant |
| [`Make_or_Buy/CLAUDE.md`](Make_or_Buy/CLAUDE.md) | les pièges, par ordre de ce qu'ils ont coûté |
| [`AGENTS.md`](AGENTS.md) | règles de collaboration, commandes interdites |

---

## La règle qui revient

**Une référence n'est pas un fait sur nous.** Elle s'est imposée six fois :

| référence | fait sur nous |
|---|---|
| source de prix | fournisseur homologué |
| prix catalogue | prix rendu constaté |
| recette de métier | recette de la maison |
| nature définitionnelle d'une matière | composition prouvée d'un SKU |
| tarif imprimé sur la facture | prix réellement payé, remise déduite |
| catalogue METRO | nos propres factures METRO |

Les deux coexistent dans le modèle. Jamais dans le même champ.

---

## Et la dette la plus chère

**G002 — ne jamais comparer un prix fournisseur au seul coût matière interne.** Le premier
est complet, le second ne l'est pas : la comparaison fait toujours gagner l'interne à tort,
d'un facteur 2 à 7. Le champ s'appelle `avoidable_cost_eur` et s'appelait `material_cost_eur`
en portant déjà le total. Un nom qui ment fait réintroduire le défaut de bonne foi.
