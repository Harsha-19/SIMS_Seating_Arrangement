from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    StudentViewSet, RoomViewSet, ExamViewSet, 
    SeatingViewSet, AttendanceViewSet, LoginView, SeedAdminView,
    DepartmentViewSet, SemesterViewSet
)

router = DefaultRouter()
router.register('students', StudentViewSet)
router.register('rooms', RoomViewSet)
router.register('exams', ExamViewSet)
router.register('seating', SeatingViewSet)
router.register('attendance', AttendanceViewSet)
router.register('departments', DepartmentViewSet)
router.register('semesters', SemesterViewSet)

urlpatterns = [
    path('auth/login', LoginView.as_view(), name='login'),
    path('auth/seed', SeedAdminView.as_view(), name='seed'),
    path('', include(router.urls)),
]
