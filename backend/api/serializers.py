from collections.abc import Mapping

from django.db import transaction
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Student, Room, Subject, ExamSchedule, Seating, SeatingPlan, Attendance, AttendanceEntry, Program, Enrollment

class BaseSerializer(serializers.ModelSerializer):
    _id = serializers.CharField(source='id', read_only=True)

class UserSerializer(BaseSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']

class ProgramSerializer(BaseSerializer):
    name = serializers.CharField(required=True, allow_blank=False, trim_whitespace=True)

    def validate_name(self, value):
        normalized = str(value).strip().upper()
        normalized = normalized.replace("B SC", "BSC").replace("B COM", "BCOM").replace("B A", "BA")

        if not normalized:
            raise serializers.ValidationError("Department name is required.")

        existing = Program.objects.filter(name=normalized)
        if self.instance is not None:
            existing = existing.exclude(pk=self.instance.pk)
        if existing.exists():
            raise serializers.ValidationError(f"Department '{normalized}' already exists.")

        return normalized

    class Meta:
        model = Program
        fields = ['_id', 'id', 'name', 'created_at']

class EnrollmentSerializer(BaseSerializer):
    program_info = ProgramSerializer(source='program', read_only=True)
    class Meta:
        model = Enrollment
        fields = ['_id', 'id', 'student', 'program', 'program_info', 'semester', 'section', 'sem_type', 'created_at']

class StudentSerializer(BaseSerializer):
    enrollments = serializers.SerializerMethodField()

    def get_enrollments(self, obj):
        enrollments = getattr(obj, 'filtered_enrollments', None)
        if enrollments is None:
            enrollments = getattr(obj, '_prefetched_objects_cache', {}).get('enrollments')
        if enrollments is None:
            enrollments = obj.enrollments.select_related('program').all()
        return EnrollmentSerializer(enrollments, many=True, context=self.context).data

    class Meta:
        model = Student
        fields = ['_id', 'id', 'reg_no', 'name', 'enrollments', 'created_at', 'updated_at']

class RoomSerializer(BaseSerializer):
    class Meta:
        model = Room
        fields = [
            '_id', 'id', 'room_number', 'total_capacity', 'rows', 
            'column_layout', 'aisle_after_column',
            'left_seats', 'middle_seats', 'right_seats', 
            'created_at', 'updated_at'
        ]

class SubjectSerializer(BaseSerializer):
    department_info = ProgramSerializer(source='department', read_only=True)
    
    class Meta:
        model = Subject
        fields = ['_id', 'id', 'subject_name', 'subject_code', 'department', 'department_info', 'semester', 'credits', 'type', 'created_at', 'updated_at']

class ExamScheduleSerializer(BaseSerializer):
    subject_info = SubjectSerializer(source='subject', read_only=True)
    duration = serializers.CharField(read_only=True)
    
    class Meta:
        model = ExamSchedule
        fields = [
            '_id', 'id', 'subject', 'subject_info', 'exam_type', 'exam_date',
            'session', 'start_time', 'end_time', 'duration', 'academic_year',
            'status', 'created_at', 'updated_at'
        ]

class SemesterOptionSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    number = serializers.IntegerField()
    name = serializers.CharField()
    department = serializers.IntegerField()

class SeatingPlanSerializer(BaseSerializer):
    class Meta:
        model = SeatingPlan
        fields = ['_id', 'id', 'exam_schedule', 'version', 'status', 'constraint_level_used', 'generated_at', 'published_at']

class SeatingSerializer(BaseSerializer):
    student_info = StudentSerializer(source='student', read_only=True)
    room_info = RoomSerializer(source='room', read_only=True)
    exam_schedule_info = ExamScheduleSerializer(source='exam_schedule', read_only=True)
    plan_info = SeatingPlanSerializer(source='plan', read_only=True)
    class Meta:
        model = Seating
        fields = ['_id', 'id', 'plan', 'student', 'room', 'exam_schedule', 'row', 'seat_position', 'student_info', 'room_info', 'exam_schedule_info', 'plan_info', 'created_at']

class AttendanceSerializer(BaseSerializer):
    exam_schedule_info = ExamScheduleSerializer(source='exam_schedule', read_only=True)
    room_info = RoomSerializer(source='room', read_only=True)
    class Meta:
        model = Attendance
        fields = ['_id', 'id', 'exam_schedule', 'room', 'exam_schedule_info', 'room_info', 'created_at']

class AttendanceEntrySerializer(BaseSerializer):
    student_info = StudentSerializer(source='student', read_only=True)
    class Meta:
        model = AttendanceEntry
        fields = ['_id', 'id', 'attendance', 'student', 'student_info', 'present', 'booklet_number']
