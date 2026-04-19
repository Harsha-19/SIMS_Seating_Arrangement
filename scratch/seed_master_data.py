import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from api.models import Program

PROGRAMS = [
    "BA Journalism",
    "BA Criminology",
    "B Sc",
    "B Sc - Forensic Science",
    "B Sc - PMC-Cs",
    "B Sc - PC",
    "B Sc - Cs - P/C/M",
    "BCA",
    "BBA",
    "BBA - Aviation",
    "B Com"
]

def seed():
    print("--- Seeding Programs ---")
    for name in PROGRAMS:
        # Check both normalized and original just in case
        prog, created = Program.objects.get_or_create(name=name.upper())
        if created:
            print(f"Created: {name}")
        else:
            print(f"Already exists: {name}")
    print("Done.")

if __name__ == "__main__":
    seed()
