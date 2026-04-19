from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    StudentViewSet, RoomViewSet, ExamViewSet, 
    SeatingViewSet, AttendanceViewSet, LoginView, SeedAdminView,
    ProgramViewSet, DepartmentViewSet, EnrollmentViewSet, semester_options,
    chrome_devtools_config, generate_seating
)

router = DefaultRouter()
router.register('students', StudentViewSet)
router.register('rooms', RoomViewSet)
router.register('exams', ExamViewSet)
router.register('seating', SeatingViewSet)
router.register('attendance', AttendanceViewSet)
router.register('programs', ProgramViewSet)
router.register('departments', DepartmentViewSet, basename='department')
router.register('enrollments', EnrollmentViewSet)

urlpatterns = [
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/seed/', SeedAdminView.as_view(), name='seed'),
    path('semesters/', semester_options, name='semester-options'),
    path('seating/generate/', generate_seating, name='seating-generate'),
    path('generate-seating/', generate_seating, name='generate-seating'),
    path('.well-known/appspecific/com.chrome.devtools.json', chrome_devtools_config),
    path('', include(router.urls)),
]
