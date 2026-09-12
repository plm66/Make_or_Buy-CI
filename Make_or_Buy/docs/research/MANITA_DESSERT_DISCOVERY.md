# MANITA_DESSERT_DISCOVERY — instruction de recherche

Passe de sourcing pour la colonne **DESSERT**. Même discipline que les passes snack et
garniture : aucun prix inventé, aucun coût effectif annoncé sans son calcul.

## Ce qui distingue cette colonne des deux précédentes

C'est la seule où un candidat peut avoir **zéro travail interne restant**. Un biscuit
individuellement emballé se sert tel quel : le gabarit `PRET_A_SERVIR` porte zéro geste, et
`SELECTED_EFFECTIVE_PRODUCT_COST` égale alors exactement le prix rendu. Aucune autre colonne
n'offre cette égalité.

Trois voies, par coût interne croissant.

| Voie | Type | Travail interne restant | Remarque |
|---|---|---|---|
| **A** | `READY_TO_SERVE` | aucun | biscuit, madeleine, barre — emballage individuel d'origine |
| **B** | `THAW_ONLY` | décongélation | voir ci-dessous : ne coûte presque pas de main-d'œuvre |
| **C** | `TRANSFORMED_SURPLUS` | transformation d'invendu | voie propre à une boulangerie |

### Voie B — la décongélation est du temps écoulé, pas du temps immobilisé

P004 : seul le temps pendant lequel quelqu'un est mobilisé est facturé. Une décongélation de
huit heures en chambre froide immobilise un opérateur le temps de sortir le produit et de le
ranger, pas huit heures. Ne pas facturer l'écoulé — ce serait le biais que la doctrine
interdit. Le coût réel de la voie B est la place en froid et la contrainte de planification,
pas la main-d'œuvre.

### Voie C — le coût du produit source n'entre pas

Un croissant invendu transformé en dessert n'apporte pas son coût de production dans le coût
du dessert : ce coût n'est plus évitable, le croissant a déjà été fabriqué. Seuls les coûts
propres à la transformation comptent — matières ajoutées, gestes, énergie, emballage.

`manita.config.json` porte la règle sous `serving_unit_model.derivations.TRANSFORMED_SURPLUS`.
Le validateur l'applique et **refuse `additional_operations`** sur cette dérivation : la
fiche *est* le produit transformé, son `avoidable_cost_total_eur` porte déjà le travail.
L'ajouter le compterait deux fois.

Cette voie exige `source_product_id` et `source_state` valant `DAY_OLD` ou `SURPLUS`.

## Fournisseurs, par ordre

Commandables en direct d'abord — un prix rendu suppose un canal.

1. **Coup de Pâtes** — `ADMITTED_CONDITIONAL`, DIRECT — `pastry`, `american_pastry`, `tartlets`
2. **Transgourmet** — `ADMITTED_CONDITIONAL`, DIRECT — `cakes`, `confectionery`
3. **Sysco France** — `ADMITTED_CONDITIONAL`, DIRECT — produits préparés
4. **Domafrais / France Frais** — `ADMITTED_CONDITIONAL`, DIRECT — traiteur, surgelés
5. **METRO France** — `BACKUP`, DIRECT / PICKUP — dépannage

Fabricants, sourçables mais **non commandables en direct** — leur prix catalogue n'est pas
un prix rendu, il suppose un distributeur identifié :

- **Traiteur de Paris** — `individual desserts`, `snacking desserts` : le plus proche de la
  cible, et le plus frustrant, puisqu'il demande un distributeur
- **Vandemoortele** — donuts, muffins, brownies, cakes
- **St Michel Professionnel** — madeleines, biscuits : la voie A par excellence
- **Délifrance**, **Bridor** — pâtisserie et viennoiserie

## Ne pas filtrer sur l'enveloppe famille

`family_cost_envelopes.DESSERT.hard_max_eur` vaut 0,20 € et porte `status: STALE_PRE_G002`.
Cette valeur a été calibrée avant la fermeture de G002, sur des coûts sous-estimés d'un
facteur deux à sept. Le cookie du catalogue d'exemple sort à 0,38 € en BUY, soit près du
double de l'enveloppe. **Relever les prix réels, ne pas écarter un candidat sur ce seuil** —
c'est le seuil qui sera recalibré, pas les candidats qui doivent s'y plier.

## Calcul exigé pour chaque candidat

```
prix rendu
+ décongélation ou remise en température (temps immobilisé seulement)
+ portionnage éventuel
+ emballage
+ pertes attendues
= SELECTED_EFFECTIVE_PRODUCT_COST
```

Voie A : les quatre lignes du milieu valent zéro, et il faut le dire explicitement plutôt
que de les omettre.

L'emballage est une variable de design du panier, pas un attribut du produit — relever ce
que le fournisseur conditionne, sans présumer qu'un contenant individuel sera nécessaire.
Voir `packaging_model` dans `manita.config.json`.

## Interdits

- Annoncer un `selected_effective_product_cost_eur` sans avoir chiffré le travail restant
- Facturer une décongélation au temps écoulé
- Faire entrer le coût du produit source dans une transformation d'invendu
- Traiter un prix catalogue fabricant comme un prix rendu : sans distributeur identifié,
  c'est `QUOTE_REQUIRED`
- Déduire un prix pièce d'un prix au kilo sans le grammage réel de la portion
- Extrapoler une allégation alimentaire depuis une absence d'ingrédient : une allégation
  vegan exige `SUPPLIER_DOCUMENTED` ou `INTERNAL_RECIPE_DOCUMENTED`

## Livrable

30 candidats au format de `data/research/supplier_candidates/dessert_discovery_candidates.json`, avec
`candidate_track` valant `READY_TO_SERVE`, `THAW_ONLY` ou `TRANSFORMED_SURPLUS`,
`supplier_id` et `procurement_registry_id` pointant vers le Supplier Master, et
`landed_cost_eur_per_piece` à `null` tant qu'un devis courant n'existe pas — le prix
historique vivant séparément en `reference_price_eur_per_piece`.

Viser une couverture végane réelle : la colonne DESSERT est celle où l'allégation est la
plus fréquente et la moins documentée.
