# Taxonomie produits

La taxonomie fait autorité dans **`data/generics/SCHEMA.md`** : familles de niveau 1,
catégories de niveau 2, règle de clé et attributs transverses.

L'état du référentiel — nombre de SKU, de génériques, de génériques inter-fournisseurs —
se lit en le calculant :

```bash
python3 generics_tool.py rebuild
```

Ce fichier ne recopie ni l'un ni l'autre, délibérément. La version précédente était une
copie de `SCHEMA.md` avec un tableau de statut saisi à la main ; elle portait trois
chiffres faux le lendemain de son écriture — 52 génériques au lieu de 47, la famille PAIN
annoncée non collectée alors que Bridor en avait livré 20, et un périmètre de pilote
restreint qui ne valait que pour le second catalogue.

Un chiffre recopié dans un Markdown est un chiffre faux en différé.
