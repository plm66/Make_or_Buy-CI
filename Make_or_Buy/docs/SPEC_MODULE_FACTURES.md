# Module factures : lire, rattacher, proposer

Ce document cadre la dernière brique du module : une page locale où l'on dépose une facture,
qui restitue ligne par ligne ce qu'on sait d'elle et ce que le dépôt propose d'en faire.

Il ne remplace pas `data/materials/SCHEMA.md` ni `RATTACHEMENT.md`, qui font autorité sur la
matière et sur le rattachement. Il ne remplace pas `doctrine/doctrine.json`. Il décrit un
chemin de lecture et une forme de proposition.

## Ce que le module fait déjà

| étape | état | preuve |
|---|---|---|
| extraire un PDF de facture METRO en lignes | fait, hors de cette branche | `metro_factures.py`, 384 lignes, contrôle arithmétique 384/384 |
| mesurer la dérive d'un article entre factures | fait | `derive`, 175 comparaisons sur 20 factures |
| lire le conditionnement et refuser quand il est illisible | fait | `prix_au_kilo`, jugé par le prix imprimé, 24 accords sur 24 |
| produire une observation de prix matière | fait | `observations_matiere`, 69 observations sur 12 matières |

## Ce que la page ajoute

Un dépôt de fichier, une lecture, et par ligne une proposition avec sa raison.

```
[PDF déposé] -> extraction -> rattachement -> prix au kilo -> proposition
```

Chaque étape peut rendre un trou, et le trou est affiché. Aucune étape ne remplit un champ
qu'elle n'a pas lu.

## La proposition, et sa règle dure

Chaque ligne reçoit un verdict parmi six. Les définitions font autorité dans
[`GLOSSAIRE.md §9`](GLOSSAIRE.md) ; ce qui suit les commente.

- **`GARDER`** — une alternative chiffrée, datée, à unité alignée existe **et elle est plus
  chère**. La comparaison a eu lieu, la source actuelle l'a emporté.
- **`NON_COMPARE`** — la ligne est rattachée et lisible, mais aucune alternative chiffrée
  n'existe sur cette matière. Ce n'est pas une validation du fournisseur, et ce n'est pas non
  plus un jugement : rien ne l'a contesté.

  Ce verdict a été scindé de `GARDER` le 2026-09-23, sur mesure : **32 `GARDER` sur 32**
  étaient ce cas, et le cas comparé n'avait jamais été atteint une seule fois. Dix `CHANGER`
  réels existant à côté, un lecteur en déduisait que les `GARDER` avaient été confrontés et
  avaient gagné. Un mot qui affirme une mesure jamais faite est le défaut que ce dépôt paie
  en boucle — voir `material_cost_eur` en §4 du glossaire.
- **`CHANGER`** — il existe une autre source de prix sur la même matière, à unité alignée,
  et elle est moins chère. **Ce verdict exige le prix de l'alternative. Sans lui, il ne peut
  pas être rendu.**
- **`A_ARBITRER`** — la ligne est lisible mais rien ne permet de trancher : rattachement
  `A_VERIFIER`, conditionnement illisible, matière sans conversion, ou alternative sans prix.
  La raison est affichée, et c'est cette liste qui dit quoi aller mesurer.
- **`HORS_PERIMETRE`** — la ligne ne vise aucune matière : non alimentaire, emballage,
  matériel. Elle est comptée à part, jamais forcée dans le référentiel.
- **`NON_RATTACHE`** — l'article n'est pas dans le rattachement. Ce n'est pas un arbitrage :
  c'est un lien manquant, et il se répare dans `data/materials/rattachement_metro.csv`. Ce
  verdict a été ajouté après la première mesure, où il portait 303 des 384 lignes.

Invariant qui tient l'ensemble : **`CHANGER` n'est jamais rendu sans un prix alternatif
aligné et daté.** Une recommandation d'achat sans prix est une opinion, et le dépôt n'en
produit pas.

## Ce qui manque aujourd'hui, et qui borne la page

Le dépôt ne porte **aucun prix concurrent** sur les articles de ces factures. Les seules
sources existantes sont des relevés de recherche (`data/research/`, non opposables), les
promotions Halal Food Service, et les candidats fournisseurs dont les prix sont vides ou
`QUOTE_REQUIRED`.

Conséquence à assumer : sur les 20 factures actuelles, la page affichera surtout `GARDER` et
`A_ARBITRER`. Les `CHANGER` apparaîtront le jour où une deuxième source de prix existe sur
une même matière. La page n'anticipe pas ce jour-là, elle rend visible ce qu'il faut aller
chercher.

## Ce que la page n'est pas

- Pas un moteur de décision d'achat : elle propose, elle ne commande rien.
- Pas un portail distant : serveur local, aucune authentification, aucun envoi vers
  l'extérieur. Une facture ne sort pas de la machine.
- Pas un substitut au rattachement : elle lit `data/materials/rattachement_metro.csv` et
  n'invente aucun rapprochement. Un article inconnu s'affiche non rattaché.

## Contraintes techniques

- Extraction PDF : `pdftotext` (poppler) est déjà requis par `metro_factures.py`, la page
  hérite de la dépendance et doit échouer proprement s'il manque.
- Serveur : bibliothèque standard Python uniquement, comme le reste du dépôt.
- Les fichiers écrits par la page vont dans un dossier temporaire, jamais dans
  `data/price_observations/`, sauf décision explicite.
- La sortie conserve la forme des artefacts existants : `dataset`, `version`, `data_status`,
  `consumer_rule`.

## Décisions ouvertes

1. **Emplacement de la couche de prix matière** : `data/material_prices/` proposé, non
   tranché. Aucun fichier n'est écrit tant que ce n'est pas décidé.
2. **Sort du non alimentaire** : famille d'achat suivie, ou statut `HORS_PERIMETRE` simple.

## Invariantes attendues, à écrire avant le code

- une ligne non rattachée ne reçoit jamais de proposition `GARDER` ou `CHANGER` ;
- un `A_VERIFIER` ne peut pas produire `GARDER` sans afficher sa réserve ;
- `CHANGER` sans prix alternatif daté fait échouer l'invariant, pas l'affichage ;
- **`GARDER` sans alternative chiffrée à unité alignée fait échouer l'invariant.** Le verdict
  affirme une comparaison ; sans les deux termes, elle n'a pas eu lieu et le cas revient à
  `NON_COMPARE` ;
- **tout code de verdict ou de raison figure dans `GLOSSAIRE.md` avant de sortir en JSON.**
  Les sept codes ont vécu non déclarés jusqu'au 2026-09-23, contre la règle que le glossaire
  pose en tête : un code absent du glossaire est un code inventé ;
- le nombre de lignes affichées égale le nombre de lignes extraites, moins celles qui sont
  explicitement déclarées comme non lues ;
- la page ne modifie aucun fichier du dépôt en dehors du dossier temporaire.
