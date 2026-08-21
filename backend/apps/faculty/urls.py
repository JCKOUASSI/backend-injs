from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.faculty.views import (
    TeacherViewSet, RoomViewSet, CourseAssignmentViewSet, ScheduleViewSet,
    AttendanceViewSet, AttendanceSessionViewSet, StaffAttendanceViewSet,
    RoomReservationViewSet, MaintenanceTicketViewSet, EquipmentAssetViewSet,
    SeanceViewSet, TeachingLoadViewSet, StudentGroupViewSet, StudentGroupMemberViewSet,
    PlanningSettingsViewSet, TimetableRunViewSet, GroupSchedulingConfigViewSet,
    BadgeEventViewSet,
)

router = DefaultRouter()
router.register('teachers', TeacherViewSet)
router.register('rooms', RoomViewSet)
router.register('assignments', CourseAssignmentViewSet)
router.register('schedules', ScheduleViewSet)
router.register('attendance-sessions', AttendanceSessionViewSet)
router.register('attendances', AttendanceViewSet)
router.register('staff-attendances', StaffAttendanceViewSet)
router.register('reservations', RoomReservationViewSet)
router.register('maintenance-tickets', MaintenanceTicketViewSet)
router.register('equipment', EquipmentAssetViewSet)
router.register('seances', SeanceViewSet)
router.register('teaching-loads', TeachingLoadViewSet)
router.register('student-groups', StudentGroupViewSet)
router.register('student-group-members', StudentGroupMemberViewSet)
router.register('group-scheduling-configs', GroupSchedulingConfigViewSet)
router.register('planning-settings', PlanningSettingsViewSet)
router.register('timetable-runs', TimetableRunViewSet)
router.register('badge-events', BadgeEventViewSet)

urlpatterns = [path('', include(router.urls))]
