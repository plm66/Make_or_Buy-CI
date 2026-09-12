# Glossaire de référence

Un terme, un sens, un référent anglais. Sans ce document, chaque passe réinvente un nom
pour une notion qui en a déjà un — et deux noms pour une même notion valent pire que pas de
nom : ils font croire à deux notions.

Le référent anglais n'est pas une traduction. C'est le terme du métier ou de la norme sur
lequel on peut retomber quand le français hésite, et qui permet de vérifier qu'on parle
bien de la même chose qu'un fournisseur, une fiche technique ou un texte réglementaire.

**Règle** : tout code qui entre dans une donnée ou un schéma figure ici avant d'être écrit.
Un code absent du glossaire est un code inventé.

---

## 1. Degré de transformation — ce qu'il reste à faire

Porté par `params/operation_templates.json`, qui donne le nombre de gestes internes
restants. C'est l'axe qui relie un achat à du travail supprimé.

| code dépôt | français | référent anglais | gestes | définition |
|---|---|---|---|---|
| `CRU` | cru surgelé, pousse contrôlée | **raw frozen dough** | 4 | Pâte crue. Pousse et cuisson à faire. |
| `PAC` | pré-poussé à cuire | **pre-proofed frozen** | 3 | Pousse déjà faite. Cuisson à faire. |
| `PRECUIT` | précuit | **par-baked** (part-baked, bake-off) | 3 | Cuisson partielle. Finition de cuisson à faire. |
| `CUIT` | cuit surgelé | **fully baked frozen** | 2 | Cuisson faite. Décongélation et présentation à faire. |
| `PRET_A_SERVIR` | prêt à l'emploi | **ready-to-use (RTU)** | 0 | Aucun geste de transformation restant. |

### L'ambiguïté de `PRET_A_SERVIR`, à trancher

Le français distingue deux choses que le code confond :

| notion | référent anglais | exemple |
|---|---|---|
| **prêt à consommer** — s'intègre tel quel, sans cuisson | **ready-to-eat (RTE)** | un macaron décongelé qu'on pose dans un panier |
| **prêt à servir** — se sert tel quel au client, dressage compris | **ready-to-serve (RTS)** | un dessert à l'assiette, dressé |

`PRET_A_SERVIR` du dépôt veut dire « zéro geste de transformation » : c'est **RTU / RTE**,
pas RTS. Le nom dit « servir », le code compte « transformer ». Deux références peuvent
être toutes deux à zéro geste et n'avoir pas la même destination — l'une entre dans un
assemblage, l'autre part en vitrine.

La décongélation ne compte pas comme un geste : c'est du temps écoulé et non du temps
immobilisé (P004). Un produit surgelé peut donc être `PRET_A_SERVIR` tout en demandant
quatre heures de chambre froide.

**À décider** : renommer en `PRET_A_L_EMPLOI` / `READY_TO_USE`, ou scinder RTE et RTS si la
distinction porte une conséquence opérationnelle. Non tranché.

---

## 2. Mode d'approvisionnement — qui fait

`doctrine.decision_modes`.

| code | français | référent anglais | définition |
|---|---|---|---|
| `MAKE` | fabriquer | **make** | Produit en interne. |
| `BUY` | acheter | **buy** | Acheté fini à l'extérieur. |
| `HYBRID` | hybride | **hybrid / partial outsourcing** | Base achetée, valeur ajoutée en interne. Voir ADR-0003 : à généraliser à N composants. |

---

## 3. Nature de composition — de quoi c'est fait

Proposé par [ADR-0001](decisions/ADR-0001-axe-de-composition.md). Ne pas confondre avec
l'axe 1 : un produit surgelé peut être irréprochable de composition.

| code | français | référent anglais | définition |
|---|---|---|---|
| `FRESH_NATURAL` | frais et naturel | **clean label, no substitutes** | Ingrédients bruts, aucun composant substitutif. |
| `FROZEN_CLEAN` | surgelé propre | **clean label frozen** | Surgelé, sans composant substitutif. Le froid n'est pas un défaut de composition. |
| `SUBSTITUTED` | substitué | **substituted / reformulated** | Porte au moins un composant qui remplace un ingrédient qu'une recette fraîche contiendrait. |
| `UNDECIDED` | non tranché | **undetermined** | Cas que la doctrine n'a pas arbitré. |

### Substitutif contre auxiliaire technologique

Distinction mesurée, pas théorique : sur les 59 fiches Bridor, l'émulsifiant est présent à
tous les degrés de transformation, l'arôme et le colorant se concentrent sur `PRET_A_SERVIR`.

| notion | référent anglais | remplace un ingrédient ? | exemples |
|---|---|---|---|
| **composant substitutif** | **substitute ingredient** | oui | vanilline pour la vanille, colorant pour le fruit |
| **auxiliaire technologique** | **processing aid** | non, modifie un procédé | émulsifiant de feuilletage, enzyme, améliorant |

Confondre les deux fait du bruit : l'émulsifiant est partout et ne dit rien de la qualité de
composition. C'est le cas ouvert d'ADR-0001.

---

## 4. Coûts — quatre notions qu'on confond

C'est ici que le dépôt a payé sa dette la plus chère (G002).

| code dépôt | français | référent anglais | définition |
|---|---|---|---|
| `material_cost_eur` | coût matière | **material cost** | Les seuls ingrédients. **Ne décide jamais rien seul.** |
| `avoidable_cost_eur` | coût complet évitable | **avoidable cost** | Tout ce qui disparaît si on cesse de fabriquer : matière, travail, énergie, emballage, pertes. |
| `landed_cost_eur` | prix rendu | **landed cost** | Prix fournisseur livré : produit, transport, droits, à l'unité utile. |
| `SELECTED_EFFECTIVE_PRODUCT_COST` | coût effectif retenu | *(propre au dépôt)* | Ce que le produit coûte réellement selon le mode retenu. MAKE → coût évitable, BUY → prix rendu, HYBRID → composants plus opérations internes. |

