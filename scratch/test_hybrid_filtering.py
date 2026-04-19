import os
import django
import sys
from datetime import date

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from api.models import Department, Semester, Student, Exam, Room
from django.db import transaction

def test_hybrid_logic():
    print("--- Running Hybrid Logic Test ---")
    
    # 1. Clean state
    with transaction.atomic():
        Student.objects.all().delete()
        Semester.objects.all().delete()
        Department.objects.all().delete()
        Exam.objects.all().delete()
        Room.objects.all().delete()
    
    # 2. Setup Meta-data
    dept, _ = Department.objects.get_or_create(name="BCA")
    sem1, _ = Semester.objects.get_or_create(name="Sem 1", department=dept) # ODD
    sem2, _ = Semester.objects.get_or_create(name="Sem 2", department=dept) # EVEN
    
    room, _ = Room.objects.get_or_create(room_number="R101", rows=10, left_seats=3, middle_seats=2, right_seats=3)
    
    # 3. Create Hybrid Students
    # 2 ODD students, 2 EVEN students
    Student.objects.create(university_id="ODD1", name="Odd Student 1", department=dept, semester=sem1, sem=1)
    Student.objects.create(university_id="ODD2", name="Odd Student 2", department=dept, semester=sem1, sem=1)
    Student.objects.create(university_id="EVE1", name="Even Student 1", department=dept, semester=sem2, sem=2)
    Student.objects.create(university_id="EVE2", name="Even Student 2", department=dept, semester=sem2, sem=2)
    
    print(f"Total Students: {Student.objects.count()}")
    
    # 4. Create an ODD Exam
    exam_odd = Exam.objects.create(subject="Python ODD", department=dept, semester=sem1, date=date.today())
    
    # Simulate generate() logic
    from api.utils import detect_semester_number
    
    def simulate_generate(exam_obj):
        num = detect_semester_number(exam_obj.semester.name)
        type = "ODD" if num in [1, 3, 5] else "EVEN"
        # We also need dept_ids from context exams
        # In this simple test, just use the exam's dept
        dept_ids = [exam_obj.department_id]
        
        eligible = Student.objects.filter(sem_type=type, department_id__in=dept_ids)
        return list(eligible)

    # 5. Test ODD generation
    print("\nTesting ODD Exam generation filter...")
    odd_eligible = simulate_generate(exam_odd)
    odd_ids = [s.university_id for s in odd_eligible]
    print(f"Found: {odd_ids}")
    
    if len(odd_eligible) == 2 and all(id.startswith("ODD") for id in odd_ids):
        print("SUCCESS: ODD filtering worked correctly.")
    else:
        print(f"FAILURE: Expected 2 ODD students, found {len(odd_eligible)}: {odd_ids}")
        sys.exit(1)

    # 6. Test EVEN generation
    exam_even = Exam.objects.create(subject="C++ EVEN", department=dept, semester=sem2, date=date.today())
    print("\nTesting EVEN Exam generation filter...")
    even_eligible = simulate_generate(exam_even)
    even_ids = [s.university_id for s in even_eligible]
    print(f"Found: {even_ids}")
    
    if len(even_eligible) == 2 and all(id.startswith("EVE") for id in even_ids):
        print("SUCCESS: EVEN filtering worked correctly.")
    else:
        print(f"FAILURE: Expected 2 EVEN students, found {len(even_eligible)}: {even_ids}")
        sys.exit(1)

if __name__ == "__main__":
    test_hybrid_logic()
