# Rattacher un achat à une matière

Un relevé de prix ne sert à rien tant qu'on ne sait pas de quelle matière il parle. Ce
fichier porte cette correspondance pour METRO, et rien d'autre.

## La clé est le numéro d'article, pas le libellé

L'article `2422798` s'est appelé `MC FARINE PANIF. T65 25KG` le 27 juillet 2026 et
`MC FARINE PANIFICAT T65 25KG` le 11 septembre. Même EAN, même prix, même produit.
Un rattachement indexé sur le libellé se serait dédoublé tout seul.

C'est la raison pour laquelle le rattachement Foodomarket a échoué là où celui-ci tient :
là-bas il n'existait que des libellés, et « amande » y désignait aussi bien le fruit sec
qu'un coquillage.

## Deux statuts, et pourquoi le second existe

`ACTIF` — la désignation de la facture porte le critère que le référentiel exige. La
farine dit T65 et `MATP-FARI-T65` demande T65 : on lit, on ne suppose pas.

`A_VERIFIER` — le critère n'est pas écrit. `BEURRE DX 500G MA PAYSANNE` est doux, mais
`MATP-BEUR-DOUX` spécifie 82 % de matière grasse et la facture ne dit aucun taux.
Rattacher quand même reviendrait à inscrire dans une base une propriété que personne n'a
mesurée — la forme exacte du défaut que G002 a coûté.

Un `A_VERIFIER` n'est pas une tâche en retard : c'est une question ouverte qui se tranche
en lisant l'étiquette du produit, pas en relisant la facture.

## Ce que le prix peut prouver quand la désignation se tait

`LEVURE 500G*5 LEVAREAL 2,5KG` ne dit ni fraîche ni sèche. Son prix, 2,32 €/kg, le dit :
la levure sèche vaut environ dix fois plus. Ces deux lignes sont `ACTIF` sur la foi du
prix, et leur note porte le raisonnement.

L'inverse ne marche pas — un prix compatible ne prouve rien. Il ne sert qu'à écarter.

## Ce que le référentiel ne couvre pas

Certains achats récurrents n'ont aucune matière correspondante, et ce n'est pas un oubli
de rattachement : `GROS SEL TRAD SAC 10KG` (84,00 € sur six mois) n'est pas du sel fin,
la granulométrie et l'usage diffèrent. Le référentiel ne porte que `MATP-SELS-FIN`.

Y rattacher le gros sel ferait entrer un prix juste sur une matière fausse.
