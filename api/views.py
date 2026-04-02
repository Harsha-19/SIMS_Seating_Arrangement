import random
import csv
import io
from rest_framework import viewsets, status, generics
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import AllowAny
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Student, Room, Exam, Seating, Attendance, AttendanceEntry, Department, Semester
from .serializers import (
    StudentSerializer, RoomSerializer, ExamSerializer, 
    SeatingSerializer, AttendanceSerializer, UserSerializer,
    DepartmentSerializer, SemesterSerializer
)

from django.db import models

class StudentViewSet(viewsets.ModelViewSet):
    queryset = Student.objects.all().select_related('department', 'semester').order_by('-created_at')
    serializer_class = StudentSerializer
    parser_classes = (JSONParser, MultiPartParser, FormParser)
    lookup_field = 'university_id'

    def get_queryset(self):
        queryset = Student.objects.all().select_related('department', 'semester').order_by('-created_at')
        dept_id = self.request.query_params.get('department_id')
        sem_id = self.request.query_params.get('semester_id')
        search = self.request.query_params.get('search')
        
        if dept_id:
            queryset = queryset.filter(department_id=dept_id)
        if sem_id:
            queryset = queryset.filter(semester_id=sem_id)
        if search:
            queryset = queryset.filter(
                models.Q(name__icontains=search) | 
                models.Q(university_id__icontains=search)
            )
        return queryset

    @action(detail=False, methods=['post'])
    def upload(self, request):
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({'message': 'Excel file (.xlsx) required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            from openpyxl import load_workbook
            wb = load_workbook(file_obj)
            sheet = wb.active
            
            # Assume first row is header
            headers = [cell.value.lower() if cell.value else "" for cell in sheet[1]]
            
            # Find indices
            try:
                idx_usn = headers.index('usn')
                idx_name = headers.index('name')
                idx_course = headers.index('course')
                idx_sem = headers.index('semester')
            except ValueError as e:
                return Response({'message': f'Required columns missing in Excel. Need: usn, name, course, semester. Missing: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
            
            students_to_create = []
            for row in sheet.iter_rows(min_row=2, values_only=True):
                # Skip empty rows
                if not any(row): continue
                
                uid = str(row[idx_usn]).strip().upper() if row[idx_usn] else ""
                name = str(row[idx_name]).strip() if row[idx_name] else ""
                dept_name = str(row[idx_course]).strip().upper() if row[idx_course] else ""
                sem_name = str(row[idx_sem]).strip() if row[idx_sem] else "1st Sem"
                
                if uid and name and dept_name:
                    # Find or create department
                    dept, _ = Department.objects.get_or_create(name=dept_name)
                    # Find or create semester in that department
                    sem, _ = Semester.objects.get_or_create(name=sem_name, department=dept)
                    
                    students_to_create.append(Student(
                        university_id=uid,
                        name=name,
                        department=dept,
                        semester=sem
                    ))
            
            # SQLite / PostgreSQL bulk create with conflict handling
            Student.objects.bulk_create(
                students_to_create,
                update_conflicts=True,
                unique_fields=['university_id'],
                update_fields=['name', 'department', 'semester']
            )
            
            return Response({'message': 'Students uploaded successfully from Excel', 'count': len(students_to_create)}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'message': f'Logic Error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.all().order_by('name')
    serializer_class = DepartmentSerializer

class SemesterViewSet(viewsets.ModelViewSet):
    queryset = Semester.objects.all().select_related('department').order_by('department__name', 'name')
    serializer_class = SemesterSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        dept_id = self.request.query_params.get('department_id')
        if dept_id:
            queryset = queryset.filter(department_id=dept_id)
        return queryset

class RoomViewSet(viewsets.ModelViewSet):
    queryset = Room.objects.all().order_by('room_number')
    serializer_class = RoomSerializer

class ExamViewSet(viewsets.ModelViewSet):
    queryset = Exam.objects.all().order_by('-date')
    serializer_class = ExamSerializer

class SeatingViewSet(viewsets.ModelViewSet):
    queryset = Seating.objects.all()
    serializer_class = SeatingSerializer

    @action(detail=False, methods=['post'])
    def generate(self, request):
        exam_id = request.data.get('examId')
        room_ids = request.data.get('roomIds')
        
        if not exam_id or not room_ids:
            return Response({'message': 'examId and roomIds are required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            exam = Exam.objects.get(id=exam_id)
            rooms = Room.objects.filter(id__in=room_ids).order_by('room_number')
            
            # Fetch only the students for this specific exam session (Dept + Sem)
            eligible_students = Student.objects.filter(
                department=exam.department,
                semester=exam.semester
            ).select_related('department')

            if not eligible_students.exists():
                return Response({'message': f'Zero students found for {exam.department} - {exam.semester}'}, status=status.HTTP_400_BAD_REQUEST)

            # Shuffling for fair distribution if needed (though here they are all same)
            interleaved = list(eligible_students)
            random.shuffle(interleaved)
            
            total_capacity = sum(r.total_capacity for r in rooms)
            if len(interleaved) > total_capacity:
                return Response({'message': f'Insufficient capacity. Need {len(interleaved)} seats, only {total_capacity} available.'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Clean existing records
            Seating.objects.filter(exam=exam).delete()
            Attendance.objects.filter(exam=exam).delete()
            
            student_idx = 0
            for room in rooms:
                attendance = Attendance.objects.create(exam=exam, room=room)
                
                # High-Fidelity Row-by-Row Filling [Left, Middle, Right]
                for r in range(room.rows):
                    sections = [
                        ('Left', room.left_seats),
                        ('Middle', room.middle_seats),
                        ('Right', room.right_seats)
                    ]
                    
                    for section_name, section_capacity in sections:
                        for s_in_sec in range(section_capacity):
                            if student_idx >= len(interleaved): break
                            
                            student = interleaved[student_idx]
                            student_idx += 1
                            
                            Seating.objects.create(
                                exam=exam,
                                room=room,
                                row=r + 1,
                                seat_position=f"{section_name} Seat {s_in_sec + 1}",
                                student=student
                            )
                            
                            AttendanceEntry.objects.create(
                                attendance=attendance,
                                student=student,
                                present=True
                            )
                        if student_idx >= len(interleaved): break
                    if student_idx >= len(interleaved): break
            
            return Response({
                'message': f'Arrangement finalized. {student_idx} Students Seated.', 
                'studentCount': student_idx
            }, status=status.HTTP_201_CREATED)
        except Exam.DoesNotExist:
            return Response({'message': 'Exam not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'message': f'Generation Error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'], url_path='(?P<exam_id>\\d+)')
    def by_exam(self, request, exam_id=None):
        seatings = Seating.objects.filter(exam_id=exam_id)
        serializer = self.get_serializer(seatings, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='(?P<exam_id>\\d+)/(?P<room_id>\\d+)')
    def by_exam_and_room(self, request, exam_id=None, room_id=None):
        seatings = Seating.objects.filter(exam_id=exam_id, room_id=room_id)
        serializer = self.get_serializer(seatings, many=True)
        return Response(serializer.data)

class AttendanceViewSet(viewsets.ModelViewSet):
    queryset = Attendance.objects.all()
    serializer_class = AttendanceSerializer

    @action(detail=False, methods=['get'], url_path='(?P<exam_id>\\d+)/(?P<room_id>\\d+)')
    def by_exam_and_room(self, request, exam_id=None, room_id=None):
        try:
            attendance = Attendance.objects.get(exam_id=exam_id, room_id=room_id)
            serializer = self.get_serializer(attendance)
            return Response(serializer.data)
        except Attendance.DoesNotExist:
            return Response({'message': 'Attendance not found'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['put'])
    def update_entries(self, request, pk=None):
        attendance = self.get_object()
        student_data = request.data.get('students', [])
        
        for s in student_data:
            entry = AttendanceEntry.objects.get(attendance=attendance, student_id=s['studentId'])
            entry.booklet_number = s.get('bookletNumber', entry.booklet_number)
            entry.present = s.get('present', entry.present)
            entry.save()
            
        return Response({'message': 'Attendance updated'})

class LoginView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(username=username, password=password)
        
        if user:
            refresh = RefreshToken.for_user(user)
            return Response({
                '_id': str(user.id),
                'id': str(user.id), # Double map to be safe
                'username': user.username,
                'token': str(refresh.access_token)
            })
        return Response({'message': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

class SeedAdminView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        if not User.objects.filter(username='admin').exists():
            user = User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
            return Response({'message': 'Admin seeded'})
        return Response({'message': 'Admin already exists'})
