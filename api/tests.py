import pytest
import time
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from django.core.exceptions import ValidationError
from django.test import TestCase, SimpleTestCase
from django.urls import resolve, reverse
from rest_framework.test import APIClient
from api.models import Program, Student, Enrollment, Room, Exam, Seating, ExamGroup
from api.utils import assign_seats_gen

# --- FIXTURES ---

@pytest.fixture
def mock_student():
    """Factory to create mock students with IDs"""
    def _make_student(id):
        s = MagicMock()
        s.id = id
        s.reg_no = f"21BCA{id:03d}"
        s.name = f"Student {id}"
        return s
    return _make_student

@pytest.fixture
def mock_room():
    """Factory to create mock rooms with layout data"""
    def _make_room(id, rows, left=3, mid=2, right=3):
        r = MagicMock()
        r.id = id
        r.room_number = f"R{id}"
        r.rows = rows
        r.left_seats = left
        r.middle_seats = mid
        r.right_seats = right
        # Total capacity based on existing model logic
        r.total_capacity = rows * (left + mid + right)
        return r
    return _make_room

# --- FUNCTIONAL TESTS ---

def test_seating_completeness(mock_student, mock_room):
    """Ensure all students are assigned a seat when capacity allows"""
    students = [mock_student(i) for i in range(10)]
    rooms = [mock_room(1, 1, 5, 5, 5)] # Capacity 15
    
    assignments = list(assign_seats_gen(students, rooms))
    
    assert len(assignments) == 10
    # Verify no duplicates
    assigned_students = [a[3].id for a in assignments]
    assert len(set(assigned_students)) == 10

def test_seating_distribution(mock_student, mock_room):
    """Validate that seats follow checkerboard-first zig-zag placement"""
    students = [mock_student(i) for i in range(6)]
    rooms = [mock_room(1, 2, 1, 1, 1)] # 2 rows of 3 seats = 6 cap
    
    assignments = list(assign_seats_gen(students, rooms))
    
    assert [(row, seat) for _, row, seat, _ in assignments] == [
        (1, 'Left Seat 1'),
        (1, 'Right Seat 1'),
        (2, 'Middle Seat 1'),
        (1, 'Middle Seat 1'),
        (2, 'Right Seat 1'),
        (2, 'Left Seat 1'),
    ]

def test_insufficient_capacity(mock_student, mock_room):
    """Test that ValueError is raised when more students exist than seats"""
    students = [mock_student(i) for i in range(50)]
    rooms = [mock_room(1, 2, 2, 2, 2)] # Capacity 2 * 6 = 12
    
    with pytest.raises(ValueError) as excinfo:
        list(assign_seats_gen(students, rooms))
    
    assert "Insufficient capacity" in str(excinfo.value)

# --- PERFORMANCE TESTS ---

def test_generation_performance(mock_student, mock_room):
    """Ensure algorithm calculates 1000+ seats in under 500ms"""
    students = [mock_student(i) for i in range(1000)]
    rooms = [mock_room(1, 50, 10, 5, 10) for _ in range(2)] # 50 * 25 * 2 = 2500 cap
    
    start_time = time.time()
    assignments = list(assign_seats_gen(students, rooms))
    end_time = time.time()
    
    duration_ms = (end_time - start_time) * 1000
    print(f"\n[PERF] Generated {len(assignments)} seats in {duration_ms:.2f}ms")
    
    assert duration_ms < 500
    assert len(assignments) == 1000

# --- EDGE CASES ---

def test_zero_students(mock_room):
    """Edge Case: Zero students provided"""
    rooms = [mock_room(1, 10)]
    assignments = list(assign_seats_gen([], rooms))
    assert len(assignments) == 0

def test_single_student_single_seat(mock_student, mock_room):
    """Edge Case: Exactly one student and one seat"""
    students = [mock_student(1)]
    rooms = [mock_room(1, 1, 1, 0, 0)] # Cap 1
    assignments = list(assign_seats_gen(students, rooms))
    assert len(assignments) == 1

def test_unbalanced_rooms(mock_student, mock_room):
    """Edge Case: Rooms with very different row/seat layouts"""
    students = [mock_student(i) for i in range(10)]
    rooms = [
        mock_room(1, 1, 2, 0, 0), # Cap 2
        mock_room(2, 5, 5, 5, 5)  # Cap 75
    ]
    assignments = list(assign_seats_gen(students, rooms))
    assert len(assignments) == 10
    # First room should be filled completely first
    room_ids = [a[0].id for a in assignments]
    assert room_ids.count(1) == 2
    assert room_ids.count(2) == 8

