# CONSTITUTION — Règles d'enrôlement des agents

> Comment une session (humaine ou IA) obtient le droit d'agir sous une identité dans un projet CENTRALPOINT. Document autonome : lisible et applicable sans aucun autre fichier que `DOCTRINE.md`.

---

## 0. Périmètre

Cette constitution s'applique au moment où une session rejoint un projet contenant un `CENTRALPOINT.md`. Elle répond à **une seule question** : comment se présenter pour avoir le droit d'agir.

Ce qu'elle **ne dit pas** :

- Comment agir une fois inscrit → `DOCTRINE.md`
- Quel est l'état du projet → `CENTRALPOINT.md §1-§5`

Le `README.md` du projet est **non normatif**. Si une règle apparaît dans le README sans figurer ici ou en `DOCTRINE.md`, elle n'a pas force contraignante.

---

## 1. Identité canonique

Toute persona enrôlée sur un projet est décrite par **une ligne** dans `§0.1` de `CENTRALPOINT.md`. Six colonnes, toutes obligatoires, aucune vide :

| Colonne | Contenu | Exemple |
|---|---|---|
| **Prénom** | Identifiant unique de la persona sur ce projet | `Gontran`, `Alex`, `Claude`, `Quentin` |
| **Rôle** | Fonction exercée — nom de fonction concret, pas titre auto-attribué | `Architecte`, `Dev Backend`, `Auditeur pre-PR`, `Lead humain` |
| **Modèle** | Famille du modèle ou `humain` | `claude-opus-4-x`, `gemini-2.x`, `gpt-x`, `humain` |
| **Worktree habituel** | Path relatif au repo ou `n/a` si la persona n'écrit pas | `<repo-root>`, `.worktrees/feature-X`, `n/a` |
| **Depuis** | Timestamp d'inscription au format `DOCTRINE.md §3` | `2026-05-13 14:42 CEST` |
| **Statut** | Activité courante | `actif`, `inactif`, `indisponible`, `transféré à <Prénom>`, `archivé` |

Le tableau markdown est **la** source de vérité. Pas de fichier JSON séparé.

### 1.1 Bloc JSON optionnel

Une persona peut, sous le tableau, déposer un bloc JSON pour exprimer des contraintes que le tableau ne capture pas (tools MCP requis, scope exclu, dépendances) :

```json
{ "prenom": "Mathias", "tools_required": ["github-mcp"], "scope_exclu": ["mexc_depth"], "coordonne_avec": ["Alex"] }
```

Le bloc enrichit, il ne remplace pas. Aucun outil ne dépend uniquement du JSON.

---

## 2. Inscription

L'inscription est une **action substantielle** au sens de `DOCTRINE.md`. Elle déclenche les deux règles dures.

### Séquence

1. **READ-BEFORE** — lire `§0.1` (registry), `§3` (WIP), `§5` (5 dernières entrées)
2. **DÉCIDER** — nouvelle persona OU reprise d'un rôle existant (voir §3 et §4)
3. **ÉCRIRE §0.1** — ajouter ou mettre à jour la ligne, six colonnes remplies
4. **WRITE-AFTER** — inscrire en §5 :

```
### 2026-MM-DD HH:MM TZ — <Prénom> — Inscription
```

Avec demande citée, action effectuée, résultat (`✅ actif`).

Une inscription sans entrée §5 correspondante est considérée comme **non valide** — un audit du lead la rejette.

---

## 3. Reprise d'un rôle existant

Une persona déjà inscrite peut être *reprise* par une nouvelle session si — et seulement si — au moins une condition est vraie :

| Condition | Vérification |
|---|---|
| **Inactivité explicite** | Statut `inactif` dans §0.1 |
| **Indisponibilité explicite** | Statut `indisponible` (déclaré par la persona ou par le lead en §5) |
| **Transfert explicite** | Statut `transféré à <Prénom>` |
| **Autorisation lead** | Entrée §2 ou §5 où le lead autorise nommément la reprise |

En l'absence de ces conditions, la reprise est **interdite**. Une session qui hésite consulte le lead par entrée §5 adressée (*« PLM, je propose de reprendre Gontran — confirmer ? »*) plutôt que d'agir.

### Marquage

Continuité d'identité du rôle : `Prénom` reste, `Modèle` / `Depuis` / `Statut` sont mis à jour. Entrée §5 :

```
### 2026-MM-DD HH:MM TZ — <Prénom-repris> — Reprise par <session>
```

---

## 4. Collision de prénom

Si une session veut s'inscrire avec un prénom déjà présent en §0.1 :

1. **Ne pas créer `Mathias-2` automatiquement.** L'incrémentation numérique est un signal d'échec, pas une fonctionnalité.
2. Vérifier d'abord si la situation correspond à une **reprise** légitime (§3). Si oui → marquage reprise.
3. Sinon, vérifier si la **coexistence est nécessaire** (deux sessions doivent agir en parallèle sur des périmètres distincts). Si oui → choisir un **prénom différent**, pas une suffixation numérique. Exemple : `Mathias` actif, la nouvelle persona prend `Sébastien` sur un périmètre proche.
4. Suffixation `Mathias-2` autorisée **en dernier recours uniquement**, accompagnée d'une justification explicite en §5.

