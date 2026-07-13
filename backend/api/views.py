from rest_framework import viewsets, status, generics
from rest_framework.response import Response
from rest_framework.decorators import action, api_view
from rest_framework.exceptions import ParseError, ValidationError as DRFValidationError
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import AllowAny
from django.db import transaction, models
from django.db.models import Prefetch
from django.core.exceptions import ValidationError as DjangoValidationError
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken
from django.http import HttpResponse, JsonResponse
from .models import (
    Student, Room, Subject, ExamSchedule, Seating, SeatingPlan, Attendance, AttendanceEntry, Program, Enrollment,
    ODD_SEMESTERS, EVEN_SEMESTERS, VALID_SEMESTERS,
)
from .serializers import (
    StudentSerializer, RoomSerializer, SubjectSerializer, ExamScheduleSerializer,
    SeatingSerializer, SeatingPlanSerializer, AttendanceSerializer, UserSerializer,
    ProgramSerializer, EnrollmentSerializer, SemesterOptionSerializer
)
from .services.student_upload_service import StudentUploadError, StudentUploadService

from .utils import (
    extract_semester_info,
    build_seating_candidate,
    extract_student_identifier,
    orchestrate_exam_seating,
    sort_students_by_university_id,
    students_are_sorted_by_university_id,
)
import logging
import re
from collections.abc import Mapping
from seating.engine.csp_engine import SeatingCSPEngine

logger = logging.getLogger(__name__)
STUDENT_FILTER_SEMESTERS = tuple(VALID_SEMESTERS)


def _snapshot_request_data(payload):
    if isinstance(payload, Mapping):
        if hasattr(payload, 'lists'):
            snapshot = {}
            for key, values in payload.lists():
                snapshot[key] = values if len(values) != 1 else values[0]
            return snapshot
        return {key: payload.get(key) for key in payload.keys()}
    return payload


def get_allowed_semesters(semester_type):
    if semester_type == 'ODD':
        return [1, 3, 5]
    if semester_type == 'EVEN':
        return [2, 4, 6]
    raise ValueError('Invalid semester type')


def normalize_semester_type(semester_type, *, required=False):
    if semester_type is None or str(semester_type).strip() == '':
        if required:
            raise ValueError('semester_type is required and must be either "ODD" or "EVEN".')
        return ''

    normalized = str(semester_type).strip().upper()
    get_allowed_semesters(normalized)
    return normalized


def normalize_student_filter_semester(semester):
    if semester in (None, ''):
        return None

    if isinstance(semester, int):
        normalized_semester = semester
    else:
        normalized = str(semester).strip().upper()
        match = re.fullmatch(r'(?:SEM(?:ESTER)?\s*)?(?P<semester>\d+)', normalized)
        if not match:
            raise DjangoValidationError({
                'semester': ['semester must be an integer between 1 and 6.'],
            })
        normalized_semester = int(match.group('semester'))

    if normalized_semester not in STUDENT_FILTER_SEMESTERS:
        raise DjangoValidationError({
            'semester': ['semester must be between 1 and 6.'],
        })

    return normalized_semester


def _response_errors(message, errors=None, **extra):
    payload = {'message': message, 'error': message}
    if errors:
        payload['errors'] = errors
    payload.update(extra)
    return payload


def _parse_generate_seating_payload(payload):
    if not isinstance(payload, Mapping):
        raise ValueError('Expected a JSON object payload.')

    exam_id = payload.get('exam_id')
    room_ids = payload.get('rooms', payload.get('room_ids'))
    semester_type = payload.get('semester_type')

    errors = {}

    if exam_id in (None, ''):
        errors['exam_id'] = ['This field is required.']

    if room_ids in (None, ''):
        errors['rooms'] = ['This field is required and must be a non-empty array of room IDs.']
    elif not isinstance(room_ids, list) or not room_ids:
        errors['rooms'] = ['This field must be a non-empty array of room IDs.']

    if errors:
        raise ValueError(_response_errors('Invalid seating generation payload.', errors))

    try:
        parsed_exam_id = int(exam_id)
    except (TypeError, ValueError) as exc:
        raise ValueError(_response_errors('Invalid seating generation payload.', {
            'exam_id': ['exam_id must be an integer.'],
        })) from exc

    try:
        parsed_room_ids = [int(room_id) for room_id in room_ids]
    except (TypeError, ValueError) as exc:
        raise ValueError(_response_errors('Invalid seating generation payload.', {
            'rooms': ['Each room ID must be an integer.'],
        })) from exc

    normalized_semester_type = normalize_semester_type(semester_type)

    return parsed_exam_id, parsed_room_ids, normalized_semester_type


