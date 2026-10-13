"""Archivage réversible du corpus CPFAE / SYGEP (aucune suppression).

- Référentiel : toute RefFormation dont l'intitulé porte une marque CPFAE/SYGEP
  passe en périmètre LEGACY et inactive (ce qui l'exclut de l'API INJS).
- Comptes : tout utilisateur dont l'identifiant ou l'e-mail porte une marque
  CPFAE/SYGEP est désactivé (is_active=False).

Les valeurs d'origine sont copiées dans ArchiveDonneeLegacy. La migration inverse
restitue ces valeurs puis supprime uniquement les snapshots créés ici.
"""

from django.db import migrations, models
from django.db.models import Q

MARQUES = ('cpfae', 'sygep')


def _q_marques(champs):
    q = Q()
    for champ in champs:
        for marque in MARQUES:
            q |= Q(**{f'{champ}__icontains': marque})
    return q


def archiver(apps, schema_editor):
    Archive = apps.get_model('core', 'ArchiveDonneeLegacy')
    RefFormation = apps.get_model('formations', 'RefFormation')
    User = apps.get_model('authentication', 'User')

    for rf in RefFormation.objects.filter(_q_marques(['intitule'])):
        if rf.perimetre == 'LEGACY' and not rf.actif:
            continue
        Archive.objects.create(
            modele='formations.RefFormation', objet_pk=str(rf.pk),
            valeurs_avant={'perimetre': rf.perimetre, 'actif': rf.actif},
        )
        RefFormation.objects.filter(pk=rf.pk).update(perimetre='LEGACY', actif=False)

    for user in User.objects.filter(_q_marques(['username', 'email'])):
        if not user.is_active:
            continue
        Archive.objects.create(
            modele='authentication.User', objet_pk=str(user.pk),
            valeurs_avant={'is_active': True},
        )
        User.objects.filter(pk=user.pk).update(is_active=False)


def restaurer(apps, schema_editor):
    Archive = apps.get_model('core', 'ArchiveDonneeLegacy')
    RefFormation = apps.get_model('formations', 'RefFormation')
    User = apps.get_model('authentication', 'User')
    cibles = {'formations.RefFormation': RefFormation, 'authentication.User': User}

    for snap in Archive.objects.all():
        cible = cibles.get(snap.modele)
        if cible is not None:
            cible.objects.filter(pk=snap.objet_pk).update(**snap.valeurs_avant)
    Archive.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
        ('authentication', '0024_contrainte_role_canonique'),
        ('formations', '0098_alter_help_text_legacy'),
    ]

    operations = [
        migrations.CreateModel(
            name='ArchiveDonneeLegacy',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('modele', models.CharField(max_length=100)),
                ('objet_pk', models.CharField(max_length=64)),
                ('valeurs_avant', models.JSONField(default=dict)),
                ('cree_le', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Donnée legacy archivée',
                'verbose_name_plural': 'Données legacy archivées',
                'indexes': [models.Index(fields=['modele', 'objet_pk'], name='core_archiv_modele_723b97_idx')],
            },
        ),
        migrations.RunPython(archiver, restaurer),
    ]
