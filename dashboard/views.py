from django.shortcuts import render, redirect, HttpResponse
from django.contrib.auth.views import LoginView as DjangoLoginView, LogoutView as DjangoLogoutView
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.db.models import Count, Q, Sum
from api.models import Student, Room, Exam, Seating, Attendance, Department, Semester
from .utils import render_to_pdf

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/home.html'
    login_url = '/login/'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from django.utils import timezone
        from datetime import timedelta
        
        now = timezone.now()
        next_24h = now + timedelta(hours=24)
        
        context['stats'] = {
            'students': Student.objects.count(),
            'rooms': Room.objects.count(),
            'exams': Exam.objects.filter(date__range=(now, next_24h)).count(),
            'total_exams': Exam.objects.count(),
            'seating': Seating.objects.values('exam').distinct().count(),
        }
        # Recent exams for the table
        context['recent_exams'] = Exam.objects.all().order_by('-date')[:5]
        # Calculate total capacity
        total_capacity = sum(r.total_capacity for r in Room.objects.all())
        context['total_capacity'] = total_capacity
        return context

class CustomLoginView(DjangoLoginView):
    template_name = 'login.html'
    redirect_authenticated_user = True

class StudentListView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/students.html'
    login_url = '/login/'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['students'] = Student.objects.all().select_related('department', 'semester').order_by('-created_at')
        context['departments'] = Department.objects.all().order_by('name')
        context['semesters'] = Semester.objects.all().order_by('name')
        return context

class AcademicSetupView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/academic_setup.html'
    login_url = '/login/'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['departments'] = Department.objects.all().prefetch_related('semesters').order_by('name')
        return context

class RoomListView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/rooms.html'
    login_url = '/login/'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        rooms = Room.objects.all().order_by('room_number')
        context['rooms'] = rooms
        context['total_seats'] = rooms.aggregate(Sum('total_capacity'))['total_capacity__sum'] or 0
        context['readiness'] = 100 if rooms.filter(total_capacity__gt=0).count() == rooms.count() and rooms.count() > 0 else 0
        
        # Build layout data for visual map
        layouts = {}
        for room in rooms:
            room_seats = []
            # Fetch latest seating for this room if any
            seatings = Seating.objects.filter(room=room).select_related('student', 'student__department')
            seat_map = {} # Key: "row-section-index"
            for s in seatings:
                # We need to extract section and index from 'seat_position' which looks like "Left Seat 1"
                try:
                    parts = s.seat_position.split(' ')
                    sec = parts[0]
                    idx = int(parts[2]) - 1
                    key = f"{s.row}-{sec}-{idx}"
                    seat_map[key] = s
                except: continue

            for r in range(1, room.rows + 1):
                row_data = {'num': r, 'sections': []}
                for sec_name, sec_cap in [('Left', room.left_seats), ('Middle', room.middle_seats), ('Right', room.right_seats)]:
                    sec_seats = []
                    for i in range(sec_cap):
                        s_data = seat_map.get(f"{r}-{sec_name}-{i}")
                        sec_seats.append({
                            'occupied': s_data is not None,
                            'student_name': s_data.student.name if s_data else None,
                            'student_usn': s_data.student.university_id if s_data else None,
                            'dept': s_data.student.department.name if s_data and s_data.student.department else None,
                            'seat_num': f"{sec_name[0]}{i+1}"
                        })
                    row_data['sections'].append({'name': sec_name, 'seats': sec_seats})
                room_seats.append(row_data)
            layouts[room.id] = room_seats
        
        context['room_layouts'] = layouts
        return context

class ExamListView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/exams.html'
    login_url = '/login/'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['exams'] = Exam.objects.all().select_related('department', 'semester').order_by('-date')
        context['departments'] = Department.objects.all().order_by('name')
        context['semesters'] = Semester.objects.all().order_by('name')
        return context

class SeatingGenerateView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/seating_generate.html'
    login_url = '/login/'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['exams'] = Exam.objects.all().select_related('department', 'semester').order_by('-date')
        context['rooms'] = Room.objects.all().order_by('room_number')
        context['student_count'] = Student.objects.count()
        context['departments'] = Department.objects.all().order_by('name')
        context['semesters'] = Semester.objects.all().order_by('name')
        return context

class AttendanceListView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/attendance.html'
    login_url = '/login/'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['attendances'] = Attendance.objects.all().order_by('-created_at')
        return context

class ExportAttendancePDFView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        attendances = Attendance.objects.all().order_by('-created_at')
        data = {
            'attendances': attendances,
        }
        response = render_to_pdf('dashboard/attendance_pdf.html', data)
        if response:
            filename = "Attendance_Report.pdf"
            response['Content-Disposition'] = f'inline; filename="{filename}"'
            return response
        return HttpResponse("Error generating PDF", status=400)

class GenerateAttendanceView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/attendance_print.html'
    login_url = '/login/'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        exam_id = self.request.GET.get('exam_id')
        if not exam_id:
            context['error'] = "No exam selected."
            return context
        
        exam = Exam.objects.get(id=exam_id)
        context['exam'] = exam
        
        # Get all seats for this exam
        seats = Seating.objects.filter(exam=exam).select_related('room', 'student', 'student__department', 'student__semester').order_by('room__room_number', 'student__department__name', 'student__semester__name', 'row', 'seat_position')
        
        # Group by Room -> (Course, Semester)
        grouped_data = {}
        for seat in seats:
            room_id = seat.room.id
            if room_id not in grouped_data:
                grouped_data[room_id] = {
                    'room_number': seat.room.room_number,
                    'sheets': {}
                }
            
            # Key for course-wise sheet
            sheet_key = (seat.student.department.name if seat.student.department else "N/A", 
                         seat.student.semester.name if seat.student.semester else "N/A")
            if sheet_key not in grouped_data[room_id]['sheets']:
                grouped_data[room_id]['sheets'][sheet_key] = []
            
            grouped_data[room_id]['sheets'][sheet_key].append(seat.student)
        
        # Sort sheets for easier template rendering: List of (room_info, [ (course_sem, students) ])
        final_rooms = []
        for r_id in sorted(grouped_data.keys(), key=lambda x: grouped_data[x]['room_number']):
            room_info = grouped_data[r_id]
            sheets_list = []
            for s_key in sorted(room_info['sheets'].keys()):
                sheets_list.append({
                    'course': s_key[0],
                    'semester': s_key[1],
                    'students': room_info['sheets'][s_key]
                })
            final_rooms.append({
                'room_number': room_info['room_number'],
                'sheets': sheets_list
            })
            
        context['rooms'] = final_rooms
        return context