# --- STABILITY TESTS ---

def test_shuffling_consistency(mock_student, mock_room):
    """Ensure repeated runs return the same ordered result"""
    students = [mock_student(i) for i in range(10)]
    rooms = [mock_room(1, 10)]
    
    run1 = [a[3].reg_no for a in assign_seats_gen(students, rooms)]
    run2 = [a[3].reg_no for a in assign_seats_gen(students, rooms)]
    
    assert run1 == run2
    
# --- INVALID INPUTS ---

def test_negative_rows(mock_room, mock_student):
    """Check behavior with invalid layout numbers (Expect empty or graceful stop)"""
    students = [mock_student(1)]
    rooms = [mock_room(1, -5, 1, 1, 1)] # -15 cap
    
    with pytest.raises(ValueError):
        list(assign_seats_gen(students, rooms))


class SeatOrderingUtilityTests(SimpleTestCase):
    def test_assign_seats_uses_natural_reg_no_order(self):
        students = [
            SimpleNamespace(id=1, reg_no='21BCA10', name='Student 10'),
            SimpleNamespace(id=2, reg_no='21BCA2', name='Student 2'),
            SimpleNamespace(id=3, reg_no='21BCA1', name='Student 1'),
            SimpleNamespace(id=4, reg_no='21BCA11', name='Student 11'),
        ]
        rooms = [
            SimpleNamespace(
                id=1,
                room_number='R101',
                rows=2,
                left_seats=1,
                middle_seats=1,
                right_seats=0,
                total_capacity=4,
            ),
        ]

        assignments = list(assign_seats_gen(students, rooms))

        assert [student.reg_no for _, _, _, student in assignments] == [
            '21BCA1',
            '21BCA2',
            '21BCA10',
            '21BCA11',
        ]
        assert [(row, seat) for _, row, seat, _ in assignments] == [
            (1, 'Left Seat 1'),
            (2, 'Middle Seat 1'),
            (1, 'Middle Seat 1'),
            (2, 'Left Seat 1'),
        ]

    def test_assign_seats_preserves_order_across_multiple_rooms(self):
        students = [
            SimpleNamespace(id=1, reg_no='21BCA1', name='Student 1'),
            SimpleNamespace(id=2, reg_no='21BCA2', name='Student 2'),
            SimpleNamespace(id=3, reg_no='21BCA10', name='Student 10'),
            SimpleNamespace(id=4, reg_no='21BCA11', name='Student 11'),
        ]
        rooms = [
            SimpleNamespace(
                id=2,
                room_number='R102',
                rows=1,
                left_seats=1,
                middle_seats=1,
                right_seats=0,
                total_capacity=2,
            ),
            SimpleNamespace(
                id=1,
                room_number='R101',
                rows=1,
                left_seats=1,
                middle_seats=1,
                right_seats=0,
                total_capacity=2,
            ),
        ]

        assignments = list(assign_seats_gen(students, rooms))

        assert [(room.room_number, student.reg_no) for room, _, _, student in assignments] == [
            ('R101', '21BCA1'),
            ('R101', '21BCA10'),
            ('R102', '21BCA2'),
            ('R102', '21BCA11'),
        ]


class SemesterFilteringTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.program = Program.objects.create(name='BCA')

        self.odd_student = Student.objects.create(reg_no='ODD001', name='Odd Student')
        self.even_student = Student.objects.create(reg_no='EVEN001', name='Even Student')
        self.other_odd_student = Student.objects.create(reg_no='ODD003', name='Another Odd Student')

        Enrollment.objects.create(student=self.odd_student, program=self.program, semester=1, section='A', sem_type='ODD')
        Enrollment.objects.create(student=self.even_student, program=self.program, semester=2, section='A', sem_type='EVEN')
        Enrollment.objects.create(student=self.other_odd_student, program=self.program, semester=5, section='B', sem_type='ODD')
        Enrollment.objects.create(student=self.odd_student, program=self.program, semester=2, section='A', sem_type='EVEN')

    def test_odd_filter_returns_only_odd_semesters(self):
        response = self.client.get('/api/students/', {'semester_type': 'ODD'})

        assert response.status_code == 200
        payload = response.json()
        semesters = {
            enrollment['semester']
            for student in payload['results']
            for enrollment in student['enrollments']
        }

        assert semesters == {1, 5}
        assert payload['counts']['filtered'] == 2
        assert payload['counts']['odd'] == 2
        assert payload['counts']['even'] == 2
        assert payload['warning'] == ''
        assert payload['diagnostics']['odd_even_overlap'] == 0

    def test_even_filter_returns_only_even_semesters(self):
        response = self.client.get('/api/students/', {'semester_type': 'EVEN'})

        assert response.status_code == 200
        payload = response.json()
        semesters = {
            enrollment['semester']
            for student in payload['results']
            for enrollment in student['enrollments']
        }

        assert semesters == {2}
        assert payload['counts']['filtered'] == 2
        assert payload['counts']['odd'] == 2
        assert payload['counts']['even'] == 2
        assert payload['warning'] == ''
        assert payload['diagnostics']['odd_even_overlap'] == 0

    def test_filtered_enrollments_do_not_leak_other_semesters(self):
        response = self.client.get('/api/students/', {'semester_type': 'ODD'})

        assert response.status_code == 200
        payload = response.json()
        odd_student = next(student for student in payload['results'] if student['reg_no'] == 'ODD001')

        assert {enrollment['semester'] for enrollment in odd_student['enrollments']} == {1}

    def test_invalid_semester_type_is_rejected(self):
        response = self.client.get('/api/students/', {'semester_type': 'MIXED'})

        assert response.status_code == 400

    def test_invalid_semester_value_is_rejected(self):
        with self.assertRaises(ValidationError):
            Enrollment.objects.create(
                student=Student.objects.create(reg_no='BAD001', name='Bad Semester'),
                program=self.program,
                semester=7,
                section='A',
                sem_type='ODD',
            )


class DepartmentEndpointTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_departments_alias_creates_program(self):
        response = self.client.post('/api/departments/', {'name': 'BCA'}, format='json')

        assert response.status_code == 201
        assert Program.objects.filter(name='BCA').exists()
        payload = response.json()
        assert payload['message'] == 'Department created'
        assert payload['department']['name'] == 'BCA'

    def test_departments_alias_lists_programs(self):
        Program.objects.create(name='BSC')

        response = self.client.get('/api/departments/')

        assert response.status_code == 200
        payload = response.json()
        assert any(item['name'] == 'BSC' for item in payload)

    def test_departments_alias_rejects_duplicate_name_with_clear_error(self):
        Program.objects.create(name='BCA')

        response = self.client.post('/api/departments/', {'name': 'bca '}, format='json')

        assert response.status_code == 400
        payload = response.json()
        assert payload['name'] == ["Department 'BCA' already exists."]

    def test_departments_alias_rejects_wrong_key_with_clear_error(self):
        response = self.client.post('/api/departments/', {'department': 'BCA'}, format='json')

        assert response.status_code == 400
        payload = response.json()
        assert payload['name'] == ['Use "name" instead of "department".']

    def test_departments_alias_rejects_empty_name(self):
        response = self.client.post('/api/departments/', {'name': ''}, format='json')

        assert response.status_code == 400
        payload = response.json()
        assert payload['name']

    def test_departments_alias_updates_program(self):
        program = Program.objects.create(name='BCA')

        response = self.client.patch(f'/api/departments/{program.id}/', {'name': 'BBA'}, format='json')

        assert response.status_code == 200
        payload = response.json()
        assert payload['message'] == 'Department updated'
        assert payload['department']['name'] == 'BBA'
        program.refresh_from_db()
        assert program.name == 'BBA'

    def test_departments_alias_deletes_program(self):
        program = Program.objects.create(name='BCA')

        response = self.client.delete(f'/api/departments/{program.id}/')

        assert response.status_code == 200
        assert not Program.objects.filter(id=program.id).exists()


class SemesterOptionsEndpointTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.program = Program.objects.create(name='BCA')

    def test_semesters_endpoint_requires_department_id(self):
        response = self.client.get('/api/semesters/')

        assert response.status_code == 400
        assert response.json() == {'error': 'department_id required'}

    def test_semesters_endpoint_returns_semester_options(self):
        response = self.client.get('/api/semesters/', {'department_id': self.program.id})

        assert response.status_code == 200
        payload = response.json()
        assert len(payload) == 6
        assert payload[0] == {
            'id': 1,
            'number': 1,
            'name': 'Sem 1',
            'department': self.program.id,
        }


class ExamEndpointTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.program = Program.objects.create(name='BCA')
        self.other_program = Program.objects.create(name='BSC')
        self.exam = Exam.objects.create(
            subject='ENGLISH',
            program=self.program,
            semester=1,
            date='2026-04-15',
            start_time='09:00',
            end_time='12:00',
        )

    def test_exam_update_accepts_department_alias_and_html5_time_inputs(self):
        response = self.client.put(
            f'/api/exams/{self.exam.id}/',
            {
                'subject': 'Data Structures',
                'department': self.other_program.id,
                'semester': 2,
                'date': '2026-04-20',
                'start_time': '09:00',
                'end_time': '12:00',
            },
            format='json',
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload['subject'] == 'DATA STRUCTURES'
        assert payload['program'] == self.other_program.id
        assert payload['semester'] == 2
        assert payload['date'] == '2026-04-20'
        assert payload['start_time'] == '09:00:00'
        assert payload['end_time'] == '12:00:00'

        self.exam.refresh_from_db()
        assert self.exam.subject == 'DATA STRUCTURES'
        assert self.exam.program_id == self.other_program.id
        assert self.exam.semester == 2

    def test_exam_create_accepts_alternate_date_and_ampm_time_formats(self):
        response = self.client.post(
            '/api/exams/',
            {
                'subject': 'Operating Systems',
                'department': self.program.id,
                'semester': 3,
                'date': '20-04-2026',
                'start_time': '09:00 AM',
                'end_time': '12:00 PM',
            },
            format='json',
        )

        assert response.status_code == 201
        payload = response.json()
        assert payload['subject'] == 'OPERATING SYSTEMS'
        assert payload['program'] == self.program.id
        assert payload['date'] == '2026-04-20'
        assert payload['start_time'] == '09:00:00'
        assert payload['end_time'] == '12:00:00'
        assert len(payload['groups']) == 1
        assert payload['groups'][0]['subject'] == 'OPERATING SYSTEMS'

    def test_exam_create_accepts_grouped_exam_payload(self):
        response = self.client.post(
            '/api/exams/',
            {
                'subject': 'COMMON ENGLISH SLOT',
                'exam_type': 'COMMON',
                'date': '2026-04-22',
                'start_time': '09:00',
                'end_time': '12:00',
                'groups': [
                    {'department': self.program.id, 'semester': 1, 'subject': 'English'},
                    {'department': self.other_program.id, 'semester': 3, 'subject': 'English'},
                ],
            },
            format='json',
        )

        assert response.status_code == 201
        payload = response.json()
        assert payload['exam_type'] == 'COMMON'
        assert payload['program'] is None
        assert payload['semester'] is None
        assert payload['is_grouped_exam'] is True
        assert len(payload['groups']) == 2
        assert {group['program'] for group in payload['groups']} == {self.program.id, self.other_program.id}

    def test_exam_partial_update_rejects_invalid_time_order(self):
        response = self.client.patch(
            f'/api/exams/{self.exam.id}/',
            {
                'start_time': '02:00 PM',
                'end_time': '09:00 AM',
            },
            format='json',
        )

        assert response.status_code == 400
        payload = response.json()
        assert payload['end_time'] == ['End time must be after start time.']


class SeatingGenerationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.program = Program.objects.create(name='BCA')
        self.room = Room.objects.create(room_number='R101', rows=10, left_seats=2, middle_seats=2, right_seats=2)
        self.exam = Exam.objects.create(
            subject='ENGLISH',
            program=self.program,
            semester=1,
            date='2026-04-15',
            start_time='09:00',
            end_time='12:00',
        )
        self.student = Student.objects.create(reg_no='1RV001', name='Student One')
        Enrollment.objects.create(
            student=self.student,
            program=self.program,
            semester=1,
            section='A',
            sem_type='ODD',
        )

    def test_seating_generate_endpoint_is_registered(self):
        assert reverse('seating-generate') == '/api/seating/generate/'
        match = resolve('/api/seating/generate/')
        assert match.url_name == 'seating-generate'
        assert reverse('generate-seating') == '/api/generate-seating/'

    def test_seating_generate_requires_exam_and_rooms(self):
        response = self.client.post('/api/seating/generate/', {}, format='json')

        assert response.status_code == 400
        payload = response.json()
        assert payload['message'] == 'Invalid seating generation payload.'
        assert payload['errors']['exam_id'] == ['This field is required.']
        assert payload['errors']['rooms'] == ['This field is required and must be a non-empty array of room IDs.']

    def test_seating_generate_accepts_expected_payload(self):
        response = self.client.post(
            '/api/seating/generate/',
            {'exam_id': self.exam.id, 'rooms': [self.room.id]},
            format='json',
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload['metrics']['allocated'] == 1
        assert payload['exam_type'] == 'CORE'
        assert 'logs' in payload
        assert Seating.objects.filter(exam=self.exam).count() == 1

    def test_seating_generate_rejects_invalid_exam(self):
        response = self.client.post(
            '/api/seating/generate/',
            {'exam_id': 999999, 'rooms': [self.room.id]},
            format='json',
        )

        assert response.status_code == 404
        payload = response.json()
        assert payload['error'] == 'Invalid exam'
        assert payload['details'] == {'exam_id': 999999}

    def test_seating_generate_rejects_exam_without_groups(self):
        empty_exam = Exam.objects.create(
            subject='EMPTY SLOT',
            date='2026-04-18',
            start_time='09:00',
            end_time='12:00',
        )

        response = self.client.post(
            '/api/seating/generate/',
            {'exam_id': empty_exam.id, 'rooms': [self.room.id]},
            format='json',
        )

        assert response.status_code == 400
        payload = response.json()
        assert payload['error'] == 'Exam has no configured groups.'

    def test_seating_generate_rejects_invalid_semester_type(self):
        response = self.client.post(
            '/api/seating/generate/',
            {'exam_id': self.exam.id, 'rooms': [self.room.id], 'semester_type': 'INVALID'},
            format='json',
        )

        assert response.status_code == 400
        assert response.json()['message'] == 'Invalid semester type'

    def test_seating_generate_rejects_semester_type_exam_mismatch(self):
        response = self.client.post(
            '/api/seating/generate/',
            {'exam_id': self.exam.id, 'rooms': [self.room.id], 'semester_type': 'EVEN'},
            format='json',
        )

        assert response.status_code == 400
        payload = response.json()
        assert payload['errors']['semester_type'] == ['EVEN is not valid for exam semester 1.']

    def test_seating_generate_filters_by_semester_type_and_exam_semester(self):
        even_exam = Exam.objects.create(
            subject='MATHS',
            program=self.program,
            semester=2,
            date='2026-04-16',
            start_time='13:00',
            end_time='16:00',
        )
        even_student = Student.objects.create(reg_no='1RV002', name='Student Two')
        Enrollment.objects.create(
            student=even_student,
            program=self.program,
            semester=2,
            section='A',
            sem_type='EVEN',
        )

        response = self.client.post(
            '/api/seating/generate/',
            {'exam_id': self.exam.id, 'rooms': [self.room.id], 'semester_type': 'ODD'},
            format='json',
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload['matched_students'] == 1
        assert payload['metrics']['allocated'] == 1
        assert Seating.objects.filter(exam=even_exam).count() == 0

    def test_seating_generate_spreads_students_safely_across_rooms(self):
        ordered_exam = Exam.objects.create(
            subject='DATABASES',
            program=self.program,
            semester=3,
            date='2026-04-17',
            start_time='09:00',
            end_time='12:00',
        )
        first_room = Room.objects.create(room_number='R201', rows=1, left_seats=1, middle_seats=1, right_seats=0)
        second_room = Room.objects.create(room_number='R202', rows=1, left_seats=1, middle_seats=1, right_seats=0)

        students = [
            Student.objects.create(reg_no='21BCA10', name='Student Ten'),
            Student.objects.create(reg_no='21BCA2', name='Student Two'),
            Student.objects.create(reg_no='21BCA1', name='Student One'),
            Student.objects.create(reg_no='21BCA11', name='Student Eleven'),
        ]
        for student in students:
            Enrollment.objects.create(
                student=student,
                program=self.program,
                semester=3,
                section='A',
                sem_type='ODD',
            )

        response = self.client.post(
            '/api/seating/generate/',
            {'exam_id': ordered_exam.id, 'rooms': [second_room.id, first_room.id]},
            format='json',
        )

        assert response.status_code == 200
        payload = response.json()
        assert 'Ordered students from 21BCA1 to 21BCA11.' in payload['logs']

        seatings = list(
            Seating.objects.filter(exam=ordered_exam)
            .select_related('student', 'room')
            .order_by('room__room_number', 'row', 'seat_position')
        )
        assert [(seat.room.room_number, seat.student.reg_no) for seat in seatings] == [
            ('R201', '21BCA1'),
            ('R201', '21BCA10'),
            ('R202', '21BCA2'),
            ('R202', '21BCA11'),
        ]

    def test_generate_seating_common_exam_mixes_groups_and_sets_exam_groups(self):
        other_program = Program.objects.create(name='BBA')
        common_exam = Exam.objects.create(
            subject='COMMON ENGLISH SLOT',
            exam_type='COMMON',
            date='2026-04-20',
            start_time='09:00',
            end_time='12:00',
        )
        first_group = ExamGroup.objects.create(exam=common_exam, program=self.program, semester=5, subject='ENGLISH')
        second_group = ExamGroup.objects.create(exam=common_exam, program=other_program, semester=3, subject='ENGLISH')
        room = Room.objects.create(room_number='R301', rows=2, left_seats=1, middle_seats=1, right_seats=0)

        bca_students = [
            Student.objects.create(reg_no='21BCA001', name='BCA One'),
            Student.objects.create(reg_no='21BCA011', name='BCA Two'),
        ]
        bba_students = [
            Student.objects.create(reg_no='21BBA001', name='BBA One'),
            Student.objects.create(reg_no='21BBA011', name='BBA Two'),
        ]

        for student in bca_students:
            Enrollment.objects.create(student=student, program=self.program, semester=5, section='A', sem_type='ODD')
        for student in bba_students:
            Enrollment.objects.create(student=student, program=other_program, semester=3, section='A', sem_type='ODD')

        response = self.client.post(
            '/api/generate-seating/',
            {'exam_id': common_exam.id, 'rooms': [room.id]},
            format='json',
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload['exam_type'] == 'COMMON'
        assert payload['diagnostics']['consecutive_id_adjacent'] == 0

        seatings = list(
            Seating.objects.filter(exam=common_exam)
            .select_related('student', 'exam_group__program')
            .order_by('id')
        )
        assert {seat.exam_group_id for seat in seatings} == {first_group.id, second_group.id}
        assert {seat.exam_group.program.name for seat in seatings[:2]} == {'BCA', 'BBA'}

    def test_generate_seating_rejects_unsafe_core_layout(self):
        other_program = Program.objects.create(name='BBA')
        core_exam = Exam.objects.create(
            subject='CORE BLOCK',
            exam_type='CORE',
            date='2026-04-21',
            start_time='09:00',
            end_time='12:00',
        )
        ExamGroup.objects.create(exam=core_exam, program=self.program, semester=3, subject='DBMS')
        ExamGroup.objects.create(exam=core_exam, program=other_program, semester=5, subject='DAA')
        room = Room.objects.create(room_number='R302', rows=1, left_seats=1, middle_seats=0, right_seats=1)

        first_student = Student.objects.create(reg_no='21BCA010', name='Student Ten')
        second_student = Student.objects.create(reg_no='21BCA011', name='Student Eleven')
        Enrollment.objects.create(student=first_student, program=self.program, semester=3, section='A', sem_type='ODD')
        Enrollment.objects.create(student=second_student, program=other_program, semester=5, section='A', sem_type='ODD')

        response = self.client.post(
            '/api/generate-seating/',
            {'exam_id': core_exam.id, 'rooms': [room.id]},
            format='json',
        )

        assert response.status_code == 400
        payload = response.json()
        assert payload['errors']['university_id'] == ['Unsafe layout: 1 adjacent consecutive university-id pair(s) remain.']

    def test_generate_seating_rejects_duplicate_student_matches_across_groups(self):
        grouped_exam = Exam.objects.create(
            subject='MIXED CORE SLOT',
            exam_type='CORE',
            date='2026-04-23',
            start_time='09:00',
            end_time='12:00',
        )
        ExamGroup.objects.create(exam=grouped_exam, program=self.program, semester=1, subject='ENGLISH')
        ExamGroup.objects.create(exam=grouped_exam, program=self.program, semester=2, subject='DBMS')
        duplicated_student = Student.objects.create(reg_no='21BCA777', name='Duplicate Student')
        Enrollment.objects.create(student=duplicated_student, program=self.program, semester=1, section='A', sem_type='ODD')
        Enrollment.objects.create(student=duplicated_student, program=self.program, semester=2, section='A', sem_type='EVEN')

        response = self.client.post(
            '/api/generate-seating/',
            {'exam_id': grouped_exam.id, 'rooms': [self.room.id]},
            format='json',
        )

        assert response.status_code == 400
        payload = response.json()
        assert payload['error'] == 'Some students match more than one exam group.'
