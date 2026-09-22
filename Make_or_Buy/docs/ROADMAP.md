# Feuille de route

L'ordre ci-dessous n'est pas une préférence : c'est une chaîne de dépendances. Chaque jalon
débloque le suivant, et aucun ne peut être devancé sans fabriquer un chiffre.

---

## Où on en est, sans ménagement

Le moteur sait arbitrer. La doctrine est versionnée. Le référentiel porte 38 matières et
384 prix réellement payés sur six mois de factures, dont le module `comparaison_factures.py`
sait tirer 69 observations de prix matière et 175 mesures de dérive.

**Et zéro produit n'est arbitrable**, parce que rien de tout cela n'arrive jusqu'au moteur.

```
catalogue                    1 produit
  internal.avoidable_cost_eur   null
  external.landed_cost_eur      null
gestes chronométrés          0 / 21
ADR acceptés                 0 / 3
```

`selected_cost()` rend `DATA_INCOMPLETE`, ce qui est **correct** : il refuse d'inventer. Le
travail restant n'est pas du code, c'est de la mesure et de l'arbitrage.

---

## Le chemin critique

### Jalon 1 — Trancher la composition

**Bloque tout le reste. Décision de l'exploitant, pas du code.**

Le choix de la matière grasse déplace le seuil de bascule MAKE/BUY du simple au double :

| beurre | prix mesuré | seuil de bascule, lot de 60 croissants |
|---|---|---|
| doux 500 g, bas de fourchette | 6,04 €/kg | **64 min** |
| doux 500 g, haut de fourchette | 7,40 €/kg | 51–61 min |
| AOP 84 % tourage | 13,03 €/kg | **30–49 min** |

Aucune erreur de chronomètre n'approche cet écart. Mesurer avant d'avoir choisi donnerait
`MAKE` avec un beurre et `BUY` avec l'autre, sur le même relevé.

C'est l'ordre qu'impose [ADR-0002](decisions/ADR-0002-modele-de-recette.md) — composition
d'abord, make-or-buy ensuite — et [ADR-0001](decisions/ADR-0001-axe-de-composition.md)
attend le même arbitrage sur l'axe frais / surgelé / substitué.

**Sortie attendue** : ADR-0001 passe de `PROPOSED` à `ACCEPTED`, et la recette maison nomme
sa matière grasse.

### Jalon 2 — Chronométrer les gestes

**21 gestes, 6 technologies, une fois pour toutes.**

Les gabarits disent *quels* gestes restent en interne. Ils ne portent aucune minute, et c'est
délibéré : une minute pré-remplie serait un coût inventé.

| gabarit | gestes | ce qu'on achète |
|---|---|---|
| `MATIERES` | 9 | rien de transformé — pesée, pétrissage, pointage, tourage, détaillage, apprêt, dorure, cuisson, défournement |
| `CRU` | 4 | pâte crue surgelée |
| `PAC` | 3 | pré-poussé |
| `PRECUIT` | 3 | précuit |
| `CUIT` | 2 | cuit surgelé |
| `PRET_A_SERVIR` | 0 | tout |

Deux nombres par geste : **minutes immobilisées** et **minutes écoulées**. Seul l'immobilisé
se facture — le pointage dure deux heures et ne coûte que la surveillance (P004). L'écart
est de la capacité libérée, pas du travail payé.

Un lot suffit si le résultat tombe loin de la zone 30–64 min. Dedans, il en faut plusieurs.

**Sortie attendue** : `params/operation_templates.json` chronométré, au moins pour
`MATIERES`, `CRU` et `PAC` — les trois voies du croissant.

### Jalon 3 — Le croissant, premier arbitrage réel

Premier produit dont les deux coûts sont non nuls. Le moteur décide seul, et sa décision est
opposable : elle cite une règle, un prix daté, une durée mesurée.

Deux manques connus à lever au passage :

- **le sel fin n'a aucun prix.** Seul du gros sel est acheté (84,00 € sur six mois), et ce
  n'est pas la même matière. Soit il entre au référentiel, soit la recette le remplace.
