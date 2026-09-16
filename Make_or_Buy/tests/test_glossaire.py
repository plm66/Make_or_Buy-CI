"""Invariants du glossaire de référence.

Un glossaire que rien ne vérifie diverge du code en quelques semaines, et devient pire
qu'absent : on le consulte et il ment. Ces tests le tiennent attaché aux vocabulaires
réellement employés.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GLOSSAIRE = (ROOT / "docs" / "GLOSSAIRE.md").read_text(encoding="utf-8")


def _lire(*parts):
    return json.loads(ROOT.joinpath(*parts).read_text(encoding="utf-8"))


DOCTRINE = _lire("doctrine", "doctrine.json")
GABARITS = _lire("params", "operation_templates.json")


def test_chaque_degre_de_transformation_est_defini():
    """`params/operation_templates.json` donne les gestes restants par degré. Un degré
    employé et non défini laisse chacun deviner ce qu'il recouvre — et c'est exactement
    l'ambiguïté de PRET_A_SERVIR, qui dit « servir » et compte « transformer ».
    """
    for code in GABARITS["templates"]:
        assert f"`{code}`" in GLOSSAIRE, code


def test_chaque_mode_de_decision_est_defini():
    """MAKE, BUY, HYBRID sont les trois sorties du moteur. Elles ne peuvent pas être
    approximatives."""
    for code in DOCTRINE["decision_modes"]:
        assert f"`{code}`" in GLOSSAIRE, code


def test_chaque_classe_de_produit_est_definie():
    """Les classes de la doctrine sont des termes propres au dépôt : aucun référent
    extérieur ne viendra les définir à notre place."""
    for code in DOCTRINE["product_classes"]:
        assert code in GLOSSAIRE, code


def test_les_termes_inventes_sont_declares_comme_tels():
    """Un terme sans référent extérieur n'a d'autorité que la nôtre. Les lister ensemble
    évite qu'on les prenne pour du vocabulaire de métier — et rappelle qu'ils se
    renégocient, contrairement à `par-baked` ou `landed cost`.
    """
    section = GLOSSAIRE.split("## Termes créés par le dépôt")[-1]
    for code in DOCTRINE["product_classes"]:
        assert code in section, code
    assert "SELECTED_EFFECTIVE_PRODUCT_COST" in section


def test_les_quatre_notions_de_cout_sont_distinguees():
    """G002 est née de la confusion entre deux d'entre elles. Le glossaire doit porter les
    quatre séparément, sans quoi il reproduit la faute qu'il documente.
    """
    for code in ("material_cost_eur", "avoidable_cost_eur", "landed_cost_eur",
                 "SELECTED_EFFECTIVE_PRODUCT_COST"):
        assert code in GLOSSAIRE, code


def test_chaque_entree_porte_un_referent_anglais():
    """C'est la raison d'être du document : sans référent, on réinvente un nom à chaque
    passe. Les tableaux de vocabulaire portent tous une colonne « référent anglais ».
    """
    assert GLOSSAIRE.count("référent anglais") >= 6


if __name__ == "__main__":
    for nom, fn in sorted(globals().items()):
        if nom.startswith("test_"):
            fn()
            print(f"OK  {nom}")
