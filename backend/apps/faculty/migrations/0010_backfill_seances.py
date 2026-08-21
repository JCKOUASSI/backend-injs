"""Convertit l'existant en séances datées, sans rien supprimer.

Chaque AttendanceSession devient une Seance, et toute présence rattachée à un
couple (créneau, date) sans session ouverte obtient elle aussi sa séance, afin
qu'aucune présence historique ne reste orpheline.
"""
from django.db import migrations
from django.utils import timezone


def backfill_seances(apps, schema_editor):
    Schedule = apps.get_model('faculty', 'Schedule')
    AttendanceSession = apps.get_model('faculty', 'AttendanceSession')
    Attendance = apps.get_model('faculty', 'Attendance')
    StaffAttendance = apps.get_model('faculty', 'StaffAttendance')
    Seance = apps.get_model('faculty', 'Seance')

    schedules = {
        schedule.id: schedule
        for schedule in Schedule.objects.select_related('assignment')
    }
    if not schedules:
        return

    today = timezone.localdate()
    # Les séances déjà présentes sont réutilisées : la reprise peut être rejouée
    # sans jamais créer de doublon.
    seances = {
        (seance.schedule_id, seance.date): seance
        for seance in Seance.objects.filter(schedule__isnull=False)
    }

    def ensure_seance(schedule, day, session=None):
        key = (schedule.id, day)
        existing = seances.get(key)
        if existing is not None:
            return existing

        assignment = schedule.assignment
        seance = Seance(
            schedule=schedule,
            course_id=assignment.course_id,
            promotion_id=assignment.promotion_id,
            teacher_id=assignment.teacher_id,
            supervisor_id=schedule.supervisor_id or assignment.supervisor_id,
            room_id=schedule.room_id,
            session_kind=schedule.session_kind,
            date=day,
            start_time=schedule.start_time,
            end_time=schedule.end_time,
            # Une séance passée est terminée ; une séance à venir était déjà
            # opposable aux étudiants, donc publiée.
            status='done' if day < today else 'published',
            is_active=schedule.is_active,
        )
        if session is not None:
            seance.is_active = session.is_active
            seance.created_by_id = session.created_by_id
            seance.teacher_checked_in = session.teacher_checked_in
            seance.teacher_checked_in_at = session.teacher_checked_in_at
            seance.teacher_checked_in_by_id = session.teacher_checked_in_by_id
            seance.supervisor_checked_in = session.supervisor_checked_in
            seance.supervisor_checked_in_at = session.supervisor_checked_in_at
            seance.supervisor_checked_in_by_id = session.supervisor_checked_in_by_id
        seance.save()
        seances[key] = seance
        return seance

    for session in AttendanceSession.objects.all().iterator():
        schedule = schedules.get(session.schedule_id)
        if schedule is not None:
            ensure_seance(schedule, session.session_date, session)

    orphans = set(Attendance.objects.values_list('schedule_id', 'date'))
    orphans |= set(StaffAttendance.objects.values_list('schedule_id', 'date'))
    for schedule_id, day in orphans:
        schedule = schedules.get(schedule_id)
        if schedule is not None:
            ensure_seance(schedule, day)

    for (schedule_id, day), seance in seances.items():
        Attendance.objects.filter(schedule_id=schedule_id, date=day).update(seance=seance)
        StaffAttendance.objects.filter(schedule_id=schedule_id, date=day).update(seance=seance)


def drop_seances(apps, schema_editor):
    Attendance = apps.get_model('faculty', 'Attendance')
    StaffAttendance = apps.get_model('faculty', 'StaffAttendance')
    Seance = apps.get_model('faculty', 'Seance')

    Attendance.objects.update(seance=None)
    StaffAttendance.objects.update(seance=None)
    Seance.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('faculty', '0009_seance_attendance_seance_staffattendance_seance_and_more'),
    ]

    operations = [
        migrations.RunPython(backfill_seances, drop_seances),
    ]
