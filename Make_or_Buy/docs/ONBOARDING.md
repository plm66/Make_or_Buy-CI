# Bienvenue

Ce document est écrit pour quelqu'un qui arrive et qui n'a pas cinq jours à passer dans
l'historique. Il dit trois choses : ce qui existe, ce qu'on fait en ce moment et pourquoi,
et ce qui reste.

Lisez-le en entier avant votre premier commit. Le dépôt a une doctrine, et la plupart de ses
règles ont été payées par un défaut réel.

---

## 1. À quoi sert ce dépôt

Rendre **exécutable et auditable** la doctrine d'arbitrage fabriquer / acheter d'une
boulangerie. Toute décision `MAKE`, `BUY` ou `HYBRID` doit se tracer à une règle nommée, un
fait daté et une incertitude déclarée.

Ce n'est pas un générateur de menus. C'est une base de décision sur le choix des produits, et
un outil d'arbitrage sur la fabrication hybride — le mélange raisonné du frais et du naturel
avec le surgelé et le substitué.

**La Manita est un module, rien de plus.** Le socle sert d'autres formules à venir.

---

## 2. Ce qui est réalisé

| brique | état |
|---|---|
| doctrine versionnée, 8 principes, `G001`–`G006` | opérationnelle, empreinte sha256 |
| référentiel de matières premières | **38 matières, sans aucun prix** — c'est voulu |
| factures METRO lues en données | **384 lignes**, 5 016 € HT, mars→septembre 2026 |
| rattachement article → matière | **46 articles** — 17 actifs, 22 à vérifier, 7 hors périmètre |
| gabarits d'opérations | 6 degrés, de `MATIERES` (9 gestes) à `PRET_A_SERVIR` (0) |
| dérive des prix payés | 175 comparaisons, 69 observations de prix matière |
| alternatives marché datées | 6 matières couvertes, **10 verdicts `CHANGER` réels** |
| moteur d'arbitrage | `selected_cost`, `menu_score`, `minutes_avant_bascule` |
| glossaire et 3 ADR | **ADR-0001 `ACCEPTED`** le 23-09 ; 0002 et 0003 `PROPOSED` |
| invariants exécutables | **206**, sans framework |

### Pourquoi le référentiel ne porte aucun prix

Une matière est une **identité** — « farine de blé T65 » ne change pas quand le prix bouge.
Un prix est un **fait daté, propre à une source**. Les mélanger produit un référentiel qui
périme en silence.

Mesure qui le justifie : le même beurre, même article METRO, a coûté de **6,04 à 7,40 €/kg
en six mois**, soit 23 % d'écart, avec une tendance baissière et trois remises de volume.

---

## 3. Ce qu'on fait en ce moment, et pourquoi

**On termine de transformer des documents en faits, et on n'a pas encore branché ces faits
sur le moteur.**

L'état brut, sans ménagement :

```
gestes chronométrés      0 / 21
ADR acceptés             0 / 3
produits au catalogue    1     dont chiffrés : 0
```

`selected_cost()` rend `DATA_INCOMPLETE`. **C'est correct** : il refuse d'inventer un coût.
Le travail restant n'est pas du code, c'est de la mesure et de l'arbitrage.

### Le chiffre qui explique l'ordre des priorités

Pour un croissant, lot de 60, le seuil au-delà duquel acheter bat fabriquer :

| beurre | prix mesuré | achats | seuil de bascule |
|---|---|---|---|
| doux 500 g, bas de fourchette | 6,04 €/kg | 16 | **64 min** |
| AOP 84 % tourage | 13,03 €/kg | **1** | **45–50 min** |

**Chronométrer avant d'avoir choisi le beurre ne décide rien** : on obtiendrait `MAKE` avec
l'un et `BUY` avec l'autre, sur le même relevé. La composition se tranche avant
l'approvisionnement — c'est ADR-0002.

