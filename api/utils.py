import re
from dataclasses import dataclass

def extract_semester(class_str):
    if not class_str:
        return None

    val = str(class_str).upper().strip()

    if "SEM" not in val:
        return None

    # STEP 1: get part before "SEM"
    sem_part = val.split("SEM")[0].strip()

    # STEP 2: get last token of the part before "SEM"
    # Example: "II SEM" -> "II"
    # Example: "BCA II SEM" -> "II"
    tokens = sem_part.split()
    if not tokens:
        return None
    sem_token = tokens[-1] # User requested "Take token before SEM"

    ROMAN_MAP = {
        "I": 1, "II": 2, "III": 3,
        "IV": 4, "V": 5, "VI": 6
    }

    # STEP 3: match Roman or Numeric
    if sem_token in ROMAN_MAP:
        return ROMAN_MAP[sem_token]
    
    # Check if numeric
    numeric_match = re.search(r'(\d+)', sem_token)
    if numeric_match:
        sem_num = int(numeric_match.group(1))
        if 1 <= sem_num <= 6:
            return sem_num

    return None

def extract_program_and_section(class_str):
    """
    Extracts program and section from the part after 'SEM'
    Rule: Last token = section IF single letter (A/B/C/D). 
    Remaining = program.
    """
    if not class_str:
        return {"program": "UNKNOWN", "section": ""}
    
    val = str(class_str).upper().strip()
    
    remainder = val
    if "SEM" in val:
        parts = val.split("SEM", 1)
        remainder = parts[1].strip()
        # Remove leading numbers (e.g. "1" in "I SEM 1 BCA A")
        remainder = re.sub(r'^\d+\b', '', remainder).strip()

    tokens = remainder.split()
    if not tokens:
        return {"program": "UNKNOWN", "section": ""}
    
    section = ""
    last_token = tokens[-1]
    if len(last_token) == 1 and last_token in "ABCD":
        section = last_token
        program_part = " ".join(tokens[:-1]).strip()
    else:
        program_part = " ".join(tokens).strip()
    
    # Normalize program name (B COM -> BCOM, B SC -> BSC, B A -> BA)
    program = program_part.replace("B COM", "BCOM").replace("B SC", "BSC").replace("B A", "BA")
    if not program:
        program = "UNKNOWN"
    
    return {"program": program, "section": section}

def sanitize_academic_info(raw_string):
    """
    Unified 3-Step Extraction Pipeline
    """
    if not raw_string:
        return None
    val = str(raw_string).upper().strip()
    semester = extract_semester(val)
    if semester is None:
        return None
    prog_sec = extract_program_and_section(val)
    return {
        "semester": semester,
        "program": prog_sec["program"],
        "section": prog_sec["section"],
        "sem_type": "ODD" if semester in [1, 3, 5] else "EVEN"
    }


def natural_sort_key(value):
    normalized = str(value or '').strip().upper()
    if not normalized:
        return ((1, ''),)

    return tuple(
        (0, int(part)) if part.isdigit() else (1, part)
        for part in re.split(r'(\d+)', normalized)
        if part
    )


def extract_identifier_parts(value):
    normalized = str(value or '').strip().upper()
    match = re.match(r'^(.*?)(\d+)$', normalized)
    if not match:
        return normalized, None
    return match.group(1), int(match.group(2))


def are_consecutive_identifiers(left_value, right_value):
    left_prefix, left_number = extract_identifier_parts(left_value)
    right_prefix, right_number = extract_identifier_parts(right_value)
    if left_number is None or right_number is None:
        return False
    return left_prefix == right_prefix and abs(left_number - right_number) == 1


def extract_student_identifier(student):
    direct_identifier = getattr(student, 'reg_no', None) or getattr(student, 'university_id', None)
    if direct_identifier not in (None, ''):
        return str(direct_identifier).strip().upper()

    nested_student = getattr(student, 'student', None)
    if nested_student is not None and nested_student is not student:
        return extract_student_identifier(nested_student)

    fallback_identifier = getattr(student, 'id', None)
    if fallback_identifier is not None:
        return str(fallback_identifier)

    return str(student).strip().upper()


def resolve_student_record(student):
    if getattr(student, 'reg_no', None) or getattr(student, 'university_id', None):
        return student

    nested_student = getattr(student, 'student', None)
    if nested_student is not None:
        return nested_student

    return student


