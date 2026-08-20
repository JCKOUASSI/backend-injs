"""Badgeage QR côté porteur (étudiant, formateur, encadrant)."""
from __future__ import annotations

from django.db.models import Q
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.faculty.models import Teacher
from apps.students.models import Student

from ..models import Pointage, Seance
from ..serializers import ScanRequestSerializer
from ..services import presence as presence_service


class BadgeViewSet(viewsets.ViewSet):
    """Scan, statut et heartbeat du badgeage mobile/web."""

    # Chaque porteur badge pour lui-même : la seule exigence est d'être authentifié.
    permission_module = None

    @action(detail=False, methods=['post'])
    def scan(self, request):
        serializer = ScanRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        donnees = serializer.validated_data
        try:
            resultat = presence_service.scanner(
                token_value=donnees['token'],
                user=request.user,
                device_id=donnees.get('device_id', ''),
                latitude=donnees.get('latitude'),
                longitude=donnees.get('longitude'),
                accuracy_m=donnees.get('accuracy_m'),
            )
        except presence_service.BadgeageRefuse as erreur:
            return Response({'detail': str(erreur)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(resultat)

    @action(detail=False, methods=['get'])
    def statut(self, request):
        """Séances ouvertes badgeables et état du pointage de l'utilisateur."""
        aujourdhui = timezone.localdate()
        etudiant = Student.objects.filter(user=request.user).first()
        enseignant = Teacher.objects.filter(user=request.user).first()

        ouvertes = Seance.objects.filter(statut='en_cours', date=aujourdhui).select_related(
            'course', 'room', 'promotion',
        )
        if etudiant is not None:
            groupes = list(etudiant.groupes_pedagogiques.values_list('groupe_id', flat=True))
            seances = ouvertes.filter(promotion_id=etudiant.promotion_id).filter(
                Q(groupe__isnull=True) | Q(groupe_id__in=groupes),
            )
            filtre_pointage = Q(student=etudiant)
            profil = 'etudiant'
        elif enseignant is not None:
            seances = ouvertes.filter(
                Q(teacher_id=enseignant.id) | Q(supervisor_id=enseignant.id),
            )
            filtre_pointage = Q(teacher=enseignant)
            profil = 'enseignant'
        else:
            return Response(
                {'detail': 'Aucun profil étudiant ou enseignant rattaché à ce compte.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        seances = list(seances.distinct())
        pointages = {
            pointage.seance_id: pointage
            for pointage in Pointage.objects.filter(filtre_pointage, seance__in=seances)
        }

        return Response({
            'profil': profil,
            'date': aujourdhui.isoformat(),
            'seances': [
                {
                    'id': str(seance.id),
                    'course_code': seance.course.code,
                    'course_name': seance.course.name,
                    'promotion_name': seance.promotion.name,
                    'room_code': seance.room.code if seance.room_id else None,
                    'heure_debut': seance.heure_debut.strftime('%H:%M'),
                    'heure_fin': seance.heure_fin.strftime('%H:%M'),
                    'deja_badge': bool(pointages.get(seance.id) and pointages[seance.id].entree_at),
                    'sortie_faite': bool(pointages.get(seance.id) and pointages[seance.id].sortie_at),
                    'statut_pointage': pointages[seance.id].statut if seance.id in pointages else None,
                }
                for seance in seances
            ],
        })

    @action(detail=False, methods=['post'])
    def heartbeat(self, request):
        """Signal de présence périodique avec position (contrôle du géofence)."""
        pointage_id = request.data.get('pointage')
        pointage = Pointage.objects.filter(pk=pointage_id).select_related('seance__room').first()
        if pointage is None:
            return Response({'detail': 'Pointage introuvable.'}, status=status.HTTP_404_NOT_FOUND)

        latitude = request.data.get('latitude')
        longitude = request.data.get('longitude')
        pointage.last_heartbeat_at = timezone.now()
        if latitude is not None and longitude is not None:
            pointage.latitude, pointage.longitude = latitude, longitude
            try:
                presence_service.verifier_geofence(
                    pointage.seance, latitude, longitude, request.data.get('accuracy_m'),
                )
            except presence_service.BadgeageRefuse:
                pointage.outside_geofence_count += 1
        pointage.save(update_fields=[
            'last_heartbeat_at', 'latitude', 'longitude', 'outside_geofence_count', 'updated_at',
        ])
        return Response({
            'ok': True,
            'outside_geofence_count': pointage.outside_geofence_count,
        })

    @action(detail=False, methods=['get'], url_path='mon-historique')
    def mon_historique(self, request):
        etudiant = Student.objects.filter(user=request.user).first()
        enseignant = Teacher.objects.filter(user=request.user).first()
        queryset = Pointage.objects.select_related(
            'seance', 'seance__course', 'seance__room',
        ).order_by('-seance__date', '-seance__heure_debut')

        if etudiant is not None:
            queryset = queryset.filter(student=etudiant)
        elif enseignant is not None:
            queryset = queryset.filter(teacher=enseignant)
        else:
            return Response({'results': [], 'count': 0})

        queryset = queryset[:200]
        return Response({
            'count': len(queryset),
            'results': [
                {
                    'id': str(item.id),
                    'date': item.seance.date.isoformat(),
                    'course_code': item.seance.course.code,
                    'heure_debut': item.seance.heure_debut.strftime('%H:%M'),
                    'heure_fin': item.seance.heure_fin.strftime('%H:%M'),
                    'room_code': item.seance.room.code if item.seance.room_id else None,
                    'statut': item.statut,
                    'statut_display': item.get_statut_display(),
                    'entree_at': item.entree_at.isoformat() if item.entree_at else None,
                    'sortie_at': item.sortie_at.isoformat() if item.sortie_at else None,
                    'duree_minutes': item.duree_minutes,
                }
                for item in queryset
            ],
        })