Et ce choix-là n'attend pas un arbitrage mais **une étiquette** : le beurre qui porte 93,6 %
de la dépense est rattaché `A_VERIFIER`, sa désignation ne déclarant aucun taux de matière
grasse.

---

## 4. Ce qui reste

L'ordre est une chaîne de dépendances, pas une préférence. Le détail est dans
[`ROADMAP.md`](ROADMAP.md).

1. ~~**Trancher la composition**~~ — ADR-0001 `ACCEPTED` le 23-09. Reste la matière grasse,
   qui attend une étiquette et non une décision.
2. **Chronométrer** 21 gestes, deux nombres chacun : minutes immobilisées et minutes écoulées.
3. **Le croissant** — premier produit dont les deux coûts sont non nuls.
4. **Brancher la couche de prix** — l'instrument existe, le câblage non.
5. Recettes · 6. Hybride par composant · 7. La Manita.

---

## 5. Relecture du 23-09-2026 — ce qu'un nouveau doit savoir

### `GARDER` affirme une décision que rien n'a contestée

Sur les 384 lignes du corpus, après la PR #3 :

```
NON_RATTACHE   ARTICLE_ABSENT_DU_RATTACHEMENT   244   63,5 %
A_ARBITRER     RESERVE_A_VERIFIER                71   18,5 %
GARDER         AUCUNE_ALTERNATIVE_CHIFFREE       32    8,3 %
A_ARBITRER     CONDITIONNEMENT_ILLISIBLE         17    4,4 %
HORS_PERIMETRE REVENTE_DIRECTE                   10    2,6 %
CHANGER        ALTERNATIVE_MOINS_CHERE           10    2,6 %
```

**32 verdicts `GARDER` sur 32 ne reposent sur aucune alternative chiffrée.** Le mot dit
« on conserve ce fournisseur » ; l'état réel est « rien n'a été comparé ».

La PR #3 a rendu le problème **plus** trompeur, pas moins. Dix verdicts `CHANGER` réels
existent désormais à côté : un lecteur en déduit raisonnablement que les `GARDER` ont été
confrontés et ont gagné. Aucun ne l'a été — le catalogue d'alternatives ne couvre que
6 matières.

C'est le motif récurrent du dépôt — un nom qui porte plus que sa preuve. `material_cost_eur`
portait un coût complet, `PRET_A_SERVIR` dit « servir » et compte « transformer ». Ici
`GARDER` dit « tranché » et signifie « jamais examiné ».

Le code distingue déjà les deux cas par la `raison`, mais un lecteur qui scanne la colonne
verdict voit une file de `GARDER` et conclut que le sourcing est optimisé. Il ne l'est pas :
il est inexploré.

**Correctif proposé** : un verdict distinct, `NON_COMPARE`, pour l'absence d'alternative.
`GARDER` réservé au cas où une alternative chiffrée existe et se révèle plus chère — celui-là
est une vraie décision. À ce jour **zéro ligne** serait dans ce cas, ce qui est précisément
l'information que le mot cache.

### Deux points sur le serveur local

`serveur_factures.py` est sain sur l'essentiel : `127.0.0.1` seulement, dossier temporaire
nettoyé, rien n'est écrit dans `data/`, une exception devient un message.

- **Lecture non bornée** : `int(Content-Length)` puis `read(taille)` sans plafond. Un fichier
  déposé par erreur — une vidéo — alloue sa taille en mémoire. Menace locale seulement.
- **`int()` sur un en-tête libre** : un `Content-Length` non numérique lève `ValueError` et
  rend une trace, alors que le module promet qu'« une erreur rend un message, pas une
  exception ».
- **Pas de contrôle d'origine** : une page tierce ouverte dans le même navigateur peut poster
  sur le port. La réponse contient le référentiel de rattachement. Faible valeur, mais c'est
  la classe de risque connue des serveurs localhost.

### Une coquille dans une valeur machine

`ALTERNATIVE_PLUS_CHEREE` — deux `E`. C'est une constante lue par la page.

---

## 6. Recommandations d'usage

