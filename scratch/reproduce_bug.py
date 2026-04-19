
import re
import sys
import os

# Add the project root to sys.path to allow importing from 'api'
sys.path.append(os.getcwd())

# Mock header_idx for testing
# We assume 'class' and 'semester' are the keys our logic looks for
HEADER_IDX = {
    'class': 0,
    'semester': 1
}

def mock_extract_semester_info(class_val, sem_val=None):
    from api.utils import extract_semester_info
    # row_data should be a list/tuple where index 0 is class and index 1 is semester
    row_data = [class_val, sem_val]
    return extract_semester_info(row_data, HEADER_IDX)

test_cases = [
    # Roman Numerals in Class Column
    ("I SEM BCA", None, 1),
    ("II SEM BCA", None, 2),
    ("III SEM BBA", None, 3),
    ("IV SEM B Sc", None, 4),
    ("VI SEM BCA", None, 6),
    
    # Keyword variations
    ("1st Sem BCA", None, 1),
    ("2nd Sem BCA", None, 2),
    ("4th Sem", None, 4),
    
    # Digit variations
    ("Semester 2 BCA", None, 2),
    ("BCA 6 Sem", None, 6),
    
    # Roman Numerals without "SEM"
    ("BCA II", None, 2),
    ("BBA IV", None, 4),
    
    # Semester in Semester Column
    (None, "II", 2),
    (None, "5th", 5),
    
    # Combined info
    ("BCA", "III", 3),
    
    # Edge cases / Conflicts
    ("II SEMESTER", None, 2), # Should match II, not I
    ("III SEMESTER", None, 3), # Should match III, not I or II
    ("BCA VI - Forensic", None, 6), # Should match VI, not I or V
]

print("--- SEMESTER EXTRACTION VERIFICATION ---")
passed = 0
for class_in, sem_in, expected in test_cases:
    result = mock_extract_semester_info(class_in, sem_in)
    sem_type = 'ODD' if result in [1,3,5] else 'EVEN' if result in [2,4,6] else 'UNKNOWN'
    
    status = "PASS" if result == expected else "FAIL"
    if status == "PASS": passed += 1
    
    print(f"Input: [Class: {class_in}, Sem: {sem_in}] -> Extracted: {result} ({sem_type}) | Expected: {expected} | {status}")

print(f"\nResults: {passed}/{len(test_cases)} cases passed.")
if passed == len(test_cases):
    print("SUCCESS: 100% Accuracy achieved.")
else:
    print("FAILURE: Some cases did not match expected output.")
    sys.exit(1)
