import logging
import re
from dataclasses import dataclass
from typing import Any, Literal, TypedDict

logger = logging.getLogger(__name__)


class ProgramSection(TypedDict):
    program: str
    section: str


class AcademicInfo(TypedDict):
    semester: int
    program: str
    section: str
    sem_type: Literal["ODD", "EVEN"]


ROMAN_SEMESTER_MAP: dict[str, int] = {
    "I": 1,
    "II": 2,
    "III": 3,
    "IV": 4,
    "V": 5,
    "VI": 6,
}
VALID_SECTION_TOKENS = {"A", "B", "C", "D"}
SEMESTER_TOKEN_REGEX = r"VI|IV|V|III|II|I|[1-6]"
SEMESTER_PATTERNS = (
    re.compile(rf"\bSEM(?:ESTER)?\s*[-:]?\s*(?P<semester>{SEMESTER_TOKEN_REGEX})\b"),
    re.compile(rf"\b(?P<semester>{SEMESTER_TOKEN_REGEX})\s*[-:]?\s*SEM(?:ESTER)?\b"),
)
IGNORED_ACADEMIC_TOKENS = {"CLASS", "COURSE", "PROGRAM", "SEC", "SECTION", "YEAR"}
PROGRAM_TOKEN_ALIASES: dict[tuple[str, str], str] = {
    ("B", "A"): "BA",
    ("B", "CA"): "BCA",
    ("B", "COM"): "BCOM",
    ("B", "SC"): "BSC",
    ("B", "BA"): "BBA",
    ("M", "A"): "MA",
    ("M", "BA"): "MBA",
    ("M", "CA"): "MCA",
    ("M", "COM"): "MCOM",
    ("M", "SC"): "MSC",
}


def _default_program_section() -> ProgramSection:
    return {"program": "UNKNOWN", "section": ""}


