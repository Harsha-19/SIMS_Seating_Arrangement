import os
import django
import sys

# Setup Django
sys.path.append('d:\\My Things\\PROJECTS\\seating arrengement')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from api.models import Program, Student, Enrollment
from django.db import transaction

def seed_programs():
    print("--- Seeding Programs ---")
    programs = [
        "BA Journalism", "BA CRIMINOLOGY", "B SC", "B SC - FORENSIC SCIENCE",
        "B SC - PMC-CS", "B SC - PC", "B SC - CS - P/C/M", "BCA", "BBA",
        "BBA - AVIATION", "B COM"
    ]
    for p_name in programs:
        p, created = Program.objects.get_or_create(name=p_name.upper().replace("B SC", "BSC").replace("B COM", "BCOM").replace("B A", "BA"))
        if created: print(f"Created: {p.name}")
    print("Done.\n")

def verify_extraction():
    print("--- Verifying Extraction Logic ---")
    from api.utils import sanitize_academic_info
    
    test_cases = [
        "II Sem BCA A",
        "IV Sem B Com B",
        "VI Sem BBA",
        "I Sem BA Journalism C",
        "3 Sem BCA B"
    ]
    
    for tc in test_cases:
        res = sanitize_academic_info(tc)
        print(f"INPUT: {tc}")
        print(f"RESULT: {res}")
        print("-" * 20)

if __name__ == "__main__":
    seed_programs()
    verify_extraction()
