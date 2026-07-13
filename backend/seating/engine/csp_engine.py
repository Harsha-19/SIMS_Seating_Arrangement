import random
import logging
import itertools
import re
import math

logger = logging.getLogger(__name__)

def distribute_students_across_rooms(students, rooms):
    """
    Distribute students across rooms proportionally based on capacity
    using a round-robin approach for maximum fairness.
    """
    if not students or not rooms:
        return {}

    total_students = len(students)
    total_capacity = sum(room.total_capacity for room in rooms)

    if total_students > total_capacity:
        raise ValueError(f"Insufficient capacity: {total_students} students > {total_capacity} seats.")

    # 1. Calculate proportional targets using Largest Remainder Method
    sorted_rooms = sorted(rooms, key=lambda r: r.room_number)
    room_targets = {}
    remainders = []
    current_total = 0

    for room in sorted_rooms:
        proportional_target = (room.total_capacity / total_capacity) * total_students
        count = math.floor(proportional_target)
        room_targets[room.id] = count
        current_total += count
        remainders.append({
            'room_id': room.id,
            'rem': proportional_target - count
        })

    # Distribute leftovers to rooms with largest decimal remainders
    diff = total_students - current_total
    if diff > 0:
        remainders.sort(key=lambda x: x['rem'], reverse=True)
        for i in range(diff):
            room_targets[remainders[i]['room_id']] += 1

    # 2. Group and interleave students (Dept/Sem mix) for fairness
    grouped = {}
    for s in students:
        key = (s.get('program_id'), s.get('semester'))
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(s)

    sorted_keys = sorted(grouped.keys())
    max_len = max(len(g) for g in grouped.values()) if grouped else 0
    interleaved = []
    for i in range(max_len):
        for key in sorted_keys:
            if i < len(grouped[key]):
                interleaved.append(grouped[key][i])

    # 3. Fair Distribution: Round-robin across rooms per group
    distributed = {room.id: [] for room in rooms}
    room_cycle = itertools.cycle(sorted_rooms)
    
    # Sort groups to maintain deterministic behavior
    for key in sorted_keys:
        group_students = grouped[key]
        for student in group_students:
            # Find next room in cycle that has remaining target capacity
            for _ in range(len(rooms)):
                room = next(room_cycle)
                if len(distributed[room.id]) < room_targets[room.id]:
                    distributed[room.id].append(student)
                    break

    return distributed



