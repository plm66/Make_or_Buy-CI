# Audit et intégration du sourcing Alex : Garniture, Dessert et Surplus

Date : 23 septembre 2026  
Périmètre audité : 65 livrables de recherche (30 candidats GARNITURE, 30 candidats DESSERT, 5 pistes de surplus TRANSFORMED_SURPLUS, 12 relevés de prix publics benchmarks).  
Statut : **AUDITÉ — CONFORME AUX RÈGLES DE RECHERCHE — AUCUNE PROMOTION CANONIQUE**

---

## 1. Contexte et mandat de l'audit

L'audit porte sur les 65 livrables exploratoires apportés par Alex pour alimenter les colonnes de menu Manita :
- **GARNITURE** : 30 candidats exploratoires (`garniture_discovery_candidates.json`), 6 benchmarks publics (`garniture_public_benchmarks.json`).
- **DESSERT** : 30 candidats exploratoires (`dessert_discovery_candidates.json`), 5 pistes de transformation de surplus (`dessert_internal_transformed_surplus_leads.json`), 6 benchmarks publics (`dessert_public_benchmarks.json`).

L'objectif de cet audit est de vérifier la stricte adéquation de ces livrables avec la doctrine du projet, de résoudre les rattachements de catalogue fabricant, et de garantir l'étanchéité absolue entre la recherche exploratoire et le catalogue opérationnel.

---

## 2. Respect de la doctrine des coûts et statuts fournisseurs

### 2.1. Absence de coûts effectifs fabriqués (G002 / P022)
- **Constat** : 100 % des 60 candidats affichent `selected_effective_product_cost_eur: null` et `landed_cost_eur_per_piece: null` lorsqu'ils sont sous statut `QUOTE_REQUIRED`.
- **Validation** : Aucun coût complet n'a été présumé. Le travail interne restant (remise en température, portionnage, pertes) n'étant pas encore chronométré en conditions réelles, le coût effectif reste rigoureusement `null` et non calculé.

### 2.2. Circuits de distribution et fabricants
- 33 candidats sont issus de fabricants en `MANUFACTURER_REFERENCE` (dont Traiteur de Paris et Tipiak).
- Ces fabricants portent le statut `DISTRIBUTOR_REQUIRED` : ils ne sont pas commandables en direct. Aucun prix rendu n'est imputé, évitant ainsi de sous-estimer la voie BUY en occultant les conditions d'un grossiste intermédiaire.

---

## 3. Statut des benchmarks publics : le cas GPO-001 (Rösti Lutosa)

Le relevé `GPO-001` (Rösti Burger Lutosa 100g, carton 4×2,5 kg = 100 pièces à 23,50 € sur AJ Foods) a fait l'objet d'un examen approfondi :

- **Base de taxe inconnue** : La source relève `tax_basis: UNKNOWN`. Il est impossible d'affirmer s'il s'agit d'un tarif HT ou TTC.
- **Conditions de livraison inconnues** : Le champ `delivery_included` est `null`. Aucun franco ni frais de port n'est garanti.
- **Coût rendu nul** : Le champ `landed_cost_eur_per_piece` est strictement `null`.
- **Statut exploratoire** : Le dataset porte l'avertissement formel :
  > *`PRICE_SOURCE observations are not registry suppliers and do not create purchase authorization.`*

**Conclusion de l'audit** :  
`GPO-001` fournit un **repère indicatif de prix brut public** (0,235 €/pièce affiché) qui situe l'ordre de grandeur d'un produit industriel de référence dans la zone de l'enveloppe cible (0,15 € à 0,30 €). En aucun cas ce chiffre ne constitue un coût unitaire rendu validé opérationnellement.

---

## 4. Traitement du candidat DES-013 (Moelleux Chocolat Noisette)

