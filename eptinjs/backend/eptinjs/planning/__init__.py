"""Moteur de planification EPT-INJS.

Portage de ``apps/seances/planning`` de l'application eptcpafefinal : allocateur
glouton jour par jour, avec index d'occupation global (salles, enseignants,
auditoires) et scoring pondéré des salles.
"""
from .conflicts import detecter_conflits
from .engine import GenerationResult, generer_planning

__all__ = ['GenerationResult', 'detecter_conflits', 'generer_planning']
