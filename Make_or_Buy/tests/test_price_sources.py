"""Invariants de la couche de capture de prix fournisseur (delta v0.3.0).

Cette couche observe des prix affichés. Elle ne décide rien. Les tests protègent les
deux frontières qui la rendent inoffensive : elle ne peut pas produire un coût effectif,
et elle ne peut pas atteindre une source sous compte tant que le compte n'existe pas.
"""
import json
import unicodedata
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _lire(*parts):
    return json.loads((ROOT.joinpath(*parts)).read_text(encoding="utf-8"))


REGISTRE = _lire("data", "supplier_price_sources", "supplier_price_sources.registry.json")
JOBS = _lire("agents", "supplier_price_crawl_jobs.json")
COMPTES = _lire("agents", "future_account_sources.json")
SCHEMA = _lire("schemas", "supplier_price_observation.schema.json")
FICHES = _lire("data", "suppliers", "index.json")


def _plie(nom):
    """Nom fournisseur réduit à sa forme comparable : sans accent, sans ponctuation."""
    sans_accent = "".join(c for c in unicodedata.normalize("NFKD", nom)
                          if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "_", sans_accent.lower()).strip("_")


def test_un_fournisseur_ne_porte_quun_seul_identifiant():
    """Le delta est arrivé avec son propre vocabulaire (METRO_FR) alors que les fiches
    portaient déjà metro_france. Deux identités pour un fournisseur, et plus aucune
    jointure ne tient entre un prix observé et le fournisseur homologué qui le pratique.
    Les fiches font foi ; cette règle empêche la reformation du doublon.
    """
    par_nom = {}
    for f in (ROOT / "data" / "suppliers").glob("*.json"):
        fiche = json.loads(f.read_text(encoding="utf-8"))
        if "supplier_id" in fiche and fiche.get("name"):
            par_nom[_plie(fiche["name"])] = fiche["supplier_id"]
    for s in REGISTRE["sources"]:
        attendu = par_nom.get(_plie(s["name"]))
        if attendu is not None:
            assert s["supplier_id"] == attendu, (s["name"], s["supplier_id"], attendu)


def test_aucune_capture_authentifiee_nest_active():
    """Les credentials ne sont jamais au dépôt. Un job AUTHENTICATED_WEB actif
    réclamerait un secret que rien ici ne peut fournir : il échouerait, ou pire,
    inviterait à déposer le secret pour le faire passer.
    """
    for j in JOBS["jobs"]:
        if j["mode"] == "AUTHENTICATED_WEB":
            assert j["enabled"] is False, j["job_id"]
            assert j.get("activation_condition"), j["job_id"]


def test_aucun_credential_nest_stocke_au_depot():
    """Politique déclarée par le delta lui-même. Un identifiant de compte déposé ici
    serait lisible par quiconque cloner le dépôt, et le resterait dans l'historique.
    """
    interdits = re.compile(r"password|passwd|secret|token|api_?key|credential|bearer|cookie",
                           re.I)
    # Une politique enonce (phrase, booleen) ; un credential est une chaine opaque.
    # C'est la forme de la valeur qui tranche, pas le nom du champ : le delta a le
    # droit de dire "les credentials ne sont jamais stockes", pas d'en porter un.
    # Melange de casses et de chiffres sur 24+ caracteres : ni un identifiant
    # snake_case, ni une enum. Un jeton, lui, a cette forme.
    opaque = re.compile(r"^(?:bearer\s|basic\s|sk-|ghp_|eyJ)"
                        r"|^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)[A-Za-z0-9+/_-]{24,}={0,2}$")
    def parcours(o, chemin=""):
        if isinstance(o, dict):
            for k, v in o.items():
                assert not (interdits.search(k) and isinstance(v, str) and " " not in v), \
                    f"{chemin}.{k}"
                parcours(v, f"{chemin}.{k}")
        elif isinstance(o, list):
            for i, v in enumerate(o):
                parcours(v, f"{chemin}[{i}]")
        elif isinstance(o, str) and not o.startswith("http"):
            assert not opaque.match(o), f"{chemin} porte une valeur de forme secrete"
    for nom, doc in (("registre", REGISTRE), ("jobs", JOBS), ("comptes", COMPTES)):
        parcours(doc, nom)


def test_une_observation_ne_peut_pas_exprimer_un_cout_effectif():
    """G002 au niveau de la donnée. Le défaut d'origine tenait à un nom de champ qui
    invitait la confusion. Ici la capture ne doit même pas disposer du vocabulaire :
    pas de champ évitable/effectif/sélectionné, et additionalProperties fermé pour
    qu'aucun n'apparaisse plus tard.
    """
    assert SCHEMA["additionalProperties"] is False
    for champ in SCHEMA["properties"]:
        assert not re.search(r"avoidable|effective|selected", champ), champ


def test_la_base_de_taxe_est_toujours_portee():
    """La politique impose de stocker UNKNOWN plutôt que d'inférer HT ou TTC. Champ
    absent et champ UNKNOWN diraient alors deux choses différentes pour un même fait.
    """
    assert "tax_basis" in SCHEMA["required"]
    assert "UNKNOWN" in SCHEMA["properties"]["tax_basis"]["enum"]


def test_tout_job_vise_une_source_enregistree():
    """Un job qui crawle un fournisseur absent du registre produirait des observations
    qu'aucune fiche ne pourrait qualifier.
    """
    sources = {s["supplier_id"] for s in REGISTRE["sources"]}
    for j in JOBS["jobs"]:
        assert j["supplier_id"] in sources, j["job_id"]
    for c in COMPTES["activation_order"]:
        assert c["supplier_id"] in sources, c["supplier_id"]


def test_une_source_sous_compte_na_pas_de_job_actif():
    """Cohérence entre l'état déclaré de la source et ce que les jobs tentent
    réellement. Les deux doivent dire la même chose, sinon l'un des deux ment.
    """
    gated = {s["supplier_id"] for s in REGISTRE["sources"]
             if s["source_status"] == "ACCOUNT_GATED_PENDING"}
    for j in JOBS["jobs"]:
        if j["supplier_id"] in gated:
            assert j["enabled"] is False, j["job_id"]


if __name__ == "__main__":
    for nom, fn in sorted(globals().items()):
        if nom.startswith("test_"):
            fn()
            print(f"OK  {nom}")
