# Référentiel produits — Boulangerie / Pâtisserie / Snacking

Collectes Perplexity sur catalogues publics, normalisées avant intégration.
Invariants protégés par `tests/test_generics.py`, qui découvre les catalogues par
convention `<fournisseur>_index.csv` / `<fournisseur>_detail.csv`.

| Fichier | Contenu |
|---|---|
| `bridor_index.csv` | 396 références, 2026-09-10 |
| `bridor_detail.csv` | 59 fiches |
| `coup_de_pates_index.csv` | 605 références, 2026-09-11 |
| `coup_de_pates_detail.csv` | 71 fiches |
| `produits_generiques.csv` | 47 génériques |
| `RATTACHEMENT_coup_de_pates.md` | rapport de rattachement du second catalogue |

## Rattachement en attente

Un `id_generique` **vide** signifie que le SKU n'a trouvé aucun générique existant et
attend un arbitrage. `motif_nouveau` porte alors la proposition. Un identifiant inventé
serait pire qu'un vide : il ferait passer la ligne pour rattachée.

65 des 71 SKU Coup de Pâtes sont dans cet état.

## Ce que le second catalogue a mesuré

6 rattachements sur 71, soit 8,5 %. La cause est structurelle et visible sur la plus
grosse catégorie :

```
croissants    Bridor [40, 50] g
              Coup de Pâtes [25, 30, 60, 70, 80, 85, 120, 125] g
```

Aucun recouvrement. Le grammage étant dans la clé, deux catalogues qui vendent le même
produit à des formats différents ne se rejoignent jamais. Une tolérance en pourcentage
ne répare pas ça — elle rattrape les quasi-ratés (28↔30 g, 295↔300 g) et laisse les
croissants disjoints.

## Objet

Constituer une base de références produits structurée, avec deux axes distincts :

- **Axe 1 — Produit générique** (« le produit en absolu ») : le croissant pur beurre 50 g en tant que catégorie de produit, indépendamment de tout fournisseur.
- **Axe 2 — Référence fournisseur** : le SKU commercial concret (ex. « Croissant 50g », REF. 32960, Bridor, colisage 100 unités).

L'axe 2 se rattache à l'axe 1 par une clé de correspondance. Les prix, food cost et commandes viendront plus tard se greffer sur ces deux tables.

## Le problème des « 300 références de sel »

Pour ne pas noyer le référentiel sous des doublons commerciaux, trois règles :

1. **Le grain du référentiel côté fournisseur = le SKU** (couple fournisseur + référence). Chaque fournisseur a droit à toutes ses références : c'est la réalité du marché.
2. **Côté générique, un seul enregistrement par (catégorie × format × caractéristique distinctive)**. « Sel fin de Guérande 1 kg » et « sel fin 25 kg » sont deux entrées génériques ; les 300 SKUs de sel de tous les fournisseurs se rattachent à ces entrées, pas à 300 nouvelles lignes.
3. **Nom normalisé** : le nom générique est nettoyé (minuscules, suppression marque, gamme marketing, qualificatifs publicitaires) pour permettre le regroupement automatique des SKUs fournisseurs vers le générique.

### Ce qui ne crée PAS un générique

Un conditionnement (blister, plateau, x48, vrac), un nom de gamme commerciale
(SelectBlend, 1778…) ou un qualificatif marketing sont des attributs de SKU. Un macaron
12 g en blister de 8 et le même en plateau de 48 sont **un** générique et **deux** SKU.

La livraison initiale portait quatre `PATI-MACA-12*` pour ce seul produit, plus un
croissant abricot dédoublé par la gamme SelectBlend et un bun'n'roll dédoublé par la
présence de moules. Cinq entrées fusionnées : 52 génériques ramenés à 47, taux de
regroupement passé de 12 % à 20 %.

Une garniture, une recette ou un grammage différents sont en revanche de vrais génériques
distincts — croissant fourré abricot et croissant fourré amande restent deux entrées.

### La clé : nature × classe de format

`FAMILLE-CATEGORIE[-FORMAT]`, et **aucun grammage**. Un croissant reste un croissant :
Bridor le fait en 40 et 50 g, Coup de Pâtes de 25 à 125 g. Un gramme dans la clé rendait
les deux catalogues disjoints — 5 % de rattachement. Sans lui, 66 %.