def sort_students_by_university_id(students):
    materialized_students = list(students)
    return sorted(materialized_students, key=lambda student: natural_sort_key(extract_student_identifier(student)))


def students_are_sorted_by_university_id(students):
    identifiers = [extract_student_identifier(student) for student in students]
    return identifiers == sorted(identifiers, key=natural_sort_key)


def sort_rooms_for_seating(rooms):
    materialized_rooms = list(rooms)
    return sorted(
        materialized_rooms,
        key=lambda room: natural_sort_key(getattr(room, 'room_number', None) or getattr(room, 'id', None)),
    )


@dataclass(frozen=True)
class SeatingCandidate:
    student: object
    exam_group: object = None
    subject: str = ''
    program_name: str = ''
    semester: int | None = None
    university_id: str = ''
    group_key: tuple = ()


@dataclass(frozen=True)
class SeatSlot:
    room: object
    row: int
    col: int
    seat_pos: str


def build_seating_candidate(student, *, exam_group=None, subject='', program_name='', semester=None, group_key=()):
    student_record = resolve_student_record(student)
    identifier = extract_student_identifier(student_record)
    normalized_subject = str(subject or '').strip().upper()
    return SeatingCandidate(
        student=student_record,
        exam_group=exam_group,
        subject=normalized_subject,
        program_name=str(program_name or '').strip().upper(),
        semester=semester,
        university_id=identifier,
        group_key=group_key,
    )


def candidate_subject(candidate):
    return str(getattr(candidate, 'subject', '') or '').strip().upper()


def column_to_seat_position(room, column_index):
    if column_index < room.left_seats:
        return f"Left Seat {column_index + 1}"
    if column_index < room.left_seats + room.middle_seats:
        return f"Middle Seat {column_index - room.left_seats + 1}"
    return f"Right Seat {column_index - room.left_seats - room.middle_seats + 1}"


def zigzag_positions(rows, cols):
    positions = []
    for row_number in range(rows):
        column_indexes = list(range(cols))
        if row_number % 2 == 1:
            column_indexes.reverse()
        for column_index in column_indexes:
            positions.append((row_number, column_index))
    return positions


def checkerboard_zigzag_positions(rows, cols):
    base_positions = zigzag_positions(rows, cols)
    primary_positions = [position for position in base_positions if (position[0] + position[1]) % 2 == 0]
    secondary_positions = [position for position in base_positions if (position[0] + position[1]) % 2 == 1]
    return primary_positions + secondary_positions


def build_room_seat_slots(room):
    total_columns = room.left_seats + room.middle_seats + room.right_seats
    slots = []
    for row_index, column_index in checkerboard_zigzag_positions(room.rows, total_columns):
        slots.append(
            SeatSlot(
                room=room,
                row=row_index + 1,
                col=column_index,
                seat_pos=column_to_seat_position(room, column_index),
            )
        )
    return slots


def iter_room_seat_slots(room):
    for slot in build_room_seat_slots(room):
        yield slot.row, slot.seat_pos


def round_robin_interleave(grouped_candidates):
    normalized_groups = [list(group) for group in grouped_candidates if group]
    if not normalized_groups:
        return []

    max_group_size = max(len(group) for group in normalized_groups)
    final_sequence = []
    for index in range(max_group_size):
        for group in normalized_groups:
            if index < len(group):
                final_sequence.append(group[index])
    return final_sequence


def normalize_candidate_groups(grouped_candidates, *, split_single_group=False):
    normalized_groups = [list(group) for group in grouped_candidates if group]
    if split_single_group and len(normalized_groups) == 1 and len(normalized_groups[0]) > 1:
        single_group = normalized_groups[0]
        midpoint = (len(single_group) + 1) // 2
        return [single_group[:midpoint], single_group[midpoint:]]
    return normalized_groups


def spread_consecutive_candidates(sequence):
    materialized_sequence = list(sequence)
    midpoint = (len(materialized_sequence) + 1) // 2
    first_half = materialized_sequence[:midpoint]
    second_half = materialized_sequence[midpoint:]

    spread_sequence = []
    for index, candidate in enumerate(first_half):
        spread_sequence.append(candidate)
        if index < len(second_half):
            spread_sequence.append(second_half[index])
    return spread_sequence