### 4.1. Rapprochement catalogue fabricant
Le croisement avec `data/supplier_products/traiteur_de_paris_catalogue_2026.json` confirme sans ambiguïté la référence catalogue officielle :
- **Référence fabricant** : `006107`
- **Désignation** : `Moelleux Chocolat Noisette Vegan`
- **Conditionnement** : Colis de 20 unités (1,8 kg brut, flowpack 10×2), portion unitaire 90 g.
- **Source catalogue** : `data/supplier_products/traiteur_de_paris_catalogue_2026.json`.

### 4.2. Quarantaine doctrinale de l'allégation végane
La doctrine de traçabilité (`traceability_requirements.vegan_products`) et le moteur [`product_tool.py`](../../product_tool.py) (`EQUIVALENCE_PREUVES`) imposent une règle sans équivoque :
> *Seule une fiche technique officielle (`OFFICIAL_TECHNICAL_SHEET`) avec versionnage et engagement sur les procédures d'alerte en cas de reformulation permet de déclarer `SUPPLIER_DOCUMENTED` pour une allégation végane.*

Un catalogue commercial fabricant (`OFFICIAL_MANUFACTURER_CATALOGUE`) atteste de la gamme commerciale au jour de parution, mais ne constitue pas la fiche technique contractuelle exigée.

**Décision d'intégration** :
- Le candidat `DES-013` intègre sa référence officielle `006107` et son rattachement `catalogue_source`.
- L'allégation végane **reste maintenue en quarantaine doctrinale** : `claim_status: NOT_VALIDATED`, `missing_critical_fields: ["dietary.official_technical_sheet"]`, `raw_imported_dietary_claim_unvalidated` consigné.
- L'allégation ne pourra être promue en vitrine qu'après réception de la fiche technique officielle du fabricant ou de son grossiste.

---

## 5. Règle doctrinale fondamentale : `consumer_rule` et étanchéité du catalogue

Chacun des trois jeux de données exploratoires porte une règle de consommation explicite :
```json
"consumer_rule": "Do not import into canonical products, supplier master, price observations, or purchase authorization."
```

### 5.1. Refus de promotion prématurée
L'audit confirme le respect strict de cette règle : **aucune fiche canonique n'est créée dans `data/products/` à partir de ces pistes**.
- Les leads de transformation de surplus (`SUR-001` à `SUR-005`) restent des orientations d'atelier internes non chiffrées.
- Les candidats fournisseurs (`GAR-001` à `GAR-030` et `DES-001` à `DES-030`) restent des pistes de sourcing non contractualisées.

### 5.2. Interdiction formelle de fabriquer des paramètres
Créer des fiches produits prématurément conduirait à inventer des valeurs sans source :
- Durées de conservation arbitraires (ex. 8760 h).
- Délais d'approvisionnement non contractés (ex. 2 ou 3 jours).
- Quantités minimales de commande inventées.
- Taux de perte estimés au doigt mouillé.
- Prix de vente consommateurs non arbitrés.

Le dossier [`data/products/`](../../data/products/) reste réservé aux produits dont les paramètres sont fondés sur des observations ou mesures réelles.

---

## 6. Synthèse des invariants de tests

La conformité de cette passe d'audit est verrouillée par trois tests invariants dans [`tests/test_discovery_candidates.py`](../../tests/test_discovery_candidates.py) :
1. `test_des013_rattache_au_catalogue_officiel` : contrôle le rattachement à la référence `006107` tout en garantissant le maintien de la quarantaine sur l'allégation végane (`claim_status: NOT_VALIDATED`, `dietary.official_technical_sheet` manquant).
2. `test_lutosa_rosti_est_un_benchmark_indicatif` : garantit que `GPO-001` ne prétend à aucun coût rendu (`landed_cost_eur_per_piece: null`, `tax_basis: UNKNOWN`).
3. `test_aucun_candidat_de_recherche_nest_promu_en_produit_canonique` : contrôle programmatiquement la `consumer_rule` en s'assurant qu'aucun identifiant de candidat de recherche ne s'est infiltré dans `data/products/`.
