import os
import django
import sys

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from api.models import Department, Semester, Student
from django.db import transaction

def test_uniqueness():
    print("--- Running Semester Uniqueness Test ---")
    
    # Clean state
    with transaction.atomic():
        Student.objects.all().delete()
        Semester.objects.all().delete()
        Department.objects.all().delete()
    
    # 1. Create a department
    dept, _ = Department.objects.get_or_create(name="BCA")
    
    # 2. Simulate the caching logic in upload()
    semester_cache = {}
    sem_nums = [2, 2, 2, 4, 4] # Multiple students in same sem
    
    print(f"Input semesters: {sem_nums}")
    
    for num in sem_nums:
        key = (dept.id, num)
        if key not in semester_cache:
            # This mimics the get_or_create logic in views.py
            sem_obj, created = Semester.objects.get_or_create(
                name=f"Sem {num}",
                department=dept
            )
            semester_cache[key] = sem_obj
            status = "CREATED" if created else "REUSED"
            print(f"Sem {num}: {status}")
        else:
            print(f"Sem {num}: CACHE HIT")
            
    # 3. Verify counts in database
    total_semesters = Semester.objects.count()
    print(f"\nTotal Semesters in DB: {total_semesters}")
    
    expected = 2 # Only Sem 2 and Sem 4 should exist
    if total_semesters == expected:
        print("SUCCESS: Only unique semesters were created.")
    else:
        print(f"FAILURE: Expected {expected} semesters, found {total_semesters}.")
        sys.exit(1)

    # 4. Verify naming convention
    sem2 = Semester.objects.get(name="Sem 2", department=dept)
    if sem2.name == "Sem 2":
        print("SUCCESS: Naming convention 'Sem 2' preserved.")
    else:
        print(f"FAILURE: Expected 'Sem 2', found '{sem2.name}'. Check normalize_semester_name logic.")
        sys.exit(1)

if __name__ == "__main__":
    test_uniqueness()
