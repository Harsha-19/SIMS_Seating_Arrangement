
import re

def detect_semester_number(val):
    if not val: return None
    t = val.upper().strip()
    
    # STRICT ROMAN MAP (Exact Matching Only)
    ROMAN_MAP = {
        "I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6
    }
    
    # 1. Check Roman Map: Exact Match
    if t in ROMAN_MAP:
        return ROMAN_MAP[t]
        
    # 2. Check Numeric
    if t.isdigit():
        num = int(t)
        if 1 <= num <= 6: return num

    # 3. Clean and check (Strict suffix removal)
    clean = re.sub(r'(ST|ND|RD|TH)$', '', t)
    if clean.isdigit():
        num = int(clean)
        if 1 <= num <= 6: return num

    return None

def extract_semester_info_debug(class_val):
    if class_val:
        # 1. Normalize
        normalized = class_val.upper().strip()
        # 2. Extract token before "SEM"
        if "SEM" in normalized:
            prefix = normalized.split("SEM")[0].strip()
            print(f"DEBUG: '{class_val}' -> prefix: '{prefix}'")
            if prefix:
                # 3. Extract ONLY first word (Token[0] logic)
                tokens = prefix.split()
                print(f"DEBUG: tokens: {tokens}")
                sem_token = tokens[0]
                print(f"DEBUG: sem_token: '{sem_token}'")
                num = detect_semester_number(sem_token)
                return num
    return None

test_cases = [
    "I Sem BCA A",
    "II Sem BCA A",
    "III Sem BBA",
    "IV Sem B Sc - Forensic Science",
    "VI Sem BCA"
]

for t in test_cases:
    res = extract_semester_info_debug(t)
    print(f"'{t}' -> {res} ({'ODD' if res in [1,3,5] else 'EVEN'})")
