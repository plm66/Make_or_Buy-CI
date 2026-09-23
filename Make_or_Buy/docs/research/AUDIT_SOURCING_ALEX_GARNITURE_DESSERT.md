# Audit et intégration du sourcing Alex : Garniture, Dessert et Surplus

Date : 23 septembre 2026  
Périmètre audité : 65 livrables de sourcing (30 candidats GARNITURE, 30 candidats DESSERT, 5 pistes de surplus TRANSFORMED_SURPLUS, 12 relevés de prix publics benchmarks).  
Statut : **VALIDÉ AVEC PROMOTION SÉLECTIVE**

---

## 1. Contexte et objectifs de l'audit

L'audit porte sur le travail de recherche exploratoire mené par Alex pour alimenter les deux colonnes d'arbitrage de menu Manita :
- **GARNITURE** (30 candidats exploratoires, 6 benchmarks publics)
- **DESSERT** (30 candidats exploratoires, 5 pistes de transformation de surplus, 6 benchmarks publics)

L'objectif de cet audit est quadruple :
1. **Contrôler la conformité doctrinale** : garantir qu'aucun coût effectif n'est fabriqué sans calcul complet (G002 / P022) et qu'aucun fournisseur grossiste ou fabricant n'est dévoyé (distinction stricte entre fabricant `MANUFACTURER_REFERENCE` et grossiste direct).
2. **Résoudre les quarantaines d'allégations** : auditer en particulier le cas `DES-013` (Moelleux Chocolat Noisette Vegan) et effectuer le rapprochement formel avec le catalogue fabricant officiel Traiteur de Paris 2026.
3. **Valider la faisabilité économique du panier garniture** : confronter les benchmarks relevés (notamment Lutosa Rösti `GPO-001`) à la cible d'enveloppe budgétaire (0,15 € – 0,30 €).
4. **Promouvoir les fiches canoniques représentatives** : créer les fiches produits 2.0.0 pour GARNITURE et DESSERT afin d'ouvrir la couverture du moteur d'assemblage sans fabriquer de fausses certitudes de coût.

---

## 2. Résultats de l'audit sur les 65 livrables

### 2.1. Respect de la doctrine des coûts (G002 / P022)
- **Constat** : 100 % des candidats affichent `selected_effective_product_cost_eur: null` et `landed_cost_eur_per_piece: null` lorsqu'ils sont sous statut `QUOTE_REQUIRED`.
- **Validation** : Aucun prix rendu n'a été présumé à partir d'un tarif catalogue public ou indicatif. Les 33 candidats issus de fabricants `MANUFACTURER_REFERENCE` (dont Traiteur de Paris, Tipiak) respectent l'obligation de passer par un distributeur (`DISTRIBUTOR_REQUIRED`) sans inventer de marge intermédiaire.

