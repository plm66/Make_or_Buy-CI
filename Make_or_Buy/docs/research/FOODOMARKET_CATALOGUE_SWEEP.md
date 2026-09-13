# Balayage complet du catalogue Foodomarket — instruction de travail

- **Destinataire** : développeur
- **Date** : 2026-09-13
- **Prérequis** : compte professionnel Foodomarket ouvert (fait), Node ≥ 18, Playwright
- **Livrable attendu** : un fichier JSON daté, un script rejouable, un rapport de couverture

## Objectif

Relever **l'intégralité** du catalogue accessible au compte, pas un échantillon.

Une première passe existe : `data/research/foodomarket_matp_capture_2026-09-13.json`.
Elle a ramené **3 097 produits distincts** chez **31 fournisseurs**, mais par
38 mots-clés — donc tout ce qui ne contient aucun de ces mots n'a jamais été vu, et
**13 recherches sur 38 ont buté sur un plafond de 250 résultats**. Elle n'est pas une
référence de couverture, seulement une preuve que la mécanique fonctionne.

## Ce qui est déjà établi et ne doit pas être refait

### La session

**Aucun identifiant ne doit apparaître dans le code, un fichier du dépôt, une variable
d'environnement commitée ou un transcript.** La méthode retenue et éprouvée :

1. `chromium.launchPersistentContext(profil, { headless: false, channel: 'chrome' })`
2. l'opérateur se connecte **à la main** dans la fenêtre
3. la session vit dans le profil, hors du dépôt : `~/.cache/foodomarket-profile`
4. les passes suivantes réutilisent le profil

Le script ne doit lire que la **présence** d'un cookie de session, jamais sa valeur.

`channel: 'chrome'` et non le Chromium de Playwright : la révision téléchargée par le
module ne correspondait pas à celle installée, et un vrai Chrome passe mieux.

### L'extraction d'une carte produit

Les cartes portent des attributs stables :

```html
<div id="product-card-<uuid>" data-id="<uuid>" data-supplier-id="<uuid>">
```

Sélecteur qui marche : `[id^="product-card-"]`. Le texte d'une carte se découpe en lignes :

```
[Promo]  nom  |  fournisseur  |  origine + colisage  |  prix colis  |  prix unitaire
```

Exemples réels :

```
Farine à pizza T00 | ABC Peyraud | 10X1 KG | 7,40 €/colis | 0,74 €/kg
Patate douce orange | Daumesnil | Afrique Du Sud 1 KG | 1,76 €/kg
Beurre de feuilletage sec Montaigu | Aux Choix | France 2 KG | 27,90 €/pc | 13,95 €/kg
```

Unités rencontrées : `€/kg`, `€/l`, `€/pc`, `€/pièce`, `€/colis`. Le prix colis divisé par
le colisage retombe sur le prix unitaire — vérifié, l'arithmétique est juste.

### Ce qui a résisté

**Les filtres de catégorie ne sont pas des liens.** Ce sont des `div` sans `href`, de classe
`fmkt-mobile-category-filter` et un jumeau bureau. Trois méthodes de clic ont échoué :
`getByText`, `locator.filter({ hasText })`, et un `.click()` en `page.evaluate`. Le contenu
ne changeait pas — 250 cartes identiques.

**Rien ne le prouve impossible**, c'est simplement ce qui n'a pas marché en trois essais.
Pistes non explorées : écouter la requête réseau qu'un clic manuel déclenche et la rejouer,
ou trouver le paramètre d'URL correspondant.

Les onze rayons : Fruits, Légumes, Crèmerie, Boucherie, Charcuterie, Marée, Epicerie salée,
Epicerie sucrée, Boissons, Cave, Fournitures.

## Le travail demandé

### 1. Trouver un chemin d'énumération exhaustif

Par ordre de préférence :

- **a.** Ouvrir les outils réseau, cliquer une catégorie à la main, observer l'appel émis.
  S'il existe une API paginée, tout le reste devient trivial. C'est la piste à tenter en
  premier, et personne ne l'a encore faite.
- **b.** Faire fonctionner le filtre de catégorie par automatisation, puis paginer chaque
  rayon jusqu'à épuisement.