Une seule classe de format, `MINI`, détectée par le mot dans l'intitulé et non par un
seuil : les bandes se recouvrent (les MINI vont de 18 à 40 g, les non-MINI commencent à
12 g). `MAXI` n'est pas une classe — un maxi pain au chocolat reste un pain au chocolat.

Exception, le macaron : 12 g en petit four et 55 à 100 g en dessert sont deux natures et
non deux formats, d'où `PATI-MACA-PETITFOUR` et `PATI-MACA-DESSERT`.

Le grammage vit sur le SKU, exact, et sert au coût. Le générique porte `poids_min_g` et
`poids_max_g`, calculés.

## La catégorie se dérive de l'intitulé, jamais du fournisseur

`generics_tool.py rebuild` reclasse famille et catégorie depuis le nom du produit, puis
reconstruit `produits_generiques.csv`. À rejouer après chaque import.

C'est une leçon payée : le premier test de rattachement croisé a rendu 8,5 %, attribués au
grammage. La vraie cause était que les 39 viennoiseries Coup de Pâtes portaient toutes
`categorie: viennoiserie` — un seul seau — quand Bridor en avait livré cinq. Même à
grammage identique, aucun croissant n'aurait pu se rejoindre.

**Une colonne dont les valeurs viennent du vocabulaire du fournisseur ne peut pas servir
de clé de rapprochement.** `famille`, `technologie` et `statut` ont tenu parce qu'ils
étaient imposés au collecteur. `categorie` a dérivé parce qu'il ne l'était pas. Ne plus la
demander : l'intitulé la donne, chez les deux fournisseurs.

`tests/test_generics.py` recalcule chaque clé depuis l'intitulé et compare — le CSV ne peut
pas diverger de la règle qui l'a produit.

## Limite précédente, corrigée

La première livraison distinguait par une lettre les génériques partageant catégorie et
grammage — `PAIN-BAGU-280`, `280a`, `280b`, `280c`. La lettre ne portait aucun sens qu'un
catalogue tiers puisse retrouver. Supprimé avec le grammage.

Trois préfixes se recouvraient également : `VIEN-CROI` couvrait croissants et croissants
fourrés, `VIEN-PAIN` les pains au chocolat et aux raisins, `PAIN-PAIN` les pains à partager
et sandwich. Les codes de catégorie sont désormais distincts — CROI, CROF, PCHO, PRAI.

## Taxonomie (3 niveaux + attributs)

### Niveau 1 — Famille

| Code | Famille |
|---|---|
| PAIN | Pains |
| VIEN | Viennoiseries |
| PATI | Pâtisseries |
| SNAC | Snacking salé |
| BOIS | Boissons (fraîches, chaudes, jus, eaux) |
| MATP | Matières premières (farines, levures, sucres, sels...) — phase 2 |
| EPIC | Épicerie / boutique — phase 2 |

### Niveau 2 — Catégorie (liste évolutive)

- PAIN : baguettes, pains sandwich, petits pains, pains à partager, autres pains
- VIEN : croissants, pains au chocolat, pains aux raisins, croissants fourrés, autres viennoiseries
- PATI : macarons, pastéis de nata, pâtes feuilletées, autres pâtisseries
- SNAC : snacks salés, pains à burger, wraps, pièces apéritives...
- BOIS : eaux, sodas, jus, infusions, cafés, thés

`BOIS` est une catégorie commerciale, pas un état physique. Une crème liquide, une huile,
un sirop à diluer ou un coulis sont des `MATP` : on ne les vend pas à boire. Le test qui
tranche est le sirop concentré — sous `BOIS` la réponse est immédiate. L'état physique,
lui, est déjà porté par `storage_mode`.

### Niveau 3 — Type produit (clé générique)

`(categorie) × (format/poids) × (caractéristique distinctive)` — ex. « croissant pur beurre 40 g ».

Les trois fichiers portent le **code** en colonne `famille` (`VIEN`), pas le libellé
(`Viennoiseries`). La livraison initiale mélangeait les deux : libellé en colonne, code
dans `id_generique`.

