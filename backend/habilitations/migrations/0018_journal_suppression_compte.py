"""Journal : autoriser la mise à NULL des clés étrangères lors d'une suppression.

Défaut corrigé : la fonction de 0002 refusait tout ``UPDATE``. Or Django met
les clés étrangères du journal à NULL (``on_delete=SET_NULL``) lorsqu'un compte
ou un utilisateur est supprimé ; la suppression échouait donc sur PostgreSQL
dès qu'un compte avait des événements au journal (constaté par sonde).

Nouvelle règle, toujours appliquée par la base :
- toute modification d'un champ de contenu (motif, valeurs, empreinte, horodatage…)
  est refusée ;
- une clé étrangère ne peut être remise qu'à NULL (jamais redirigée vers une autre
  valeur) ;
- toute suppression d'événement est refusée.

L'identité de l'acteur reste lisible dans ``acteur_label``. Migration
réversible : la fonction de 0002 est restaurée en arrière.
"""
from django.db import migrations

NOM_TABLE = 'habilitations_journalhabilitation'

FONCTION_NOUVELLE = """
CREATE OR REPLACE FUNCTION habilitations_journal_immuable()
RETURNS trigger AS $$
BEGIN
    IF TG_OP = 'UPDATE'
       AND NEW.id IS NOT DISTINCT FROM OLD.id
       AND NEW.numero IS NOT DISTINCT FROM OLD.numero
       AND NEW.horodatage IS NOT DISTINCT FROM OLD.horodatage
       AND NEW.acteur_label IS NOT DISTINCT FROM OLD.acteur_label
       AND NEW.type_evenement IS NOT DISTINCT FROM OLD.type_evenement
       AND NEW.object_id IS NOT DISTINCT FROM OLD.object_id
       AND NEW.objet_type IS NOT DISTINCT FROM OLD.objet_type
       AND NEW.objet_libelle IS NOT DISTINCT FROM OLD.objet_libelle
       AND NEW.ancienne_valeur IS NOT DISTINCT FROM OLD.ancienne_valeur
       AND NEW.nouvelle_valeur IS NOT DISTINCT FROM OLD.nouvelle_valeur
       AND NEW.motif IS NOT DISTINCT FROM OLD.motif
       AND NEW.adresse_ip IS NOT DISTINCT FROM OLD.adresse_ip
       AND NEW.agent_utilisateur IS NOT DISTINCT FROM OLD.agent_utilisateur
       AND NEW.correlation_id IS NOT DISTINCT FROM OLD.correlation_id
       AND NEW.empreinte_precedente IS NOT DISTINCT FROM OLD.empreinte_precedente
       AND NEW.empreinte IS NOT DISTINCT FROM OLD.empreinte
       AND (NEW.acteur_id IS NULL OR NEW.acteur_id IS NOT DISTINCT FROM OLD.acteur_id)
       AND (NEW.compte_concerne_id IS NULL OR NEW.compte_concerne_id IS NOT DISTINCT FROM OLD.compte_concerne_id)
       AND (NEW.personne_concernee_id IS NULL OR NEW.personne_concernee_id IS NOT DISTINCT FROM OLD.personne_concernee_id)
       AND (NEW.content_type_id IS NULL OR NEW.content_type_id IS NOT DISTINCT FROM OLD.content_type_id)
       AND (NEW.delegation_source_id IS NULL OR NEW.delegation_source_id IS NOT DISTINCT FROM OLD.delegation_source_id)
    THEN
        RETURN NEW;
    END IF;
    RAISE EXCEPTION
        'Le journal des habilitations est append-only : operation % refusee',
        TG_OP;
END;
$$ LANGUAGE plpgsql;
"""

# Fonction d'origine (migration 0002), restaurée au retour arrière.
FONCTION_ORIGINE = """
CREATE OR REPLACE FUNCTION habilitations_journal_immuable()
RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION
        'Le journal des habilitations est append-only : operation % refusee',
        TG_OP;
END;
$$ LANGUAGE plpgsql;
"""


class _SeulementPostgresSQL(migrations.RunSQL):
    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        if schema_editor.connection.vendor == 'postgresql':
            super().database_forwards(app_label, schema_editor, from_state, to_state)

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        if schema_editor.connection.vendor == 'postgresql':
            super().database_backwards(app_label, schema_editor, from_state, to_state)


class Migration(migrations.Migration):

    dependencies = [
        ('habilitations', '0017_double_approbation_delegation'),
    ]

    operations = [
        _SeulementPostgresSQL(sql=FONCTION_NOUVELLE, reverse_sql=FONCTION_ORIGINE),
    ]