### Urgent — ce qui fait perdre du travail ou produit un chiffre faux

| | |
|---|---|
| **`python3 -B` sur toute exécution de test.** | Python valide son cache sur `(mtime, taille)`. Inverser deux chaînes de même longueur ne change ni l'une ni l'autre, et un `.pyc` périmé passe pour frais. Mesuré le 21-09 : le garde G002 est passé **au vert sur la régression même qu'il surveille**. `-B` n'empêche que l'écriture — pour guérir un cache déjà posé, supprimez `__pycache__`. |
| **Activez le hook, une fois par clone.** | `git config core.hooksPath .githooks`. Sans cette ligne, la règle « `main` ne reçoit que des fusions » existe et rien ne la tient. Trois sessions se sont déjà croisées. |
| **Jamais `git checkout`, `git switch`, `git reset --hard`, `git stash`.** | On ne change pas de branche, on ouvre un worktree : `git worktree add ../Make_or_Buy-worktrees/<nom> -b <type>/<sujet> main`. Jamais sous `.claude/` — un dev sous un autre modèle ne pourrait pas prendre la relève. |
| **Ne jamais inventer un chiffre.** | Coût, prix, DLC, allégation absents se déclarent absents. Une donnée manquante rend `None`, qui remonte en `DATA_INCOMPLETE`. Un repli silencieux sur zéro est la faute la plus chère du dépôt. |

### Important — ce qui fait dériver la qualité

| | |
|---|---|
| **Un test vert ne prouve rien.** | Cassez la règle exprès, voyez le test rougir, restaurez. C'est la seule preuve qu'il protège quelque chose. Un test écrit depuis l'implémentation ratifie le bug. |
| **Chaque fichier de test finit par son bloc `__main__`.** | Sans lui il sort en zéro sans rien exécuter. Deux fichiers étaient dans ce cas : douze invariants ne tournaient pas sous la commande documentée. |
| **Un compte n'est pas un finding.** | « 4 MEDIUM et 3 LOW » sans les énumérer ne laisse rien d'actionnable. Tout rapport porte un `file:line` et une phrase par finding, et une section de ce qui n'a **pas** été ouvert. |
| **Le libellé fournisseur n'est jamais une clé.** | L'article `2422798` a changé de nom entre juillet et septembre, même EAN, même prix. Le rattachement Foodomarket a échoué là où celui de METRO tient, parce que là-bas il n'existait que des libellés — et « amande » y désigne aussi un coquillage. |
| **Deux taxonomies de famille coexistent.** | `famille` (`PAIN`, `VIEN`, `PATI`, `SNAC`, `BOIS`, `MATP`, `EPIC`) est une nature de produit. `family` (`SNACK`, `COLD_DRINK`, …) est un rôle dans le panier. Un croissant est `VIEN` par nature et `DESSERT` dans un panier. Le réflexe de fusionner `SNAC` et `SNACK` est le piège. |
| **G002, la dette la plus chère.** | Ne jamais comparer un prix fournisseur au seul coût matière interne. Le premier est complet, le second non : la comparaison fait gagner l'interne à tort, d'un facteur 2 à 7. |
| **`sed -i` et tout équivalent en écriture sont interdits.** | Un `sed` global sur `registry_supplier_id` a confondu trois espaces de noms partageant un mot et cassé cinq tests, sans qu'aucune commande n'échoue. |

---

## 7. Le motif qui revient

**Une référence n'est pas un fait sur nous.** Six occurrences mesurées :

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

## Par où commencer

```bash
git config core.hooksPath .githooks
cd Make_or_Buy && python3 -B tests/test_*.py        # 206 invariants
python3 -B comparaison_factures.py derive --top 10  # la dispersion des prix payés
```

Puis lisez [`GLOSSAIRE.md`](GLOSSAIRE.md) — un code absent du glossaire est un code inventé —
et [`../CLAUDE.md`](../CLAUDE.md), qui liste les pièges par ordre de ce qu'ils ont coûté.
