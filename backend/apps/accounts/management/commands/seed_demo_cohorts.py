"""
Remplit la démo INJS au maximum d'étudiants et de professeurs,
avec parité hommes/femmes, par formation et par promotion (session).

Usage:
  python manage.py seed_demo_cohorts
  python manage.py seed_demo_cohorts --students-per-promo 40 --teachers-per-program 12
"""
from __future__ import annotations

from datetime import date

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

DEMO_PASSWORD = 'Demo@INJS2026!'

FIRST_NAMES_M = [
    'Kouassi', 'Koffi', 'Yao', 'Konan', 'Moussa', 'Ibrahim', 'Jean', 'Eric',
    'Serge', 'Alain', 'Patrick', 'Michel', 'François', 'David', 'Paul',
    'Amadou', 'Sékou', 'Bakary', 'Issa', 'Abdoulaye', 'Mamadou', 'Ousmane',
    'Lacina', 'Didier', 'Hervé', 'Wilfried', 'Junior', 'Samuel', 'Daniel', 'Marc',
]
FIRST_NAMES_F = [
    'Aminata', 'Fatou', 'Aya', 'Mariam', 'Aïcha', 'Adjoua', 'Akissi', 'Amenan',
    'Grace', 'Esther', 'Sarah', 'Rachel', 'Christelle', 'Patricia', 'Nadia',
    'Salimata', 'Rokia', 'Bintou', 'Kadiatou', 'Awa', 'Mariame', 'Hawa',
    'Clarisse', 'Sandrine', 'Laure', 'Emmanuelle', 'Sylvie', 'Josiane', 'Inès', 'Chantal',
]
LAST_NAMES = [
    'Traoré', 'Koné', 'Ouattara', 'Coulibaly', 'Bamba', 'Diallo', 'Touré',
    "N'Guessan", 'Kouamé', 'Yao', 'Brou', 'Assi', 'Gomé', 'Doh', 'Aka',
    'Soro', 'Cissé', 'Sangaré', 'Fofana', 'Keita', 'Camara', 'Dembélé',
    'Zadi', 'Gnahoré', 'Drogba', 'Kalou', 'Bakayoko', 'Doumbia', 'Diabaté', 'Koffi',
]

# (template_name, years_back, current_semester)
PROMOTION_SPECS = {
    'L': [
        ('L1-{y}', 0, 2),
        ('L2-{y1}', 1, 4),
        ('L3-{y2}', 2, 6),
    ],
    'M': [
        ('M1-{y}', 0, 2),
        ('M2-{y1}', 1, 4),
    ],
}


