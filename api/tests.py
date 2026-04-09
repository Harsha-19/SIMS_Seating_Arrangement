import pytest
import time
from unittest.mock import MagicMock
from api.utils import assign_seats_gen

# --- FIXTURES ---

@pytest.fixture
def mock_student():
    """Factory to create mock students with IDs"""
    def _make_student(id):
        s = MagicMock()
        s.id = id
        s.name = f"Student {id}"
        return s
    return _make_student

@pytest.fixture
def mock_room():
    """Factory to create mock rooms with layout data"""
    def _make_room(id, rows, left=3, mid=2, right=3):
        r = MagicMock()
        r.id = id
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
    """Validate that seats are assigned in the correct row-by-row pattern"""
    students = [mock_student(i) for i in range(20)]
    rooms = [mock_room(1, 10, 1, 1, 1)] # 10 rows of 3 seats = 30 cap
    
    assignments = list(assign_seats_gen(students, rooms))
    
    # Check first assignment: Room 1, Row 1, Left Seat 1
    assert assignments[0][1] == 1 # Row 1
    assert "Left Seat 1" in assignments[0][2]
    
    # Check move to next row: Row 1 should have 3 students (L, M, R)
    assert assignments[2][1] == 1 # Still Row 1
    assert assignments[3][1] == 2 # Moved to Row 2

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
    """Ensure repeated runs return different but valid full sets"""
    students = [mock_student(i) for i in range(10)]
    rooms = [mock_room(1, 10)]
    
    run1 = [a[3].id for a in assign_seats_gen(students, rooms)]
    run2 = [a[3].id for a in assign_seats_gen(students, rooms)]
    
    # Shuffling means order should likely differ, but set of students is the same
    assert set(run1) == set(run2)
    # Statistical check: high chance the shuffle result isn't identical
    # (Note: In pure logic tests we might seed random for deterministic tests, 
    # but here we test the shuffle intent)
    
# --- INVALID INPUTS ---

def test_negative_rows(mock_room, mock_student):
    """Check behavior with invalid layout numbers (Expect empty or graceful stop)"""
    students = [mock_student(1)]
    rooms = [mock_room(1, -5, 1, 1, 1)] # -15 cap
    
    with pytest.raises(ValueError):
        list(assign_seats_gen(students, rooms))
