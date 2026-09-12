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