class SeatingCSPEngine:
    """
    Constraint Satisfaction Problem (CSP) based seating engine for exams.
    Uses backtracking with constraint relaxation strategy.
    """

    MAX_ITERATIONS = 5000

    def __init__(self):
        self.iterations = 0

    def _extract_batch(self, university_id):
        """
        Extract batch identifier from reg_no/university_id.
        Example: 22BCA01 -> 22BCA
        """
        if not university_id:
            return ""
        match = re.match(r'^(.*?)(\d+)$', str(university_id))
        if match:
            return match.group(1)
        return str(university_id)

    def _get_neighbors(self, seat, assignment_map):
        """
        Get neighbors for a given seat.
        Horizontal: (row, col-1), (row, col+1)
        Vertical: (row-1, col), (row+1, col)
        Diagonal: (row-1, col-1), (row-1, col+1), (row+1, col-1), (row+1, col+1)
        """
        row, col = seat
        neighbors = {
            'horizontal': [],
            'vertical': [],
            'diagonal': []
        }
        
        h_offsets = [(0, -1), (0, 1)]
        v_offsets = [(-1, 0), (1, 0)]
        d_offsets = [(-1, -1), (-1, 1), (1, -1), (1, 1)]

        for dr, dc in h_offsets:
            if (row + dr, col + dc) in assignment_map:
                neighbors['horizontal'].append(assignment_map[(row + dr, col + dc)])
        
        for dr, dc in v_offsets:
            if (row + dr, col + dc) in assignment_map:
                neighbors['vertical'].append(assignment_map[(row + dr, col + dc)])

        for dr, dc in d_offsets:
            if (row + dr, col + dc) in assignment_map:
                neighbors['diagonal'].append(assignment_map[(row + dr, col + dc)])

        return neighbors

    def satisfies(self, student, seat, assignment_map, level):
        """
        Check if placing 'student' in 'seat' satisfies constraints for 'level'.
        """
        neighbors = self._get_neighbors(seat, assignment_map)
        
        # S1: No same department adjacent (left/right)
        if level <= 4:
            for n in neighbors['horizontal']:
                if n['program_id'] == student['program_id']:
                    return False
        
        # S2: No same semester adjacent (H/V)
        if level <= 3:
            for n in neighbors['horizontal'] + neighbors['vertical']:
                if n['semester'] == student['semester']:
                    return False

        # S3: No same subject adjacent (H/V)
        if level <= 2:
            for n in neighbors['horizontal'] + neighbors['vertical']:
                if n['subject'] == student['subject']:
                    return False

        # S4: Diagonal gap between same batch
        if level <= 1:
            s_batch = self._extract_batch(student['university_id'])
            for n in neighbors['diagonal']:
                if self._extract_batch(n['university_id']) == s_batch:
                    return False

        return True

    def _backtrack(self, students, seats, level, assignment_map, student_idx):
        self.iterations += 1
        if self.iterations > self.MAX_ITERATIONS:
            return None

        if student_idx == len(students):
            return assignment_map

        student = students[student_idx]
        current_seat = seats[student_idx]
        
        if self.satisfies(student, current_seat, assignment_map, level):
            assignment_map[current_seat] = student
            result = self._backtrack(students, seats, level, assignment_map, student_idx + 1)
            if result is not None:
                return result
            del assignment_map[current_seat]
        
        return None

    def generate(self, students, rooms, optimize=True):
        """
        Main entry point for seating generation.
        """

        total_seats = sum(room.total_capacity for room in rooms)
        if len(students) > total_seats:
            return {
                "success": False,
                "reason": f"Insufficient capacity. Need {len(students)} seats, have {total_seats}."
            }

        # Distribute students across rooms
        try:
            room_assignments = distribute_students_across_rooms(students, rooms)
        except ValueError as e:
            return {
                "success": False,
                "reason": str(e)
            }
        
        final_assignments = []
        for level in range(1, 7):
            self.iterations = 0
            all_rooms_success = True
            current_assignments = []
            
            for room in sorted(rooms, key=lambda r: r.room_number):
                room_students = room_assignments.get(room.id, [])
                if not room_students:
                    continue

                # Use unified grid generator
                from api.utils import build_room_seat_slots
                slots = build_room_seat_slots(room)
                
                # Filter slots to match student count
                seats = [(slot.row, slot.col, slot.seat_pos) for slot in slots[:len(room_students)]]
                
                assignment_map = {}
                # Separate coords for backtrack
                coords = [(s[0], s[1]) for s in seats]
                result_map = self._backtrack(room_students, coords, level, assignment_map, 0)
                
                if result_map is None:
                    all_rooms_success = False
                    break
                
                # Map labels back to assignments
                label_map = {(s[0], s[1]): s[2] for s in seats}
                for (r_idx, c_idx), student in result_map.items():
                    current_assignments.append({
                        'room': room,
                        'row': r_idx,
                        'col': c_idx,
                        'seat_pos': label_map[(r_idx, c_idx)],
                        'student': student['object'],
                        'exam_group': student['exam_group'],
                        'program_id': student['program_id'],
                        'semester': student['semester'],
                        'subject': student['subject'],
                        'university_id': student['university_id']
                    })


            if all_rooms_success:
                logger.info(f"Seating generation succeeded at constraint level {level}")
                
                # AI Optimization Layer
                from api.engine.ai_engine import SeatingScorer, SeatingOptimizer, RiskProfiler
                
                initial_score = SeatingScorer.calculate_assignment_score(current_assignments)
                
                if optimize:
                    optimizer = SeatingOptimizer(iterations=2000)
                    optimized_assignments = optimizer.refine(current_assignments)
                else:
                    optimized_assignments = current_assignments
                
                final_score = SeatingScorer.calculate_assignment_score(optimized_assignments)
                risk_index = RiskProfiler.calculate_risk_index(optimized_assignments, final_score)
                
                return {
                    "success": True,
                    "assignments": optimized_assignments,
                    "constraint_level_used": level,
                    "iterations": self.iterations,
                    "ai_metrics": {
                        "initial_score": initial_score,
                        "final_score": final_score,
                        "improvement": final_score - initial_score,
                        "risk_index": risk_index
                    }
                }



        return {
            "success": False,
            "reason": "Unable to seat all students even after relaxing constraints"
        }
