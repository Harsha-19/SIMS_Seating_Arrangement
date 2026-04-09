import re

def normalize_semester_name(val):
    if not val: return "EMPTY_VAL"
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
    roman_pattern = r"\b(III|II|IV|VI|V|I)\b"
    roman_match = re.search(roman_pattern, val)
    if roman_match:
        roman = roman_match.group(1)
        return roman_map.get(roman, "ROMAN_MISS")

    # 3. FALLBACK: KEYWORD EXTRACTION (1ST, 2ND, etc.)
    keyword_pattern = r"\b(1ST|2ND|3RD|4TH|5TH|6TH)\b"
    keyword_match = re.search(keyword_pattern, val)
    if keyword_match:
        k = keyword_match.group(1)
        return keyword_map.get(k, "KEY_MISS")

    # 4. FALLBACK: RAW DIGIT EXTRACTION
    digit_match = re.search(r"\b([1-6])\b", val)
    if digit_match:
        return f"SEM {digit_match.group(1)}"

    return "NO_MATCH"

test_cases = [
    "I SEM", "II SEM", "III SEM", "IV SEM", "V SEM", "VI SEM",
    "1st Sem", "2nd Sem", "3rd Sem", "4th Sem", "5th Sem", "6th Sem",
    "SEM 1", "SEM 2", "SEM 3", "SEM 4", "SEM 5", "SEM 6",
    "BCA II", "BBA IV", "BCOM VI",
    "CLASS 1", "TERM 2"
]

for t in test_cases:
    print(f"'{t}' -> {normalize_semester_name(t)}")
