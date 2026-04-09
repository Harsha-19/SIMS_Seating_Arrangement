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
from .models import Student, Room, Exam, Seating, Attendance, AttendanceEntry, Department, Semester, SystemSettings
from .serializers import (
    StudentSerializer, RoomSerializer, ExamSerializer, 
    SeatingSerializer, AttendanceSerializer, UserSerializer,
    DepartmentSerializer, SemesterSerializer
)

from django.db import models

class StudentViewSet(viewsets.ModelViewSet):
    from rest_framework.pagination import PageNumberPagination
    class StudentPagination(PageNumberPagination):
        page_size = 10000
        page_size_query_param = 'page_size'

    queryset = Student.objects.all().select_related('department', 'semester').order_by('-created_at')
    serializer_class = StudentSerializer
    pagination_class = StudentPagination
    parser_classes = (JSONParser, MultiPartParser, FormParser)
    lookup_field = 'university_id'

    def get_queryset(self):
        queryset = Student.objects.all().select_related('department', 'semester').order_by('-created_at')
        dept_id = self.request.query_params.get('department_id')
        sem_id = self.request.query_params.get('semester_id')
        sem_type = self.request.query_params.get('sem_type')
        search = self.request.query_params.get('search')
        
        if dept_id:
            queryset = queryset.filter(department_id=dept_id)
        if sem_id:
            queryset = queryset.filter(semester_id=sem_id)
        if sem_type:
            queryset = queryset.filter(sem_type=sem_type)
        
        # Optimize fields for performance under load
        queryset = queryset.select_related('department', 'semester')
        
        if search:
            queryset = queryset.filter(
                models.Q(name__icontains=search) | 
                models.Q(university_id__icontains=search)
            )
        return queryset

    @action(detail=False, methods=['delete'], url_path='bulk-delete')
    def bulk_delete(self, request):
        ids = request.data.get('ids', [])
        if not ids:
            return Response({'message': 'No IDs provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        from django.db import transaction
        try:
            with transaction.atomic():
                count, _ = Student.objects.filter(university_id__in=ids).delete()
            return Response({'message': f'Successfully deleted {count} students.'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'message': f'Deletion failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['delete'], url_path='clear-all')
    def clear_all(self, request):
        from django.db import transaction
        from django.db.models import Count
        try:
            with transaction.atomic():
                count, _ = Student.objects.all().delete()
                # Mirroring orphan cleanup from upload()
                Semester.objects.annotate(stu_count=Count('students'), ex_count=Count('exams')).filter(stu_count=0, ex_count=0).delete()
                Department.objects.annotate(stu_count=Count('students'), ex_count=Count('exams')).filter(stu_count=0, ex_count=0).delete()
            return Response({'message': f'Successfully cleared {count} students and cleaned up orphans.'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'message': f'Clear failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def upload(self, request):
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({'message': 'Excel file (.xlsx) required. Please select a valid file.'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            from openpyxl import load_workbook
            wb = load_workbook(file_obj, read_only=True)
            sheet = wb.active
            
            # Identify headers (Prioritizing Semester and Class for extraction)
            header_map = {
                'usn': ['usn', 'roll', 'university', 'registration', 'reg', 'id', 'student id'],
                'name': ['name', 'full name', 'student', 'fullname', 'firstname', 'first'],
                'course': ['course', 'department', 'dept', 'branch', 'subject', 'stream'],
                'semester': ['semester', 'sem', 'term', 'session'],
                'class': ['class', 'year', 'yr', 'grade']
            }
            
            # Find the header row
            header_idx = {}
            header_row_num = 0
            
            for row_num, row in enumerate(sheet.iter_rows(min_row=1, max_row=15, values_only=True), start=1):
                if not any(row): continue
                low_row = [str(cell).lower().strip() if cell else "" for cell in row]
                
                temp_map = {}
                matches = 0
                for logic_key, variants in header_map.items():
                    for i, h in enumerate(low_row):
                        if any(v in h for v in variants):
                            temp_map[logic_key] = i
                            matches += 1
                            break
                
                if matches >= 2:
                    if matches >= 3 or not header_idx:
                        header_idx = temp_map
                        header_row_num = row_num
                    if matches >= 3: break
            
            if len(header_idx) < 2:
                return Response({
                    'message': 'Required columns missing. Ensure your Excel has: USN and Name.',
                }, status=status.HTTP_400_BAD_REQUEST)
            
            from django.db import transaction
            from .models import Department, Semester, Student, SystemSettings
            from .utils import extract_semester_info, sanitize_class_info
            
            # Use specific indices found
            idx_usn = header_idx.get('usn')
            idx_name = header_idx.get('name')
            idx_course = header_idx.get('course')

            # PIPELINE METRICS
            total_rows_received = 0
            invalid_rows_removed = 0
            duplicates_removed = 0
            skipped_rows = []
            
            unique_map = {} # usn -> data
            
            import re
            def clean_text(val):
                if not val: return ""
                # Strip + Upper + Remove redundant interior spaces
                return re.sub(r'\s+', ' ', str(val).strip().upper())

            # PHASE 1: PARSE -> CATEGORIZE -> VALIDATE
            for i, row in enumerate(sheet.iter_rows(min_row=header_row_num + 1, values_only=True)):
                if not any(row): continue
                total_rows_received += 1
                
                get_val = lambda idx: str(row[idx]).strip() if idx is not None and idx < len(row) and row[idx] is not None else ""
                raw_uid = clean_text(get_val(idx_usn))
                raw_name = clean_text(get_val(idx_name))
                raw_dept = clean_text(get_val(idx_course))
                
                excel_row = i + header_row_num + 1
                if not raw_uid or not raw_name:
                    skipped_rows.append({"row": excel_row, "reason": "Missing USN/Name"})
                    continue
                
                # Semester Detection Pipeline
                sem_num, sem_group = extract_semester_info(row, header_idx)
                if not sem_num:
                    skipped_rows.append({"row": excel_row, "reason": "Unresolvable semester"})
                    continue

                extracted = sanitize_class_info(f"{raw_dept}")
                processed_dept = extracted['department'] or raw_dept[:20]

                if raw_uid in unique_map:
                    duplicates_removed += 1
                
                unique_map[raw_uid] = {
                    'usn': raw_uid,
                    'name': raw_name,
                    'dept': processed_dept,
                    'sem_num': sem_num,
                    'sem_type': sem_group,
                    'sem_name': f"SEM {sem_num}",
                    'spec': extracted['specialization'],
                    'section': extracted['section']
                }

            if not unique_map:
                return Response({'message': 'No valid rows found.'}, status=status.HTTP_400_BAD_REQUEST)

            # --- STRICT GROUP VALIDATION ---
            groups_found = set(s['sem_type'] for s in unique_map.values())
            if len(groups_found) > 1:
                return Response({
                    'status': 'error',
                    'message': 'DATASET CONTAINS MIXED SEMESTER TYPES. Only ODD (1,3,5) or EVEN (2,4,6) permitted per file.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            detected_group = groups_found.pop()
            current_mode = SystemSettings.get_current_type()
            is_empty = Student.objects.count() == 0
            confirm_override = request.data.get('confirm', 'false').lower() == 'true'

            if not is_empty and current_mode != detected_group and not confirm_override:
                return Response({
                    'status': 'mismatch',
                    'message': f'Uploading this file will switch system to {detected_group} and DELETE all {current_mode} data. Continue?'
                }, status=status.HTTP_200_OK)

            # PHASE 2: ATOMIC TRUNCATE-AND-LOAD
            with transaction.atomic():
                from .models import Department, Semester, Student, SystemSettings
                SystemSettings.set_current_type(detected_group)
                Student.objects.all().delete()
                
                whitelist = ["BCA", "BBA", "BCOM", "BSC", "BA"]
                dept_cache = {d.name: d for d in Department.objects.filter(name__in=whitelist)}
                sem_cache = {f"{s.name}_{s.department_id}": s for s in Semester.objects.all()}
                
                students_to_create = []
                for s_data in unique_map.values():
                    p_dept = s_data['dept']
                    if p_dept not in dept_cache:
                        obj, _ = Department.objects.get_or_create(name=p_dept)
                        dept_cache[p_dept] = obj
                    dept = dept_cache[p_dept]

                    s_name = s_data['sem_name']
                    s_key = f"{s_name}_{dept.id}"
                    if s_key not in sem_cache:
                        obj, _ = Semester.objects.get_or_create(name=s_name, department=dept)
                        sem_cache[s_key] = obj
                    sem = sem_cache[s_key]

                    students_to_create.append(Student(
                        university_id=s_data['usn'],
                        name=s_data['name'],
                        department=dept,
                        semester=sem,
                        sem=s_data['sem_num'],
                        sem_type=s_data['sem_type'],
                        section=s_data['section'],
                        specialization=s_data['spec']
                    ))
                
                Student.objects.bulk_create(students_to_create)

                return Response({
                    'message': f'Successfully uploaded {len(students_to_create)} students in {detected_group} mode.',
                    'group': detected_group
                }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({'message': f'Sync Failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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

    @action(detail=False, methods=['delete'], url_path='bulk-delete')
    def bulk_delete(self, request):
        ids = request.data.get('ids', [])
        if not ids:
            return Response({'message': 'No IDs provided'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            from django.db import transaction
            with transaction.atomic():
                count, _ = Room.objects.filter(id__in=ids).delete()
            return Response({'message': f'Deleted {count} rooms'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ExamViewSet(viewsets.ModelViewSet):
    queryset = Exam.objects.all().order_by('-date')
    serializer_class = ExamSerializer

    @action(detail=False, methods=['delete'], url_path='bulk-delete')
    def bulk_delete(self, request):
        ids = request.data.get('ids', [])
        if not ids:
            return Response({'message': 'No IDs provided'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            from django.db import transaction
            with transaction.atomic():
                count, _ = Exam.objects.filter(id__in=ids).delete()
            return Response({'message': f'Deleted {count} exams'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class SeatingViewSet(viewsets.ModelViewSet):
    queryset = Seating.objects.all()
    serializer_class = SeatingSerializer

    @action(detail=False, methods=['post'])
    def generate(self, request):
        exam_ids = request.data.get('examIds', []) or ([request.data.get('examId')] if request.data.get('examId') else [])
        room_ids = request.data.get('roomIds')
        
        if not exam_ids or not room_ids:
            return Response({'message': 'examIds and roomIds are required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            related_exams = list(Exam.objects.filter(id__in=exam_ids).select_related('department'))
            if not related_exams:
                return Response({'message': 'Exams not found'}, status=status.HTTP_404_NOT_FOUND)
            
            exam = related_exams[0]
            rooms = list(Room.objects.filter(id__in=room_ids).order_by('room_number'))
            
            # PHASE 1: Logging and Diagnostics
            print("--- SEATING GENERATION DIAGNOSTIC ---")
            print(f"Requested Exam: {exam.subject} | ID: {exam.id}")
            print(f"Context Dept: {exam.department.name if exam.department else 'N/A'}")
            print(f"Context Sem: {exam.semester.name if exam.semester else 'N/A'}")
            print(f"Total Database Students: {Student.objects.count()}")

            # PHASE 2: Broadened Context Filtering
            # We filter by Date and Semester NAME (e.g., 'SEM 1') instead of the specific Semester Object.
            # This ensures BCA, BBA, BCOM are all included if they share the same semester name on this date.
            all_context_exams = Exam.objects.filter(
                date=exam.date, 
                semester__name=exam.semester.name,
                department__isnull=False,
                semester__isnull=False
            ).select_related('department', 'semester')
            
            # Fetch valid department IDs for student filtering
            dept_ids = [e.department.id for e in all_context_exams if e.department]
            print(f"Active Departments in Context: {list(all_context_exams.values_list('department__name', flat=True))}")
            
            # Filter students by Semester NAME and Department IDs
            eligible_students = list(Student.objects.filter(
                semester__name=exam.semester.name,
                department_id__in=dept_ids
            ).select_related('department', 'semester'))

            # FALLBACK: If Zero Students found with strict semester name, try broadening further
            if not eligible_students:
                print("WARNING: Zero students found via Name match. Falling back to explicit Department filter.")
                eligible_students = list(Student.objects.filter(
                    department_id__in=dept_ids
                ).select_related('department', 'semester'))

            if not eligible_students:
                print("CRITICAL: Still zero students found after fallback.")
                return Response({
                    'message': f'Zero students found for {exam.subject}',
                    'debug': {
                        'total_students': Student.objects.count(),
                        'filtered_count': 0,
                        'dept_ids': dept_ids,
                        'sem_name': exam.semester.name if exam.semester else 'N/A'
                    }
                }, status=status.HTTP_400_BAD_REQUEST)

            print(f"Eligible Students Found: {len(eligible_students)}")

            from .utils import allocate_multi_room_seating
            from django.db import transaction
            
            # PHASE 5-10: Execute Seating Engine
            engine_output = allocate_multi_room_seating(eligible_students, rooms)
            
            # Create exam lookup for seat mapping (SAFETY: Ensure non-null departments)
            dept_to_exam = {e.department.id: e for e in all_context_exams if e.department}
            
            with transaction.atomic():
                # PHASE 9: Save Final State (Clear old assignments for context)
                Seating.objects.filter(exam__in=all_context_exams, room__in=rooms).delete()
                Attendance.objects.filter(exam__in=all_context_exams, room__in=rooms).delete()
                
                # 1. Bulk create Attendance records first
                atts_to_build = []
                for e in all_context_exams:
                    for r in rooms:
                        atts_to_build.append(Attendance(exam=e, room=r))
                Attendance.objects.bulk_create(atts_to_build, ignore_conflicts=True)
                
                # 2. Map them for O(1) Student assignment
                att_map = {(a.exam_id, a.room_id): a for a in Attendance.objects.filter(exam__in=all_context_exams, room__in=rooms)}
                
                seatings_to_create = []
                entries_to_create = []
                
                for assign in engine_output['assignments']:
                    stu = assign['student']
                    stu_exam = dept_to_exam.get(stu.department_id)
                    room = assign['room']
                    if not stu_exam: continue 
                    
                    seatings_to_create.append(Seating(
                        exam=stu_exam, room=room, row=assign['row'],
                        seat_position=assign['seat_pos'], student=stu
                    ))
                    
                    att = att_map.get((stu_exam.id, room.id))
                    if att:
                        entries_to_create.append(AttendanceEntry(attendance=att, student=stu, present=True))

                Seating.objects.bulk_create(seatings_to_create, batch_size=500)
                AttendanceEntry.objects.bulk_create(entries_to_create, batch_size=500)

            return Response({
                'message': 'SIMS Engine: Multi-room allocation finalized.',
                'studentCount': engine_output['metrics']['allocated'],
                'logs': engine_output['logs'],
                'metrics': engine_output['metrics']
            }, status=status.HTTP_201_CREATED)
        except Exam.DoesNotExist:
            return Response({'message': 'Exam not found'}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as e: # Catch capacity errors from util
            return Response({'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'message': f'System Logic Error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
        
        # Mass optimized update for large rooms
        entries_map = {e.student_id: e for e in attendance.entries.all()}
        updates = []
        for s in student_data:
            entry = entries_map.get(s.get('studentId'))
            if entry:
                entry.booklet_number = s.get('bookletNumber', entry.booklet_number)
                entry.present = s.get('present', entry.present)
                updates.append(entry)
        
        AttendanceEntry.objects.bulk_update(updates, ['booklet_number', 'present'], batch_size=500)
            
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

class SystemSettingsViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]

    def list(self, request):
        mode = SystemSettings.get_current_type()
        return Response({'current_sem_type': mode})

    @action(detail=False, methods=['post'])
    def set_mode(self, request):
        new_mode = request.data.get('mode')
        if new_mode in ['ODD', 'EVEN']:
            from django.db import transaction
            from .models import Student, Semester, Department
            from django.db.models import Count
            
            current_mode = SystemSettings.get_current_type()
            
            if new_mode != current_mode:
                try:
                    with transaction.atomic():
                        # Truncate all student data as per requirements
                        Student.objects.all().delete()
                        
                        # Cleanup orphans to ensure a fresh state for the new mode
                        Semester.objects.annotate(stu_count=Count('students'), ex_count=Count('exams')).filter(stu_count=0, ex_count=0).delete()
                        Department.objects.annotate(stu_count=Count('students'), ex_count=Count('exams')).filter(stu_count=0, ex_count=0).delete()
                        
                        SystemSettings.set_current_type(new_mode)
                        
                    return Response({
                        'message': f'System mode updated to {new_mode} and student data cleared.',
                        'current_sem_type': new_mode
                    })
                except Exception as e:
                    return Response({'message': f'Failed to switch mode: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            return Response({'message': f'System is already in {new_mode} mode.', 'current_sem_type': new_mode})
        return Response({'message': 'Invalid mode'}, status=status.HTTP_400_BAD_REQUEST)
