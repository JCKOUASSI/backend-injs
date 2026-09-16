#!/usr/bin/env python3
"""
Régénère les fixtures de catalogue utilisées par les tests du menu RBAC.

Deux fixtures sont produites côté frontend (`src/menu/__fixtures__/`) :

* `catalogue-curp.json`       — les codes `module.ressource.action` réellement
                                présents en base (table
                                `habilitations_permissionmetier`) ;
* `catalogue-capacites.json`  — les couples module/action du contrat legacy
                                `GET /auth/capabilities/`
                                (`authentication/capabilities.py`).

Les tests d'invariants du menu (`src/menu/arborescence.test.js`) vérifient que
chaque droit cité dans `src/menu/arborescence.js` existe dans l'un de ces deux
catalogues. Sans ce contrôle, un code inventé masquerait silencieusement une
entrée pour tous les comptes concernés.

Usage (depuis la racine du dépôt) :

    python3 arena/genere-catalogues-menu.py [--db backend/db.sqlite3]

Le script est **en lecture seule** : il n'écrit que les deux fichiers JSON et
ne touche ni à la base, ni au code applicatif.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sqlite3
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
CIBLE = RACINE / "frontend" / "src" / "menu" / "__fixtures__"
CAPACITIES = RACINE / "backend" / "authentication" / "capabilities.py"


def catalogue_curp(chemin_db: Path) -> dict:
    """Codes CURP présents en base, regroupés par module."""
    if not chemin_db.exists():
        sys.exit(f"Base introuvable : {chemin_db} (lancer d'abord les migrations).")
    connexion = sqlite3.connect(f"file:{chemin_db}?mode=ro", uri=True)
    try:
        lignes = list(connexion.execute(
            "SELECT module, ressource, action FROM habilitations_permissionmetier"
        ))
    finally:
        connexion.close()
    codes = sorted({".".join(ligne) for ligne in lignes})
    return {
        "genere_le": dt.date.today().isoformat(),
        "source": f"{chemin_db.relative_to(RACINE)} · table habilitations_permissionmetier",
        "regenerer": "python3 arena/genere-catalogues-menu.py",
        "nombre": len(codes),
        "modules": sorted({ligne[0] for ligne in lignes}),
        "codes": codes,
    }


def catalogue_capacites(chemin_py: Path) -> dict:
    """Couples module/action exposés par CAPACITES_DESCRIPTEURS."""
    if not chemin_py.exists():
        sys.exit(f"Fichier introuvable : {chemin_py}")
    source = chemin_py.read_text(encoding="utf-8")
    debut = source.index("CAPACITES_DESCRIPTEURS = {")
    profondeur = 0
    fin = debut
    for index in range(debut, len(source)):
        if source[index] == "{":
            profondeur += 1
        elif source[index] == "}":
            profondeur -= 1
            if profondeur == 0:
                fin = index + 1
                break
    bloc = source[debut:fin]
    modules = re.findall(r"^    '([a-z_]+)':\s*\{(.*?)^    \}", bloc, re.S | re.M)
    capacites = {
        module: sorted(set(re.findall(r"^        '([a-z_]+)':", corps, re.M)))
        for module, corps in modules
    }
    capacites = {cle: valeur for cle, valeur in capacites.items() if valeur}
    return {
        "genere_le": dt.date.today().isoformat(),
        "source": f"{chemin_py.relative_to(RACINE)} · CAPACITES_DESCRIPTEURS",
        "regenerer": "python3 arena/genere-catalogues-menu.py",
        "nombre_modules": len(capacites),
        "nombre_actions": sum(len(actions) for actions in capacites.values()),
        "capacites": capacites,
    }


def catalogue_endpoints(chemin_backend: Path) -> dict:
    """Motifs d'URL de l'API, tels que résolus par Django.

    Priorité au résolveur Django (`get_resolver`) : c'est la seule source qui
    inclut les routes enregistrées par les routers DRF et les `re_path`. À
    défaut d'environnement Django importable, un repli **textuel** lit les
    `path(...)` de `config/urls.py` et des `urls.py` d'applications — moins
    exhaustif, mais sans dépendance.

    Les convertisseurs (`<int:pk>`, `<str:code>`…) sont normalisés en `{}` pour
    que le frontend compare ses chemins après substitution des identifiants.
    """
    motifs = _endpoints_via_django(chemin_backend)
    mode = "django"
    if not motifs:
        motifs = _endpoints_textuels(chemin_backend)
        mode = "texte"

    simples = []
    regexes = []
    for motif in sorted(motifs):
        if not motif.startswith("/"):
            motif = "/" + motif
        if any(c in motif for c in "^$*+?()[]|\\"):
            regexes.append(motif)
        else:
            simples.append(motif)
    return {
        "genere_le": dt.date.today().isoformat(),
        "source": "backend · résolveur d'URL Django" if mode == "django"
                  else "backend · lecture textuelle des urls.py (repli)",
        "mode": mode,
        "regenerer": "cd backend && USE_SQLITE=1 .venv/bin/python ../arena/genere-catalogues-menu.py",
        "nombre": len(simples) + len(regexes),
        "motifs": simples,
        "motifs_regex": regexes,
    }


def _normalise(brut: str) -> str:
    """Normalise un motif d'URL pour un usage côté frontend.

    * motif `path()`  : `<int:pk>` / `<pk>` → `{}` (un segment quelconque) ;
    * motif `re_path()`: réécriture de la syntaxe Python `(?P<nom>…)` en
      syntaxe JavaScript `(?<nom>…)`, la fixture étant consommée par les tests
      frontend via `new RegExp(...)`. Les deux formes ne sont jamais mélangées,
      sinon les groupes nommés seraient détruits par la normalisation.
    """
    # Les ancres `^`/`$` internes (issues de `re_path(r'^…/$')` concaténés sous
    # un préfixe) sont retirées : le frontend ancre lui-même ses expressions.
    if "(?P<" in brut or "^" in brut or "$" in brut:
        return brut.replace("(?P<", "(?<").replace("^", "").replace("$", "")
    out = re.sub(r"<[^<>]*?:[^<>]+>", "{}", brut)
    return re.sub(r"<[^<>]+>", "{}", out)


def _endpoints_via_django(chemin_backend: Path) -> set:
    try:
        import os
        import sys
        sys.path.insert(0, str(chemin_backend))
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
        os.environ.setdefault("USE_SQLITE", "1")
        import django  # noqa: PLC0415
        django.setup()
        from django.urls import get_resolver  # noqa: PLC0415
    except Exception:  # environnement backend indisponible → repli textuel
        return set()

    motifs = set()

    def marcher(resolver, prefixe=""):
        for motif in resolver.url_patterns:
            if hasattr(motif, "url_patterns"):
                marcher(motif, prefixe + str(motif.pattern))
            else:
                motifs.add(_normalise(prefixe + str(motif.pattern)))

    try:
        marcher(get_resolver())
    except Exception:
        return set()
    return {m for m in motifs if m.startswith("api/")}


def _endpoints_textuels(chemin_backend: Path) -> set:
    config = chemin_backend / "config" / "urls.py"
    if not config.exists():
        return set()
    montages = re.findall(r"path\(\s*'([^']*)'\s*,\s*include\(\s*'([\w.]+)'\s*\)",
                          config.read_text(encoding="utf-8"))
    motifs = set()
    for prefixe, module in montages:
        parties = module.split(".")
        dossier = chemin_backend / Path(*parties[:-1])
        chemin = dossier / f"{parties[-1]}.py"
        if not chemin.exists():
            continue
        for brut in re.findall(r"path\(\s*r?'([^']*)'", chemin.read_text(encoding="utf-8")):
            motifs.add(_normalise(prefixe + brut))
    return motifs


def ecrire(nom: str, contenu: dict) -> Path:
    CIBLE.mkdir(parents=True, exist_ok=True)
    chemin = CIBLE / nom
    chemin.write_text(json.dumps(contenu, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return chemin


def main() -> int:
    analyseur = argparse.ArgumentParser(description=__doc__)
    analyseur.add_argument("--db", default=str(RACINE / "backend" / "db.sqlite3"),
                           help="Base SQLite contenant le catalogue CURP.")
    arguments = analyseur.parse_args()

    curp = catalogue_curp(Path(arguments.db))
    capacites = catalogue_capacites(CAPACITIES)
    endpoints = catalogue_endpoints(RACINE / "backend")

    chemin_curp = ecrire("catalogue-curp.json", curp)
    chemin_caps = ecrire("catalogue-capacites.json", capacites)
    chem_eps = ecrire("catalogue-endpoints.json", endpoints)

    print(f"{chemin_curp.relative_to(RACINE)} : {curp['nombre']} codes, "
          f"{len(curp['modules'])} modules")
    print(f"{chemin_caps.relative_to(RACINE)} : {capacites['nombre_modules']} modules, "
          f"{capacites['nombre_actions']} actions")
    print(f"{chem_eps.relative_to(RACINE)} : {endpoints['nombre']} motifs d'URL")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
