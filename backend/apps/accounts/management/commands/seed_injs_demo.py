"""Seed INJS demo data: groupes Django, permissions, institution, 31 demo accounts."""
from datetime import date, time, timedelta
from decimal import Decimal
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.rbac import sync_module_permissions, module_permissions_queryset, parse_codename

DEMO_PASSWORD = 'Demo@INJS2026!'

ROLES = [
    ('super_admin', 'Super Administrateur', 0),
    ('directeur_general', 'Directeur Général', 1),
    ('directeur_academique', 'Directeur Académique', 1),
    ('directeur_financier', 'Directeur Financier', 1),
    ('directeur_general_adjoint', 'Directeur Général Adjoint', 1),
    ('secretaire_general', 'Secrétaire Général', 1),
    ('conseil_administration', "Conseil d'Administration", 1),
    ('directeur_enseps', 'Directeur ENSEPS', 1),
    ('directeur_ensep', 'Directeur ENSEP', 1),
    ('directeur_rh', 'Directeur RH', 1),
    ('comptable', 'Comptable', 1),
    ('responsable_patrimoine', 'Responsable Patrimoine', 2),
    ('responsable_maintenance', 'Responsable Maintenance', 2),
    ('chef_departement', 'Chef Département', 2),
    ('responsable_filiere', 'Responsable Filière', 2),
    ('responsable_scolarite', 'Responsable Scolarité', 2),
    ('chercheur', 'Chercheur', 3),
    ('enseignant', 'Enseignant', 3),
    ('jury', 'Jury', 3),
    ('examinateur', 'Examinateur', 3),
    ('delegue', 'Délégué', 4),
    ('resident', 'Résident', 4),
    ('etudiant', 'Étudiant', 4),
]

DEMO_USERS = [
    ('dga@demo.injs.ci', 'Directeur', 'Général Adjoint', 'directeur_general_adjoint'),
    ('sg@demo.injs.ci', 'Secrétaire', 'Général', 'secretaire_general'),
    ('ca@demo.injs.ci', 'Conseil', 'Administration', 'conseil_administration'),
    ('enseps@demo.injs.ci', 'Directeur', 'ENSEPS', 'directeur_enseps'),
    ('ensep@demo.injs.ci', 'Directeur', 'ENSEP', 'directeur_ensep'),
    ('drh@demo.injs.ci', 'Directeur', 'RH', 'directeur_rh'),
    ('comptable@demo.injs.ci', 'Comptable', 'INJS', 'comptable'),
    ('patrimoine@demo.injs.ci', 'Responsable', 'Patrimoine', 'responsable_patrimoine'),
    ('maintenance@demo.injs.ci', 'Responsable', 'Maintenance', 'responsable_maintenance'),
    ('chercheur@demo.injs.ci', 'Chercheur', 'INJS', 'chercheur'),
    ('delegue@demo.injs.ci', 'Délégué', 'Étudiant', 'delegue', True),
    ('resident@demo.injs.ci', 'Résident', 'Étudiant', 'resident', True),
    ('dg@demo.injs.ci', 'Directeur', 'Général', 'directeur_general'),
    ('da@demo.injs.ci', 'Directeur', 'Académique', 'directeur_academique'),
    ('df@demo.injs.ci', 'Directeur', 'Financier', 'directeur_financier'),
    ('chef.staps@demo.injs.ci', 'Chef', 'STAPS', 'chef_departement'),
    ('resp.licence@demo.injs.ci', 'Resp.', 'Licence STAPS', 'responsable_filiere'),
    ('scolarite@demo.injs.ci', 'Scolarité', 'INJS', 'responsable_scolarite'),
    ('prof.martin@demo.injs.ci', 'Prof.', 'Martin', 'enseignant'),
    ('prof.kone@demo.injs.ci', 'Prof.', 'Koné', 'enseignant'),
    ('jury1@demo.injs.ci', 'Membre', 'Jury 1', 'jury'),
    ('exam1@demo.injs.ci', 'Examinateur', 'INJS', 'examinateur'),
    ('admin@demo.injs.ci', 'Super', 'Admin', 'super_admin', False, True),
    ('etudiant1@demo.injs.ci', 'Kouassi', 'Jean', 'etudiant', True),
    ('etudiant2@demo.injs.ci', 'Traoré', 'Aminata', 'etudiant', True),
    ('etudiant3@demo.injs.ci', 'Diallo', 'Moussa', 'etudiant', True),
    ('etudiant4@demo.injs.ci', 'Bamba', 'Fatou', 'etudiant', True),
    ('etudiant5@demo.injs.ci', 'Yao', 'Koffi', 'etudiant', True),
    ('etudiant6@demo.injs.ci', 'Coulibaly', 'Aya', 'etudiant', True),
    ('etudiant7@demo.injs.ci', 'N\'Guessan', 'Eric', 'etudiant', True),
    ('etudiant8@demo.injs.ci', 'Ouattara', 'Mariam', 'etudiant', True),
]


