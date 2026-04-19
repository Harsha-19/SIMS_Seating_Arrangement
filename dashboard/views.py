from django.shortcuts import render, redirect, HttpResponse
from django.contrib.auth.views import LoginView as DjangoLoginView, LogoutView as DjangoLogoutView
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.db.models import Count, Q, Sum
from collections import defaultdict
from api.models import Student, Room, Exam, Seating, Attendance, Program, Enrollment
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
        # Recent activities
        activities = []
        
        # Latest 3 Students
        latest_students = Student.objects.all().order_by('-created_at')[:3]
        for s in latest_students:
            activities.append({
                'title': 'Students Added',
                'description': f'Added {s.name} ({s.reg_no})',
                'time': s.created_at,
                'icon': 'user-plus',
                'color': 'blue'
            })
            
        # Latest 3 Seating Plans (Distinct exams)
        latest_seating = Seating.objects.all().values('exam', 'created_at').annotate(cnt=Count('id')).order_by('-created_at')[:3]
        exam_map = Exam.objects.in_bulk([item['exam'] for item in latest_seating])
        for se in latest_seating:
            exam = exam_map.get(se['exam'])
            if not exam:
                continue
            activities.append({
                'title': 'Plan Created',
                'description': f'Seating arrangement for {exam.subject} ready.',
                'time': se['created_at'],
                'icon': 'zap',
                'color': 'emerald'
            })

        # Sort by latest
        activities.sort(key=lambda x: x['time'], reverse=True)
        context['activities'] = activities[:5]
        
        return context

class CustomLoginView(DjangoLoginView):
    template_name = 'login.html'
    redirect_authenticated_user = True

class StudentListView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/students.html'
    login_url = '/login/'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # We prefetch enrollments to show current academic status
        context['students'] = Student.objects.all().prefetch_related('enrollments__program').order_by('-created_at')
        context['programs'] = Program.objects.all().order_by('name')
        context['departments'] = context['programs']
        return context

class AcademicSetupView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/academic_setup.html'
    login_url = '/login/'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['programs'] = Program.objects.all().order_by('-created_at')
        context['departments'] = context['programs']
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
        all_seatings = list(
            Seating.objects.filter(room__in=rooms)
            .select_related('student', 'room', 'exam__program', 'exam_group__program')
            .order_by('room_id', 'row', 'seat_position')
        )
        student_ids = {seat.student_id for seat in all_seatings}
        program_ids = {
            seat.effective_program.id
            for seat in all_seatings
            if seat.effective_program is not None
        }
        semesters = {
            seat.effective_semester
            for seat in all_seatings
            if seat.effective_semester is not None
        }
        enrollment_map = {}
        if student_ids and program_ids and semesters:
            enrollments = Enrollment.objects.filter(
                student_id__in=student_ids,
                program_id__in=program_ids,
                semester__in=semesters,
            ).select_related('program')
            enrollment_map = {
                (enrollment.student_id, enrollment.program_id, enrollment.semester): enrollment
                for enrollment in enrollments
            }
        seatings_by_room = defaultdict(list)
        for seating in all_seatings:
            seatings_by_room[seating.room_id].append(seating)

        for room in rooms:
            room_seats = []
            seat_map = {} # Key: "row-section-index"
            for s in seatings_by_room.get(room.id, []):
                try:
                    parts = s.seat_position.split(' ')
                    sec = parts[0]
                    idx = int(parts[2]) - 1

                    effective_program = s.effective_program
                    effective_semester = s.effective_semester
                    enrollment = enrollment_map.get((
                        s.student_id,
                        effective_program.id if effective_program else None,
                        effective_semester,
                    ))
                    key = f"{s.row}-{sec}-{idx}"
                    s.enrollment_info = enrollment # Attach for template
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
                            'student_usn': s_data.student.reg_no if s_data else None,
                            'dept': s_data.enrollment_info.program.name if s_data and s_data.enrollment_info else 'N/A',
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
        context['exams'] = Exam.objects.all().select_related('program').prefetch_related('groups__program').order_by('-date')
        context['programs'] = Program.objects.all().order_by('name')
        context['departments'] = context['programs']
        return context

class SeatingGenerateView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/seating_generate.html'
    login_url = '/login/'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['exams'] = Exam.objects.all().select_related('program').prefetch_related('groups__program').order_by('-date')
        context['rooms'] = Room.objects.all().order_by('room_number')
        context['student_count'] = Student.objects.count()
        context['programs'] = Program.objects.all().order_by('name')
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
        
        exam = Exam.objects.select_related('program').prefetch_related('groups__program').get(id=exam_id)
        context['exam'] = exam
        
        # Get all seats for this exam
        seats = (
            Seating.objects.filter(exam=exam)
            .select_related('room', 'student', 'exam_group__program', 'exam__program')
            .order_by('room__room_number', 'row', 'seat_position')
        )
        program_ids = {
            seat.effective_program.id
            for seat in seats
            if seat.effective_program is not None
        }
        semesters = {
            seat.effective_semester
            for seat in seats
            if seat.effective_semester is not None
        }
        enrollment_map = {
            (enrollment.student_id, enrollment.program_id, enrollment.semester): enrollment
            for enrollment in Enrollment.objects.filter(
                student_id__in=seats.values_list('student_id', flat=True),
                program_id__in=program_ids,
                semester__in=semesters,
            ).select_related('program')
        }
        
        # Group by Room -> (Course, Semester)
        grouped_data = {}
        for seat in seats:
            room_id = seat.room.id
            if room_id not in grouped_data:
                grouped_data[room_id] = {
                    'room_number': seat.room.room_number,
                    'sheets': {}
                }
            
            # Fetch enrollment for this student for the exam's program/semester
            effective_program = seat.effective_program
            effective_semester = seat.effective_semester
            enrollment = enrollment_map.get((
                seat.student_id,
                effective_program.id if effective_program else None,
                effective_semester,
            ))
            
            # Key for course-wise sheet
            sheet_key = (
                enrollment.program.name if enrollment else "N/A",
                f"SEM {enrollment.semester}" if enrollment else "N/A",
                seat.effective_subject or exam.subject,
            )
            
            if sheet_key not in grouped_data[room_id]['sheets']:
                grouped_data[room_id]['sheets'][sheet_key] = []
            
            # Attach enrollment info to seat for template
            seat.enrollment_info = enrollment
            grouped_data[room_id]['sheets'][sheet_key].append(seat)
        
        # Sort sheets for easier template rendering: List of (room_info, [ (course_sem, students) ])
        final_rooms = []
        for r_id in sorted(grouped_data.keys(), key=lambda x: grouped_data[x]['room_number']):
            room_info = grouped_data[r_id]
            sheets_list = []
            for s_key in sorted(room_info['sheets'].keys()):
                sheets_list.append({
                    'course': s_key[0],
                    'semester': s_key[1],
                    'subject': s_key[2],
                    'seats': room_info['sheets'][s_key]
                })
            final_rooms.append({
                'room_number': room_info['room_number'],
                'sheets': sheets_list
            })
            
        context['rooms'] = final_rooms
        return context
