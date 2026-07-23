from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.faculty.views import (
    TeacherViewSet, RoomViewSet, CourseAssignmentViewSet, ScheduleViewSet,
    AttendanceViewSet, AttendanceSessionViewSet,
    RoomReservationViewSet, MaintenanceTicketViewSet, EquipmentAssetViewSet,
)

router = DefaultRouter()
router.register('teachers', TeacherViewSet)
router.register('rooms', RoomViewSet)
router.register('assignments', CourseAssignmentViewSet)
router.register('schedules', ScheduleViewSet)
router.register('attendance-sessions', AttendanceSessionViewSet)
router.register('attendances', AttendanceViewSet)
router.register('reservations', RoomReservationViewSet)
router.register('maintenance-tickets', MaintenanceTicketViewSet)
router.register('equipment', EquipmentAssetViewSet)

urlpatterns = [path('', include(router.urls))]