class Command(BaseCommand):
    help = 'Seed INJS-LMD demo database with Django groups, permissions, and 31 demo accounts'

    @staticmethod
    def _filter_permissions(modules=None, actions=None):
        qs = module_permissions_queryset()
        if modules:
            qs = [p for p in qs if parse_codename(p.codename)[0] in modules]
        else:
            qs = list(qs)
        if actions:
            qs = [p for p in qs if parse_codename(p.codename)[1] in actions]
        return qs

    @transaction.atomic
    def handle(self, *args, **options):
        from apps.accounts.models import User, GroupProfile
        from apps.academics.models import (
            Institution, Department, Program, Promotion, AcademicYear,
            Semester, TeachingUnit, Course, ProgramCourse,
        )
        from apps.students.models import Student, Enrollment
        from apps.faculty.models import Teacher, Room
        from apps.exams.models import ExamSession, Evaluation
        from apps.finance.models import FeeType, StudentFee

        self.stdout.write('Creating permissions...')
        sync_module_permissions()
        all_perms = list(module_permissions_queryset())

        self.stdout.write('Creating Django groups...')
        groups = {}
        for code, name, level in ROLES:
            group, _ = Group.objects.get_or_create(name=name)
            GroupProfile.objects.update_or_create(
                group=group,
                defaults={'code': code, 'level': level, 'is_active': True},
            )
            groups[code] = group
            if level <= 2:
                group.permissions.set(all_perms)
            elif level == 3:
                group.permissions.set(self._filter_permissions(
                    modules=['faculty', 'exams', 'academics', 'students', 'notifications'],
                    actions=['view', 'create', 'update', 'export_pdf'],
                ))
            elif level == 4:
                group.permissions.set(self._filter_permissions(
                    modules=['students', 'exams', 'finance', 'academics', 'notifications', 'documents'],
                    actions=['view'],
                ))

        self.stdout.write('Creating INJS institution...')
        inst, _ = Institution.objects.get_or_create(
            code='INJS',
            defaults={
                'name': 'Institut National de la Jeunesse et des Sports',
                'acronym': 'INJS',
                'city': 'Abidjan',
                'email': 'contact@injs.ci',
            },
        )
        # Logo officiel INJS (fichier frontend public)
        if not inst.logo:
            from pathlib import Path
            from django.core.files import File
            logo_candidates = [
                Path(__file__).resolve().parents[5] / 'ings-fe' / 'public' / 'logo-INJS-ABIDJAN-1.png',
                Path(__file__).resolve().parents[4] / 'ings-fe' / 'public' / 'logo-INJS-ABIDJAN-1.png',
            ]
            for logo_path in logo_candidates:
                if logo_path.exists():
                    with logo_path.open('rb') as f:
                        inst.logo.save('logo-INJS-ABIDJAN-1.png', File(f), save=True)
                    break

        dept_staps, _ = Department.objects.get_or_create(
            institution=inst, code='STAPS',
            defaults={'name': 'Sciences et Techniques des Activités Physiques et Sportives'},
        )
        dept_ensep, _ = Department.objects.get_or_create(
            institution=inst, code='ENSEP',
            defaults={'name': 'École Normale Supérieure d\'Éducation Physique'},
        )

        self.stdout.write('Importing maquette STAPS 2026...')
        from django.core.management import call_command
        call_command('import_maquette_staps2026', '--replace')
        self.stdout.write('Importing nomenclature emplois STAPS...')
        call_command('import_nomenclature_staps', '--replace')

        prog_licence = Program.objects.get(department=dept_staps, code='L-STAPS-PL')
        legacy = Program.objects.filter(department=dept_staps, code='L-STAPS').first()
        if legacy:
            Student.objects.filter(program=legacy).update(program=prog_licence)
            for promo_name, entry_year, current_semester in (
                ('L1-2025', 2024, 2), ('L3-2023', 2020, 6),
            ):
                target, _ = Promotion.objects.get_or_create(
                    program=prog_licence, name=promo_name,
                    defaults={'entry_year': entry_year, 'current_semester': current_semester},
                )
                for old in Promotion.objects.filter(name=promo_name).exclude(pk=target.pk):
                    Student.objects.filter(promotion=old).update(promotion=target)
                    old.delete()
            legacy.is_active = False
            legacy.save(update_fields=['is_active'])
        prog_master, _ = Program.objects.get_or_create(
            department=dept_staps, code='M-STAPS',
            defaults={
                'name': 'Master STAPS - Management du Sport',
                'degree_type': 'M', 'duration_semesters': 4, 'total_credits': 120,
            },
        )
        self.stdout.write('Seeding maquette Master Management du Sport...')
        call_command('seed_maquette_master_ms', '--replace')

        promo_l3, _ = Promotion.objects.get_or_create(
            program=prog_licence, name='L3-2023',
            defaults={'entry_year': 2020, 'current_semester': 6},
        )
        promo_l1, _ = Promotion.objects.get_or_create(
            program=prog_licence, name='L1-2025',
            defaults={'entry_year': 2024, 'current_semester': 2},
        )

        years_data = [
            ('2023-2024', date(2023, 9, 1), date(2024, 8, 31), False, True),
            ('2024-2025', date(2024, 9, 1), date(2025, 8, 31), False, True),
            ('2025-2026', date(2025, 9, 1), date(2026, 8, 31), True, False),
        ]
        academic_years = {}
        for label, start, end, archived, current in years_data:
            ay, _ = AcademicYear.objects.get_or_create(
                institution=inst, label=label,
                defaults={'start_date': start, 'end_date': end, 'is_archived': archived, 'is_current': current},
            )
            academic_years[label] = ay
            for num in [1, 2]:
                Semester.objects.get_or_create(
                    academic_year=ay, number=num,
                    defaults={
                        'name': f'Semestre {num}',
                        'start_date': start + timedelta(days=30 * (num - 1)),
                        'end_date': start + timedelta(days=30 * num),
                        'is_current': current and num == 2,
                    },
                )

        teaching_units = {}

        ay_current = academic_years['2025-2026']
        exam_session = None
        exam_evaluations = []
        sem = Semester.objects.filter(academic_year=ay_current, number=1).first()
        if sem:
            exam_session, _ = ExamSession.objects.get_or_create(
                academic_year=ay_current, semester=sem, session_type='normal',
                defaults={'start_date': date(2026, 1, 10), 'end_date': date(2026, 1, 25), 'is_open': False},
            )
            s1_ues = TeachingUnit.objects.filter(department=dept_staps, semester_number=1).prefetch_related('courses')
            sample_scores = [
                (12, 14), (11, 13), (9, 11), (8, 12), (14, 15), (10, 10), (13, 12),
            ]
            for idx, ue in enumerate(s1_ues):
                course = ue.courses.filter(is_deleted=False).first()
                cc, ct = sample_scores[idx % len(sample_scores)]
                cc_ev, _ = Evaluation.objects.get_or_create(
                    teaching_unit=ue, course=course, exam_session=exam_session,
                    evaluation_type='cc', name=f'CC {ue.code}',
                    defaults={'weight': Decimal('1'), 'date': date(2026, 1, 5)},
                )
                ct_ev, _ = Evaluation.objects.get_or_create(
                    teaching_unit=ue, course=course, exam_session=exam_session,
                    evaluation_type='exam', name=f'CT {ue.code}',
                    defaults={'weight': Decimal('1'), 'date': date(2026, 1, 15)},
                )
                exam_evaluations.append((cc_ev, ct_ev, cc, ct))

        from django.core.management import call_command
        call_command('seed_campus_rooms', verbosity=0)
        Room.objects.get_or_create(
            institution=inst, code='AMPHI-A',
            defaults={
                'name': 'Amphithéâtre A', 'capacity': 200, 'room_type': 'amphitheater',
                'building': 'ENSEPS', 'status': 'available',
            },
        )

        FeeType.objects.get_or_create(
            code='INSCRIPTION-2025',
            defaults={'name': 'Frais d\'inscription 2025-2026', 'amount': Decimal('150000'), 'academic_year': ay_current},
        )

        self.stdout.write('Creating demo users...')
        student_count = 0
        teacher_count = 0
        for entry in DEMO_USERS:
            email, first, last = entry[0], entry[1], entry[2]
            role_code = entry[3]
            is_student = entry[4] if len(entry) > 4 else False
            is_super = entry[5] if len(entry) > 5 else False

            group = groups.get(role_code)
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'first_name': first, 'last_name': last,
                    'institution': inst,
                    'department': dept_staps if role_code in ('enseignant', 'chef_departement') else None,
                    'is_staff': group.profile.level <= 2 if group and hasattr(group, 'profile') else False,
                    'is_superuser': is_super,
                },
            )
            if created or not user.check_password(DEMO_PASSWORD):
                user.set_password(DEMO_PASSWORD)
                user.save()
            if group:
                user.groups.set([group])

            if is_student or role_code in ('delegue', 'resident', 'etudiant'):
                student_count += 1
                matricule = f'INJS2025{student_count:04d}'
                Student.objects.get_or_create(
                    user=user,
                    defaults={
                        'matricule': matricule, 'program': prog_licence,
                        'promotion': promo_l1 if student_count <= 4 else promo_l3,
                        'status': 'active', 'enrollment_date': date(2024, 9, 15),
                    },
                )
                if user.student_profile.program_id != prog_licence.id:
                    Student.objects.filter(user=user).update(program=prog_licence)
                Enrollment.objects.get_or_create(
                    student=user.student_profile,
                    academic_year=ay_current,
                    enrollment_type='administrative',
                    defaults={'status': 'approved'},
                )
            elif role_code in ('enseignant', 'chercheur'):
                teacher_count += 1
                Teacher.objects.get_or_create(
                    user=user,
                    defaults={
                        'employee_id': f'ENS{teacher_count:03d}',
                        'department': dept_staps,
                        'grade': 'maitre_conferences' if role_code == 'chercheur' else 'assistant',
                    },
                )

        # Spécialités STAPS pour étudiants L1 (parcours emploi demo)
        from apps.academics.models import Specialization
        spec_codes = ['APA', 'EM', 'ES', 'MS']
        for idx, student in enumerate(Student.objects.filter(promotion=promo_l1).order_by('matricule')):
            spec = Specialization.objects.filter(code=spec_codes[idx % len(spec_codes)]).first()
            if spec:
                student.specialization = spec
                student.save(update_fields=['specialization'])

        # Assign fees to students
        fee = FeeType.objects.filter(code='INSCRIPTION-2025').first()
        if fee:
            for student in Student.objects.all():
                StudentFee.objects.get_or_create(
                    student=student, fee_type=fee,
                    defaults={'amount_due': fee.amount, 'due_date': date(2025, 10, 31)},
                )

        # Affectations & emploi du temps demo (badgeage QR séance)
        from apps.faculty.models import CourseAssignment, Schedule
        room_amphi = (
            Room.objects.filter(institution=inst, code='AMP-001').first()
            or Room.objects.filter(institution=inst, code='AMPHI-A').first()
        )
        prof_user = User.objects.filter(email='prof.martin@demo.injs.ci').first()
        if prof_user and hasattr(prof_user, 'teacher_profile') and room_amphi:
            demo_course = Course.objects.filter(
                teaching_unit__department=dept_staps,
                teaching_unit__semester_number=1,
                is_deleted=False,
            ).first()
            if demo_course:
                assignment, _ = CourseAssignment.objects.get_or_create(
                    teacher=prof_user.teacher_profile,
                    course=demo_course,
                    academic_year=ay_current,
                    promotion=promo_l1,
                    defaults={'is_primary': True},
                )
                kone = User.objects.filter(email='prof.kone@demo.injs.ci').first()
                if kone and hasattr(kone, 'teacher_profile') and not assignment.supervisor_id:
                    assignment.supervisor = kone.teacher_profile
                    assignment.save(update_fields=['supervisor', 'updated_at'])
                for day_idx, start_h, end_h, kind in ((0, 8, 10, 'cm'), (2, 14, 16, 'td')):
                    Schedule.objects.get_or_create(
                        assignment=assignment,
                        day_of_week=day_idx,
                        start_time=time(start_h, 0),
                        defaults={
                            'room': room_amphi,
                            'end_time': time(end_h, 0),
                            'is_active': True,
                            'session_kind': kind,
                        },
                    )
                gym = (
                    Room.objects.filter(institution=inst, room_type='gym').first()
                    or Room.objects.filter(institution=inst, room_type='sport').first()
                )
                Schedule.objects.get_or_create(
                    assignment=assignment,
                    day_of_week=4,
                    start_time=time(8, 0),
                    defaults={
                        'room': gym or room_amphi,
                        'end_time': time(10, 0),
                        'is_active': True,
                        'session_kind': 'tp',
                        'supervisor': assignment.supervisor,
                    },
                )

        # Notes demo CC/CT pour étudiants L1
        if exam_evaluations:
            from apps.exams.models import Grade
            admin_user = User.objects.filter(is_superuser=True).first()
            for student in Student.objects.filter(promotion=promo_l1):
                for cc_ev, ct_ev, cc, ct in exam_evaluations:
                    Grade.objects.get_or_create(
                        student=student, evaluation=cc_ev,
                        defaults={'score': Decimal(str(cc)), 'entered_by': admin_user},
                    )
                    Grade.objects.get_or_create(
                        student=student, evaluation=ct_ev,
                        defaults={'score': Decimal(str(ct)), 'entered_by': admin_user},
                    )

        self.stdout.write(self.style.SUCCESS(
            f'Seed complete: {User.objects.count()} users, {Student.objects.count()} students, '
            f'{Group.objects.count()} groups, {module_permissions_queryset().count()} permissions'
        ))
