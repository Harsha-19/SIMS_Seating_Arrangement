from django.db import models
from django.core.exceptions import ValidationError

class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        self.name = self.name.upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Semester(models.Model):
    name = models.CharField(max_length=50) # 1st Sem, 2nd Sem, etc.
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='semesters')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('name', 'department')

    def __str__(self):
        return f"{self.department.name} - {self.name}"

class Student(models.Model):
    university_id = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, related_name='students')
    semester = models.ForeignKey(Semester, on_delete=models.SET_NULL, null=True, related_name='students')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.university_id} - {self.name}"

    def save(self, *args, **kwargs):
        self.university_id = self.university_id.upper()
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