### Attributs transverses (filtres)

- **Technologie** : CRU (pousse contrôlée), PAC (pré-poussé), PRECUIT, CUIT, PRET_A_SERVIR
- **Labels / signes** : BIO, Clean Label, Halal, Végétarien/Vegan, Pur beurre, AOP, œufs plein air...
- **Allergènes majeurs** : deux champs distincts — `allergenes_declares` (présents dans la recette) et `traces_possibles` (contamination possible), listes normées séparées par « ; »
- **Statut** : ACTIF = présent dans le catalogue public du fournisseur à la date de collecte (pas une garantie de disponibilité commerciale) ; NOUVEAUTE ; ARRETE (fin de vie) ; REMPLACE_PAR (ref)

## Modèle de données — deux fichiers CSV

### 1. `produits_generiques.csv` (axe 1)

| Champ | Description |
|---|---|
| `id_generique` | Clé stable (ex. `VIEN-CRO-PB-040`) |
| `famille` / `categorie` | Taxonomie ci-dessus |
| `nom_normalise` | Nom nettoyé, ex. « croissant pur beurre 40 g » |
| `poids_unitaire_nominal` | Grammage de référence |
| `description_generique` | Définition neutre du produit |
| `ingredients_typiques` | Composition usuelle (indicative) |
| `usages` | Petit-déjeuner ; snacking ; buffet... |

### 2. `references_fournisseurs.csv` (axe 2)

| Champ | Description |
|---|---|
| `fournisseur` | Nom commercial (Bridor, Coup de Pates...) |
| `ref_sku` | Référence catalogue fournisseur |
| `nom_commercial` | Libellé exact du catalogue |
| `famille` / `categorie` / `gamme` | Taxonomie + collection marketing (ex. « Eclat du Terroir ») |
| `technologie` | CRU / PAC / PRECUIT / CUIT / PRET_A_SERVIR |
| `poids_unitaire` | Poids unitaire annoncé |
| `unites_par_colis` | Colisage (unités/carton) |
| `colis_par_palette` | Palettisation si publiée |
| `poids_colis_kg` | Calculé = poids unitaire × colisage |
| `ingredients` | Liste exacte de la fiche technique |
| `allergenes_declares` | Allergènes présents dans la recette (liste normée « ; ») |
| `traces_possibles` | Traces / contamination possible (liste normée « ; ») |
| `labels` | BIO ; Clean Label ; Halal ; Végétarien ; Pur beurre... |
| `ddm_mois` | Durée de conservation (congélation −18 °C) |
| `provenance` | Site/pays de fabrication si publié au niveau produit (sinon `n.d.` — Bridor ne publie la provenance qu'au niveau marque : usines en France, gamme Panidor au Portugal ; à compléter via fiche technique ou compte pro) |
| `statut` | ACTIF / NOUVEAUTE / ARRETE |
| `url_source` | Fiche produit d'origine |
| `date_collecte` | AAAA-MM-JJ |

## Sources de collecte (périmètre surgelés boulangerie)

Sources exactes du pilote Bridor :

- Catalogue en ligne : https://www.bridor.com/fr-fr/catalogue-produit (396 références recensées, 15 catégories)
- Catalogue PDF 2025 : https://ecatalogue.bridor.com/pdf/output/6793a03f8d4fc368830367/fr/2025-01-24%20-%20Catalogue%202025%20(fr).pdf

| Fournisseur | Accès | Méthode |
|---|---|---|
| Bridor | Catalogue en ligne public (396 réf. recensées) + PDF catalogue 2025 | Extraction pages catégories + fiches produit |
| Coup de Pates (Aryzta) | E-shop en accès libre, prix sur compte | Fiches produit publiques |
| Pasquier, Boncolac, Tipiak | Catalogues web publics | À traiter en phase 2 |
| Distributeurs (Metro, Transgourmet...) | Compte pro / EDI | Phase 3 |

## Règles de qualité

- Toute ligne cite sa `url_source` et sa `date_collecte`.
- Champ non renseigné = `n.d.` (jamais deviné).
- Un SKU disparu du catalogue passe en `statut = ARRETE` (on ne supprime pas : historique food cost).
