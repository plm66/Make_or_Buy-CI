# Make_or_Buy — règles locales

Ces règles complètent les instructions globales et `Make_or_Buy/CLAUDE.md` pour ce dépôt.

## Préservation de l'état Git

- Jamais `git reset --hard`, ni aucun équivalent qui puisse écraser du travail, sans
  autorisation explicite.
- Jamais `git checkout` sans autorisation explicite, y compris pour changer de branche ou
  restaurer un fichier.

## Livraison documentaire

Pour le périmètre documentaire non impactant de la session actuelle, travailler directement sur
`main`, valider le contenu et le diff, puis committer. L'absence de worktree, de branche dédiée
et de pull request est une décision provisoire de portée, pas une interdiction générale.

Si la documentation devient substantielle ou impactante, ou si le travail devient concurrent,
réévaluer l'isolation et le besoin d'une branche, d'un worktree ou d'une pull request.

## Livraison de code

Dès qu'une modification de code est nécessaire, isoler le travail dans une branche ou
worktree, verrouiller le comportement par des tests, exécuter la validation appropriée, faire
la revue, puis ouvrir une pull request si le changement doit être proposé pour intégration.

## Où vivent les worktrees

**Jamais sous `.claude/`.** Les worktrees vont dans `../Make_or_Buy-worktrees/<nom>`, à côté
du dépôt.

`.claude/` est un répertoire d'outil, propre à un seul assistant. Un worktree qui y vit
n'est pas relevable par un développeur travaillant sous un autre modèle, et disparaît avec
une remise à zéro de l'outil — en emportant ce qui n'aurait pas été poussé.

Le hook `spec-first` l'ignore par ailleurs : son `SKIP_DIRS` contient `/.claude/` et
`/.worktrees/`. Un worktree placé là échappe à tout contrôle de spec, ce qui annule la
raison d'être de l'isolation. Mesuré : le même fichier rend `skipped: non-code or filtered
path` sous `.claude/`, et `BLOCKED: spec-first rule` une fois déplacé.

`EnterWorktree` crée sous `.claude/worktrees/` sans que le chemin soit configurable — le
réglage `worktree` de `settings.json` ne porte que `symlinkDirectories`. Créer donc le
worktree à la main puis l'ouvrir par son chemin :

```bash
git worktree add ../Make_or_Buy-worktrees/<nom> -b <branche>
# puis EnterWorktree avec path, depuis le répertoire de lancement
```

Un worktree déjà créé au mauvais endroit se déplace sans perte : `git worktree move`.
