from django.db import models
from django.core.exceptions import ValidationError

VALID_SEMESTERS = (1, 2, 3, 4, 5, 6)
ODD_SEMESTERS = (1, 3, 5)
EVEN_SEMESTERS = (2, 4, 6)


def derive_sem_type(semester):
    if semester in ODD_SEMESTERS:
        return 'ODD'
    if semester in EVEN_SEMESTERS:
        return 'EVEN'
    raise ValidationError("Semester must be between 1 and 6.")


class Program(models.Model):
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        self.name = str(self.name).strip().upper()
        # "B SC" -> "BSC", etc. is handled in extraction, but we keep it here as safety
        self.name = self.name.replace("B SC", "BSC").replace("B COM", "BCOM").replace("B A", "BA")
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Student(models.Model):
    reg_no = models.CharField(max_length=20, unique=True, default='') # Added default for migration
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.reg_no} - {self.name}"

    def save(self, *args, **kwargs):
        self.reg_no = self.reg_no.upper().strip()
        super().save(*args, **kwargs)

    @property
    def university_id(self):
        return self.reg_no

    @university_id.setter
    def university_id(self, value):
        self.reg_no = value

class Enrollment(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='enrollments')
    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name='enrollments')
    semester = models.IntegerField() # 1-6
    section = models.CharField(max_length=10, blank=True, null=True) # A, B, C, D
    sem_type = models.CharField(max_length=10, choices=[('ODD', 'ODD'), ('EVEN', 'EVEN')])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'program', 'semester')
        indexes = [
            models.Index(fields=['sem_type']),
            models.Index(fields=['semester']),
            models.Index(fields=['section']),
            models.Index(fields=['program', 'semester']),
            models.Index(fields=['program', 'semester', 'section']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(semester__in=VALID_SEMESTERS),
                name='enrollment_semester_range_valid',
            ),
            models.CheckConstraint(
                check=(
                    models.Q(semester__in=ODD_SEMESTERS, sem_type='ODD') |
                    models.Q(semester__in=EVEN_SEMESTERS, sem_type='EVEN')
                ),
                name='enrollment_semester_sem_type_match',
            ),
        ]

    def clean(self):
        if self.semester not in VALID_SEMESTERS:
            raise ValidationError("Semester must be between 1 and 6.")
        derived_sem_type = derive_sem_type(self.semester)
        if self.sem_type and str(self.sem_type).upper().strip() != derived_sem_type:
            raise ValidationError("Semester type does not match the semester value.")
        self.sem_type = derived_sem_type
        super().clean()

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.student.reg_no} | {self.program.name} Sem {self.semester}"

class Room(models.Model):
    room_number = models.CharField(max_length=20, unique=True)
    rows = models.IntegerField()
    # New dynamic layout fields
    column_layout = models.JSONField(default=list, help_text="List of seat counts per block, e.g. [3, 2, 3]")
    aisle_after_column = models.JSONField(default=list, blank=True, help_text="Block indices after which to place an aisle")
    
    # Legacy fields
    left_seats = models.IntegerField(default=3)
    middle_seats = models.IntegerField(default=2)
    right_seats = models.IntegerField(default=3)
    
    total_capacity = models.IntegerField(editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        self.room_number = self.room_number.upper()
        
        # Prefer dynamic layout if provided
        if self.column_layout:
            self.total_capacity = self.rows * sum(self.column_layout)
        else:
            # Fallback to legacy fields
            self.total_capacity = self.rows * (self.left_seats + self.middle_seats + self.right_seats)
            # Auto-populate column_layout for migration support
            self.column_layout = [self.left_seats, self.middle_seats, self.right_seats]
            
        super().save(*args, **kwargs)

    def __str__(self):
        return self.room_number


class Subject(models.Model):
    subject_name = models.CharField(max_length=150)
    subject_code = models.CharField(max_length=50, unique=True)
    department = models.ForeignKey(Program, on_delete=models.CASCADE, related_name='subjects', null=True, blank=True)
    semester = models.IntegerField(null=True, blank=True)
    credits = models.IntegerField(null=True, blank=True)
    type = models.CharField(max_length=50, default='CORE', choices=[('CORE', 'Core'), ('ELECTIVE', 'Elective'), ('COMMON', 'Common')])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.subject_code} - {self.subject_name}"

    def clean(self):
        if self.semester is not None and self.semester not in VALID_SEMESTERS:
            raise ValidationError("Semester must be between 1 and 6.")
        super().clean()

    def save(self, *args, **kwargs):
        self.subject_name = self.subject_name.upper()
        self.subject_code = self.subject_code.upper()
        super().save(*args, **kwargs)


