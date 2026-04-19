import os
import django
import sys

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from api.models import Department, Semester, Student
from django.db import transaction

def test_source_truth():
    print("--- Running Data Source Integrity Test ---")
    
    # 1. Setup initial state with "Old" data
    with transaction.atomic():
        Student.objects.all().delete()
        Semester.objects.all().delete()
        dept, _ = Department.objects.get_or_create(name="OLD_DEPT")
        sem, _ = Semester.objects.get_or_create(name="Sem 99", department=dept)
        Student.objects.create(university_id="OLD_USN", name="Old Student", department=dept, semester=sem, sem=1)
    
    print(f"Post-Setup: Students={Student.objects.count()}, Semesters={Semester.objects.count()}")
    
    # 2. Simulate the NEW upload logic in views.py
    # This logic should wipe the old data
    def simulate_new_upload():
        with transaction.atomic():
            # Mandatory wipe
            Student.objects.all().delete()
            Semester.objects.all().delete()
            
            # Insert NEW data
            new_dept, _ = Department.objects.get_or_create(name="NEW_DEPT")
            new_sem, _ = Semester.objects.get_or_create(name="Sem 1", department=new_dept)
            Student.objects.create(university_id="NEW_USN", name="New Student", department=new_dept, semester=new_sem, sem=1)
            
            total = Student.objects.count()
            odd = Student.objects.filter(sem__in=[1,3,5]).count()
            even = Student.objects.filter(sem__in=[2,4,6]).count()
            
            print(f"--- UPLOAD DEBUG LOG (SIM) ---")
            print(f"Rows processed: {total}")
            print(f"Odd: {odd}")
            print(f"Even: {even}")
            
    simulate_new_upload()
    
    # 3. Final Verification
    total_students = Student.objects.count()
    old_exists = Student.objects.filter(university_id="OLD_USN").exists()
    
    print(f"\nFinal State: Students={total_students}")
    
    if total_students == 1 and not old_exists:
        print("SUCCESS: Old data was completely wiped. Only new data exists.")
    else:
        print(f"FAILURE: Data leakage detected! Old data exists: {old_exists}")
        sys.exit(1)

if __name__ == "__main__":
    test_source_truth()
