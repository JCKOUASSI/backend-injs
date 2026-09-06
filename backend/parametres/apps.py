from django.apps import AppConfig


class ParametresConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'parametres'
    verbose_name = 'Paramètres'

    def ready(self):
        """Enregistre les signaux lors du chargement de l'app."""
        # Historique géré directement dans le serializer de mise à jour.
        pass
