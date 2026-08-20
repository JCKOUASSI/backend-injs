"""Module produit « Cours (ECUE) ».

Façade de lecture sur ``academics.Course`` × ``Promotion``, enrichie des
programmes, des séances de toutes les périodes et des présences.
"""
from __future__ import annotations

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from ..services.catalog import construire_catalogue
from ..services.offering import get_offering


class CoursViewSet(viewsets.ViewSet):
    """Catalogue et fiche détaillée des offres d'enseignement."""

    permission_module = 'academics'

    def list(self, request):
        return Response(construire_catalogue(request.query_params))

    @action(detail=False, methods=['get'])
    def offering(self, request):
        """Fiche d'une offre : ``?id=<course>:<promotion>`` ou ``?course=&promotion=``."""
        donnees = get_offering(request.query_params)
        if donnees is None:
            return Response(
                {'detail': 'Offre introuvable. Vérifiez l’ECUE et la promotion.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(donnees)
