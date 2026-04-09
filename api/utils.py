import re

def normalize_semester_name(val):
    if not val: return ""
    val = val.upper().strip()
    
    # 1. MAPPING DICTIONARIES
    roman_map = {
        "I": "SEM 1", "II": "SEM 2", "III": "SEM 3",
        "IV": "SEM 4", "V": "SEM 5", "VI": "SEM 6"
    }
    
    keyword_map = {
        "1ST": "SEM 1", "2ND": "SEM 2", "3RD": "SEM 3",
        "4TH": "SEM 4", "5TH": "SEM 5", "6TH": "SEM 6"
    }

    # 2. ROMAN NUMERAL EXTRACTION (EXACT WORD BOUNDARY)
    # Order matters: Longest first inside the group to prevent 'III' being matched as 'I'
    roman_pattern = r"\b(III|II|IV|VI|V|I)\b"
    roman_match = re.search(roman_pattern, val)
    if roman_match:
        roman = roman_match.group(1)
        return roman_map.get(roman, "")

    # 3. FALLBACK: KEYWORD EXTRACTION (1ST, 2ND, etc.)
    keyword_pattern = r"\b(1ST|2ND|3RD|4TH|5TH|6TH)\b"
    keyword_match = re.search(keyword_pattern, val)
    if keyword_match:
        k = keyword_match.group(1)
        return keyword_map.get(k, "")

    # 4. FALLBACK: RAW DIGIT EXTRACTION
    digit_match = re.search(r"\b([1-6])\b", val)
    if digit_match:
        return f"SEM {digit_match.group(1)}"

    # 5. VALIDATE: ONLY ALLOW SEM 1 TO SEM 6
    # If the value is already 'SEM X', ensure it's in range
    if val.startswith("SEM "):
        try:
            num = int(val.split(" ")[1])
            if 1 <= num <= 6: return val
        except: pass

    return ""

def sanitize_class_info(raw_class_string):
    if not raw_class_string:
        return {"semester": "", "department": "", "specialization": "", "section": ""}
        
    val = str(raw_class_string).upper().strip()
    
    # 1. Normalize Semester First
    semester = normalize_semester_name(val)
    
    # 2. Extract Section (Check for trailing single char or "SEC X")
    section = ""
    sec_match = re.search(r'\b(SEC\s+)?([A-D]|ALPHA|BETA)\b$', val)
    if sec_match:
        section = sec_match.group(2)
        val = val[:sec_match.start()].strip()
        
    # 3. Clean Semester logic from String to isolate Dept
    clean_val = val
    sem_variants = ["1ST", "2ND", "3RD", "4TH", "5TH", "6TH", "7TH", "8TH", 
                    "SEM", "SEMESTER", "I", "II", "III", "IV", "V", "VI", "VII", "VIII"]
    for sv in sem_variants:
        clean_val = re.sub(rf'\b{sv}\b', '', clean_val).strip()

    # 4. Extract Specialization (Check for dash or parenthesis)
    specialization = ""
    if "-" in clean_val:
        parts = clean_val.split("-", 1)
        clean_val = parts[0].strip()
        specialization = parts[1].strip()

    # 6. Extract Department (STRICT KEYWORD MATCHING)
    whitelist = ["BCA", "BBA", "BCOM", "BSC", "BA"]
    department = ""
    check_val = val.replace("B COM", "BCOM").replace("B SC", "BSC").replace("B A ", "BA ")
    
    for major in whitelist:
        if major in check_val:
            department = major
            break
            
    if department not in whitelist:
        department = ""

    return {
        "semester": semester if semester.startswith("SEM") else "",
        "department": department,
        "specialization": specialization,
        "section": section
    }