class Command(BaseCommand):
    help = (
        "Génère le maximum d'étudiants et de professeurs (parité H/F) "
        'par formation et promotion pour la démo INJS'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--students-per-promo',
            type=int,
            default=40,
            help='Effectif cible par promotion (pair, défaut 40 = 20H+20F)',
        )
        parser.add_argument(
            '--teachers-per-program',
            type=int,
            default=12,
            help='Effectif cible professeurs par formation (pair, défaut 12 = 6H+6F)',
        )
        parser.add_argument(
            '--session',
            type=str,
            default='2025',
            help='Année de session pour libellés (ex. 2025 → L1-2025)',
        )
        parser.add_argument(
            '--with-qr',
            action='store_true',
            help='Générer les QR étudiants (plus lent)',
        )

    def handle(self, *args, **options):
        students_target = options['students_per_promo']
        teachers_target = options['teachers_per_program']
        session = int(options['session'])
        with_qr = options['with_qr']

        if students_target % 2:
            students_target += 1
            self.stdout.write(self.style.WARNING(f'Effectif étudiants forcé à {students_target} (pair)'))
        if teachers_target % 2:
            teachers_target += 1
            self.stdout.write(self.style.WARNING(f'Effectif professeurs forcé à {teachers_target} (pair)'))

        with transaction.atomic():
            stats = self._run(students_target, teachers_target, session, with_qr)

        self.stdout.write(self.style.SUCCESS(
            f"\nTerminé — +{stats['students']} étudiants, +{stats['teachers']} professeurs, "
            f"+{stats['assignments']} affectations.\n"
            f'Mot de passe démo : {DEMO_PASSWORD}\n'
            f"Totaux : {stats['total_students']} étudiants "
            f"({stats['sm']}H / {stats['sf']}F) — "
            f"{stats['total_teachers']} professeurs ({stats['tm']}H / {stats['tf']}F)"
        ))

    def _run(self, students_target, teachers_target, session, with_qr):
        from apps.accounts.models import User
        from apps.academics.models import (
            Program, Promotion, AcademicYear, ProgramCourse, Department, Course,
        )
        from apps.students.models import Student, Enrollment
        from apps.faculty.models import Teacher, CourseAssignment

        half_s = students_target // 2
        half_t = teachers_target // 2

        ay = (
            AcademicYear.objects.filter(is_current=True).first()
            or AcademicYear.objects.order_by('-start_date').first()
        )
        if not ay:
            raise SystemExit('Aucune année académique — lancez d\'abord seed_injs_demo')

        group_etudiant = Group.objects.filter(name='Étudiant').first()
        group_enseignant = Group.objects.filter(name='Enseignant').first()
        dept_staps = Department.objects.filter(code='STAPS').first()

        programs = list(Program.objects.filter(is_active=True).select_related('department'))
        if not programs:
            raise SystemExit('Aucune formation active')

        created_students = 0
        created_teachers = 0
        created_assignments = 0
        next_matricule = Student.objects.count() + 1
        next_emp = Teacher.objects.count() + 1

        y, y1, y2 = session, session - 1, session - 2

        for program in programs:
            degree = program.degree_type if program.degree_type in PROMOTION_SPECS else 'L'
            promo_objs = []

            for name_tpl, years_back, semester in PROMOTION_SPECS[degree]:
                base_name = name_tpl.format(y=y, y1=y1, y2=y2)
                promo_name = self._promo_name(program, base_name)
                entry_year = (session - years_back - 1) if degree == 'L' else (session - years_back)

                # Réutiliser promos historiques PL
                promo = self._resolve_promo(program, promo_name, base_name, entry_year, semester)
                promo_objs.append(promo)

            self.stdout.write(f'\n▸ Formation {program.code} — {len(promo_objs)} promotion(s)')

            # ——— Étudiants ———
            for promo in promo_objs:
                created_students += self._fill_students(
                    program=program,
                    promo=promo,
                    half=half_s,
                    session=session,
                    ay=ay,
                    group=group_etudiant,
                    with_qr=with_qr,
                    counters={
                        'matricule': next_matricule,
                        'User': User,
                        'Student': Student,
                        'Enrollment': Enrollment,
                    },
                )
                next_matricule = Student.objects.count() + 1

                total = Student.objects.filter(promotion=promo, status='active').count()
                m = Student.objects.filter(promotion=promo, status='active', gender='M').count()
                f = Student.objects.filter(promotion=promo, status='active', gender='F').count()
                self.stdout.write(f'  {promo.name}: {total} étudiants ({m}H / {f}F)')

            # ——— Professeurs ———
            prog_slug = slugify(program.code).replace('-', '')[:14]
            program_teachers, added, next_emp = self._fill_teachers(
                program=program,
                prog_slug=prog_slug,
                half=half_t,
                next_emp=next_emp,
                dept_fallback=dept_staps,
                group=group_enseignant,
                User=User,
                Teacher=Teacher,
            )
            created_teachers += added

            tm = sum(1 for t in program_teachers if t.gender == 'M')
            tf = sum(1 for t in program_teachers if t.gender == 'F')
            self.stdout.write(f'  Professeurs: {len(program_teachers)} ({tm}H / {tf}F)')

            # Affectations
            pcs = list(
                ProgramCourse.objects.filter(program=program)
                .select_related('teaching_unit')
                .prefetch_related('teaching_unit__courses')
                .order_by('semester_number')
            )
            course_list = []
            for pc in pcs:
                for c in pc.teaching_unit.courses.filter(is_deleted=False).order_by('code'):
                    course_list.append(c)
            if not course_list:
                course_list = list(
                    Course.objects.filter(
                        teaching_unit__department=program.department,
                        is_deleted=False,
                    ).order_by('code')[:40]
                )

            if program_teachers and promo_objs and course_list:
                for i, teacher in enumerate(program_teachers):
                    course = course_list[i % len(course_list)]
                    promo = promo_objs[i % len(promo_objs)]
                    _, ca_created = CourseAssignment.objects.get_or_create(
                        teacher=teacher,
                        course=course,
                        academic_year=ay,
                        promotion=promo,
                        defaults={'is_primary': True},
                    )
                    if ca_created:
                        created_assignments += 1

        return {
            'students': created_students,
            'teachers': created_teachers,
            'assignments': created_assignments,
            'total_students': Student.objects.filter(status='active').count(),
            'sm': Student.objects.filter(status='active', gender='M').count(),
            'sf': Student.objects.filter(status='active', gender='F').count(),
            'total_teachers': Teacher.objects.filter(is_active=True).count(),
            'tm': Teacher.objects.filter(is_active=True, gender='M').count(),
            'tf': Teacher.objects.filter(is_active=True, gender='F').count(),
        }

    @staticmethod
    def _promo_name(program, base_name):
        if program.code.endswith('-PC'):
            return f'{base_name}-PC'
        return base_name

    def _resolve_promo(self, program, promo_name, base_name, entry_year, semester):
        from apps.academics.models import Promotion

        # Alias historiques PL
        aliases = []
        if program.code == 'L-STAPS-PL':
            if base_name.startswith('L1-'):
                aliases.append('L1-2025')
            if base_name.startswith('L3-'):
                aliases.append('L3-2023')

        for alias in aliases:
            existing = Promotion.objects.filter(program=program, name=alias).first()
            if existing:
                existing.current_semester = semester
                existing.is_active = True
                existing.save(update_fields=['current_semester', 'is_active', 'updated_at'])
                return existing

        promo, _ = Promotion.objects.get_or_create(
            program=program,
            name=promo_name,
            defaults={
                'entry_year': entry_year,
                'current_semester': semester,
                'is_active': True,
            },
        )
        if promo.current_semester != semester or not promo.is_active:
            promo.current_semester = semester
            promo.is_active = True
            promo.save(update_fields=['current_semester', 'is_active', 'updated_at'])
        return promo

    def _fill_students(self, *, program, promo, half, session, ay, group, with_qr, counters):
        User = counters['User']
        Student = counters['Student']
        Enrollment = counters['Enrollment']
        created = 0

        qs = Student.objects.filter(promotion=promo)
        for st in qs.filter(gender=''):
            st.gender = 'M' if (hash(st.matricule) % 2 == 0) else 'F'
            st.save(update_fields=['gender', 'updated_at'], skip_qr=True)

        need_m = max(0, half - qs.filter(gender='M').count())
        need_f = max(0, half - qs.filter(gender='F').count())
        next_matricule = counters['matricule']
        prog_slug = slugify(program.code).replace('-', '')[:12]

        for gender, need in (('M', need_m), ('F', need_f)):
            firsts = FIRST_NAMES_M if gender == 'M' else FIRST_NAMES_F
            for i in range(need):
                idx = next_matricule
                next_matricule += 1
                first = firsts[(idx + i) % len(firsts)]
                last = LAST_NAMES[(idx * 3 + i) % len(LAST_NAMES)]
                email = f'etu.{prog_slug}.{slugify(promo.name)}.{idx:04d}@demo.injs.ci'

                user, user_created = User.objects.get_or_create(
                    email=email,
                    defaults={'first_name': first, 'last_name': last, 'is_active': True},
                )
                if user_created:
                    user.set_password(DEMO_PASSWORD)
                    user.save()
                else:
                    user.first_name = first
                    user.last_name = last
                    user.is_active = True
                    user.save(update_fields=['first_name', 'last_name', 'is_active'])
                if group:
                    user.groups.add(group)

                if hasattr(user, 'student_profile'):
                    student = user.student_profile
                    student.program = program
                    student.promotion = promo
                    student.gender = gender
                    student.status = 'active'
                    student.save(
                        update_fields=['program', 'promotion', 'gender', 'status', 'updated_at'],
                        skip_qr=True,
                    )
                else:
                    matricule = f'INJS{session}{idx:04d}'
                    while Student.objects.filter(matricule=matricule).exists():
                        idx = next_matricule
                        next_matricule += 1
                        matricule = f'INJS{session}{idx:04d}'

                    student = Student(
                        user=user,
                        matricule=matricule,
                        program=program,
                        promotion=promo,
                        gender=gender,
                        status='active',
                        enrollment_date=date(session, 9, 15),
                        nationality='Ivoirienne',
                    )
                    student.save(skip_qr=not with_qr)
                    created += 1

                Enrollment.objects.get_or_create(
                    student=student,
                    academic_year=ay,
                    enrollment_type='administrative',
                    defaults={'status': 'approved'},
                )

        counters['matricule'] = next_matricule
        return created

    def _fill_teachers(self, *, program, prog_slug, half, next_emp, dept_fallback, group, User, Teacher):
        tagged = list(
            Teacher.objects.filter(user__email__startswith=f'prof.{prog_slug}.', is_active=True)
        )
        legacy_emails = []
        if program.code == 'L-STAPS-PL':
            legacy_emails = ['prof.martin@demo.injs.ci', 'prof.kone@demo.injs.ci']
            for email, default_g in (
                ('prof.martin@demo.injs.ci', 'M'),
                ('prof.kone@demo.injs.ci', 'F'),
            ):
                t = Teacher.objects.filter(user__email=email, is_active=True).first()
                if t:
                    if not t.gender:
                        t.gender = default_g
                        t.save(update_fields=['gender', 'updated_at'])
                    if t not in tagged:
                        tagged.append(t)

        for t in tagged:
            if not t.gender:
                t.gender = 'M' if hash(t.employee_id) % 2 == 0 else 'F'
                t.save(update_fields=['gender', 'updated_at'])

        men = sum(1 for t in tagged if t.gender == 'M')
        women = sum(1 for t in tagged if t.gender == 'F')
        need_m = max(0, half - men)
        need_f = max(0, half - women)
        added = 0
        new_ones = []

        for gender, need in (('M', need_m), ('F', need_f)):
            firsts = FIRST_NAMES_M if gender == 'M' else FIRST_NAMES_F
            for i in range(need):
                idx = next_emp
                next_emp += 1
                first = firsts[(idx + i) % len(firsts)]
                last = LAST_NAMES[(idx * 5 + i) % len(LAST_NAMES)]
                email = f'prof.{prog_slug}.{idx:03d}@demo.injs.ci'

                user, user_created = User.objects.get_or_create(
                    email=email,
                    defaults={'first_name': first, 'last_name': last, 'is_active': True},
                )
                if user_created:
                    user.set_password(DEMO_PASSWORD)
                    user.save()
                if group:
                    user.groups.add(group)

                if hasattr(user, 'teacher_profile'):
                    teacher = user.teacher_profile
                    teacher.gender = gender
                    teacher.is_active = True
                    teacher.save(update_fields=['gender', 'is_active', 'updated_at'])
                else:
                    emp_id = f'ENS{idx:03d}'
                    while Teacher.objects.filter(employee_id=emp_id).exists():
                        idx = next_emp
                        next_emp += 1
                        emp_id = f'ENS{idx:03d}'
                    teacher = Teacher.objects.create(
                        user=user,
                        employee_id=emp_id,
                        department=program.department or dept_fallback,
                        grade='maitre_assistant' if i % 2 == 0 else 'assistant',
                        specialization=(program.name or '')[:200],
                        gender=gender,
                        hire_date=date(2020, 9, 1),
                        is_active=True,
                    )
                    added += 1
                new_ones.append(teacher)

        all_teachers = list(
            Teacher.objects.filter(user__email__startswith=f'prof.{prog_slug}.', is_active=True)
        )
        for email in legacy_emails:
            t = Teacher.objects.filter(user__email=email, is_active=True).first()
            if t and t not in all_teachers:
                all_teachers.append(t)
        # include newly ensured
        for t in new_ones:
            if t not in all_teachers:
                all_teachers.append(t)

        return all_teachers, added, next_emp