**G002** : ne jamais comparer un prix fournisseur à un coût matière interne. Le premier est
complet, le second ne l'est pas — la comparaison fait toujours gagner l'interne à tort.

| autre terme | français | référent anglais | piège |
|---|---|---|---|
| `reference_price_eur_per_piece` | prix de référence | **reference price** | Un historique ou un affichage. **N'est pas** un devis courant. |
| — | mercuriale | **price list** | Tarif négocié d'un grossiste, souvent derrière un compte. |
| — | franco de port | **free freight threshold** | Montant au-delà duquel la livraison ne se facture plus. |
| — | ratio de coût matière | **food cost ratio** | Coût rapporté au prix de vente. La cible et le plafond sont **deux nombres distincts**. |

---

## 5. Temps — ce qui se facture et ce qui ne se facture pas

| notion | référent anglais | se facture ? |
|---|---|---|
| temps immobilisé | **hands-on time, active labour** | oui |
| temps écoulé | **elapsed time, passive time** | non |

P004. Une infusion de trente minutes surveillée une minute coûte une minute. Une
décongélation de quatre heures coûte le temps de sortir et de ranger. Compter l'écoulé
externaliserait tout ce qui lève, repose ou infuse.

---

## 6. Entités d'approvisionnement — qui vend quoi

| code dépôt | français | référent anglais | définition |
|---|---|---|---|
| `supplier_id` | fournisseur homologué | **approved supplier** | Entité avec qui une relation d'achat est envisagée. |
| `price_source_id` | source de prix | **price source** | Entité dont on relève les prix, qu'on achète chez elle ou non. |
| `MANUFACTURER_REFERENCE` | fabricant | **manufacturer** | Fabrique, ne vend pas en direct. Son tarif catalogue n'est pas un prix rendu. |
| `DISTRIBUTOR_REQUIRED` | distributeur requis | **distributor required** | L'achat suppose un intermédiaire identifié. |
| `ACCOUNT_GATED_PENDING` | sous compte | **account-gated** | Les prix demandent un compte. |

**Une source de prix n'est pas un fournisseur.** `supplier_id` ne vaut non-null qu'après
promotion au registre.

---

## 7. Entités produit — de quoi on parle

| code dépôt | français | référent anglais | définition |
|---|---|---|---|
| `id_generique` | générique | **generic product** | Le produit en absolu, indépendant du fournisseur. |
| `ref_sku` | référence fournisseur | **SKU** | L'article commercial concret d'un fournisseur. |
| `id_matiere` | matière première | **raw material, ingredient** | L'étage bas. Une recette la référence, elle ne référence rien. |
| `candidate_id` | candidat | **candidate** | Référence repérée, pas encore qualifiée. |
| `lead_id` | piste | **lead** | Intention de sourcing sans référence établie. |
| `observation_id` | observation de prix | **price observation** | Un prix vu, à une date, à une source. |
| — | nomenclature | **bill of materials (BOM)** | La décomposition d'un produit en composants. ADR-0002. |
| — | rendement | **yield** | Ce qui sort rapporté à ce qui entre. |
| — | colisage | **case pack, pack size** | Unités par carton. |

---

## 8. Dates et preuves

| code / notion | français | référent anglais | définition |
|---|---|---|---|
| DLC | date limite de consommation | **use-by date** | Sécurité alimentaire. Impérative. |
| DDM | date de durabilité minimale | **best-before date** | Qualité. Indicative. |
| `observed_at` | date de relevé | **observation date** | Quand on a regardé. |
| `price_reference_date` | date de validité du prix | **price effective date** | À quelle date le prix valait. Peut précéder le relevé. |
| QUID | déclaration quantitative des ingrédients | **Quantitative Ingredient Declaration** | Pourcentage d'un ingrédient mis en avant. Réglementaire UE. |

| niveau de preuve | quand il s'applique |
|---|---|
| `SUPPLIER_DOCUMENTED` | fiche technique du fournisseur |
| `INTERNAL_RECIPE_DOCUMENTED` | recette interne écrite |
| `OFFICIAL_TECHNICAL_SHEET` | document technique officiel |
| `PARTIAL` | page produit ou étiquette seule |
| `NONE` | rien d'opposable |
| `DEFINITIONAL` | découle de la définition, ne vaut pas pour un SKU |

---

## 9. Le motif qui revient

Quatre fois déjà, la même distinction s'est imposée :

| référence | fait sur nous |
|---|---|
| source de prix | fournisseur homologué |
| prix de référence | prix rendu constaté |
| recette de métier | recette de la maison |
| nature définitionnelle d'une matière | composition prouvée d'un SKU |

**Une référence n'est pas un fait sur nous.** Les deux coexistent dans le modèle, jamais
dans le même champ.

---

## Termes créés par le dépôt, sans référent extérieur

À surveiller : ils n'ont d'autorité que la nôtre, et doivent donc être définis ici.

`SELECTED_EFFECTIVE_PRODUCT_COST`, `FROZEN_CLEAN`, `READY_PORTION_HEAT`,
`COOKED_BULK_PORTIONABLE`, `DRY_HIGH_YIELD`, `TRANSFORMED_SURPLUS`, `INHOUSE_SIGNATURE_ADVANTAGE`,
`HYBRID_SIGNATURE`, `SUPPLIER_SUPERIOR`, `STANDARDIZABLE`.
