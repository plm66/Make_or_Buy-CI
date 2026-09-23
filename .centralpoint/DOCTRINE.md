# CENTRALPOINT — Doctrine du protocole textuel

> Mutex distribué textuel pour coordonner plusieurs sessions Claude (ou IA) parallèles sur un même projet, sans support natif d'inter-session coordination.

---

## 0. Pourquoi

Claude Code (et la plupart des CLI IA) n'a **aucun mécanisme natif** pour qu'une session sache ce qu'une autre session fait au même moment :

- Pas de lock filesystem partagé entre sessions Claude
- Pas de canal de communication inter-process intégré
- Chaque session voit son propre contexte uniquement
- Aucune visibilité sur les worktrees git ouverts ailleurs, les branches en cours, les fichiers en édition par d'autres

**Conséquence directe** : sans discipline imposée, deux sessions Claude en parallèle (terminal principal + worktree + sub-agent) entrent silencieusement en collision sur :

- création / suppression de worktrees
- merges et rebases concurrents
- édition simultanée des mêmes fichiers
- destruction de travail non commité

CENTRALPOINT comble ce vide par un **fichier markdown discipliné** placé à la racine du repo, qui sert de :

- snapshot partagé de l'état réel du projet (§1)
- canal d'instructions adressées (§2)
- registre des chantiers en cours par contributeur (§3 WIP)
- mémorial des décisions architecturales (§4, append-only horodaté)
- journal de dialogue inscriptible par tous (§5)

Le fichier est l'**instrument du mutex**. Le protocole en est la **sémantique**.

---

## 1. Activation

CENTRALPOINT s'active **par présence du fichier** :

```
<repo-root>/CENTRALPOINT.md     →  protocole actif
absent                          →  protocole non applicable
```

Aucune configuration globale. Pas de feature flag. Pas d'opt-in interactif. Le fichier *est* la déclaration que le projet utilise ce protocole.

**Conséquence** : tout outil (humain ou IA) qui détecte `CENTRALPOINT.md` au démarrage **doit** appliquer le protocole. Le bypass = violation contractuelle.

---

## 2. Le protocole double (obligatoire)

### 2.1 READ-BEFORE-ACTION

Avant **toute action substantielle ou destructive** sur le repo :

1. Lire `CENTRALPOINT.md §3 (Work in Progress)` — identifier les contributeurs actifs et leurs worktrees/branches.
2. Lire les **5 entrées les plus récentes** du §5 (Journal de dialogue) pour le contexte frais.
3. Exécuter `git worktree list` — voir les worktrees parallèles physiquement présents. Si le projet n'est pas un repo git, sauter cette étape et rendre cette limite visible dans `§1 État actuel` jusqu'à initialisation git.
4. Si l'action envisagée chevauche un WIP actif : **coordonner via inscription §5 AVANT d'agir.**

### 2.2 WRITE-AFTER-ACTION

Après **toute action substantielle**, inscrire en §5 :

- timestamp complet (voir §3 ci-dessous — règle dure)
- demande utilisateur citée verbatim
- action effectuée
- fichiers touchés (paths absolus ou relatifs au repo)
- résultat (succès / blocage / état mixte)
- décisions restées en suspens

Sans cette inscription, les sessions parallèles ne voient pas le travail effectué et peuvent dupliquer ou entrer en conflit.

---

## 3. Format de timestamp (règle dure)

Toute entrée §5 — humain ou IA — **doit** porter date **ET** heure locale **avec timezone** :

```
### YYYY-MM-DD HH:MM TZ — <Persona/Auteur> — <Titre>
```

Exemples corrects :

```
### 2026-05-13 17:42 CEST — Quentin — Amendement Step 0
### 2026-05-13 14:42 CEST — Claudine — PR #102 mergée
### 2026-05-13 09:15 CEST — PLM — Décision provider LLM
```

**Pourquoi cette rigueur** : plusieurs sessions IA peuvent écrire dans le §5 le même jour. Une entrée date-seule (`### 2026-05-13 — ...`) crée une ambiguïté sur l'ordre d'action — un Claude parallèle ne peut pas déterminer si ta "mission acceptée" précède ou suit son action. La sémantique mutex se brise. **L'heure + TZ résout sans recourir à `git log`.**