- **c.** À défaut, balayage alphabétique : rechercher `a`, `b`, … et dédupliquer par
  `data-id`. Coûteux, et le plafond de 250 reste à contourner.

### 2. Contourner le plafond de 250

Treize recherches ont été tronquées. Déterminer si 250 est un plafond d'affichage, de
virtualisation ou de résultats, et comment paginer au-delà. Sans ça, aucune couverture ne
peut être affirmée.

### 3. Produire le fichier

Un JSON par passe, nommé `foodomarket_catalogue_AAAA-MM-JJ.json`, avec :

```json
{
  "dataset": "FOODOMARKET_FULL_CATALOGUE",
  "observed_at": "AAAA-MM-JJ",
  "price_source_id": "foodomarket",
  "capture_method": "AUTHENTICATED_WEB",
  "enumeration_method": "<comment l'exhaustivité a été obtenue>",
  "coverage_claim": "<ce qui est couvert, et ce qui ne l'est pas>",
  "data_status": "RAW_UNMATCHED_NOT_OPERATIONALLY_VALIDATED",
  "products": [
    {
      "marketplace_product_ref": "<data-id>",
      "marketplace_supplier_ref": "<data-supplier-id>",
      "marketplace_supplier_name": "ABC Peyraud",
      "product_name": "Farine à pizza T00",
      "pack_raw": "10X1 KG",
      "case_price_eur": 7.40,
      "unit_price_eur": 0.74,
      "unit": "kg",
      "tax_basis": "UNKNOWN",
      "category_path": ["Epicerie sucrée"],
      "observed_at": "AAAA-MM-JJ"
    }
  ]
}
```

### 4. Rapport de couverture

- nombre de produits distincts par `data-id`
- nombre de fournisseurs distincts, **et lesquels des 32 manquent**
- par rayon : nombre de produits, et si le rayon a été épuisé ou tronqué
- toute recherche ou page ayant buté sur une limite

## Interdits

Ils ne sont pas des préférences de style — chacun correspond à une erreur déjà commise.

| interdit | pourquoi |
|---|---|
| Écrire un identifiant, mot de passe ou cookie dans le code, le dépôt ou un log | Un dépôt et un log sont permanents |
| Déduire `HT` ou `TTC` | Aucune page ne l'indique. Écrire `UNKNOWN` |
| Se fier au prix unitaire affiché quand la division du colis en donne un autre | Trois prix d'une livraison précédente étaient des arrondis contredisant l'arithmétique |
| Rattacher un produit à une matière par le terme de recherche | `beurre doux` ramène vingt-cinq patates **douces** ; `levure sèche` des dattes **séchées** ; `Amande` chez un mareyeur est un **coquillage** |
| Compléter un champ absent par une valeur vraisemblable | Un champ vide se déclare vide |
| Annoncer une couverture sans la mesurer | « tout le catalogue » sans compte de produits distincts n'est pas une affirmation vérifiable |

## Critères de recette

1. Le script est rejouable sans intervention, une fois la session établie une première fois.
2. Aucun identifiant n'apparaît dans le dépôt — vérifiable par `git log -p` et un `grep`.
3. Le nombre de produits distincts est supérieur à **3 097** — sinon la passe n'apporte rien
   sur la précédente.
4. Les **32** fournisseurs de la liste du compte apparaissent, ou l'absence de chacun des
   manquants est expliquée. `My Halal Food` n'est jamais apparu dans la première passe.
5. Chaque produit porte son `data-id` : c'est la clé de déduplication entre deux passes.
6. Un contrôle automatique vérifie, sur chaque produit portant les deux, que
   `prix colis / colisage == prix unitaire`, et signale les écarts plutôt que de les corriger
   en silence.
7. Le rapport de couverture distingue ce qui a été épuisé de ce qui a été tronqué.

## Ce que le fichier ne doit pas faire

Il ne décide rien. Aucune de ces offres n'alimente un coût matière tant qu'un rattachement
explicite à un `id_matiere` n'a pas été établi — par autre chose qu'une correspondance de
chaîne. Le statut `RAW_UNMATCHED_NOT_OPERATIONALLY_VALIDATED` est porté par le fichier
lui-même, et un invariant l'impose.

Le rattachement est un travail distinct, et il est plus délicat que la capture.
