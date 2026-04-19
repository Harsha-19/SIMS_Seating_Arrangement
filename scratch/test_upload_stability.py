import os
import django
import sys

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from api.models import Department, Semester, Student
from django.db import transaction

def test_upload_stability():
    print("--- Running Upload Stability & Idempotency Test ---")
    
    # Simulate the refined upload logic in views.py
    def simulate_refined_upload(data_list):
        from api.models import Department, Semester, Student
        with transaction.atomic():
            # RESOLUTION CACHES
            dept_cache = {}
            semester_cache = {}
            
            inserted_count = 0
            for row in data_list:
                # 1. Dept Resolution
                d_name = row['dept']
                if d_name not in dept_cache:
                    d_obj, _ = Department.objects.get_or_create(name=d_name)
                    dept_cache[d_name] = d_obj
                dept = dept_cache[d_name]
                
                # 2. Sem Resolution
                s_num = row['sem']
                s_key = (dept.id, s_num)
                if s_key not in semester_cache:
                    s_obj, _ = Semester.objects.get_or_create(
                        name=f"Sem {s_num}",
                        department=dept
                    )
                    semester_cache[s_key] = s_obj
                sem = semester_cache[s_key]
                
                # 3. Safe Student Insert
                student, created = Student.objects.update_or_create(
                    university_id=row['usn'],
                    defaults={
                        "name": row['name'],
                        "department": dept,
                        "semester": sem,
                        "sem": s_num
                    }
                )
                inserted_count += 1
            return inserted_count

    # Test Data with Redundancy (Multiple students in same sem/dept)
    batch_1 = [
        {'usn': 'S1', 'name': 'Student 1', 'dept': 'BCA', 'sem': 1},
        {'usn': 'S2', 'name': 'Student 2', 'dept': 'BCA', 'sem': 1},
        {'usn': 'S3', 'name': 'Student 3', 'dept': 'BCOM', 'sem': 2},
    ]
    
    # First Upload
    simulate_refined_upload(batch_1)
    
    # Verification 1
    s_count = Student.objects.count()
    sem_count = Semester.objects.count()
    print(f"Post-Upload 1: Students={s_count}, Semesters={sem_count}")
    
    # Duplicate Upload (Same data)
    simulate_refined_upload(batch_1)
    
    # Verification 2 (Should not increase semester count)
    s_count_2 = Student.objects.count()
    sem_count_2 = Semester.objects.count()
    print(f"Post-Upload 2 (Duplicate): Students={s_count_2}, Semesters={sem_count_2}")
    
    if sem_count == sem_count_2 and s_count == s_count_2:
        print("SUCCESS: Idempotency enforced. No duplicate semesters or students created.")
    else:
        print("FAILURE: Duplicates detected!")
        sys.exit(1)

if __name__ == "__main__":
    test_upload_stability()