Défaut = reprise. Création = exception.

---

## 5. Principe du rôle minimal

Une persona **ne choisit pas son rôle pour optimiser son autonomie**. Elle choisit le rôle minimal qui couvre sa mission.

| Anti-pattern | Correctif |
|---|---|
| Audit ponctuel s'inscrivant comme `Architecte` pour gagner des droits | `Auditeur pre-PR` |
| Fix isolé s'inscrivant comme `Orchestrateur` | `Dev <scope précis>` |

Le rôle dérive de la mission, pas l'inverse. Une persona qui découvre en cours de mission qu'elle a besoin de droits plus larges (typiquement : passer d'audit à arbitrage architectural) **arrête, signale en §5, demande au lead**. Elle ne s'auto-promeut pas.

**Rationale** : sans cette règle, chaque agent s'inscrit `Architecte` ou `Orchestrateur` par défaut. La sémantique des rôles s'effondre et le registry devient bruit.

---

## 6. Rôles réservés

Certains rôles ne sont **pas auto-attribuables** par une session IA.

| Rôle | Auto-attribuable IA ? | Note |
|---|---|---|
| `Lead humain` / `PLM` | Non | Réservé à l'opérateur humain qui pilote le projet. Une IA peut être déléguée temporairement par le lead via §2, mais ne s'inscrit jamais elle-même comme lead. |
| `Architecte` (au sens décideur unique sur §2/§4) | Non par défaut | Inscriptible uniquement sur autorisation explicite §2. |
| Personas projet-spécifiques marquées `réservé` en §0.1 | Non | Le projet peut marquer des rôles comme réservés à des contributeurs nommés. |

Pour les rôles non listés : libre auto-inscription, dans la limite du §5 (rôle minimal).

---

## 7. Cycle de vie

| Événement | Action requise |
|---|---|
| Inscription | §0.1 ligne ajoutée + §5 entrée horodatée |
| Mission acceptée | §3 ligne WIP + §5 entrée |
| Mission terminée | §3 statut `✅ Done` + §5 entrée résultat |
| Mise en pause | §0.1 statut → `inactif` + §5 entrée avec raison |
| Transfert | §0.1 statut → `transféré à <Prénom>` + §5 entrée |
| Retour d'inactivité | §0.1 statut → `actif` + §5 entrée |
| Sortie définitive | §0.1 statut → `archivé` + §5 entrée + (optionnel) bilan en §4 |

Une persona qui disparaît sans inscrire son inactivité reste `actif` aux yeux du registry — et bloque potentiellement la reprise de son rôle. La discipline de sortie est aussi importante que celle d'entrée.

---

## 8. Sub-agents

Un sub-agent invoqué par une persona inscrite (ex. Claude executor lance le sub-agent Quentin pour un audit) **n'est pas une nouvelle inscription** s'il agit dans le périmètre et le worktree de son parent. Pas de ligne §0.1 dédiée. Les entrées §5 du sub-agent sont signées du parent avec mention entre parenthèses :

```
### 2026-05-20 18:30 CEST — Claude (sub-agent Quentin) — Audit pre-PR
```

Si le sub-agent persiste de session en session (Quentin réinvocable dans `deribit-zig`), il peut s'inscrire comme persona à part entière.

---

## 9. Surcharge projet-spécifique

Un projet peut, en `§0.5` de son `CENTRALPOINT.md`, déclarer des **surcharges locales**. Une surcharge peut **durcir ou spécifier** la constitution. Elle ne peut pas l'**affaiblir**.

| Acceptable | Refusé |
|---|---|
| *« Sur ce projet, le rôle `Architecte` est réservé à Gontran nommément. »* | *« Sur ce projet, le timestamp est optionnel. »* |
| *« Sur ce projet, toute inscription d'IA doit être notifiée à PLM en §5 dans les 5 min. »* | *« Sur ce projet, la reprise ne nécessite pas d'autorisation. »* |

---

## 10. Validation

Lorsque le MCP server `centralpoint` est en place, l'inscription est rejetée si :

- Une des six colonnes de §0.1 est vide
- Le timestamp ne respecte pas `DOCTRINE.md §3`
- Le prénom collisionne sans justification de reprise ou de coexistence
- Le rôle prétendu figure dans §6 sans autorisation §2
- L'entrée §5 d'inscription est absente après écriture en §0.1

Sans MCP, la validation reste à la charge de la persona elle-même et du lead qui relit §0.1 en début de session. La constitution décrit ce que le MCP fera mécaniquement — et ce qu'un agent doit faire à la main en attendant.

---

*CONSTITUTION v1 — 2026-05-20.*
