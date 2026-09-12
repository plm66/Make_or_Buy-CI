# Décisions d'architecture

Un ADR par décision qui engage la doctrine, le modèle de données ou le moteur. Il porte la
question, ce qu'on a écarté, et pourquoi — pas seulement ce qu'on a retenu. Une option
rejetée sans motif revient tous les six mois.

## Ce qui mérite un ADR

Ce qu'un lecteur ne peut pas déduire du code : un arbitrage entre deux options défendables,
une contrainte métier qui explique une forme bizarre, un refus argumenté.

Ce qui n'en mérite pas : un choix que le code énonce déjà, une convention de nommage, un
correctif de défaut. Ceux-là vivent dans le message de commit et dans `CLAUDE.md`.

## Statuts

| statut | sens |
|---|---|
| `PROPOSED` | posé, pas tranché — Philippe décide |
| `ACCEPTED` | tranché, engage la suite |
| `SUPERSEDED by ADR-XXXX` | remplacé, conservé pour l'historique |
| `REJECTED` | écarté, conservé pour la même raison |

Un ADR ne se supprime pas et ne se réécrit pas. Il se remplace par un suivant qui le cite.

## Articulation avec la doctrine

`doctrine/doctrine.json` suit le document humain, il ne se modifie pas depuis le dépôt. Un
ADR `ACCEPTED` qui touche à la doctrine **alimente la version suivante du .docx**, il ne la
devance pas. Les postulats, eux, se modifient par delta versionné sous
`postulates/*/deltas/`.

## Index

| ADR | statut | objet |
|---|---|---|
| [0001](ADR-0001-axe-de-composition.md) | PROPOSED | frais et naturel, surgelé, chimique : l'axe absent de la doctrine |