def _normalize_academic_string(value: Any) -> str:
    if value is None:
        return ""

    normalized = str(value).upper().strip()
    if not normalized:
        return ""

    normalized = re.sub(r"[\.,:/\\_\-\(\)\[\]]+", " ", normalized)
    normalized = re.sub(r"\bSEMESTER\b", "SEM", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def _semester_token_to_int(token: str) -> int | None:
    token = str(token or "").strip().upper()
    if token in ROMAN_SEMESTER_MAP:
        return ROMAN_SEMESTER_MAP[token]

    if token.isdigit():
        semester = int(token)
        if 1 <= semester <= 6:
            return semester

    return None


def _is_semester_token(token: str) -> bool:
    return _semester_token_to_int(token) is not None


def _normalize_program_tokens(tokens: list[str]) -> str:
    normalized_tokens: list[str] = []
    index = 0

    while index < len(tokens):
        pair = None
        if index + 1 < len(tokens):
            pair = (tokens[index], tokens[index + 1])

        if pair in PROGRAM_TOKEN_ALIASES:
            normalized_tokens.append(PROGRAM_TOKEN_ALIASES[pair])
            index += 2
            continue

        normalized_tokens.append(tokens[index])
        index += 1

    return re.sub(r"\s+", " ", " ".join(normalized_tokens)).strip()


def _looks_like_valid_program(program: str) -> bool:
    if not program or program == "UNKNOWN":
        return False

    cleaned_tokens = [re.sub(r"[^A-Z0-9]", "", token) for token in program.split()]
    cleaned_tokens = [token for token in cleaned_tokens if token]
    if not cleaned_tokens:
        return False

    return any(len(token) >= 2 for token in cleaned_tokens)


def _program_quality(program: str) -> int:
    if not _looks_like_valid_program(program):
        return -1

    tokens = [token for token in program.split() if token]
    score = 0
    for token in tokens:
        score += 4 if len(token) >= 2 else 0
        score -= 2 if len(token) == 1 else 0
    score -= max(len(tokens) - 1, 0)
    return score


def extract_semester(class_str: Any, debug: bool = False) -> int | None:
    """
    Extract a semester number from a class string.

    Supported values include Roman numerals ``I``-``VI`` and numeric semesters
    ``1``-``6`` appearing before or after ``SEM``.
    """
    try:
        normalized = _normalize_academic_string(class_str)
        if not normalized:
            if debug:
                logger.warning("extract_semester received an empty academic string: %r", class_str)
            else:
                logger.debug("extract_semester received an empty academic string: %r", class_str)
            return None

        matches: list[tuple[int, int, str]] = []
        for pattern in SEMESTER_PATTERNS:
            for match in pattern.finditer(normalized):
                semester = _semester_token_to_int(match.group("semester"))
                if semester is not None:
                    matches.append((match.start(), semester, match.group(0)))

        if not matches:
            if debug:
                logger.warning("No semester token could be extracted from %r", normalized)
            else:
                logger.debug("No semester token could be extracted from %r", normalized)
            return None

        matches.sort(key=lambda item: item[0])
        semester = matches[0][1]
        logger.debug(
            "extract_semester parsed %r into semester=%s using token=%r",
            normalized,
            semester,
            matches[0][2],
        )
        return semester
    except Exception:
        logger.exception("Unexpected error while extracting semester from %r", class_str)
        return None


def extract_program_and_section(class_str: Any, debug: bool = False) -> ProgramSection:
    """
    Extract and normalize the academic program and optional section.

    Semester markers and tokens are stripped before program detection so the
    function can handle both ``BCA V SEM`` and ``V SEM BCA`` style inputs.
    """
    try:
        normalized = _normalize_academic_string(class_str)
        if not normalized:
            if debug:
                logger.warning("extract_program_and_section received an empty academic string: %r", class_str)
            else:
                logger.debug("extract_program_and_section received an empty academic string: %r", class_str)
            return _default_program_section()

        filtered_tokens = [
            token
            for token in normalized.split()
            if token not in {"SEM", "SEMESTER"}
            and token not in IGNORED_ACADEMIC_TOKENS
            and not _is_semester_token(token)
            and not token.isdigit()
        ]

        if not filtered_tokens:
            if debug:
                logger.warning("No program tokens remained after cleanup for %r", normalized)
            else:
                logger.debug("No program tokens remained after cleanup for %r", normalized)
            return _default_program_section()

        program_tokens = filtered_tokens
        section = ""

        if filtered_tokens[-1] in VALID_SECTION_TOKENS:
            with_section_program = _normalize_program_tokens(filtered_tokens[:-1])
            without_section_program = _normalize_program_tokens(filtered_tokens)
            if _program_quality(with_section_program) > _program_quality(without_section_program):
                section = filtered_tokens[-1]
                program_tokens = filtered_tokens[:-1]

        program = _normalize_program_tokens(program_tokens)
        if not _looks_like_valid_program(program):
            if debug:
                logger.warning(
                    "Program extraction failed for %r after cleanup tokens=%r",
                    normalized,
                    filtered_tokens,
                )
            else:
                logger.debug(
                    "Program extraction failed for %r after cleanup tokens=%r",
                    normalized,
                    filtered_tokens,
                )
            return _default_program_section()

        result: ProgramSection = {"program": program, "section": section}
        logger.debug(
            "extract_program_and_section parsed %r into program=%r section=%r",
            normalized,
            result["program"],
            result["section"],
        )
        return result
    except Exception:
        logger.exception("Unexpected error while extracting program/section from %r", class_str)
        return _default_program_section()


def sanitize_academic_info(raw_string: Any, debug: bool = False) -> AcademicInfo | None:
    """
    Parse an uploaded academic class string into normalized enrollment metadata.

    Returns a structured dictionary when parsing succeeds and ``None`` only when
    the semester or program cannot be safely derived.
    """
    try:
        normalized = _normalize_academic_string(raw_string)
        if not normalized:
            if debug:
                logger.warning("sanitize_academic_info received an empty academic string: %r", raw_string)
            else:
                logger.debug("sanitize_academic_info received an empty academic string: %r", raw_string)
            return None

        semester = extract_semester(normalized, debug=debug)
        if semester is None:
            if debug:
                logger.warning("sanitize_academic_info could not extract semester from %r", normalized)
            else:
                logger.debug("sanitize_academic_info could not extract semester from %r", normalized)
            return None

        prog_sec = extract_program_and_section(normalized, debug=debug)
        program = str(prog_sec.get("program", "UNKNOWN")).strip().upper()
        section = str(prog_sec.get("section", "")).strip().upper()

        if not _looks_like_valid_program(program):
            if debug:
                logger.warning("sanitize_academic_info could not extract program from %r", normalized)
            else:
                logger.debug("sanitize_academic_info could not extract program from %r", normalized)
            return None

        if section not in VALID_SECTION_TOKENS:
            section = ""

        result: AcademicInfo = {
            "semester": semester,
            "program": program,
            "section": section,
            "sem_type": "ODD" if semester % 2 else "EVEN",
        }
        logger.debug("sanitize_academic_info parsed %r into %s", normalized, result)
        return result
    except Exception:
        logger.exception("Unexpected error while sanitizing academic info from %r", raw_string)
        return None


ACADEMIC_PARSE_VALIDATION_CASES: tuple[tuple[str, AcademicInfo], ...] = (
    ("BCA V Sem", {"semester": 5, "program": "BCA", "section": "", "sem_type": "ODD"}),
    ("BCA V SEM", {"semester": 5, "program": "BCA", "section": "", "sem_type": "ODD"}),
    ("BCA 5 SEM", {"semester": 5, "program": "BCA", "section": "", "sem_type": "ODD"}),
    ("V SEM BCA", {"semester": 5, "program": "BCA", "section": "", "sem_type": "ODD"}),
    ("III SEM BCOM", {"semester": 3, "program": "BCOM", "section": "", "sem_type": "ODD"}),
    ("BCOM III SEM", {"semester": 3, "program": "BCOM", "section": "", "sem_type": "ODD"}),
    ("1 SEM MBA", {"semester": 1, "program": "MBA", "section": "", "sem_type": "ODD"}),
    ("MBA 1 SEM", {"semester": 1, "program": "MBA", "section": "", "sem_type": "ODD"}),
    ("B SC III SEM", {"semester": 3, "program": "BSC", "section": "", "sem_type": "ODD"}),
    ("B COM V SEM", {"semester": 5, "program": "BCOM", "section": "", "sem_type": "ODD"}),
    ("BA II SEM A", {"semester": 2, "program": "BA", "section": "A", "sem_type": "EVEN"}),
    ("BCA VI SEM C", {"semester": 6, "program": "BCA", "section": "C", "sem_type": "EVEN"}),
    ("MCA 4 SEM", {"semester": 4, "program": "MCA", "section": "", "sem_type": "EVEN"}),
    ("2 SEM BCA A", {"semester": 2, "program": "BCA", "section": "A", "sem_type": "EVEN"}),
    ("I SEM 1 BCA A", {"semester": 1, "program": "BCA", "section": "A", "sem_type": "ODD"}),
)


def run_academic_parsing_self_check(debug: bool = False) -> list[dict[str, Any]]:
    """
    Validate the bundled academic parsing samples.

    Returns a list of mismatches so the helper can be safely used in scripts,
    tests, or manual debugging without raising exceptions.
    """
    mismatches: list[dict[str, Any]] = []
    for raw_value, expected in ACADEMIC_PARSE_VALIDATION_CASES:
        actual = sanitize_academic_info(raw_value, debug=debug)
        if actual != expected:
            mismatches.append(
                {
                    "input": raw_value,
                    "expected": expected,
                    "actual": actual,
                }
            )

    if mismatches:
        logger.warning("Academic parsing self-check found %s mismatch(es).", len(mismatches))
    else:
        logger.debug("Academic parsing self-check passed for %s sample input(s).", len(ACADEMIC_PARSE_VALIDATION_CASES))

    return mismatches


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


def build_seat_grid(room):
    """
    Generates a list of seats for a room based on its rows, column_layout, and aisle placements.
    Returns: List of {"row": row, "col": col, "label": label}
    """
    grid = []
    # Use column_layout if available, otherwise fallback to legacy L/M/R
    layout = room.column_layout
    if not layout:
        layout = [room.left_seats, room.middle_seats, room.right_seats]
        # For legacy layout, aisles are assumed after first and second blocks
        aisles = [0, 1]
    else:
        aisles = room.aisle_after_column

    for row_idx in range(1, room.rows + 1):
        visual_col = 1
        for block_idx, block_size in enumerate(layout):
            for _ in range(block_size):
                grid.append({
                    "row": row_idx,
                    "col": visual_col,
                    "label": f"R{row_idx}C{visual_col}"
                })
                visual_col += 1
            if block_idx in aisles:
                visual_col += 1  # Skip a column for the aisle
    return grid


def build_room_seat_slots(room):
    """
    Generates ordered SeatSlot objects for a room using checkerboard-zigzag patterns.
    """
    grid = build_seat_grid(room)
    if not grid:
        return []

    # Filter/Order by checkerboard-zigzag
    # 1. Group by rows
    rows_map = {}
    for seat in grid:
        if seat['row'] not in rows_map:
            rows_map[seat['row']] = []
        rows_map[seat['row']].append(seat)

    # 2. Zigzag the rows
    all_seats_ordered = []
    sorted_row_indices = sorted(rows_map.keys())
    for i, row_idx in enumerate(sorted_row_indices):
        row_seats = sorted(rows_map[row_idx], key=lambda x: x['col'])
        if i % 2 == 1: # Zigzag: reverse every second row
            row_seats.reverse()
        all_seats_ordered.extend(row_seats)

    # 3. Apply Checkerboard sorting (Priority to seats where row+col is even)
    # This helps in spreading students by creating a gap in a 2D grid.
    primary = [s for s in all_seats_ordered if (s['row'] + s['col']) % 2 == 0]
    secondary = [s for s in all_seats_ordered if (s['row'] + s['col']) % 2 == 1]
    ordered_grid = primary + secondary

    slots = []
    for seat in ordered_grid:
        slots.append(
            SeatSlot(
                room=room,
                row=seat['row'],
                col=seat['col'],
                seat_pos=seat['label'],
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
