# Make_or_Buy

Moteur local de doctrine, sourcing et composition de menus pour boulangerie.

## Destination du projet

Make_or_Buy n'est pas seulement un générateur de menus. Sa destination est de créer des
**modules de vente alimentaires** — des formules commerciales — à partir de données de coûts
matière fiables et d'une réflexion explicite sur le `MAKE / BUY / HYBRID`.

Le projet repose sur un socle commun :

- catalogue produit canonique, recettes, rendements et coûts complets ;
- coûts matière, main-d'œuvre, énergie, emballage, pertes et conservation ;
- fournisseurs, prix rendus, traçabilité et qualité des preuves ;
- arbitrage déterministe entre fabrication interne, achat externe et modèle hybride ;
- contraintes alimentaires, allergènes, disponibilité et valeur client.

Ce socle alimente ensuite plusieurs **modules de formules**, chacun avec sa propre promesse,
son prix, ses composants obligatoires, ses contraintes et ses règles de substitution :

- **La Manita** : premier module, avec 5 choix, 5 produits et un prix fixe de 5 € ;
- **menu vegan** : formule et prix indépendants de La Manita ;
- **menu oriental ou subsaharien** : par exemple autour d'accras, de mafé ou d'autres
  inspirations culinaires ;
- **menu diététique** : par exemple autour de poulet braisé et d'accompagnements adaptés ;
- futurs modules inspirés de tendances, de saisons ou d'opportunités commerciales.

La Manita est donc un cas d'usage contraint, pas la destination unique du moteur. Un nouveau
module réutilise la doctrine de coûts, de sourcing et de traçabilité, mais ne doit pas hériter
artificiellement des règles commerciales de La Manita.

Chaque module doit pouvoir produire deux sorties :

1. une offre lisible par le client : promesse, composition, options et prix ;
2. une fiche exploitable par la boulangerie : coût, marge, choix `MAKE / BUY / HYBRID`,
   fournisseurs, risques et substitutions.

## Installation

Dézipper ce projet dans :

```text
/Users/erasmus/DEVELOPER/BOULANGERIES/Make_or_Buy/Make_or_Buy
```

Puis :

```bash
cd /Users/erasmus/DEVELOPER/BOULANGERIES/Make_or_Buy/Make_or_Buy
uv venv .venv --python python3
uv pip install --python .venv/bin/python -e .
source .venv/bin/activate
```

Aucune dépendance Python externe n'est requise pour le moteur local.

## Premier test

Smoke test avec le catalogue exemple :

```bash
make-or-buy menu --diet ANY --tiers 15 --top 1
```

Cette commande compose une formule à partir des cinq familles du catalogue et affiche le
coût, le ratio de coût et le mode `MAKE / BUY / HYBRID` de chaque produit.

Pour explorer trois paliers vegan :

```bash
make-or-buy menu --diet VEGAN --tiers 5 7 9 --top 1
```

Une liste `menus: []` signifie que le catalogue courant ne satisfait pas les contraintes du
palier demandé ; ce n'est pas une formule vendable validée.

## Utilisation avec un LLM

Le projet sait générer un paquet complet doctrine + catalogue + question :

```bash
make-or-buy packet "compose-moi un menu vegan sur la base de 3 gammes de prix"
```

Pour interroger directement un endpoint compatible avec l'API OpenAI :

```bash
export LLM_BASE_URL="https://..."
export LLM_MODEL="..."
export LLM_API_KEY="..."
make-or-buy ask "compose-moi un menu vegan sur la base de 3 gammes de prix"
```

`LLM_API_KEY` peut être omis si le fournisseur n'en exige pas.

## Structure

- `doctrine/doctrine.json` : doctrine machine normative.
- `schemas/` : schémas des produits, requêtes et jeux de recherche.
- `data/catalog.example.json` : catalogue exemple à remplacer progressivement par les données réelles.
- `data/research/` : preuves et candidats de recherche non opposables, jamais importés directement dans les décisions opérationnelles.
- `data/research/supplier_candidates/` : candidats fournisseurs, benchmarks et leads de découverte par formule.
- `docs/research/` : contrats et consignes de recherche par famille de menu.
- `src/make_or_buy/engine.py` : moteur déterministe de composition.
- `src/make_or_buy/llm.py` : connecteur générique OpenAI-compatible.
- `src/make_or_buy/cli.py` : interface en ligne de commande.
- `doctrine_tool.py` : outil de validation et de mise à jour versionnée de la doctrine.
- `prompts/system_prompt.md` : comportement attendu du LLM.

## Doctrine et catalogue sont séparés

La doctrine contient les règles durables.
Le catalogue contient les données variables : coûts, fournisseurs, durée de conservation, régime alimentaire,
allergènes, valeur signature, etc.

Cette séparation est essentielle : une évolution du prix d'un cookie ne doit pas modifier la doctrine.

## Exemple de recherche cible

```text
compose-moi un menu vegan sur la base de 3 gammes de prix
```

L'outil doit ensuite :
1. filtrer les produits vegan documentés ;
2. construire les combinaisons compatibles ;
3. respecter le ratio maximal de coût ;
4. privilégier les produits signature lorsqu'ils améliorent la valeur client ;
5. appliquer la doctrine MAKE / BUY / HYBRID ;
6. signaler les données manquantes ou incertaines.


## Version 0.3.0 — fiche produit canonique 2.0.0

Renseigner d'abord le taux de travail, qui vaut pour toutes les fiches :

```bash
$EDITOR params/establishment.json     # labor.cost_per_minute_eur
```

La donnée produit réelle doit ensuite être créée dans `data/products/`, un fichier par référence.

```bash
cp data/product.template.json data/products/mon_produit.json
python3 product_tool.py validate data/products/mon_produit.json
```

Suivre l'avancement :

```bash
python3 product_tool.py status data/products
```

Puis compiler les produits actifs :

```bash
python3 product_tool.py compile data/products --output data/catalog.generated.json
```

Voir `docs/PRODUCT_MODEL.md`.
