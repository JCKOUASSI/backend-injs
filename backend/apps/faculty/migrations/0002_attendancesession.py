import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('faculty', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AttendanceSession',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('session_date', models.DateField(db_index=True)),
                ('is_active', models.BooleanField(db_index=True, default=True)),
                ('teacher_checked_in', models.BooleanField(default=False)),
                ('teacher_checked_in_at', models.DateTimeField(blank=True, null=True)),
                ('created_by', models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='opened_attendance_sessions',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('schedule', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='attendance_sessions',
                    to='faculty.schedule',
                )),
                ('teacher_checked_in_by', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='checked_in_sessions',
                    to='faculty.teacher',
                )),
            ],
            options={
                'ordering': ['-session_date', 'schedule__start_time'],
                'unique_together': {('schedule', 'session_date')},
            },
        ),
    ]
