"""EPT-INJS — module de gestion des emplois du temps, présences et badgeages.

Portage de l'application « eptcpafefinal » adaptée au référentiel LMD d'INJS :
la séance datée (``Seance``) remplace le créneau hebdomadaire ``faculty.Schedule``
et sert simultanément d'unité d'emploi du temps et de séance de badgeage.
"""

default_app_config = 'eptinjs.apps.EptInjsConfig'