class ExamSchedule(models.Model):
    EXAM_TYPE_CHOICES = [
        ('REGULAR', 'Regular'),
        ('SUPPLEMENTARY', 'Supplementary'),
        ('INTERNAL', 'Internal Assessment'),
        ('PRACTICAL', 'Practical'),
    ]
    SESSION_CHOICES = [
        ('MORNING', 'Morning'),
        ('AFTERNOON', 'Afternoon'),
        ('EVENING', 'Evening'),
    ]
    STATUS_CHOICES = [
        ('UPCOMING', 'Upcoming'),
        ('ONGOING', 'Ongoing'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]

    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='exam_schedules')
    exam_type = models.CharField(max_length=20, choices=EXAM_TYPE_CHOICES, default='REGULAR')
    exam_date = models.DateField()
    session = models.CharField(max_length=20, choices=SESSION_CHOICES, default='MORNING')
    start_time = models.TimeField()
    end_time = models.TimeField()
    academic_year = models.CharField(max_length=20, default='2026-27')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='UPCOMING')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.subject.subject_name} ({self.exam_date}) - {self.session}"

    @property
    def duration(self):
        if self.start_time and self.end_time:
            from datetime import datetime, date
            start = datetime.combine(date.min, self.start_time)
            end = datetime.combine(date.min, self.end_time)
            diff = end - start
            hours = diff.seconds // 3600
            minutes = (diff.seconds % 3600) // 60
            if hours > 0 and minutes > 0:
                return f"{hours}h {minutes}m"
            elif hours > 0:
                return f"{hours}h"
            else:
                return f"{minutes}m"
        return ""


class SeatingPlan(models.Model):
    STATUS_CHOICES = [
        ('DRAFT', 'DRAFT'),
        ('PUBLISHED', 'PUBLISHED'),
        ('ARCHIVED', 'ARCHIVED'),
    ]
    exam_schedule = models.ForeignKey(ExamSchedule, on_delete=models.CASCADE, related_name='seating_plans')
    version = models.IntegerField(default=1)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    constraint_level_used = models.IntegerField(default=0)
    generated_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-version']
        verbose_name = "Seating Plan"
        verbose_name_plural = "Seating Plans"

    def __str__(self):
        return f"{self.exam_schedule.subject.subject_name} - v{self.version} ({self.status})"


class Seating(models.Model):
    plan = models.ForeignKey(SeatingPlan, on_delete=models.CASCADE, related_name='assignments', null=True)
    exam_schedule = models.ForeignKey(ExamSchedule, on_delete=models.CASCADE, related_name='seats')
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='seats')
    row = models.IntegerField()
    seat_position = models.CharField(max_length=50) # Coordinated label like R1C1
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='seats')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [
            ('plan', 'student'),
            ('plan', 'room', 'row', 'seat_position'),
        ]

    @property
    def effective_subject(self):
        return self.exam_schedule.subject.subject_name

    @property
    def effective_program(self):
        return self.exam_schedule.subject.department

    @property
    def effective_semester(self):
        return self.exam_schedule.subject.semester


class Attendance(models.Model):
    exam_schedule = models.ForeignKey(ExamSchedule, on_delete=models.CASCADE, related_name='attendances')
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='attendances')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('exam_schedule', 'room')


class AttendanceEntry(models.Model):
    attendance = models.ForeignKey(Attendance, on_delete=models.CASCADE, related_name='entries')
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    booklet_number = models.CharField(max_length=50, blank=True, default='')
    present = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.student.reg_no} - {'P' if self.present else 'A'}"
