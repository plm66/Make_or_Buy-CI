# Tableau de pondération métier

## Pourquoi ce tableau existe

Make_or_Buy utilise des recherches pour éclairer un choix, pas pour transformer
automatiquement une information trouvée en décision d'achat.

Un **tableau de pondération** rend explicites :

- les critères qui comptent pour la décision ;
- le poids relatif de chaque critère ;
- la note attribuée à chaque option ;
- la qualité de la preuve ;
- les éléments qui restent à vérifier.

Le tableau est réutilisable pour comparer un produit, un ingrédient, un fournisseur,
une recette, une option `MAKE`, `BUY` ou `HYBRID`, ou plusieurs réponses à une même
recherche.

## Règle de calcul

Chaque critère reçoit une note de **0 à 5** :

| Note | Signification |
|---:|---|
| 0 | Inacceptable, absent ou contredit par les preuves |
| 1 | Très faible, risque majeur ou information presque inutilisable |
| 2 | Faible, utilisable seulement avec réserves importantes |
| 3 | Acceptable, mais améliorable ou partiellement documenté |
| 4 | Bon, documenté et compatible avec le besoin |
| 5 | Excellent, démontré et nettement supérieur aux alternatives |

La somme des pondérations doit être égale à **100 %**.

```text
score_final_sur_100 = somme(note_sur_5 × poids_en_pourcentage × 4)
```

Exemple : une note de 4/5 sur un critère pondéré à 20 % donne `16 points` :
`(4 / 5) × 20 = 16`.

```text
score_du_critere = (note_sur_5 / 5) × poids_en_pourcentage
score_final_sur_100 = somme(score_du_critere)
```

## Grille alimentaire générique par défaut

Cette pondération est un point de départ. Elle doit être adaptée à la formule
commerciale étudiée : un menu à 5 € ne donne pas nécessairement le même poids au coût
qu'un menu premium, diététique ou événementiel.

| Critère | Poids | Question métier |
|---|---:|---|
| Coût matière rendu et stabilité du prix | 20 % | Le coût par unité vendue est-il connu, réaliste et durable ? |
| Adéquation à la promesse client | 15 % | Le produit sert-il réellement le positionnement du menu ? |
| Qualité et valeur perçue | 15 % | Le client voit-il une différence justifiant l'offre ? |
| Faisabilité opérationnelle | 15 % | La production, la remise en œuvre et le service sont-ils maîtrisables ? |
| Disponibilité et continuité d'approvisionnement | 10 % | Peut-on obtenir le produit dans la durée et avec une solution de repli ? |
| Make / Buy / Hybrid | 10 % | Le mode retenu est-il économiquement et opérationnellement cohérent ? |
| Données, traçabilité et niveau de preuve | 10 % | Les prix, grammages, allergènes et claims sont-ils documentés ? |
| Pertes, conservation et sécurité d'usage | 5 % | Les risques de perte, DLC et conservation sont-ils acceptables ? |
| **Total** | **100 %** | |

### Règles de sécurité métier

- Une donnée inconnue reçoit une note basse ou `NON DÉTERMINÉ`, jamais une note moyenne
  par défaut.
- Une URL de catégorie, un prix ancien ou une allégation non vérifiée ne constitue pas
  une preuve de fiche produit.
- Un coût rendu non confirmé ne peut pas être présenté comme un coût opérationnel.
- Une note globale élevée ne compense pas un blocage critique : allergène inconnu,
  fournisseur non achetable, coût absent ou preuve contradictoire.
- Toute note doit citer sa source, sa date et son niveau de confiance.

## Fiche de comparaison

### Contexte de recherche

| Champ | Valeur |
|---|---|
| Décision recherchée | À compléter |
| Formule / module | À compléter |
| Segment client | À compléter |
| Prix de vente cible | À compléter |
| Portion ou unité vendue | À compléter |
| Date de l'évaluation | À compléter |
| Responsable | À compléter |

### Options évaluées

| Option | Type | Fournisseur / source | Statut |
|---|---|---|---|
| Option A | Produit / ingrédient / recette | À compléter | À vérifier |
| Option B | Produit / ingrédient / recette | À compléter | À vérifier |
| Option C | Produit / ingrédient / recette | À compléter | À vérifier |

### Tableau de décision

| Critère | Poids | A note /5 | A score | B note /5 | B score | C note /5 | C score | Preuve / réserve |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Coût matière rendu et stabilité | 20 % |  |  |  |  |  |  |  |
| Adéquation à la promesse client | 15 % |  |  |  |  |  |  |  |
| Qualité et valeur perçue | 15 % |  |  |  |  |  |  |  |
| Faisabilité opérationnelle | 15 % |  |  |  |  |  |  |  |
| Disponibilité et continuité | 10 % |  |  |  |  |  |  |  |
| Make / Buy / Hybrid | 10 % |  |  |  |  |  |  |  |
| Données et traçabilité | 10 % |  |  |  |  |  |  |  |
| Pertes, conservation et sécurité | 5 % |  |  |  |  |  |  |  |
| **Total / 100** | **100 %** |  | ** / 100** |  | ** / 100** |  | ** / 100** |  |

### Confiance et décision

| Option | Confiance globale | Mode recommandé | Décision | Conditions de passage |
|---|---|---|---|---|
| A | Faible / moyenne / forte | MAKE / BUY / HYBRID | À vérifier |  |
| B | Faible / moyenne / forte | MAKE / BUY / HYBRID | À vérifier |  |
| C | Faible / moyenne / forte | MAKE / BUY / HYBRID | À vérifier |  |

## Pondérations spécialisées

La grille générique n'est pas sacrée. On peut créer une variante en fonction de la
question, à condition de conserver le total de 100 % et d'expliquer le choix des poids.

### Exemple : grille de capacité agentique

Cette grille évalue un produit, un modèle ou un outil logiciel selon une autre finalité.
Elle ne doit pas être mélangée à une décision de coût matière sans expliciter le changement
de contexte.

| Critère | Poids |
|---|---:|
| Fiabilité agentique | 30 % |
| Développement et débogage | 25 % |
| Compréhension de dépôts et long contexte | 15 % |
| Utilisation des outils et reprise après erreur | 10 % |
| Coût total | 10 % |
| Vitesse | 5 % |
| Respect des instructions | 5 % |
| **Total** | **100 %** |

La note de cette grille se calcule exactement de la même façon : chaque critère reçoit
une note sur 5, puis les scores pondérés sont additionnés pour obtenir une note sur 100.

## Processus recommandé

1. Définir la décision et l'unité vendue avant de chercher des options.
2. Choisir les critères et leur pondération ; vérifier que le total vaut 100 %.
3. Fixer l'échelle de notation avant de regarder le résultat final.
4. Documenter chaque note avec une preuve, une date et une réserve.
5. Calculer les scores, puis inspecter les blocages critiques séparément.
6. Comparer `MAKE`, `BUY` et `HYBRID` sur la même unité vendue.
7. Décider : retenir, tester, demander un devis, compléter la preuve ou écarter.
8. Refaire l'évaluation lorsque le prix, la disponibilité, la recette ou la promesse change.

## Conclusion

Oui, les tableaux de pondération constituent une bonne idée générique pour Make_or_Buy.
Ils donnent une structure commune à des recherches très différentes tout en laissant
chaque module — La Manita, vegan, oriental, subsaharien, diététique ou tendance — définir
ses propres priorités.

Ils ne remplacent pas les données sources ni la doctrine : ils rendent visibles les
arbitrages, les incertitudes et les désaccords entre critères. La note est donc une aide
à la décision, jamais une autorisation automatique d'achat ou de publication.
