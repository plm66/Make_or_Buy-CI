# Référentiel matières premières (`MATP`)

L'étage le plus bas du modèle. Une recette référence des matières, une matière ne
référence rien. C'est ce qui rend un coût matière calculable au lieu d'être saisi.

Prévu de longue date — `data/generics/SCHEMA.md` annonce `MATP` en « phase 2 » — et resté
vide jusqu'ici. Ouvert par [ADR-0002](../../docs/decisions/ADR-0002-modele-de-recette.md),
qui recommande de commencer par là : sans prix matière, une nomenclature calcule zéro.

## Ce que ce fichier ne porte pas

**Aucun prix.** Un prix est un fait daté qui bouge ; l'identité d'une matière ne bouge pas.
Les mêler ferait de chaque relevé de prix une modification du référentiel, et rendrait
impossible de savoir quel prix a servi à une décision passée.

C'est la même séparation que `price_source` contre `supplier`, et que
`reference_price_eur_per_piece` contre `landed_cost_eur_per_piece`. Les prix matière
viendront dans une couche datée qui référence `id_matiere`.

## Colonnes

| champ | rôle |
|---|---|
| `id_matiere` | clé stable, `MATP-<CAT>-<SPEC>` |
| `categorie` | liste fermée, voir plus bas |
| `nom_normalise` | nom de métier, sans marque ni gamme |
| `unite_achat` | `kg`, `L` ou `piece` — comme on l'achète |
| `unite_recette` | `g` ou `ml` — comme on la pèse |
| `grammes_par_unite_achat` | conversion vers le gramme, **vide si non mesurée** |
| `composition_nature` | `FRESH_NATURAL`, `SUBSTITUTED`, `UNDECIDED` — vocabulaire d'[ADR-0001](../../docs/decisions/ADR-0001-axe-de-composition.md) |
| `preuve_composition` | `DEFINITIONAL` ici : la nature découle de la définition de la matière |
| `substitut_de` | ce que la matière remplace, pour les seules `SUBSTITUTED` |
| `allergenes` | liste normée, séparateur `;` |
| `statut` | `ACTIF` ou `TO_VERIFY` |
| `note` | ce qui reste à établir |

Catégories : `farines`, `matieres-grasses`, `sucres`, `oeufs`, `laits-cremes`, `chocolats`,
`fruits-secs`, `aromes`, `levures-agents`, `sels`, `liquides`.

## Aucune conversion devinée

Treize matières sur trente-huit portent `TO_VERIFY` parce que leur conversion vers le
gramme n'est pas mesurée : tout ce qui s'achète au litre, et l'œuf coquille dont le poids
dépend du calibre.

Une masse volumique inventée se propagerait dans chaque recette qui utilise la matière, et
plus rien ne dirait qu'elle a été devinée. Vide et `TO_VERIFY` est plus utile qu'un chiffre
crédible.

L'eau fait exception : 1 000 g par litre est connu, pas estimé.

## La nature est définitionnelle ici, pas prouvée

Une matière générique porte la nature qui découle de sa définition : une margarine de
tourage remplace le beurre par des matières grasses végétales, c'est ce qu'elle *est*.

Une **référence fournisseur** rattachée à cette matière ne bénéficie pas de cette nature :
un beurre concentré peut porter un émulsifiant, un chocolat annoncé « de couverture » peut
ne pas l'être. Le SKU porte sa propre preuve — `SUPPLIER_DOCUMENTED` ou faute de mieux
`PARTIAL` — et peut contredire la matière qu'il prétend fournir.

## Les paires de substitution

Cinq couples nomment explicitement l'arbitrage que la mission demande :

| substituée | remplace |
|---|---|
| margarine de tourage | beurre de tourage 84 % |
| crème végétale à foisonner | crème liquide 35 % |
| chocolat de confiserie MGV | chocolat noir de couverture |
| arôme vanille artificiel | extrait naturel de vanille |
| arôme fraise artificiel | purée de fraise |

Une matière `SUBSTITUTED` qui ne nomme pas ce qu'elle remplace rend l'axe inutilisable : on
saurait qu'elle est substituée sans pouvoir proposer l'alternative. L'invariant l'interdit.

## Cas non tranché

`MATP-LEVU-AMEL`, l'améliorant de panification, porte `UNDECIDED`. Il ne substitue pas un
ingrédient : il modifie un procédé. ADR-0001 laisse le cas ouvert et cette matière le rend
visible dans la donnée plutôt que dans une note de bas de document.

## Ce qui manque

- Les prix, dans une couche datée à construire.
- Les rendements et pertes par matière, qui se mesurent en production.
- Les matières des colonnes salées : la première passe couvre la pâtisserie et la
  boulangerie, parce que l'opéra était l'exemple de départ.
