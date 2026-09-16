# Make_or_Buy — repères de session

Le dépôt se documente lui-même. Ce fichier ne redit pas ce que `docs/`, `SCHEMA.md` et
`POSTULATE.md` portent déjà : il donne l'itinéraire et les pièges qui ont coûté cher.

## Ce que le projet est

Rendre exécutable et auditable une **doctrine d'arbitrage fabriquer / acheter**. Chaque
décision MAKE, BUY ou HYBRID doit se tracer à une règle durable nommée, un fait daté et une
incertitude déclarée. Le versionnement crypto de `doctrine_tool.py` est le tell : on ne
construit pas du change-control sha256 pour un générateur de menus, on le construit pour
une référence normative citable à une date.

## Quatre couches, et ce qui fait autorité

| | Rôle | Autorité |
|---|---|---|
| `doctrine/doctrine.json` | comment décider — 8 principes, G001-G006 | normative, suit le .docx humain |
| `postulates/la_manita/` | La Manita, panier à prix fixe | normative, versionnée par `deltas/` |
| `data/` | sur quoi décider — fiches, référentiel, fournisseurs | faits datés |
| `data/research/` | pistes et preuves de recherche | non-opposable, jamais une autorisation d'achat |
| `src/make_or_buy/`, `*_tool.py` | application des règles | implémentation, corrigeable |

Un paquet normatif l'est sur ses **règles**, jamais sur son implémentation. `manita_validator.py`
est livré avec le postulat et se corrige comme n'importe quel code — le traiter comme
intouchable a laissé passer quatre défauts dont un bloquant.

## Les pièges, par ordre de ce qu'ils ont coûté

**Le coût d'un produit est le coût complet évitable, jamais le coût matière.** C'est G002.
Le champ s'appelle `avoidable_cost_eur` et s'appelait `material_cost_eur` en portant déjà le
total — un nom qui ment fait réintroduire le défaut de bonne foi. Aucun repli silencieux :
donnée absente ⇒ `None` ⇒ `DATA_INCOMPLETE`.

**Une cible n'est pas un plafond.** `manita.config.json` porte les deux, nommés
séparément : `target_bundle_cost_ratio` 0,30 oriente, `hard_max_bundle_cost_ratio` 0,35
rejette. `engine.py` avait retenu la cible comme seuil de rejet et supprimait toute la bande
intermédiaire — dont le panier réellement sourcé, à 30,9 %. Même famille que G002 d'un cran
plus haut : là un *nom* mentait, ici un *nombre* portait deux sens.

**Une source de prix n'est pas un fournisseur.** `price_source_id` désigne l'entité dont on
capture les prix ; `supplier_id` celle chez qui on envisage d'acheter, et vaut `null` tant
qu'aucune promotion au Supplier Master n'a eu lieu. Cinq des dix sources sont des
mercuriales pures.

**Deux taxonomies de famille coexistent et ne doivent pas fusionner.** `famille` du
référentiel (`PAIN`, `VIEN`, `PATI`, `SNAC`, `BOIS`, `MATP`, `EPIC`) est une *nature de
produit*. `family` de la fiche canonique (`SNACK`, `COLD_DRINK`, `GARNITURE`, `DESSERT`,
`HOT_DRINK`) est un *rôle dans le panier*. Un croissant est `VIEN` par nature et `DESSERT`
dans un panier. Voir `SNAC` / `SNACK` : le réflexe de les unifier est le piège.

**Une colonne dont les valeurs viennent du vocabulaire du fournisseur ne peut pas servir de
clé de rapprochement.** `famille`, `technologie` et `statut` ont tenu parce qu'ils étaient
imposés au collecteur ; `categorie` a dérivé. Elle se dérive désormais de l'intitulé —
`generics_tool.py rebuild`.

**Le grammage n'est pas dans la clé générique.** Deux catalogues vendent le même produit à
des formats différents : Bridor fait le croissant en 40 et 50 g, Coup de Pâtes de 25 à 125 g,
sans recouvrement. Le rattachement croisé est passé de 5 % à 66 % en retirant le gramme.

