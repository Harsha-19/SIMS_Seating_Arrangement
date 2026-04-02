from django.urls import path
from django.contrib.auth.views import LogoutView
from .views import (
    DashboardView, StudentListView, CustomLoginView,
    RoomListView, ExamListView, SeatingGenerateView, AttendanceListView,
    ExportAttendancePDFView, GenerateAttendanceView, AcademicSetupView
)

app_name = 'dashboard'

urlpatterns = [
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(next_page='dashboard:login'), name='logout'),
    path('', DashboardView.as_view(), name='home'),
    path('students/', StudentListView.as_view(), name='students'),
    path('setup/', AcademicSetupView.as_view(), name='setup'),
    path('rooms/', RoomListView.as_view(), name='rooms'),
    path('exams/', ExamListView.as_view(), name='exams'),
    path('seating/', SeatingGenerateView.as_view(), name='seating'),
    path('attendance/', AttendanceListView.as_view(), name='attendance'),
    path('attendance/export/', ExportAttendancePDFView.as_view(), name='attendance_export'),
    path('attendance/generate/', GenerateAttendanceView.as_view(), name='attendance_generate'),
]