- **22 rattachements sur 46 sont `A_VERIFIER`** — le beurre 500 g ne déclare aucun taux de
  matière grasse alors que `MATP-BEUR-DOUX` en exige 82 %. Se lit sur l'étiquette, pas sur
  la facture.

### Jalon 4 — Le prix n'est pas un nombre · **l'instrument est fait, le branchement non**

Le beurre a varié de **6,04 à 7,40 €/kg en six mois, 23 %**, tendance baissière, avec trois
remises de volume déjà obtenues. Une matière porte donc une **série datée**, pas un prix.

**Fait** — `comparaison_factures.py` sait mesurer cette série :

| | |
|---|---|
| dérive d'un article entre deux factures | 175 comparaisons sur 20 factures |
| prix au kilo, refusé quand le conditionnement est illisible | 24 accords sur 24, jugés par le prix imprimé |
| observations de prix matière | 69 observations sur 12 matières |

```bash
python3 comparaison_factures.py derive --top 10
python3 comparaison_factures.py observations --out <chemin>
```

**Pas fait** — rien ne consomme ces observations. `engine.py` lit toujours
`avoidable_cost_eur` et `landed_cost_eur` écrits à la main dans la fiche produit ; aucun
appel vers ce module n'existe dans `src/`, `product_tool.py` ni `generics_tool.py`.

Deux décisions avant de brancher, et l'outil refuse volontairement de les prendre pour nous
— `observations` n'a aucun chemin de sortie par défaut, parce que l'emplacement de la couche
de prix est un arbitrage, pas une commodité :

1. **Où vit la série.** Un fichier daté sous `data/price_observations/`, comme les relevés
   fournisseur ? Ou une couche distincte, puisqu'un prix matière n'est pas un relevé
   catalogue mais une déduction faite sur nos propres factures ?
2. **Quelle valeur le moteur retient.** Le dernier prix payé, la médiane sur N mois, ou le
   prix à une date donnée. Quelle qu'elle soit, la fiche doit **dire laquelle** — un coût
   qui ne déclare pas sa règle de sélection n'est pas auditable.

Tant que ce branchement n'existe pas, le jalon 4 ne débloque rien du jalon 3 : le croissant
sera chiffré sur un prix choisi à la main, comme avant.

### Jalon 5 — Les recettes

[ADR-0002](decisions/ADR-0002-modele-de-recette.md), trois couches à ne pas confondre :
l'opéra standard du métier, les opéras des autres (1 140 références déjà en catalogue), et
le nôtre. Une recette de métier est une référence ; la nôtre est un fait sur nous.

### Jalon 6 — L'hybride par composant

[ADR-0003](decisions/ADR-0003-hybride-par-composant.md). Aujourd'hui `HYBRID` est un seul
nombre saisi à la main. Un vrai hybride achète une base et y ajoute du travail : son coût est
une **somme** par composant, jamais un minimum. Prendre le minimum faisait de l'hybride le
poste le moins cher du catalogue et biaisait tout le classement vers lui.

### Jalon 7 — La Manita

Le module commercial : 5 compartiments, 5 produits, 5 €. Il ne peut pas précéder les
jalons 1 à 3 — un panier dont aucun composant n'a de coût n'est pas un panier, c'est un vœu.

---

## Ce qui n'est pas sur cette route, et pourquoi

| | raison |
|---|---|
| API catalogue METRO | derrière Akamai, prix pro lié au compte. Les factures PDF donnent mieux : le prix payé, pas le prix affiché. |
| Balayage complet Foodomarket | 5 905 offres capturées, non rattachées. Le blocage est le rattachement, pas la capture — et le libellé ment (« amande » y désigne aussi un coquillage). |
| Nouveaux modules de formules | vegan, oriental, diététique. Ils réutilisent le socle ; le socle n'est pas fini. |

---

## Ce que ce document promet

Les compteurs ci-dessus sont vérifiés par `tests/test_roadmap.py` contre les données réelles.
Une feuille de route qui se contredit elle-même est pire qu'absente : elle fait croire à un
état qui n'existe plus.
