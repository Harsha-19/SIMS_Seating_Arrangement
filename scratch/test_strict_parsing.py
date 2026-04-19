import os
import sys

# Setup mock environment or point to project
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.utils import extract_semester

def test_strict_logic():
    print("--- Running Strict Semester Extraction Test ---")
    
    test_cases = [
        {"input": "II SEM B SC", "expected": 2},
        {"input": "4 SEM BCA", "expected": 4},
        {"input": "VI SEM B COM", "expected": 6},
        {"input": "SEM 2", "expected": None}, # Because part before SEM is empty
        {"input": "BCA 4 SEM", "expected": 4}, # wait, "BCA 4 SEM".split("SEM")[0] is "BCA 4 ". tokens[0] is "BCA". fails.
        {"input": "II SEM", "expected": 2},
        {"input": "", "expected": None},
        {"input": None, "expected": None},
        {"input": "IV SEMESTER", "expected": 4}, # User's code says if "SEM" not in class_str. "SEMESTER" contains "SEM".
    ]
    
    success_count = 0
    for case in test_cases:
        actual = extract_semester(case["input"])
        status = "PASS" if actual == case["expected"] else "FAIL"
        print(f"Input: '{case['input']}' | Expected: {case['expected']} | Actual: {actual} | status: {status}")
        if status == "PASS":
            success_count += 1
            
    if success_count == len(test_cases):
        print("\nALL TESTS PASSED: Strict logic enforced.")
    else:
        print(f"\n{len(test_cases) - success_count} TESTS FAILED. Verify strict logic requirements.")
        # sys.exit(1) # Don't exit yet, let's see why

if __name__ == "__main__":
    test_strict_logic()
