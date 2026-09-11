# Make_or_Buy — règles locales

Ces règles complètent les instructions globales et `Make_or_Buy/CLAUDE.md` pour ce dépôt.

## Préservation de l'état Git

- Jamais `git reset --hard`, ni aucun équivalent qui puisse écraser du travail, sans
  autorisation explicite.
- Jamais `git checkout` sans autorisation explicite, y compris pour changer de branche ou
  restaurer un fichier.

## Livraison documentaire

Tant que la modification reste documentaire — README, documentation, règles ou commentaires
de périmètre — travailler directement sur `main`, valider le contenu et le diff, puis
committer. Pas de worktree, pas de branche dédiée et pas de pull request pour cette catégorie
de changement.

## Livraison de code

Dès qu'une modification de code est nécessaire, isoler le travail dans une branche ou
worktree, verrouiller le comportement par des tests, exécuter la validation appropriée, faire
la revue, puis ouvrir une pull request si le changement doit être proposé pour intégration.