def _build_grouped_candidates(exam_schedule):
    grouped_candidates = []
    matched_students = 0
    group_logs = []
    seen_student_groups = {}
    student_identifiers = {}
    
    subject = exam_schedule.subject
    program = subject.department
    semester = subject.semester

    if not program or not semester:
        return [], 0, ["Subject missing program or semester"], {}, {}

    enrollments = (
        Enrollment.objects
        .filter(program=program, semester=semester)
        .select_related('student', 'program')
        .order_by('student__reg_no')
    )

    if not enrollments.exists():
        similar_programs = Enrollment.objects.filter(semester=semester).values_list('program__name', flat=True).distinct()
        logger.info(
            "Program %s (Sem %s) has 0 students. Other programs in this semester: %s",
            program.name, semester, list(similar_programs)
        )
        name_query = models.Q(program__name__iexact=program.name)
        p_name_up = program.name.upper()
        if "COMPUTER" in p_name_up or "CS" in p_name_up or "BCA" in p_name_up:
            name_query |= models.Q(program__name__icontains="CS") | models.Q(program__name__icontains="BCA") | models.Q(program__name__icontains="COMPUTER")
        
        enrollments = (
            Enrollment.objects
            .filter(name_query, semester=semester)
            .select_related('student', 'program')
            .order_by('student__reg_no')
        )

    ordered_students = sort_students_by_university_id(enrollment.student for enrollment in enrollments)

    if not students_are_sorted_by_university_id(ordered_students):
        raise AssertionError("Students are not sorted properly")

    candidate_group = []
    for student in ordered_students:
        seen_student_groups.setdefault(student.id, []).append(subject)
        student_identifiers[student.id] = extract_student_identifier(student)
        candidate_group.append(
            build_seating_candidate(
                student,
                exam_group=None,
                subject=subject.subject_name,
                program_name=program.name,
                semester=semester,
                group_key=(program.name, semester, subject.subject_name),
            )
        )

    grouped_candidates.append(candidate_group)
    matched_students += len(candidate_group)
    group_logs.append(
        f"{program.name} SEM {semester} - {subject.subject_name}: {len(candidate_group)} student(s)"
    )

    duplicate_students = {
        student_id: groups
        for student_id, groups in seen_student_groups.items()
        if len(groups) > 1
    }

    return grouped_candidates, matched_students, group_logs, duplicate_students, student_identifiers


def _build_unsafe_seating_response(result, exam_schedule):
    diagnostics = result['diagnostics']
    errors = {}

    if diagnostics['consecutive_id_adjacent']:
        errors['university_id'] = [
            f"Unsafe layout: {diagnostics['consecutive_id_adjacent']} adjacent consecutive university-id pair(s) remain."
        ]

    if exam_schedule.exam_type == 'CORE' and diagnostics['subject_count'] > 1 and diagnostics['same_subject_adjacent']:
        errors['subject'] = [
            f"Unsafe layout: {diagnostics['same_subject_adjacent']} adjacent same-subject pair(s) remain."
        ]

    if not errors:
        return None

    return Response(
        _response_errors(
            'Unsafe seating layout. Add more rooms or split the exam groups further.',
            errors,
            diagnostics=diagnostics,
        ),
        status=status.HTTP_400_BAD_REQUEST,
    )


