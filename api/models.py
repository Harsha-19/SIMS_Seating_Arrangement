from django.db import models
from django.core.exceptions import ValidationError

class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # 4. NORMALIZE DEPARTMENT VALUES
        self.name = str(self.name).strip().upper()
        # "B SC" -> "BSC", "B COM" -> "BCOM"
        self.name = self.name.replace("B SC", "BSC").replace("B COM", "BCOM").replace("B A", "BA")
        
        # 7. VALIDATION BEFORE INSERT (Strict rejection of dirty data)
        invalid_keywords = ["SEM", "-", "TEST", "CLASS", "SESSION"]
        if any(kw in self.name for kw in invalid_keywords) or len(self.name) > 35:
             # SILENTLY CLEAN or REJECT? User said "REJECT or CLEAN before insert"
             # I will skip saving if it's clearly garbage or raise error
             # In a production context, raising ValidationError is safer
             raise ValidationError(f"INVALID DEPARTMENT NAME: {self.name}")
             
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Semester(models.Model):
    name = models.CharField(max_length=50) # 1st Sem, 2nd Sem, etc.
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='semesters')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('name', 'department')
        # Standardize ordering by name string (will handle 1st..6th reasonably well)
        ordering = ['name']

    def save(self, *args, **kwargs):
        from .utils import normalize_semester_name
        self.name = normalize_semester_name(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.department.name} - {self.name}"

class Student(models.Model):
    university_id = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, related_name='students')
    semester = models.ForeignKey(Semester, on_delete=models.SET_NULL, null=True, related_name='students')
    sem = models.IntegerField(null=True, blank=True)
    sem_type = models.CharField(max_length=10, choices=[('ODD', 'ODD'), ('EVEN', 'EVEN')], null=True, blank=True)
    section = models.CharField(max_length=10, blank=True, default='') # NEW FIELD
    specialization = models.CharField(max_length=100, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['department']),
            models.Index(fields=['semester']),
            models.Index(fields=['sem_type']),
        ]

    def __str__(self):
        return f"{self.university_id} - {self.name}"

    def save(self, *args, **kwargs):
        self.university_id = self.university_id.upper()
        if self.sem and not self.sem_type:
            if self.sem in [1, 3, 5]:
                self.sem_type = 'ODD'
            elif self.sem in [2, 4, 6]:
                self.sem_type = 'EVEN'
        super().save(*args, **kwargs)

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
    subject = models.CharField(max_length=100)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='exams', null=True)
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE, related_name='exams', null=True)
    date = models.DateField()
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def duration_str(self):
        if self.start_time and self.end_time:
            # Fake date to calculate duration
            from datetime import datetime, date
            dt1 = datetime.combine(date.today(), self.start_time)
            dt2 = datetime.combine(date.today(), self.end_time)
            diff = dt2 - dt1
            total_seconds = int(diff.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            if hours > 0:
                return f"{hours}h {minutes}m" if minutes > 0 else f"{hours} hours"
            return f"{minutes} mins"
        return "Unknown"

    def clean(self):
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValidationError("End time must be after start time.")
        super().clean()

    def save(self, *args, **kwargs):
        self.full_clean()
        self.subject = self.subject.upper()
        super().save(*args, **kwargs)

    def __str__(self):
        time_range = f"{self.start_time.strftime('%I:%M %p')} - {self.end_time.strftime('%I:%M %p')}" if self.start_time and self.end_time else ""
        dept_name = self.department.name if self.department else "Unknown"
        sem_name = self.semester.name if self.semester else "Unknown"
        return f"{self.subject} ({dept_name} {sem_name}) | {time_range}"

    class Meta:
        indexes = [
            models.Index(fields=['date', 'subject']),
        ]

class Seating(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='seats')
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='seats')
    row = models.IntegerField()
    # Position in the row (e.g., "Left Seat 1", "Middle Seat 2")
    seat_position = models.CharField(max_length=50)
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='seats')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [
            ('exam', 'student'),
            ('exam', 'room', 'row', 'seat_position'),
        ]
        indexes = [
            models.Index(fields=['student']),
            models.Index(fields=['room']),
            models.Index(fields=['exam']),
        ]

    def __str__(self):
        return f"{self.student.university_id} - {self.room.room_number}"

class Attendance(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='attendances')
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='attendances')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('exam', 'room')

class AttendanceEntry(models.Model):
    attendance = models.ForeignKey(Attendance, on_delete=models.CASCADE, related_name='entries')
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    booklet_number = models.CharField(max_length=50, blank=True, default='')
    present = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.student.university_id} - {'P' if self.present else 'A'}"
class SystemSettings(models.Model):
    SEMESTER_TYPES = [
        ('ODD', 'ODD Semester (1, 3, 5)'),
        ('EVEN', 'EVEN Semester (2, 4, 6)'),
    ]
    current_sem_type = models.CharField(max_length=10, choices=SEMESTER_TYPES, default='ODD')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "System Settings"

    def __str__(self):
        return f"System Mode: {self.current_sem_type}"

    @classmethod
    def get_current_type(cls):
        obj, _ = cls.objects.get_or_create(id=1)
        return obj.current_sem_type

    @classmethod
    def set_current_type(cls, sem_type):
        obj, _ = cls.objects.get_or_create(id=1)
        obj.current_sem_type = sem_type
        obj.save()