def linear_candidate_conflict(left_candidate, right_candidate, exam_type):
    if left_candidate is None or right_candidate is None:
        return False
    if exam_type == 'CORE' and candidate_subject(left_candidate) and candidate_subject(left_candidate) == candidate_subject(right_candidate):
        return True
    return are_consecutive_identifiers(left_candidate.university_id, right_candidate.university_id)


def rebalance_candidate_sequence(sequence, exam_type):
    remaining_candidates = list(sequence)
    rebalanced_sequence = []

    while remaining_candidates:
        previous_candidate = rebalanced_sequence[-1] if rebalanced_sequence else None
        chosen_index = None

        for index, candidate in enumerate(remaining_candidates):
            if not linear_candidate_conflict(previous_candidate, candidate, exam_type):
                chosen_index = index
                break

        if chosen_index is None:
            chosen_index = 0

        rebalanced_sequence.append(remaining_candidates.pop(chosen_index))

    return rebalanced_sequence


def sequence_penalty(sequence, exam_type):
    if len(sequence) < 2:
        return 0

    penalty = 0
    for index in range(1, len(sequence)):
        left_candidate = sequence[index - 1]
        right_candidate = sequence[index]
        if exam_type == 'CORE' and candidate_subject(left_candidate) and candidate_subject(left_candidate) == candidate_subject(right_candidate):
            penalty += 10
        if are_consecutive_identifiers(left_candidate.university_id, right_candidate.university_id):
            penalty += 1
    return penalty


def prepare_candidate_sequence(grouped_candidates, exam_type):
    normalized_groups = normalize_candidate_groups(grouped_candidates)
    if not normalized_groups:
        return []
    if len(normalized_groups) == 1:
        return list(normalized_groups[0])

    base_sequence = round_robin_interleave(normalized_groups)
    spread_sequence = spread_consecutive_candidates(base_sequence)
    chosen_sequence = spread_sequence if sequence_penalty(spread_sequence, exam_type) < sequence_penalty(base_sequence, exam_type) else base_sequence
    return rebalance_candidate_sequence(chosen_sequence, exam_type)


def neighboring_slot_keys(slot):
    for row_delta, col_delta in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        yield (slot.room.id, slot.row + row_delta, slot.col + col_delta)


def candidate_conflicts_with_neighbors(candidate, slot, assignment_map, exam_type):
    for slot_key in neighboring_slot_keys(slot):
        neighbor_assignment = assignment_map.get(slot_key)
        if neighbor_assignment is None:
            continue
        neighbor_candidate = neighbor_assignment['candidate']
        if exam_type == 'CORE' and candidate_subject(candidate) and candidate_subject(candidate) == candidate_subject(neighbor_candidate):
            return True
        if are_consecutive_identifiers(candidate.university_id, neighbor_candidate.university_id):
            return True
    return False


def validate_seating_assignments(assignments, exam_type):
    assignment_map = {
        (assignment['room'].id, assignment['row'], assignment['col']): assignment
        for assignment in assignments
    }
    same_subject_adjacent = []
    consecutive_id_adjacent = []

    for assignment in assignments:
        current_key = (assignment['room'].id, assignment['row'], assignment['col'])
        for neighbor_key in (
            (assignment['room'].id, assignment['row'] + 1, assignment['col']),
            (assignment['room'].id, assignment['row'], assignment['col'] + 1),
        ):
            neighbor_assignment = assignment_map.get(neighbor_key)
            if neighbor_assignment is None:
                continue

            current_candidate = assignment['candidate']
            neighbor_candidate = neighbor_assignment['candidate']

            if exam_type == 'CORE' and candidate_subject(current_candidate) and candidate_subject(current_candidate) == candidate_subject(neighbor_candidate):
                same_subject_adjacent.append((assignment, neighbor_assignment))

            if are_consecutive_identifiers(current_candidate.university_id, neighbor_candidate.university_id):
                consecutive_id_adjacent.append((assignment, neighbor_assignment))

    return {
        'same_subject_adjacent': same_subject_adjacent,
        'consecutive_id_adjacent': consecutive_id_adjacent,
    }