def _build_generate_seating_response(request):
    try:
        payload = request.data if isinstance(request.data, Mapping) else {}
    except ParseError:
        return Response(
            _response_errors('Invalid JSON payload. Please ensure the request body is valid JSON.'),
            status=status.HTTP_400_BAD_REQUEST
        )
    request_snapshot = {
        'exam_id': payload.get('exam_id'),
        'rooms': payload.get('rooms', payload.get('room_ids')),
        'semester_type': payload.get('semester_type'),
    }
    logger.info("generate_seating request received: %s", request_snapshot)
    print(f"REQUEST HIT: {request_snapshot}")
    
    exam_id, room_ids, semester_type = _parse_generate_seating_payload(payload)

    exam = (
        ExamSchedule.objects
        .select_related('subject__department')
        .filter(id=exam_id)
        .first()
    )
    if not exam:
        logger.warning("generate_seating failed: invalid exam_id=%s", exam_id)
        available_exam_ids = list(ExamSchedule.objects.values_list('id', flat=True)[:10])
        return Response(
            {
                "success": False,
                "error": "ExamSchedule not found",
                "details": {"exam_id": exam_id},
                "available_exam_ids": available_exam_ids
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    logger.info(
        "generate_seating exam lookup: exam_id=%s, exam_type=%s",
        exam.id,
        exam.exam_type,
    )

    if semester_type:
        allowed_semesters = get_allowed_semesters(semester_type)
        if exam.subject.semester not in allowed_semesters:
            logger.warning(
                "generate_seating failed: semester_type=%s does not match exam semester=%s",
                semester_type,
                exam.subject.semester,
            )
            return Response(
                _response_errors(
                    f'Exam semester {exam.subject.semester} does not belong to the {semester_type} semester set {list(allowed_semesters)}.',
                    {
                        'semester_type': [f'{semester_type} is not valid for exam semester {exam.subject.semester}.'],
                    },
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )

    rooms = list(Room.objects.filter(id__in=room_ids).order_by('room_number'))
    if len(rooms) != len(set(room_ids)):
        logger.warning("generate_seating failed: invalid room ids=%s", room_ids)
        return Response(
            _response_errors(
                'One or more selected rooms were not found.',
                {'rooms': ['One or more room IDs are invalid.']},
            ),
            status=status.HTTP_400_BAD_REQUEST,
        )

    grouped_candidates, matched_students, group_logs, duplicate_students, student_identifiers = _build_grouped_candidates(exam)
    total_capacity = sum(room.total_capacity for room in rooms)
    logger.info(
        "generate_seating filters resolved: exam_id=%s, exam_type=%s, rooms=%s, group_logs=%s, matched_students=%s, capacity=%s",
        exam.id,
        exam.exam_type,
        [room.id for room in rooms],
        group_logs,
        matched_students,
        total_capacity,
    )

    if duplicate_students:
        duplicate_messages = []
        for student_id, groups in duplicate_students.items():
            duplicate_messages.append(
                f"Student {student_identifiers.get(student_id, student_id)} matched multiple groups."
            )
        logger.warning("generate_seating failed: duplicate student matches for exam_id=%s", exam.id)
        return Response(
            _response_errors(
                'Some students match more than one exam group.',
                {'groups': duplicate_messages},
            ),
            status=status.HTTP_400_BAD_REQUEST,
        )

    if matched_students == 0:
        logger.warning(
            "generate_seating failed: no enrollments found for exam_id=%s. Group logs: %s",
            exam.id,
            group_logs
        )
        total_students = Student.objects.count()
        total_enrollments = Enrollment.objects.count()
        
        return Response(
            {
                "success": False,
                "error": "No enrolled students found for the selected exam.",
                "details": {
                    "exam_id": exam.id,
                    "matched_students": 0,
                    "total_students_in_db": total_students,
                    "total_enrollments_in_db": total_enrollments,
                    "groups_queried": group_logs,
                    "suggestion": "Ensure students are enrolled in the correct Program and Semester matching the Exam."
                }
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if matched_students > total_capacity:
        logger.warning(
            "generate_seating failed: insufficient capacity for exam_id=%s, matched_students=%s, capacity=%s",
            exam.id,
            matched_students,
            total_capacity,
        )
        return Response(
            {
                "success": False,
                "error": "Insufficient room capacity.",
                "details": {
                    "students": matched_students,
                    "capacity": total_capacity,
                    "shortage": matched_students - total_capacity
                }
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    engine_students = []
    for group in grouped_candidates:
        for candidate in group:
            engine_students.append({
                'object': candidate.student,
                'exam_group': None,
                'program_id': exam.subject.department_id,
                'semester': candidate.semester,
                'subject': candidate.subject,
                'university_id': candidate.university_id
            })

    engine = SeatingCSPEngine()
    result = engine.generate(engine_students, rooms)

    if not result['success']:
        logger.error("generate_seating failed: %s", result.get('reason', 'Unknown reason'))
        return Response(
            _response_errors(result.get('reason', 'Unable to seat all students even after relaxing constraints')),
            status=status.HTTP_400_BAD_REQUEST
        )

    logger.info("generate_seating succeeded using constraint level %s", result['constraint_level_used'])

    preview_only = payload.get('preview_only', False)
    
    with transaction.atomic():
        from django.db.models import Max
        max_version = SeatingPlan.objects.filter(exam_schedule=exam).aggregate(Max('version'))['version__max'] or 0
        next_version = max_version + 1
        
        status_val = 'DRAFT' if preview_only else 'PUBLISHED'
        
        if status_val == 'PUBLISHED':
            SeatingPlan.objects.filter(exam_schedule=exam, status='PUBLISHED').update(status='ARCHIVED')
        
        plan = SeatingPlan.objects.create(
            exam_schedule=exam,
            version=next_version,
            status=status_val,
            constraint_level_used=result['constraint_level_used'],
            published_at=models.functions.Now() if status_val == 'PUBLISHED' else None
        )

        for seat in result['assignments']:
            Seating.objects.create(
                plan=plan,
                exam_schedule=exam,
                room=seat['room'],
                row=seat['row'],
                seat_position=seat['seat_pos'],
                student=seat['student'],
            )

    room_wise_results = []
    assignments_by_room = {}
    for seat in result['assignments']:
        r_id = seat['room'].id
        if r_id not in assignments_by_room:
            assignments_by_room[r_id] = []
        assignments_by_room[r_id].append(seat)

    for room in rooms:
        room_assignments = assignments_by_room.get(room.id, [])
        room_wise_results.append({
            'room_id': room.id,
            'room_number': room.room_number,
            'capacity': room.total_capacity,
            'students_seated': len(room_assignments),
            'assignments': [
                {
                    'row': seat['row'],
                    'col': seat['col'],
                    'seat_pos': seat['seat_pos'],
                    'student_name': seat['student'].name,
                    'reg_no': seat['student'].reg_no,
                    'program': exam.subject.department.name if exam.subject.department else 'DEFAULT',
                    'semester': seat['semester'],
                    'subject': seat['subject']
                }
                for seat in room_assignments
            ]
        })

    ai_metrics = result.get('ai_metrics', {})

    return Response(
        {
            "success": True,
            "message": "Seating generated successfully",
            "data": {
                'message': f'Generated {len(result["assignments"])} seats across {len(rooms)} rooms.',
                'exam_id': exam.id,
                'exam_type': exam.exam_type,
                'semester_type': semester_type or '',
                'matched_students': matched_students,
                'constraint_level_used': result['constraint_level_used'],
                'iterations': result.get('iterations', 0),
                'ai_metrics': ai_metrics,
                'total_score': ai_metrics.get('final_score'),
                'risk_index': ai_metrics.get('risk_index'),
                'rooms': room_wise_results,
                'plan': {
                    'id': plan.id,
                    'version': plan.version,
                    'status': plan.status,
                },
                'logs': [
                    f"Loaded exam {exam.subject.subject_name} ({exam.exam_type}).",
                    f"Validated {len(rooms)} room(s) with total capacity {total_capacity}.",
                    *group_logs,
                    f"Matched {matched_students} enrollment(s).",
                    f"CSP Engine succeeded at level {result['constraint_level_used']}.",
                    f"Placed {len(result['assignments'])} student(s).",
                ],
            }
        },
        status=status.HTTP_200_OK,
    )


@api_view(['POST'])
def generate_seating(request):
    try:
        return _build_generate_seating_response(request)
    except ValueError as exc:
        error_payload = exc.args[0] if exc.args and isinstance(exc.args[0], dict) else _response_errors(str(exc))
        logger.warning("generate_seating validation failed: %s", error_payload)
        return Response(error_payload, status=status.HTTP_400_BAD_REQUEST)
    except Exception:
        logger.exception("generate_seating failed unexpectedly")
        return Response(
            _response_errors('Unable to generate seating due to an internal server error.'),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(['GET'])
def semester_options(request):
    department_id = request.query_params.get('department_id') or request.query_params.get('program_id')
    if not department_id:
        return Response({'error': 'department_id required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        department_id = int(department_id)
    except (TypeError, ValueError):
        return Response({'error': 'department_id must be an integer'}, status=status.HTTP_400_BAD_REQUEST)

    if not Program.objects.filter(id=department_id).exists():
        return Response({'error': 'Department not found'}, status=status.HTTP_404_NOT_FOUND)

    semester_payload = [
        {
            'id': semester,
            'number': semester,
            'name': f'Sem {semester}',
            'department': department_id,
        }
        for semester in VALID_SEMESTERS
    ]
    serializer = SemesterOptionSerializer(semester_payload, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

class StudentViewSet(viewsets.ModelViewSet):
    queryset = Student.objects.all().prefetch_related('enrollments__program').order_by('-created_at')
    serializer_class = StudentSerializer
    parser_classes = (JSONParser, MultiPartParser, FormParser)
    lookup_field = 'reg_no'

    def _normalize_semester_type(self, semester_type):
        return normalize_semester_type(semester_type)

    def _normalize_semester_filter(self, semester):
        return normalize_student_filter_semester(semester)

    def _build_enrollment_queryset(self, semester_type=None):
        if semester_type == 'ODD':
            queryset = Enrollment.objects.filter(
                sem_type='ODD',
                semester__in=ODD_SEMESTERS,
            )
        elif semester_type == 'EVEN':
            queryset = Enrollment.objects.filter(
                sem_type='EVEN',
                semester__in=EVEN_SEMESTERS,
            )
        elif semester_type:
            queryset = Enrollment.objects.none()
        else:
            queryset = Enrollment.objects.all()

        return queryset.select_related('student', 'program').order_by(
            'student_id', 'program__name', 'semester', 'section', '-created_at'
        )

    def _build_queryset(self, semester_type=None):
        enrollment_queryset = self._build_enrollment_queryset(semester_type)
        program_id = self.request.query_params.get('program_id')
        semester = self._normalize_semester_filter(self.request.query_params.get('semester'))
        section = self.request.query_params.get('section')
        search = self.request.query_params.get('search')

        if program_id:
            enrollment_queryset = enrollment_queryset.filter(program_id=program_id)
        if semester:
            enrollment_queryset = enrollment_queryset.filter(semester=semester)
        if section:
            enrollment_queryset = enrollment_queryset.filter(section=section)

        queryset = Student.objects.all()

        if search:
            queryset = queryset.filter(
                models.Q(name__icontains=search) |
                models.Q(reg_no__icontains=search)
            )

        if semester_type or program_id or semester or section:
            matching_enrollments = enrollment_queryset.filter(student_id=models.OuterRef('pk'))
            queryset = (
                queryset
                .annotate(has_matching_enrollment=models.Exists(matching_enrollments))
                .filter(has_matching_enrollment=True)
            )

        queryset = (
            queryset
            .prefetch_related(
                Prefetch(
                    'enrollments',
                    queryset=enrollment_queryset,
                    to_attr='filtered_enrollments',
                )
            )
            .order_by('-created_at')
        )
        return queryset, enrollment_queryset.distinct()

    def get_queryset(self):
        semester_type = self.request.query_params.get('semester_type') or self.request.query_params.get('sem_type')
        normalized_semester_type = self._normalize_semester_type(semester_type)
        queryset, _ = self._build_queryset(normalized_semester_type)
        return queryset

    def list(self, request, *args, **kwargs):
        try:
            semester_type = request.GET.get("semester_type", None)
            semester_type = self._normalize_semester_type(
                semester_type or request.query_params.get('sem_type')
            )
            semester = self._normalize_semester_filter(request.query_params.get('semester'))
            search = str(request.query_params.get('search', '') or '').strip()
            # Fetch necessary data
            queryset, _ = self._build_queryset(semester_type)
            filtered_count = queryset.count()

            # Pagination
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data, filtered_count)

            serializer = self.get_serializer(queryset, many=True)
            
            return Response({
                'results': serializer.data,
                'counts': {
                    'filtered': filtered_count,
                    'odd': 0,
                    'even': 0,
                },
                'filters': {
                    'semester': semester,
                    'semester_type': semester_type or '',
                    'search': search,
                },
                'semester_type': semester_type or 'ALL',
                'success': True
            })
        except (DjangoValidationError, ValueError) as exc:
            if isinstance(exc, ValueError):
                detail = str(exc)
            else:
                detail = exc.message_dict if hasattr(exc, 'message_dict') else exc.messages

            error_payload = {
                'results': [],
                'counts': {
                    'filtered': 0,
                    'odd': 0,
                    'even': 0
                },
                'success': False,
            }
            if isinstance(detail, dict):
                error_payload.update({
                    'message': 'Invalid student filters.',
                    'error': 'Invalid student filters.',
                    'errors': detail,
                })
            else:
                error_message = str(detail)
                error_payload.update({
                    'message': error_message,
                    'error': error_message,
                })

            return Response(error_payload, status=status.HTTP_400_BAD_REQUEST)

    def get_paginated_response(self, data, filtered_count=None):
        return Response({
            'results': data,
            'counts': {
                'filtered': filtered_count if filtered_count is not None else self.paginator.page.paginator.count,
                'odd': 0,
                'even': 0,
            },
            'success': True
        })

    @action(detail=False, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def upload(self, request):
        logger.info("Student upload endpoint hit.")
        logger.info("Student upload request content_type=%s", request.content_type)
        logger.info("Student upload request files=%s", list(request.FILES.keys()))

        file_obj = request.FILES.get('file')
        if not file_obj:
            logger.warning("Student upload rejected because request.FILES did not include 'file'.")
            return Response(
                {
                    'message': 'Excel file required. Submit the request as multipart/form-data with a file field.',
                    'request_files': list(request.FILES.keys()),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            response_payload = StudentUploadService.process(file_obj)
            logger.info("Student upload succeeded with summary=%s", response_payload)
            return Response(response_payload, status=status.HTTP_200_OK)
        except StudentUploadError as exc:
            logger.warning("Student upload validation failed: %s", exc)
            return Response(
                {
                    'message': str(exc),
                    'filename': getattr(file_obj, 'name', ''),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception:
            logger.exception("Student upload failed unexpectedly for filename=%s", getattr(file_obj, 'name', ''))
            return Response(
                {
                    'message': 'Upload failed due to an internal server error.',
                    'filename': getattr(file_obj, 'name', ''),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


    @action(detail=False, methods=['delete'], url_path='bulk-delete')
    def bulk_delete(self, request):
        ids = request.data.get('ids', [])
        if not ids:
            return Response({'message': 'No IDs provided'}, status=status.HTTP_400_BAD_REQUEST)
        Student.objects.filter(reg_no__in=ids).delete()
        return Response({'message': f'Deleted {len(ids)} students'}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['delete'], url_path='clear-all')
    def clear_all(self, request):
        with transaction.atomic():
            Enrollment.objects.all().delete()
            Student.objects.all().delete()
        return Response({'message': 'All student records cleared'}, status=status.HTTP_200_OK)

class ProgramViewSet(viewsets.ModelViewSet):
    queryset = Program.objects.all().order_by('name')
    serializer_class = ProgramSerializer


class DepartmentViewSet(ProgramViewSet):
    """
    Backward-compatible alias for legacy frontend code that still uses
    `/api/departments/` after the Department model was renamed to Program.
    """
    queryset = Program.objects.all().order_by('-created_at')

    def _validate_department_payload(self, request, *, partial=False, instance=None):
        print("Incoming Data:", request.data)

        if not isinstance(request.data, Mapping):
            errors = {'non_field_errors': ['Expected a JSON object like {"name": "BCA"} .']}
            print("Serializer Errors:", errors)
            return None, Response(errors, status=status.HTTP_400_BAD_REQUEST)

        if 'name' not in request.data and 'department' in request.data:
            errors = {'name': ['Use "name" instead of "department".']}
            print("Serializer Errors:", errors)
            return None, Response(errors, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(instance=instance, data=request.data, partial=partial)
        if serializer.is_valid():
            return serializer, None

        print("Serializer Errors:", serializer.errors)
        logger.warning(
            "Department create validation failed",
            extra={
                'request_data': dict(request.data),
                'errors': serializer.errors,
            },
        )
        return None, Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def create(self, request, *args, **kwargs):
        serializer, error_response = self._validate_department_payload(request)
        if error_response:
            return error_response

        instance = serializer.save()
        response_serializer = self.get_serializer(instance)
        return Response(
            {
                'message': 'Department created',
                'department': response_serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer, error_response = self._validate_department_payload(
            request,
            partial=True,
            instance=instance,
        )
        if error_response:
            return error_response

        instance = serializer.save()
        response_serializer = self.get_serializer(instance)
        return Response(
            {
                'message': 'Department updated',
                'department': response_serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        name = instance.name
        instance.delete()
        return Response(
            {'message': f"Department '{name}' deleted."},
            status=status.HTTP_200_OK,
        )

class EnrollmentViewSet(viewsets.ModelViewSet):
    queryset = Enrollment.objects.all().select_related('student', 'program')
    serializer_class = EnrollmentSerializer

class RoomViewSet(viewsets.ModelViewSet):
    queryset = Room.objects.all().order_by('room_number')
    serializer_class = RoomSerializer

class SubjectViewSet(viewsets.ModelViewSet):
    queryset = Subject.objects.all().select_related('department').order_by('subject_code')
    serializer_class = SubjectSerializer

class ExamScheduleViewSet(viewsets.ModelViewSet):
    queryset = ExamSchedule.objects.all().select_related('subject__department').order_by('exam_date', 'start_time')
    serializer_class = ExamScheduleSerializer

    # TODO: uncomment when auth is implemented to enforce admin-only deletion
    # def get_permissions(self):
    #     if self.action == 'destroy':
    #         return [permissions.IsAdminUser()]
    #     return super().get_permissions()

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # Check if the schedule is used by seating plans, seats, or attendance
        if (instance.seating_plans.exists() or 
            instance.seats.exists() or 
            instance.attendances.exists()):
            return Response(
                {"error": "This exam schedule cannot be deleted because seating or attendance records have already been generated."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)


class SeatingPlanViewSet(viewsets.ModelViewSet):
    queryset = SeatingPlan.objects.all().order_by('-generated_at')
    serializer_class = SeatingPlanSerializer

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        plan = self.get_object()
        with transaction.atomic():
            # Archive other versions for the same exam
            SeatingPlan.objects.filter(
                exam_schedule=plan.exam_schedule, 
                status='PUBLISHED'
            ).exclude(id=plan.id).update(status='ARCHIVED')
            
            plan.status = 'PUBLISHED'
            plan.published_at = models.functions.Now()
            plan.save()
            
        return Response({
            'message': f'Plan v{plan.version} for {plan.exam_schedule.subject.subject_name} has been published.',
            'status': plan.status,
            'published_at': plan.published_at
        })

    @action(detail=False, methods=['get'])
    def versions(self, request):
        exam_id = request.query_params.get('exam_id')
        if not exam_id:
            return Response({'error': 'exam_id query parameter is required.'}, status=status.HTTP_400_BAD_REQUEST)
        
        plans = self.queryset.filter(exam_schedule_id=exam_id)
        serializer = self.get_serializer(plans, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['patch'])
    def move(self, request, pk=None):
        plan = self.get_object()
        student_id = request.data.get('student_id')
        target_room_id = request.data.get('target_room_id')
        row = request.data.get('row')
        col = request.data.get('col')
        seat_pos = request.data.get('seat_pos')

        try:
            assignment = Seating.objects.get(plan=plan, student_id=student_id)
            room = Room.objects.get(id=target_room_id)
            
            with transaction.atomic():
                # Check if target is occupied
                collision = Seating.objects.filter(plan=plan, room=room, row=row, seat_position=seat_pos).exclude(student_id=student_id).first()
                if collision:
                    return Response({'error': f'Seat {seat_pos} is already occupied by {collision.student.name}'}, status=status.HTTP_400_BAD_REQUEST)
                
                assignment.room = room
                assignment.row = row
                assignment.seat_position = seat_pos
                assignment.save()
            
            # Simple warning logic (could be expanded with full CSP check)
            warnings = []
            return Response({'message': 'Seat updated successfully', 'warnings': warnings})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['patch'])
    def swap(self, request, pk=None):
        plan = self.get_object()
        student_a_id = request.data.get('student_a_id')
        student_b_id = request.data.get('student_b_id')

        try:
            with transaction.atomic():
                assign_a = Seating.objects.get(plan=plan, student_id=student_a_id)
                assign_b = Seating.objects.get(plan=plan, student_id=student_b_id)

                # Swap coordinates
                a_room, a_row, a_pos = assign_a.room, assign_a.row, assign_a.seat_position
                
                assign_a.room, assign_a.row, assign_a.seat_position = assign_b.room, assign_b.row, assign_b.seat_position
                assign_b.room, assign_b.row, assign_b.seat_position = a_room, a_row, a_pos
                
                assign_a.save()
                assign_b.save()

            return Response({'message': 'Seats swapped successfully', 'warnings': []})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def export_excel(self, request, pk=None):
        from .services.export_service import ExcelExportService
        plan = self.get_object()
        output = ExcelExportService.generate_plan_excel(plan)
        
        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="seating_plan_{plan.id}.xlsx"'
        return response

    @action(detail=True, methods=['get'])
    def export_pdf(self, request, pk=None):
        from .services.export_service import PDFExportService
        plan = self.get_object()
        buffer = PDFExportService.generate_plan_pdf(plan)
        
        response = HttpResponse(buffer.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="seating_plan_{plan.id}.pdf"'
        return response

    @action(detail=True, methods=['get'])
    def export_attendance(self, request, pk=None):
        from .services.export_service import PDFExportService
        plan = self.get_object()
        buffer = PDFExportService.generate_attendance_pdf(plan)
        
        response = HttpResponse(buffer.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="attendance_{plan.id}.pdf"'
        return response

    @action(detail=True, methods=['get'])
    def export_hall_tickets(self, request, pk=None):
        from .services.export_service import PDFExportService
        plan = self.get_object()
        buffer = PDFExportService.generate_hall_tickets(plan)
        
        response = HttpResponse(buffer.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="hall_tickets_{plan.id}.pdf"'
        return response



from django.db.models import Count, Q, Avg
from rest_framework.views import APIView

class AnalyticsViewSet(viewsets.ViewSet):
    def list(self, request):
        total_students = Student.objects.count()
        total_exams = ExamSchedule.objects.count()
        total_plans = SeatingPlan.objects.filter(status='PUBLISHED').count()
        
        # Room Utilization
        # Based on latest published plan for each exam
        rooms = Room.objects.all()
        room_data = []
        for room in rooms:
            # How many students are currently assigned to this room across all PUBLISHED plans?
            # Or maybe just based on the last published plan globally?
            # Let's show "Capacity vs Assignments" for the most recent published plans.
            last_published_plans = SeatingPlan.objects.filter(status='PUBLISHED').order_by('-published_at')[:5]
            avg_occupancy = Seating.objects.filter(
                plan__in=last_published_plans,
                room=room
            ).count() / len(last_published_plans) if last_published_plans.exists() else 0
            
            room_data.append({
                'name': room.room_number,
                'total': room.total_capacity,
                'used': round(avg_occupancy, 1),
                'percentage': round((avg_occupancy / room.total_capacity * 100), 1) if room.total_capacity > 0 else 0
            })

        # Constraint Satisfaction Distribution
        dist = SeatingPlan.objects.values('constraint_level_used').annotate(count=Count('id')).order_by('constraint_level_used')
        levels = {str(i): 0 for i in range(1, 7)}
        for item in dist:
            levels[str(item['constraint_level_used'])] = item['count']
        
        # Dept Distribution
        from .models import Enrollment
        dept_dist = Enrollment.objects.values('program__name').annotate(count=Count('student_id', distinct=True)).order_by('-count')
        dept_data = [{'name': item['program__name'], 'value': item['count']} for item in dept_dist]

        return Response({
            'stats': {
                'students': total_students,
                'exams': total_exams,
                'plans': total_plans,
                'rooms': rooms.count()
            },
            'room_utilization': room_data,
            'constraints': [{'level': k, 'count': v} for k, v in levels.items()],
            'departments': dept_data
        })

class SeatingViewSet(viewsets.ModelViewSet):
    queryset = Seating.objects.all().select_related('exam_schedule__subject__department', 'room', 'student')
    serializer_class = SeatingSerializer

class AttendanceViewSet(viewsets.ModelViewSet):
    queryset = Attendance.objects.all().select_related('exam_schedule__subject', 'room').order_by('-created_at')
    serializer_class = AttendanceSerializer

class LoginView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = UserSerializer

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(username=username, password=password)
        if user:
            refresh = RefreshToken.for_user(user)
            return Response({
                'token': str(refresh.access_token),
                'user': UserSerializer(user).data
            })
        return Response({'message': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

class SeedAdminView(generics.GenericAPIView):
    permission_classes = [AllowAny]

    def post(self, request):
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
            return Response({'message': 'Admin created (admin/admin123)'})
        return Response({'message': 'Admin already exists'})


def chrome_devtools_config(request):
    """
    Handle requests to .well-known/appspecific/com.chrome.devtools.json
    and return an empty JSON response.
    """
    return JsonResponse({})
