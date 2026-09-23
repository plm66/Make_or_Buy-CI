# CENTRALPOINT — <Nom du projet>

> Mutex distribué textuel. Voir `DOCTRINE.md` (https://github.com/.../CLaudeCode-centralpoint) pour le protocole complet.

---

## §0. Méta

### §0.1 Personas reconnues sur ce projet

> Format normé par `CONSTITUTION.md §1` — six colonnes obligatoires, aucune vide.

| Prénom | Rôle | Modèle | Worktree habituel | Depuis | Statut |
|---|---|---|---|---|---|
| PLM | Lead humain | humain | `<repo-root>` | `<scaffolding>` | `actif` |
| Claude | Executor principal | claude-opus-5 | `../Make_or_Buy-worktrees/<mission>` | `2026-09-23 01:59 CEST` | `actif` |
| Quentin | Auditeur pre-PR | claude-opus-4-x | n/a | `<scaffolding>` | `actif` |
| Jérémie | Dev opérationnel — installation et validation CENTRALPOINT | gpt-5.6-luna | `<repo-root>` | `2026-09-23 01:57 CEST` | `actif` |

### §0.2 Commande implicite : `go central`

Quand un participant tape `go central`, la séquence attendue est :

1. Relire `CENTRALPOINT.md` (§1 état, §2 arbitrages, §3 WIP, §5 récents)
2. Identifier les instructions actives qui le concernent
3. Si la persona n'est pas encore reconnue en §0.1 : lire `CONSTITUTION.md` et s'enrôler avant d'accepter une mission
4. S'inscrire en §3 pour accepter la mission (ou refuser explicitement)
5. Exécuter
6. Inscrire le résultat en §5

### §0.3 Signalement des informations manquantes

Si un participant ne retrouve pas une info attendue (commit, fichier, décision), il l'**inscrit explicitement** en §5 plutôt que de procéder à l'aveugle.

### §0.5 Doctrine projet-spécifique

(Surcharge / précisions locales par-dessus la doctrine globale — exceptions, conventions de timezone, branches protégées, etc.)

---

## §1. État actuel (snapshot partagé)

> Mis à jour par PLM ou Claude executor lors d'un changement d'état macro. Snapshot, pas log.

- Branche principale : `main` — 208 invariants verts sous `python3 -B`
- Dernier tag livré : aucun tag. Le dépôt n'a jamais été taggé.
- Phase en cours : `socle` — le moteur et le référentiel sont complets, **aucun produit n'est
  arbitrable**. Voir `Make_or_Buy/docs/ROADMAP.md`.
- Worktrees actifs : `main`, `chore/hygiene-depot` et `feat/verdicts-au-glossaire` (Claude,
  tous deux fusionnés, worktrees encore sur disque)
- Blockers macro :
  0. **Lire l'étiquette de la plaquette de beurre.** Trente secondes, et 93,6 % de la
     dépense en matière grasse cesse de reposer sur une supposition.
  1. `0 / 21` gestes chronométrés — mesure en laboratoire, décision PLM
  2. `1 / 3` ADR acceptés — ADR-0001 tranché le 23-09. Le seuil MAKE/BUY va de 45 à 64 min
     par lot de 60 selon le beurre (et non 30 à 64 : le 30 reposait sur un taux de tourage
     inventé). Chronométrer avant de choisir ne décide rien.
  3. La couche de prix matière n'est branchée sur aucun moteur : `engine.py` lit toujours des
     coûts saisis à la main.
  4. ~~`GARDER` rendu 32 fois sur 32 sans contradicteur chiffré~~ → ✅ **levé** par
     `feat/verdicts-au-glossaire` : le verdict est scindé, `NON_COMPARE` prend l'absence
     d'alternative, `GARDER` reste au seul cas comparé. Les onze codes sont déclarés au
     glossaire et un invariant refuse tout code non défini. Mesure initiale : Claude, §5 du
     02:14 ; correctif : §5 du 02:44.
- Snapshot au 2026-09-23 02:50 CEST

---

## §2. Arbitrages actifs

> Décisions / instructions de PLM aux personas. Écriture restreinte : PLM uniquement. Lecture par tous.

### <date> — <persona destinataire> — <titre instruction>

(corps de l'instruction)

---

## §3. Work in Progress (WIP)

> Qui fait quoi *maintenant*. Mise à jour à chaque début et fin de mission.

| Persona | Worktree / branche | Mission | Démarré | Statut |
|---|---|---|---|---|
| Jérémie | `<repo-root>` | Enrôlement et initialisation de CENTRALPOINT | 2026-09-23 01:57 CEST | `✅ Terminée` |
| Jérémie | `feat/factures-volumes-et-alternatives` | Volumes, boîtes, sources alternatives, CI | 2026-09-22 21:33 CEST | `✅ PR #3 fusionnée (babb6ca)` |
| Claude | `chore/onboarding` | Relecture de code et document d'accueil | 2026-09-23 01:59 CEST | `✅ Fusionnée (368d113)` |
| Claude | `chore/hygiene-depot` | Hygiène du dépôt : node_modules ignoré, CENTRALPOINT versionné, §1/§3 rafraîchis | 2026-09-23 02:10 CEST | `✅ Fusionnée (0b18eb6)` — worktree encore sur disque |
| Claude | `feat/verdicts-au-glossaire` | Déclarer les 11 codes de verdict, scinder `GARDER` en `GARDER` / `NON_COMPARE` | 2026-09-23 02:40 CEST | `✅ Fusionnée` — worktree encore sur disque |

---

## §4. Mémorial des décisions

> **Append-only**. Une fois écrit, jamais modifié ni supprimé. Réservé aux décisions architecturales ou de scope.

### 2026-09-23 02:38 CEST — Décision N°1 — ADR-0001 ACCEPTED, l'axe de composition

- **Décision** : `composition_nature` devient un attribut de fiche porté avec son niveau de
  preuve (option C), doublé d'un garde-fou `G007` qui pose ce qui ne se négocie pas (option B).
- **Contexte** : la doctrine pondère huit critères dont aucun ne mesure de quoi un produit est
  fait. Le moteur pouvait rendre `BUY` sur un produit dont le seul défaut était sa composition,
  et le refus humain qui aurait suivi serait resté hors doctrine — non tracé, non rejouable.
- **Alternatives écartées** :
  - A, un neuvième critère pondéré : une pondération se compense, et elle répond à « combien
    d'euros vaut l'absence d'arôme artificiel ».
  - D, ne rien faire : revient à renoncer à la seconde moitié de la mission.
- **Auteur de la décision** : Philippe.
- **Implémenté par** : `e2626f7`, fusionné en `510b0a0`.
- **Ne tranche pas** : le choix beurre doux 82 % contre tourage AOP 84 %. Les deux sont
  `FRESH_NATURAL` — cet axe ne les distingue pas. Ce choix attend la lecture d'une étiquette,
  `BEURRE DX 500G MA PAYSANNE` portant 93,6 % de la dépense en matière grasse avec un
  rattachement `A_VERIFIER`.

### 2026-MM-DD HH:MM TZ — <Décision N°>

- Décision : (1 phrase)
- Contexte : (pourquoi)
- Alternatives écartées : (liste)
- Auteur de la décision : (nom)
- Implémenté par : (commit ou PR, si applicable)

---

## §5. Journal de dialogue

> Bus de messages. Lecture par tous. Écriture par tous (chaque persona dans son créneau). Une entrée = un événement substantiel ou une action destructive.
>
> **Format de header obligatoire :** `### YYYY-MM-DD HH:MM TZ — <Persona/Auteur> — <Titre>`
>
> **Un « reste en suspens » résolu s'annote, il ne s'efface pas** : `→ ✅ clos par <sha>
> (<date>)`. Le corps d'une entrée reste ce qu'il était au moment où il a été écrit ; c'est la
> seule ligne qu'on y ajoute. Sans cette annotation, un point résolu continue de se lire comme
> ouvert, et §5 devient une liste de faux blocages — le lecteur ne peut pas distinguer ce qui
> attend de ce qui est fait. §2 et §4 restent immuables ; §5 ne l'est pas.

---

### 2026-09-23 01:57 CEST — Jérémie — Inscription

**Demande citée** : "enrole toi... normalement tu es jeremie..."

**Action effectuée** :
- Lecture de `.centralpoint/CONSTITUTION.md`.
- Lecture de `CENTRALPOINT.md` (§0.1, §3 et §5).
- Inscription de Jérémie dans §0.1.
- Enregistrement de la mission de Jérémie dans §3.

**Fichiers touchés** :
- `CENTRALPOINT.md`

**Résultat** : ✅ Jérémie est inscrit et actif.

**Reste en suspens** :
- Aucun.

---

### 2026-09-23 01:59 CEST — Claude — Inscription, relecture de code, document d'accueil

**Demande citée** : « on relit le code ! et tu expliques aux nouveaux qui nous rejoignent ce
que nous avons déjà réalisé, ce que nous sommes en train de faire et pourquoi, et ce qu'il
nous reste à faire »

**Action effectuée** :
- Inscription en §0.1 (modèle corrigé : `claude-opus-5`) et en §3.
- §1 rempli : le champ « blockers macro » était un gabarit, il porte maintenant les trois.
- Relecture de `serveur_factures.py`, `comparaison_factures.py`, `metro_factures.py`.
- Rédaction de `Make_or_Buy/docs/ONBOARDING.md`.

**Trouvaille principale** : sur les 384 lignes du corpus, **33 verdicts `GARDER` sur 33 ne
reposent sur aucune alternative chiffrée**. Le mot affirme une décision de sourcing que rien
n'a contestée. C'est le motif récurrent du dépôt — un nom qui porte plus que sa preuve, comme
`material_cost_eur` portait un coût complet. Détail en §5 du document d'accueil.

**Fichiers touchés** : `CENTRALPOINT.md`, `Make_or_Buy/docs/ONBOARDING.md`.

**Reste en suspens** :
- `CENTRALPOINT.md` n'est pas suivi par git. Tant qu'il n'est pas commité, le mutex ne
  traverse pas les clones — il ne protège que cette machine.
  → ✅ clos par `d24db65` (2026-09-23 02:18 CEST)
- La branche de Jérémie est prête et non fusionnée. Elle n'est pas de mon ressort.
  → ✅ clos par `babb6ca`, PR #3 fusionnée (2026-09-23 01:59 CEST)

---

### 2026-09-23 02:14 CEST — Claude — Correction : mes chiffres dataient d'avant la PR #3

**Constat** : j'ai mesuré les verdicts avant que `alternatives_marche.json` n'entre dans
l'arbre. `origin/main` affichait `674beb9` au début de ma passe ; la PR #3 a été fusionnée
à 01:59 (`babb6ca`) pendant que je travaillais. Vérifié : rien n'a été écrasé, `c61a429` est
bien ancêtre de `main`.

**Effet** : `ONBOARDING.md` annonçait 24 rattachements et 33 `GARDER`. Réel après fusion :
46 rattachements (17 actifs, 22 à vérifier, 7 hors périmètre), et **32 `GARDER` sur 32**.

**La trouvaille survit et se durcit** : 10 verdicts `CHANGER` réels existent maintenant à
côté. Un lecteur en déduit que les `GARDER` ont été confrontés et ont gagné — aucun ne l'a
été, le catalogue d'alternatives ne couvre que 6 matières. La PR a rendu le mot **plus**
trompeur, pas moins.

**Fichiers touchés** : `README.md`, `Make_or_Buy/docs/ONBOARDING.md`,
`Make_or_Buy/tests/test_roadmap.py`, `CENTRALPOINT.md`.

**Résultat** : `edf043a` fusionné, 206/206 invariants verts, poussé.

**Reste en suspens** :
- `NON_COMPARE` n'est pas implémenté. `comparaison_factures.py` appartient au chantier de
  Jérémie ; l'arbitrage sur le nom du verdict revient à PLM.
- `CENTRALPOINT.md` n'est toujours pas suivi par git.
  → ✅ clos par `d24db65` (2026-09-23 02:18 CEST)

---

### 2026-09-23 02:18 CEST — Claude — Hygiène du dépôt : node_modules, CENTRALPOINT versionné, §1/§3

**Demande citée** : « quelles sont tes recommandations pour l'immédiat ? situe-toi sur le
centralpoint.md », puis « go ».

**Situation trouvée** : §1 annonçait `674beb9` / 195 invariants ; le réel était `3a55194` /
206. §3 portait deux missions comme actives alors que les deux branches étaient fusionnées.
Un contributeur parallèle lisant §3 pouvait refaire un travail déjà livré.

**Action effectuée** :
- `node_modules/` (23 Mo, 92 paquets déposés par `npm install` de `@plm/centralpoint`)
  n'était ignoré par rien. Ajouté au `.gitignore`. `package.json` et `package-lock.json`
  restent suivis : ils épinglent la version de l'outil qui tient le mutex.
- `CENTRALPOINT.md` et `.centralpoint/` versionnés. Ferme le point resté ouvert dans les
  entrées de 01:59 et 02:14 — sans cela le mutex ne protège que cette machine.
- §1 rafraîchi sur les faits mesurés, §3 mis à jour, blocker macro n°4 ajouté.

**Correction reçue** : mon premier jet du blocker n°4 portait « 33 `GARDER` sur 33 », chiffre
de l'entrée de 01:59. L'entrée de 02:14 le corrige à **32 sur 32**, avec 10 `CHANGER` réels
désormais à côté. J'ai repris ses chiffres. C'est le mutex qui a fonctionné : la mesure la
plus récente a écrasé la mienne parce qu'elle était lisible ici.

**Fichiers touchés** : `.gitignore`, `CENTRALPOINT.md`, `.centralpoint/`, `package.json`,
`package-lock.json`.

**Travail antérieur non journalisé, inscrit ici pour mémoire** : les 4 commits du 2026-09-21
(`329a1b1` `d1f165b` `72c48d0` `b7240a3`, fusionnés) sont antérieurs à la création du
CENTRALPOINT et n'y figuraient pas. Ils corrigent une `SyntaxError` qui rendait
`web/factures.html` entièrement inerte, un chemin de test mort qui expliquait pourquoi
personne ne l'avait vue, et ajoutent `rapport_factures.py`.

**Reste en suspens** :
- Le worktree `chore/hygiene-depot` reste sur disque après fusion. `git worktree remove` est
  une action destructive au sens du protocole : elle attend son double verrou, pas mon
  initiative.
- **Conséquence à trancher du versionnement** : `CENTRALPOINT.md` étant désormais suivi, et
  les commits directs sur `main` étant bloqués par hook, chaque inscription en §5 demande
  maintenant une branche et une fusion. C'est plus auditable et c'est plus lourd, pour un
  fichier dont l'intérêt est d'être écrit souvent. Si la friction l'emporte, la sortie est
  d'exempter ce seul chemin dans le hook — décision PLM, pas la mienne.
- Un `__pycache__` périmé peut servir du bytecode faux quand une édition conserve la taille
  du fichier : Python valide son cache sur `(mtime, taille)`. Mesuré le 2026-09-21 sur
  `CHAMPS_PRIX`, dont l'inversion est neutre en octets. La convention `python3 -B` désormais
  documentée dans le README ferme le cas ; une session qui lance `python3` sans `-B` le
  rouvre.

---

### 2026-09-23 02:34 CEST — Claude — Trois « reste en suspens » résolus se lisaient encore comme ouverts

**Demande citée** : « CENTRALPOINT.md n'est toujours pas suivi par git > ?? »

**Constat** : la phrase citée est dans l'entrée de 02:14. Elle était vraie à 02:14 et fausse
depuis 02:18. Rien ne le disait. Trois points résolus se lisaient encore comme ouverts — deux
dans l'entrée de 01:59, un dans celle de 02:14 — et un lecteur ne pouvait pas distinguer ce
qui attend de ce qui est fait. C'est le défaut de la maison sous une forme de plus : une
information exacte à sa date qui ment le lendemain, faute de porter sa date de péremption.

**Action effectuée** :
- Les trois points annotés `→ ✅ clos par <sha> (<date>)`. Vérifiés un par un avant écriture :
  `babb6ca` et `d24db65` sont ancêtres de `main`, `CENTRALPOINT.md` est bien suivi.
- Le corps des entrées n'est pas retouché. Seule la ligne d'annotation s'ajoute.
- Convention inscrite en tête de §5 pour que le cas ne se repose pas.

**Ce qui reste réellement ouvert, après le tri** :
- `NON_COMPARE` n'est pas implémenté — arbitrage PLM sur le nom du verdict (entrée 02:14).
- Le blocker macro n°4, `GARDER` rendu 32 fois sur 32 sans contradicteur chiffré (§1).
- La friction du versionnement : une inscription en §5 demande une branche (entrée 02:18).
- Le worktree `chore/hygiene-depot`, sur disque après fusion (entrée 02:18).

**Fichiers touchés** : `CENTRALPOINT.md`.

**Reste en suspens** :
- §5 annonce « ordre chronologique inverse, plus récent en haut » et ses entrées sont rangées
  du plus ancien au plus récent. La note ou le rangement a tort ; je n'ai pas tranché lequel,
  l'ordre du journal appartient à celui qui l'a défini.

---

### 2026-09-23 02:44 CEST — Claude — `NON_COMPARE` : le blocker macro n°4 est levé

**Demande citée** : « recommandations ? » puis « c'est parti, alors ».

**Ce qui a décidé du correctif, et non l'inverse** : les sept codes de verdict n'étaient
déclarés nulle part, alors que `GLOSSAIRE.md` pose sa règle en tête — un code absent du
glossaire est un code inventé. C'est là que `GARDER` avait pu dériver : personne n'avait
jamais eu à écrire sa définition, donc personne n'avait buté sur ce qu'elle affirmait. La
recommandation n'était pas « renommer `GARDER` » mais « écrire les définitions » ; le
renommage en est tombé.

**Mesure** : 32 `GARDER` sur 32 portaient `AUCUNE_ALTERNATIVE_CHIFFREE`, et le cas
`ALTERNATIVE_PLUS_CHERE` — le seul où le mot serait mérité — n'avait jamais été atteint une
seule fois.

**Action effectuée** :
- Onze codes déclarés en `GLOSSAIRE.md §9`, statuts de dérive compris (`ALIGNED`,
  `UNIT_GAP`, `PROMO_EXCLUDED`), qui sortaient aussi en JSON sans définition.
- `NON_COMPARE` prend l'absence d'alternative ; `GARDER` reste au seul cas comparé.
- Invariant : tout code sorti par `comparaison_factures.py` doit être défini par une **ligne
  de tableau** du glossaire. La première version acceptait une mention en prose — vérifié par
  mutation, elle ne mordait pas. Durcie, elle mord sur les trois codes testés.
- `ALTERNATIVE_PLUS_CHEREE` (deux `E`) corrigé dans la même passe.
- `SPEC_MODULE_FACTURES.md`, `ONBOARDING.md`, `README.md` suivis. 208 invariants verts.

**Relevé de symétrie avant édition** : `GARDER` avait trois sites, pas un. Deux le méritent —
la branche hors périmètre confronte une revente à une alternative grossiste — et gardent le
mot. Seul le troisième devient `NON_COMPARE`.

**Fichiers touchés** : `comparaison_factures.py`, `rapport_factures.py`, `web/factures.html`,
`docs/GLOSSAIRE.md`, `docs/SPEC_MODULE_FACTURES.md`, `docs/ONBOARDING.md`, `README.md`,
`tests/test_verdicts.py`, `tests/test_roadmap.py`, `tests/test_serveur_factures.py`,
`CENTRALPOINT.md`.

**Reste en suspens** :
- Deux worktrees fusionnés restent sur disque, `chore/hygiene-depot` et
  `feat/verdicts-au-glossaire`. Leur retrait est destructif au sens du protocole.
- La friction du versionnement de `CENTRALPOINT.md` reste entière : cette entrée elle-même a
  demandé une branche et une fusion. Toujours un arbitrage PLM.
- `GARDER` est désormais à **zéro occurrence**. Ce n'est pas un défaut : c'est la mesure que
  le mot cachait. Il redeviendra non nul le jour où le catalogue d'alternatives couvrira une
  matière où nous achetons déjà au mieux.

---

### 2026-09-23 02:47 CEST — Claude — Mission acceptée : retrait de deux worktrees fusionnés

**Verrou posé avant action** — action destructive au sens du protocole.

**Demande citée** : « on peut les suppr sans risque ? » puis « go ».

**Périmètre exact** :
- `git worktree remove` sur `chore/hygiene-depot` et `feat/verdicts-au-glossaire`. Les deux
  arbres sont propres : aucune modification non commitée, aucun fichier non suivi.
- `git branch -d chore/hygiene-depot` — zéro commit absent de `main`.
- **La branche `feat/verdicts-au-glossaire` est conservée.** Elle porte `6e8f488`, non fusionné
  et non poussé : l'inscription qui lève le blocker macro n°4. La supprimer perdrait ce commit.
  Elle attend un arbre de travail propre sur cette machine pour être fusionnée.

**Ce que je ne touche pas** : `CENTRALPOINT.md` porte en ce moment 23 lignes non commitées
d'une session parallèle — blocker 0 sur l'étiquette du beurre, ADR-0001 accepté, décision N°1
en §4. Cette entrée est un ajout en fin de §5 ; leurs lignes sont intactes. Une première
tentative d'écriture a été refusée parce que le fichier avait bougé entre ma lecture et mon
écriture : la course existe, elle n'est pas théorique.

**Résultat** — verrou refermé :
- Les deux répertoires sont retirés. Propreté revérifiée à l'instant du retrait, pas
  seulement à l'analyse : `0 modification` sur chacun.
- `chore/hygiene-depot` supprimée (était `7e2c968`, entièrement dans `main`).
- `feat/verdicts-au-glossaire` conservée, et `6e8f488` vérifié présent après coup —
  `git branch --contains` le confirme. Rien n'a été perdu.
- Le retrait a révélé un worktree que je ne connaissais pas : `feat/sourcing-garniture-dessert`
  (`ba906a6`), actif. Il n'est pas inscrit en §3 — un travail en cours invisible au mutex est
  exactement ce que §3 existe pour empêcher. À inscrire par celui qui le mène.

---

### 2026-MM-DD HH:MM TZ — <Persona> — <Titre>

**Demande citée** : "(extrait verbatim de la demande utilisateur)"

**Action effectuée** :
- (puces)

**Fichiers touchés** :
- `path/to/file1`
- `path/to/file2`

**Résultat** : ✅ succès / ⚠️ partiel / ❌ blocage

**Reste en suspens** :
- (puces)

---

(les entrées suivent dans l'ordre chronologique inverse — plus récent en haut, plus ancien en bas)

---

## Glossaire des statuts

| Statut | Signification |
|---|---|
| `✅ Mission acceptée` | Persona prend en charge, va commencer |
| `EN ATTENTE` | Bloqué sur une dépendance (préciser laquelle) |
| `STOP` | Demande explicite d'arrêt (préciser raison) |
| `GO` | Feu vert PLM pour procéder |
| `NO-GO` | Refus PLM (préciser pourquoi) |
| `✅ Done` | Action terminée, résultat inscrit |
| `❌ Échec` | Action tentée, échouée (préciser cause) |

---

## Règles dures (rappel)

1. **READ-BEFORE-ACTION** — lire §3 + 5 dernières entrées §5 avant toute action substantielle
2. **WRITE-AFTER-ACTION** — inscrire en §5 après toute action substantielle
3. **Timestamp complet obligatoire** sur chaque entrée §5 (`YYYY-MM-DD HH:MM TZ`)
4. **Double lock** pour actions destructives (inscrire AVANT + APRÈS)
5. **§2 et §4 immutables** sauf par leur propriétaire (PLM pour §2, append-only pour §4)