**Backward compatibility** : les entrées historiques date-seule restent telles quelles. Seules les NOUVELLES entrées (à partir de l'introduction de cette règle) portent le timestamp complet. Pas de retro-édition.

---

## 4. Double lock pour actions destructives

Actions **destructives** = `git worktree remove`, `git branch -d/-D`, `git push --force`, modifications CI/CD, `rm -rf`, `DROP TABLE`, etc.

Protocole renforcé :

1. **Inscrire §5 "mission acceptée" AVANT d'agir** (timestamp, lock visible aux sessions parallèles)
2. **Agir**
3. **Inscrire §5 "résultat"** (timestamp, ferme la fenêtre de lock)

Le pattern verrouille la fenêtre temporelle pendant laquelle l'action destructive est en cours. Une session parallèle qui lit §5 entre l'étape 1 et 3 voit explicitement qu'une opération destructive est en flight.

---

## 5. Portée

Le protocole s'applique à **tous les acteurs** sur le projet :

| Acteur | Application |
|---|---|
| Claude executor (session principale) | Via règle globale en CLAUDE.md user-level |
| Quentin (sub-agent natif) | Step 0 bloquant dans `~/.claude/agents/quentin.md` |
| Sub-agents futurs (Hector exécutant, Zoe, …) | Hériter de la règle au niveau du fichier persona |
| Humain (PLM) | Inscription manuelle dans §5 lors d'actions hors-Claude |
| Codex, Gemini (si MCP server CENTRALPOINT actif) | Via tools exposés par le MCP — voir `handoff_centralpoint_machine.md` |

Zoe et Hector en mode **purement textuel** (pas d'écriture filesystem) n'ont pas besoin du protocole appliqué — leurs sorties sont des suggestions, pas des mutations.

---

## 6. Incident de référence

**2026-05-13** — Audit Quentin sur `fix/spike-truth-and-gates` dans `deribit-zig`.

Pendant l'audit, un terminal parallèle a supprimé le worktree `.worktrees/advices-s0` qui contenait **26 fichiers `zig fmt` non commités**.

**Cause** :

- Quentin n'avait **pas lu §3 WIP** (aurait vu le worktree actif)
- Quentin n'avait **pas inscrit son lock §5** avant le scan
- La session parallèle qui a fait `git worktree remove` n'avait pas non plus consulté §5

**Conséquence** : 26 fichiers perdus, non récupérables (pas de stash, pas de commit, pas de reflog sur du contenu non versionné).

Cet incident est la raison d'être du protocole. La règle existe pour le rendre impossible à reproduire, pas pour discipliner par principe.

---

## 7. Articulation avec ce dossier

Ce fichier (`DOCTRINE.md`) définit le **protocole opérationnel manuel** — ce que tout participant doit faire textuellement.

Les autres documents du dossier :

- `explains.md` — la question d'origine : peut-on automatiser ce protocole entre Gemini/Codex/Claude ?
- `handoff_centralpoint_machine.md` — l'analyse des 3 options d'automation (script, MCP server, orchestrateur async). Décision pendante : Option B (MCP `centralpoint`).
- `CONSTITUTION.md` — règles d'enrôlement des personas : identité canonique, reprise de rôle, collisions de prénom, rôles réservés.
- `CENTRALPOINT.template.md` — squelette markdown à copier-coller à la racine d'un nouveau projet qui adopte le protocole.

**Relation** : la DOCTRINE est la spec que l'automation future devra implémenter. Un MCP server `centralpoint` exposera des tools (`read_my_inbox`, `accept_mission`, `commit_journal_entry`) qui *appliquent automatiquement* ce que cette doctrine demande à un humain ou une IA de faire manuellement.

Sans la doctrine, l'automation ne sait pas quel comportement encoder. Sans l'automation, la doctrine repose entièrement sur la discipline du participant (et donc casse en pratique, cf §6).

---

## 8. Implémentation de référence

L'implémentation manuelle la plus aboutie à ce jour :

```
/Users/erasmus/DEVELOPER/_Trading/zig-trader/deribit-zig/CENTRALPOINT.md
```

951 lignes, en production, ~6 mois d'usage. À parcourir pour comprendre comment les §0 à §5 vivent dans un projet réel sur la durée.

---

## 9. Critique honnête du protocole

**Faiblesses** :

- Repose sur la discipline — toute IA qui ignore l'instruction casse le mutex
- Pas de garantie d'atomicité (deux écritures simultanées sur §5 peuvent se corrompre — git résout en pratique mais pas par construction)
- Verbeux : chaque action substantielle = lecture + écriture supplémentaire
- Aucun mécanisme de notification — il faut *aller lire*, personne ne te prévient

**Pourquoi le protocole tient quand même** :

- Le coût d'une inscription §5 (~10 secondes) << coût d'un incident type §6
- Git versionne le fichier → si corruption, recovery via `git log -p CENTRALPOINT.md`
- Les `### YYYY-MM-DD HH:MM TZ` créent un ordre total déchiffrable
- En attendant l'automation MCP (Option B), c'est le seul mécanisme disponible

L'objectif final est de rendre ce protocole **mécaniquement vérifiable** par un MCP server qui refuse l'action si §5 n'a pas été mis à jour. Tant que ce server n'existe pas, la discipline textuelle est le mutex.