def assign_candidates_to_seat_slots(candidate_sequence, rooms, exam_type):
    ordered_rooms = sort_rooms_for_seating(rooms)
    remaining_candidates = list(candidate_sequence)
    assignments = []
    assignment_map = {}
    room_logs = []

    for room in ordered_rooms:
        if not remaining_candidates:
            break

        room_slots = build_room_seat_slots(room)
        room_seated = 0
        room_first_identifier = None
        room_last_identifier = None

        for slot in room_slots:
            if not remaining_candidates:
                break

            chosen_index = None
            for index, candidate in enumerate(remaining_candidates):
                if not candidate_conflicts_with_neighbors(candidate, slot, assignment_map, exam_type):
                    chosen_index = index
                    break

            if chosen_index is None:
                chosen_index = 0

            candidate = remaining_candidates.pop(chosen_index)
            assignment = {
                'room': room,
                'row': slot.row,
                'col': slot.col,
                'seat_pos': slot.seat_pos,
                'student': candidate.student,
                'exam_group': candidate.exam_group,
                'candidate': candidate,
            }
            assignments.append(assignment)
            assignment_map[(room.id, slot.row, slot.col)] = assignment
            room_seated += 1

            if room_first_identifier is None:
                room_first_identifier = candidate.university_id
            room_last_identifier = candidate.university_id

        if room_seated:
            room_logs.append(
                f"Room {room.room_number} seated {room_seated} student(s) from {room_first_identifier} to {room_last_identifier}."
            )

    return assignments, room_logs


def orchestrate_exam_seating(grouped_candidates, rooms, exam_type='CORE', *, split_single_group=False):
    normalized_groups = normalize_candidate_groups(grouped_candidates, split_single_group=split_single_group)
    flat_candidates = [candidate for group in normalized_groups for candidate in group]
    candidate_sequence = prepare_candidate_sequence(normalized_groups, exam_type)
    assignments, room_logs = assign_candidates_to_seat_slots(candidate_sequence, rooms, exam_type)
    diagnostics = validate_seating_assignments(assignments, exam_type)

    unique_subjects = sorted({candidate_subject(candidate) for candidate in flat_candidates if candidate_subject(candidate)})
    metrics = {
        'total': len(flat_candidates),
        'allocated': len(assignments),
        'remaining': len(flat_candidates) - len(assignments),
    }

    return {
        'assignments': assignments,
        'logs': room_logs,
        'metrics': metrics,
        'diagnostics': {
            'group_count': len(normalized_groups),
            'subject_count': len(unique_subjects),
            'same_subject_adjacent': len(diagnostics['same_subject_adjacent']),
            'consecutive_id_adjacent': len(diagnostics['consecutive_id_adjacent']),
        },
        'violations': diagnostics,
        'ordered_ids': [candidate.university_id for candidate in candidate_sequence],
        'ordered_subjects': unique_subjects,
    }


def allocate_multi_room_seating(students, rooms):
    """
    Backward-compatible deterministic multi-room seating engine.
    """
    ordered_students = sort_students_by_university_id(students)
    if not students_are_sorted_by_university_id(ordered_students):
        raise AssertionError("Students are not sorted properly")

    grouped_candidates = [[build_seating_candidate(student) for student in ordered_students]]
    return orchestrate_exam_seating(grouped_candidates, rooms, exam_type='COMMON')


def assign_seats_gen(students, rooms):
    students = list(students)
    rooms = list(rooms)

    for room in rooms:
        if room.rows < 0 or room.left_seats < 0 or room.middle_seats < 0 or room.right_seats < 0:
            raise ValueError("Insufficient capacity: room layout values must be non-negative.")

    total_capacity = sum(room.rows * (room.left_seats + room.middle_seats + room.right_seats) for room in rooms)
    if len(students) > total_capacity:
        raise ValueError("Insufficient capacity for all students.")

    result = allocate_multi_room_seating(students, rooms)
    for assignment in result['assignments']:
        yield assignment['room'], assignment['row'], assignment['seat_pos'], assignment['student']

def extract_semester_info(row_data, header_idx):
    sources = []
    for key in ['semester', 'class']:
        idx = header_idx.get(key)
        if idx is not None and idx < len(row_data) and row_data[idx] is not None:
            sources.append(str(row_data[idx]).strip().upper())
    
    if not sources:
        return None
    return extract_semester(sources[0])

def detect_semester_number(val):
    return extract_semester(val)