def allocate_multi_room_seating(students, rooms):
    """
    PROFESSIONAL EXAM SEATING ENGINE (Multi-Room / Deterministic)
    Phases 5-10: Timetable-driven allocation with cyclic column distribution.
    """
    import random
    
    from collections import deque
    # GROUP BY DEPARTMENT for cyclic distribution
    dept_groups = {}
    for s in students:
        # SAFETY CHECK: Ensure department and name exist
        if not s.department or not s.department.name:
            continue
            
        d_name = s.department.name.upper()
        if d_name not in dept_groups:
            dept_groups[d_name] = deque() # Use deque for O(1) popleft
        dept_groups[d_name].append(s)
    
    # Sort for deterministic behavior
    depts = sorted(dept_groups.keys())
    for d in depts:
        # Convert to list to shuffle, then back to deque
        temp_list = list(dept_groups[d])
        random.shuffle(temp_list)
        dept_groups[d] = deque(temp_list)
    
    # Global Tracking
    results = []
    room_logs = []
    total_to_seat = len(students)
    seated_count = 0
    
    # PHASE 5: Room-by-Room Allocation Flow
    for room in rooms:
        if seated_count >= total_to_seat: break
        
        r_count = room.rows
        c_count = room.left_seats + room.middle_seats + room.right_seats
        room_matrix = [[None for _ in range(c_count)] for _ in range(r_count)]
        
        last_student_in_room = None
        # PHASE 7 & 6: Column-Wise Filling
        for c in range(c_count):
            # Assign department to this column (Phase 6) 
            pref_dept = depts[c % len(depts)] if depts else "N/A"
            
            for r in range(r_count):
                student = None
                
                # Check preferred department (Phase 7)
                if pref_dept in dept_groups and dept_groups[pref_dept]:
                    student = dept_groups[pref_dept].popleft()
                else:
                    # Edge Case: Dept ends early (Phase 8) - Pull from any available
                    found_alt = False
                    for alt_dept in depts:
                        if dept_groups[alt_dept]:
                            student = dept_groups[alt_dept].popleft()
                            found_alt = True
                            break
                    if not found_alt: break # No students left anywhere
                            
                if student:
                    room_matrix[r][c] = student
                    seated_count += 1
                    
                    if c < room.left_seats:
                        sec, pos = "Left", c + 1
                    elif c < room.left_seats + room.middle_seats:
                        sec, pos = "Middle", c - room.left_seats + 1
                    else:
                        sec, pos = "Right", c - room.left_seats - room.middle_seats + 1
                    
                    results.append({
                        'room': room,
                        'row': r + 1,
                        'seat_pos': f"{sec} Seat {pos}",
                        'student': student,
                    })
                    last_student_in_room = f"{student.university_id} / {student.name}"

                if seated_count >= total_to_seat: break
            if seated_count >= total_to_seat: break
            
        # PHASE 5 notification data
        if last_student_in_room:
            room_logs.append(f"Room {room.room_number} filled. Last student: {last_student_in_room}")

    # PHASE 10: Validation metrics
    return {
        'assignments': results,
        'logs': room_logs,
        'metrics': {
            'total': total_to_seat,
            'allocated': seated_count,
            'remaining': total_to_seat - seated_count
        }
    }
def extract_semester_info(row_data, header_idx):
    """
    Implements 3-step priority logic for semester extraction.
    STEP 1: Check "Semester/Sem" columns.
    STEP 2: Extract from "Class" column using patterns.
    STEP 3: Reject if unresolvable.
    Returns (semester_num, sem_type) or (None, None).
    """
    sem_val = ""
    class_val = ""
    
    # Header Mapping Priority
    idx_sem = header_idx.get('semester')
    idx_class = header_idx.get('class')
    
    if idx_sem is not None:
        sem_val = str(row_data[idx_sem]).strip().upper() if row_data[idx_sem] is not None else ""
    
    if idx_class is not None:
        class_val = str(row_data[idx_class]).strip().upper() if row_data[idx_class] is not None else ""

    # STEP 1: Direct Semester Detection
    if sem_val:
        num = detect_semester_number(sem_val)
        if num: return num, get_sem_type(num)

    # STEP 2: Pattern Extraction from Class
    if class_val:
        num = detect_semester_number(class_val)
        if num: return num, get_sem_type(num)

    return None, None

def detect_semester_number(val):
    if not val: return None
    val = val.upper().strip()
    
    roman_map = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6}
    
    # 1. Direct Digit Check
    digit_match = re.search(r'\b([1-6])\b', val)
    if digit_match:
        return int(digit_match.group(1))
        
    # 2. Roman Numeral Check
    roman_pattern = r'\b(III|II|IV|VI|V|I)\b'
    roman_match = re.search(roman_pattern, val)
    if roman_match:
        return roman_map.get(roman_match.group(1))
        
    # 3. Keyword Pattern Check (1st Sem, etc.)
    keyword_match = re.search(r'\b([1-6])(ST|ND|RD|TH)\b', val)
    if keyword_match:
        return int(keyword_match.group(1))
        
    return None

def get_sem_type(num):
    if num in [1, 3, 5]: return 'ODD'
    if num in [2, 4, 6]: return 'EVEN'
    return None

def identify_semester_group(sem_name):
    """
    Legacy helper kept for compatibility if needed, 
    prefer extract_semester_info for new pipeline.
    """
    num = detect_semester_number(sem_name)
    return get_sem_type(num) if num else None

def validate_semester_group_consistency(sem_names):
    """
    Checks if a list of semester names all belong to the same group.
    Returns (group, is_consistent).
    """
    detected_groups = set()
    for name in sem_names:
        group = identify_semester_group(name)
        if group:
            detected_groups.add(group)
    
    if len(detected_groups) > 1:
        return None, False
    
    return detected_groups.pop() if detected_groups else None, True
