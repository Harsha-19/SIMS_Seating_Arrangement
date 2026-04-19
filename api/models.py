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
    left_seats = models.IntegerField(default=3)
    middle_seats = models.IntegerField(default=2)
    right_seats = models.IntegerField(default=3)
    total_capacity = models.IntegerField(editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        self.room_number = self.room_number.upper()
        self.total_capacity = self.rows * (self.left_seats + self.middle_seats + self.right_seats)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.room_number

class Exam(models.Model):
    COMMON = 'COMMON'
    CORE = 'CORE'
    EXAM_TYPE_CHOICES = [
        (COMMON, 'Common Subject'),
        (CORE, 'Department Specific'),
    ]

    subject = models.CharField(max_length=100)
    program = models.ForeignKey(
        Program,
        on_delete=models.CASCADE,
        related_name='exams',
        null=True,
        blank=True,
    )
    semester = models.IntegerField(null=True, blank=True) # 1-6
    date = models.DateField()
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    exam_type = models.CharField(max_length=10, choices=EXAM_TYPE_CHOICES, default=CORE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if self.semester is not None and self.semester not in VALID_SEMESTERS:
            raise ValidationError("Semester must be between 1 and 6.")
        super().clean()

    def save(self, *args, **kwargs):
        self.subject = self.subject.upper()
        super().save(*args, **kwargs)

    @property
    def name(self):
        return self.subject

    @name.setter
    def name(self, value):
        self.subject = value

    def _resolved_groups(self):
        prefetched_groups = getattr(self, '_prefetched_objects_cache', {}).get('groups')
        if prefetched_groups is not None:
            return list(prefetched_groups)
        if not self.pk:
            return []
        return list(self.groups.select_related('program').order_by('program__name', 'semester', 'subject', 'id'))

    @property
    def primary_group(self):
        groups = self._resolved_groups()
        if groups:
            return groups[0]
        return None

    @property
    def display_programs(self):
        groups = self._resolved_groups()
        if groups:
            return ', '.join(dict.fromkeys(group.program.name for group in groups))
        if self.program:
            return self.program.name
        return 'MULTI-DEPARTMENT'

    @property
    def display_semesters(self):
        groups = self._resolved_groups()
        if groups:
            semester_tokens = [f"SEM {group.semester}" for group in groups]
            return ', '.join(dict.fromkeys(semester_tokens))
        if self.semester:
            return f"SEM {self.semester}"
        return 'MULTI-SEMESTER'

    @property
    def group_summary(self):
        groups = self._resolved_groups()
        if groups:
            summaries = [
                f"{group.program.name} SEM {group.semester} - {group.subject}"
                for group in groups[:3]
            ]
            if len(groups) > 3:
                summaries.append(f"+{len(groups) - 3} more")
            return ' | '.join(summaries)
        if self.program and self.semester:
            return f"{self.program.name} SEM {self.semester} - {self.subject}"
        return 'No exam groups configured.'

    @property
    def is_grouped_exam(self):
        return len(self._resolved_groups()) > 1

    def __str__(self):
        time_range = f"{self.start_time.strftime('%I:%M %p')} - {self.end_time.strftime('%I:%M %p')}" if self.start_time and self.end_time else ""
        return f"{self.subject} ({self.display_programs} {self.display_semesters}) | {time_range}"


class ExamGroup(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='groups')
    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name='exam_groups')
    semester = models.IntegerField() # 1-6
    subject = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('exam', 'program', 'semester', 'subject')
        indexes = [
            models.Index(fields=['exam', 'program', 'semester']),
            models.Index(fields=['subject']),
        ]

    def clean(self):
        if self.semester not in VALID_SEMESTERS:
            raise ValidationError("Semester must be between 1 and 6.")
        super().clean()

    def save(self, *args, **kwargs):
        self.subject = str(self.subject).upper().strip()
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def department(self):
        return self.program

    def __str__(self):
        return f"{self.exam.subject} | {self.program.name} Sem {self.semester} | {self.subject}"

class Seating(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='seats')
    exam_group = models.ForeignKey(
        ExamGroup,
        on_delete=models.CASCADE,
        related_name='seats',
        null=True,
        blank=True,
    )
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='seats')
    row = models.IntegerField()
    seat_position = models.CharField(max_length=50) # "Left Seat 1", etc.
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='seats')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [
            ('exam', 'student'),
            ('exam', 'room', 'row', 'seat_position'),
        ]

    @property
    def effective_subject(self):
        if self.exam_group_id:
            return self.exam_group.subject
        return self.exam.subject

    @property
    def effective_program(self):
        if self.exam_group_id:
            return self.exam_group.program
        return self.exam.program

    @property
    def effective_semester(self):
        if self.exam_group_id:
            return self.exam_group.semester
        return self.exam.semester

class Attendance(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='attendances')
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='attendances')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('exam', 'room')

class AttendanceEntry(models.Model):
    attendance = models.ForeignKey(Attendance, on_delete=models.CASCADE, related_name='entries')
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    booklet_number = models.CharField(max_length=50, blank=True, default='')
    present = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.student.reg_no} - {'P' if self.present else 'A'}"
