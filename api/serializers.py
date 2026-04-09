from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Student, Room, Exam, Seating, Attendance, AttendanceEntry, Department, Semester

class BaseSerializer(serializers.ModelSerializer):
    _id = serializers.CharField(source='id', read_only=True)

class UserSerializer(BaseSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']

class DepartmentSerializer(BaseSerializer):
    class Meta:
        model = Department
        fields = ['_id', 'id', 'name', 'created_at']

class SemesterSerializer(BaseSerializer):
    department_info = DepartmentSerializer(source='department', read_only=True)
    class Meta:
        model = Semester
        fields = ['_id', 'id', 'name', 'department', 'department_info', 'created_at']

class StudentSerializer(BaseSerializer):
    department_info = DepartmentSerializer(source='department', read_only=True)
    semester_info = SemesterSerializer(source='semester', read_only=True)
    class Meta:
        model = Student
        fields = ['_id', 'id', 'university_id', 'name', 'department', 'semester', 'department_info', 'semester_info', 'created_at', 'updated_at']

class RoomSerializer(BaseSerializer):
    class Meta:
        model = Room
        fields = ['_id', 'id', 'room_number', 'total_capacity', 'rows', 'left_seats', 'middle_seats', 'right_seats', 'created_at', 'updated_at']

class ExamSerializer(BaseSerializer):
    department_info = DepartmentSerializer(source='department', read_only=True)
    semester_info = SemesterSerializer(source='semester', read_only=True)
    class Meta:
        model = Exam
        fields = ['_id', 'id', 'subject', 'department', 'semester', 'department_info', 'semester_info', 'date', 'start_time', 'end_time', 'created_at', 'updated_at']

class SeatingSerializer(BaseSerializer):
    student_info = StudentSerializer(source='student', read_only=True)
    room_info = RoomSerializer(source='room', read_only=True)
    exam_info = ExamSerializer(source='exam', read_only=True)
    class Meta:
        model = Seating
        fields = ['_id', 'id', 'student', 'room', 'exam', 'row', 'seat_position', 'student_info', 'room_info', 'exam_info', 'created_at']

class AttendanceSerializer(BaseSerializer):
    exam_info = ExamSerializer(source='exam', read_only=True)
    class Meta:
        model = Attendance
        fields = ['_id', 'id', 'exam', 'exam_info', 'created_at']

class AttendanceEntrySerializer(BaseSerializer):
    student_info = StudentSerializer(source='student', read_only=True)
    class Meta:
        model = AttendanceEntry
        fields = ['_id', 'id', 'attendance', 'student', 'student_info', 'present', 'booklet_number']