### 2.2. Contrôle de la couche prix et benchmarks
- **Cohérence des sources** : Tous les `price_source_id` des observations publiques (`aj_foods`, `foodomarket`) correspondent strictement aux sources déclarées dans le registre `supplier_price_sources.registry.json`.
- **Arithmétique colis/pièce** : La règle fondamentale de recalcul du prix unitaire depuis le colis a été vérifiée :
  $$\text{prix unitaire} = \frac{\text{prix du colis}}{\text{nombre d'unités}}$$
  Les 12 relevés respectent cette arithmétique sans arrondi abusif.

---

## 3. Résolution formelle du candidat DES-013 (Moelleux Vegan)

### 3.1. Diagnostic initial
Le candidat `DES-013` (*Moelleux au Chocolat Noisette Vegan*) avait été consigné avec une allégation végane placée en quarantaine sous le champ `raw_imported_dietary_claim_unvalidated`, avec `claim_status: NOT_VALIDATED` et `missing_critical_fields: ["dietary.official_technical_sheet"]`, car sa référence exacte dans le catalogue fabricant Traiteur de Paris n'avait pas été rattachée.

### 3.2. Rapprochement catalogue
Le croisement avec la base officielle `data/supplier_products/traiteur_de_paris_catalogue_2026.json` identifie sans ambiguïté :
- **Référence fabricant officielle** : `006107`
- **Désignation catalogue** : `Moelleux Chocolat Noisette Vegan`
- **Conditionnement** : Colis de 20 pièces (1,8 kg brut, conditionné en Flowpack 10×2)
- **Portion unitaire** : 90,0 g (dimensions 70×40 mm)
- **Remise en œuvre** : Décongélation 2 h à +4°C ; DLC après décongélation de 120 h (5 jours) ; option de réchauffage au four 12 min à 180°C.
- **Preuve d'allégation** : `OFFICIAL_MANUFACTURER_CATALOGUE` avec engagement fabricant (23 % de chocolat noir, poudre de noisettes grillées, recette 100 % végétale).

### 3.3. Décision d'intégration
- Mise à jour du candidat `DES-013` :
  - `supplier_product_ref: "006107"`
  - `dietary.vegan: true`, `dietary.vegan_evidence: "SUPPLIER_DOCUMENTED"`
  - `catalogue_source: "data/supplier_products/traiteur_de_paris_catalogue_2026.json"`
  - Retrait du bloc de quarantaine `raw_imported_dietary_claim_unvalidated`.
- Promotion en fiche produit canonique : `data/products/moelleux_chocolat_noisette_vegan_90g.json`.

---

## 4. Faisabilité économique de la garniture (Benchmark GPO-001)

### 4.1. Analyse du benchmark Lutosa Rösti Burger 100g
- **Observation** : `GPO-001` (relevé AJ Foods)
- **Conditionnement** : Carton 4 × 2,5 kg = 10 kg, soit 100 portions de 100 g.
- **Prix affiché colis** : 23,50 € HT
- **Coût unitaire rendu brut** : **0,235 € / pièce**.

### 4.2. Confrontation à l'enveloppe cible Manita
Le brief de sourcing `MANITA_GARNITURE_DISCOVERY.md` fixe l'enveloppe cible pour la voie A (`READY_PORTION_HEAT`) entre **0,15 € et 0,30 €** par portion.
- À 0,235 €/pièce pour une portion généreuse de 100 g d'un industriel de référence (Lutosa), la cible économique est **parfaitement réaliste et tenable**.
- La marge d'absorption pour l'énergie de réchauffage (estimée à ~0,02 €) et l'emballage/perte (~0,02 €) laisse le coût effectif global en-deçà du seuil plafond de 0,30 €.

---

## 5. Doctrine de valorisation des surplus internes (P003 / G003)

L'audit a validé les 5 pistes de valorisation d'invendus de viennoiserie et boulangerie (`dessert_internal_transformed_surplus_leads.json`).

### 5.1. Règle fondamentale du coût matière source
Selon les principes P003 et G003 :
> *Le coût du produit source invendu (ex. croissant de la veille J-1 ou pain rassis) est nul dans le calcul du coût évitable du produit dérivé, car ce coût est déjà engagé et non récupérable (sunk cost).*

### 5.2. Composition du coût évitable
Seuls entrent dans le coût du produit transformé :
1. **Les ingrédients additionnels** : crème d'amandes, sirop de sucre, amandes effilées, sucre glace.
2. **Le travail actif de transformation** : temps humain réellement immobilisé (siropage, pochage, dressage), sans compter les temps morts de cuisson.
3. **L'énergie de seconde cuisson**.
4. **L'emballage incrémental**.

Cette règle a été modélisée et formalisée dans la fiche canonique `croissant_aux_amandes_surplus_j1.json`.

---

## 6. Fiches canoniques promues dans `data/products/`

Trois fiches canoniques au schéma 2.0.0 ont été promues et validées par `product_tool.py` :

| ID Produit | Famille | Mode | Poids | Description / Origine | Statut mesure |
|---|---|---|---|---|---|
| `pommes_anna_60g` | GARNITURE | BUY | 60 g | Pommes de terre Anna individuelles (Coup de Pâtes 832909) | Prêt pour devis grossiste |
| `moelleux_chocolat_noisette_vegan_90g` | DESSERT | BUY | 90 g | Moelleux individuel vegan (Traiteur de Paris 006107) | Prêt pour devis grossiste |
| `croissant_aux_amandes_surplus_j1` | DESSERT | MAKE | 95 g | Recette anti-gaspillage sur croissant J-1 (Doctrine P003/G003) | Prêt pour chronométrage & pesée |

### 6.1. Impact sur la couverture du catalogue (`product_tool.py status`)
- **GARNITURE** : passe de 0 fiche à **1 fiche** (`pommes_anna_60g`).
- **DESSERT** : passe de 0 fiche à **2 fiches** (`moelleux_chocolat_noisette_vegan_90g`, `croissant_aux_amandes_surplus_j1`).
- Aucune donnée n'a été falsifiée : les champs non mesurés sont honnêtement déclarés dans `missing_critical_fields`.

---

## 7. Couverture de tests et invariants

La conformité de l'ensemble de ces ajouts est verrouillée par 3 nouveaux invariants ajoutés à `tests/test_discovery_candidates.py` :
1. `test_des013_rattache_au_catalogue_officiel` : contrôle le rattachement formel à la référence `006107` et l'allégation végane documentée.
2. `test_lutosa_rosti_dans_la_cible_economique_garniture` : contrôle que le relevé `GPO-001` (0,235 €) valide la cible `[0.15, 0.30] €`.
3. `test_fiches_canoniques_promues_valident_sans_cout_fabrique` : contrôle que les 3 fiches promues passent la validation stricte de `product_tool` sans inventer de coûts évitables.

Le passage complet de la suite de tests confirme le respect strict des invariants du projet.
