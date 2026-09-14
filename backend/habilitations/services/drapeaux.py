"""Lecture des drapeaux U5 (cycle de vie, provisionnement, imports).

Chaque automatisme possède son interrupteur indépendant, livré ÉTEINT. Un
drapeau inconnu, inactif ou absent est toujours considéré faux (c'est la
sémantique de :func:`parametres.flags.is_enabled`, sans passe-droit
super-utilisateur) : les automatismes s'éteignent donc immédiatement, sans
redéploiement, par le seul écran Paramètres.
"""
from parametres.flags import is_enabled

#: Drapeau maître : doit être ouvert EN PLUS de la sonde concernée.
MAITRE_PROVISIONNEMENT = 'flag.curp_provisionnement_auto'

#: Déclencheurs événementiels individuels (clé → code PropositionProvisionnement.Declencheur).
DRAPEAUX_SONDES = {
    'ADMISSION': 'flag.curp_declencheur_admission',
    'INSCRIPTION': 'flag.curp_declencheur_inscription',
    'RECRUTEMENT': 'flag.curp_declencheur_recrutement',
    'AFFECTATION_ENSEIGNANT': 'flag.curp_declencheur_affectation_enseignant',
    'FIN_RELATION': 'flag.curp_declencheur_fin_relation',
    'JURY': 'flag.curp_declencheur_jury',
}

DRAPEAU_INACTIVITE = 'flag.curp_suspension_inactivite'
DRAPEAU_EXPIRATION = 'flag.curp_expiration_auto'
DRAPEAU_IMPORT_MASSE = 'flag.curp_import_masse'


def sonde_active(code_declencheur, user=None):
    """Une sonde n'est active que si le maître ET son drapeau sont ouverts."""
    drapeau = DRAPEAUX_SONDES.get(code_declencheur)
    if not drapeau:
        return False
    return is_enabled(MAITRE_PROVISIONNEMENT, user) and is_enabled(drapeau, user)


def inactivite_active():
    return is_enabled(DRAPEAU_INACTIVITE)


def expiration_active():
    return is_enabled(DRAPEAU_EXPIRATION)


def import_masse_actif():
    return is_enabled(DRAPEAU_IMPORT_MASSE)