**Le temps facturé est le temps immobilisé, pas le temps écoulé.** Une infusion de 30 min
surveillée en 1 min coûte 1 min. Compter l'écoulé externalise tout ce qui lève, repose ou
infuse — biais orienté, pas bruit.

**Ne jamais inventer un chiffre.** Un coût, un prix, une DLC ou une allégation absents se
déclarent absents. `missing_critical_fields` est obligatoire dès que `confidence != HIGH`.
Une allégation vegan exige `SUPPLIER_DOCUMENTED` ou `INTERNAL_RECIPE_DOCUMENTED` — une page
produit ne suffit pas, elle ne dit rien des changements de recette.

**Un fabricant n'est pas un fournisseur.** 7 des 13 au registre sont
`MANUFACTURER_REFERENCE` / `DISTRIBUTOR_REQUIRED` : sourçables, pas commandables.

**`PATI-PATE` est de la pâte feuilletée, pas des pâtes alimentaires.**

## Commandes

```bash
product_tool.py status|validate|compile|operations   fiches produit, gabarits par technologie
generics_tool.py rebuild                             référentiel: catégories dérivées, clés
suppliers_tool.py import-registry <xlsx>             supplier master depuis le registre d'achat
doctrine_tool.py validate|update                     doctrine versionnée
make-or-buy manita-check [--dietary VEGAN]           validation du panier contre le postulat
make-or-buy manita --lignes N --cible X              grille à prix cible (CONSTRAINED_MATRIX)
```

Tests sans framework : `python3 tests/test_*.py`. Ils encodent des règles, pas des sorties —
un test écrit depuis l'implémentation ratifie le bug.

## Manière de travailler

Les revues d'Alex arrivent en prose et se traduisent en **delta versionné** sous
`postulates/*/deltas/`, jamais en édition directe du postulat. Toute modification normative
porte son `from_version` / `to_version` et sa raison.

Un test vert ne prouve rien. Casser la règle exprès, voir le test rougir, restaurer.
C'est la seule preuve qu'il protège quelque chose.

**Purger `__pycache__` avant chaque essai.** Sinon :

```bash
find . -name __pycache__ -type d -exec rm -rf {} +
```

Python décide de recompiler en comparant la date et la taille du fichier. Remplacer `0.35`
par `0.30` ne change ni l'une ni l'autre. Il garde son cache, exécute l'ancien code, et le
test répond sur une version qui n'est plus sur le disque.

Vérifier les chiffres annoncés contre les fichiers avant de les reprendre. Trois livraisons
sur quatre portaient au moins une affirmation fausse — des scripts inexistants, des
compteurs périmés, un statut de famille erroné.

## Workflow de livraison

Pour le périmètre documentaire non impactant de la session actuelle, on peut travailler
directement sur `main`, valider le contenu et le diff, puis committer. L'absence de worktree,
de branche dédiée et de pull request est une décision provisoire de portée, pas une interdiction
générale.

Si la documentation devient substantielle ou impactante, ou si le travail devient concurrent,
réévaluer l'isolation et le besoin d'une branche, d'un worktree ou d'une pull request.

Commandes Git interdites sans autorisation explicite :

- jamais `git reset --hard`, ni aucun équivalent qui puisse écraser du travail ;
- jamais `git checkout`, y compris pour changer de branche ou restaurer un fichier.

Mutation de texte : `sed` et ses équivalents lisent et filtrent, ils ne réécrivent pas.
`sed -i`, `perl -i`, `awk -i inplace`, `ed`, `ex -s`, et les boucles qui les masquent sont
interdits en écriture — une substitution globale sur un identifiant partagé a déjà confondu
trois espaces de noms ici et cassé cinq tests sans qu'aucune commande n'échoue. Éditer par
ancrage, puis relire le diff. Détail : `AGENTS.md`, et PART 10 des règles globales.

Dès qu'une modification de code devient nécessaire, ce régime cesse de s'appliquer : il faut
repenser l'isolation du travail (branche ou worktree), verrouiller le comportement par des
tests, valider le changement, puis appliquer le workflow de revue avant une éventuelle PR.
