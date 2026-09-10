# Make_or_Buy

Moteur local de doctrine, sourcing et composition de menus pour boulangerie.

## Installation

Dézipper ce projet dans :

```text
/Users/erasmus/developer/BOULANGERIES/Make_or_Buy
```

Puis :

```bash
cd /Users/erasmus/developer/BOULANGERIES/Make_or_Buy
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Aucune dépendance Python externe n'est requise pour le moteur local.

## Premier test

```bash
make-or-buy menu --diet VEGAN --tiers 5 7 9
```

Cette commande construit un menu vegan pour trois prix cibles en utilisant le catalogue exemple.

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
- `schemas/` : schémas des produits et requêtes.
- `data/catalog.example.json` : catalogue exemple à remplacer progressivement par les données réelles.
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
