from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    StudentViewSet, RoomViewSet, ExamScheduleViewSet, SubjectViewSet,
    SeatingViewSet, SeatingPlanViewSet, AttendanceViewSet, AnalyticsViewSet, LoginView, SeedAdminView,
    ProgramViewSet, DepartmentViewSet, EnrollmentViewSet, semester_options,
    chrome_devtools_config, generate_seating
)


router = DefaultRouter()
router.register('students', StudentViewSet)
router.register('rooms', RoomViewSet)
router.register('subjects', SubjectViewSet)
router.register('exam-schedules', ExamScheduleViewSet)
router.register('plans', SeatingPlanViewSet)
router.register('seating', SeatingViewSet)

router.register('attendance', AttendanceViewSet)
router.register('programs', ProgramViewSet)
router.register('analytics', AnalyticsViewSet, basename='analytics')
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
