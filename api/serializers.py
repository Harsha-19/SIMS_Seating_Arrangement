from collections.abc import Mapping

from django.db import transaction
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Student, Room, Exam, Seating, Attendance, AttendanceEntry, Program, Enrollment, ExamGroup

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
        fields = ['_id', 'id', 'room_number', 'total_capacity', 'rows', 'left_seats', 'middle_seats', 'right_seats', 'created_at', 'updated_at']

class ExamGroupSerializer(BaseSerializer):
    program_info = ProgramSerializer(source='program', read_only=True)
    department = serializers.IntegerField(source='program_id', read_only=True)
    semester = serializers.IntegerField(min_value=1, max_value=6)
    subject = serializers.CharField(required=True, allow_blank=False, trim_whitespace=True)

    def to_internal_value(self, data):
        if isinstance(data, Mapping):
            normalized = data.copy()
            department = normalized.get('department')
            program = normalized.get('program')

            if department not in (None, ''):
                if program not in (None, '') and str(program) != str(department):
                    raise serializers.ValidationError({
                        'program': ['Program and department must match when both are provided.'],
                    })
                normalized['program'] = department

            try:
                del normalized['department']
            except (KeyError, TypeError):
                pass

            return super().to_internal_value(normalized)

        return super().to_internal_value(data)

    def validate_subject(self, value):
        normalized = str(value).strip().upper()
        if not normalized:
            raise serializers.ValidationError('Subject is required.')
        return normalized

    class Meta:
        model = ExamGroup
        fields = ['_id', 'id', 'program', 'department', 'program_info', 'semester', 'subject', 'created_at']

class ExamSerializer(BaseSerializer):
    program_info = ProgramSerializer(source='program', read_only=True)
    department = serializers.IntegerField(source='program_id', read_only=True)

    subject = serializers.CharField(required=True, allow_blank=False, trim_whitespace=True)
    semester = serializers.IntegerField(min_value=1, max_value=6, required=False, allow_null=True)
    exam_type = serializers.ChoiceField(choices=Exam.EXAM_TYPE_CHOICES, required=False, default=Exam.CORE)
    date = serializers.DateField(
        input_formats=['%Y-%m-%d', '%d-%m-%Y'],
        error_messages={'invalid': 'Use YYYY-MM-DD or DD-MM-YYYY.'},
    )
    start_time = serializers.TimeField(
        input_formats=['%H:%M:%S', '%H:%M', '%I:%M %p'],
        required=False,
        allow_null=True,
        error_messages={'invalid': 'Use HH:MM:SS, HH:MM, or h:mm AM/PM.'},
    )
    end_time = serializers.TimeField(
        input_formats=['%H:%M:%S', '%H:%M', '%I:%M %p'],
        required=False,
        allow_null=True,
        error_messages={'invalid': 'Use HH:MM:SS, HH:MM, or h:mm AM/PM.'},
    )
    groups = ExamGroupSerializer(many=True, required=False)
    group_summary = serializers.CharField(read_only=True)
    display_programs = serializers.CharField(read_only=True)
    display_semesters = serializers.CharField(read_only=True)
    is_grouped_exam = serializers.BooleanField(read_only=True)

    def to_internal_value(self, data):
        if isinstance(data, Mapping):
            normalized = data.copy()
            if normalized.get('name') not in (None, '') and normalized.get('subject') in (None, ''):
                normalized['subject'] = normalized.get('name')
            department = normalized.get('department')
            program = normalized.get('program')

            if department not in (None, ''):
                if program not in (None, '') and str(program) != str(department):
                    raise serializers.ValidationError({
                        'program': ['Program and department must match when both are provided.'],
                    })
                normalized['program'] = department

            try:
                del normalized['department']
            except (KeyError, TypeError):
                pass

            return super().to_internal_value(normalized)

        return super().to_internal_value(data)

    def validate_subject(self, value):
        normalized = str(value).strip().upper()
        if not normalized:
            raise serializers.ValidationError('Subject is required.')
        return normalized

    def validate(self, data):
        start = data.get('start_time', getattr(self.instance, 'start_time', None))
        end = data.get('end_time', getattr(self.instance, 'end_time', None))
        groups = data.get('groups', serializers.empty)
        program = data.get('program', getattr(self.instance, 'program', None))
        semester = data.get('semester', getattr(self.instance, 'semester', None))

        if start and end and start >= end:
            raise serializers.ValidationError({
                'end_time': ['End time must be after start time.'],
            })

        if groups is not serializers.empty:
            if not groups:
                raise serializers.ValidationError({
                    'groups': ['Provide at least one exam group.'],
                })
        elif not getattr(self.instance, 'pk', None) and (program is None or semester is None):
            raise serializers.ValidationError({
                'program': ['Program is required when groups are not provided.'],
                'semester': ['Semester is required when groups are not provided.'],
            })

        return data

    def _legacy_group_payload(self, validated_data, *, instance=None):
        program = validated_data.get('program', getattr(instance, 'program', None))
        semester = validated_data.get('semester', getattr(instance, 'semester', None))
        subject = validated_data.get('subject', getattr(instance, 'subject', None))

        if program is None or semester is None or subject in (None, ''):
            return []

        return [{
            'program': program,
            'semester': semester,
            'subject': subject,
        }]

    def _set_exam_summary_fields(self, exam, group_payloads):
        if len(group_payloads) == 1:
            group_payload = group_payloads[0]
            exam.program = group_payload['program']
            exam.semester = group_payload['semester']
        else:
            exam.program = None
            exam.semester = None

    def _sync_groups(self, exam, group_payloads):
        exam.groups.all().delete()
        for group_payload in group_payloads:
            ExamGroup.objects.create(exam=exam, **group_payload)
        self._set_exam_summary_fields(exam, group_payloads)
        exam.save(update_fields=['program', 'semester', 'subject', 'date', 'start_time', 'end_time', 'exam_type', 'updated_at'])

    def create(self, validated_data):
        groups_data = validated_data.pop('groups', serializers.empty)
        group_payloads = groups_data if groups_data is not serializers.empty else self._legacy_group_payload(validated_data)

        if not group_payloads:
            raise serializers.ValidationError({'groups': ['Unable to derive exam groups from the payload.']})

        if len(group_payloads) > 1:
            validated_data['program'] = None
            validated_data['semester'] = None

        with transaction.atomic():
            exam = Exam.objects.create(**validated_data)
            self._sync_groups(exam, group_payloads)
            return exam

    def update(self, instance, validated_data):
        groups_data = validated_data.pop('groups', serializers.empty)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if groups_data is not serializers.empty:
            group_payloads = groups_data
        elif instance.groups.exists():
            if instance.groups.count() == 1:
                group_payloads = self._legacy_group_payload(validated_data, instance=instance)
            else:
                group_payloads = [
                    {
                        'program': group.program,
                        'semester': group.semester,
                        'subject': group.subject,
                    }
                    for group in instance.groups.select_related('program').order_by('program__name', 'semester', 'subject', 'id')
                ]
        else:
            group_payloads = self._legacy_group_payload(validated_data, instance=instance)

        if not group_payloads:
            raise serializers.ValidationError({'groups': ['Unable to derive exam groups from the payload.']})

        with transaction.atomic():
            self._set_exam_summary_fields(instance, group_payloads)
            instance.save()
            self._sync_groups(instance, group_payloads)
            return instance

    class Meta:
        model = Exam
        fields = [
            '_id', 'id', 'subject', 'program', 'department', 'program_info', 'semester',
            'date', 'start_time', 'end_time', 'exam_type', 'groups', 'group_summary',
            'display_programs', 'display_semesters', 'is_grouped_exam', 'created_at', 'updated_at',
        ]


class SemesterOptionSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    number = serializers.IntegerField()
    name = serializers.CharField()
    department = serializers.IntegerField()

class SeatingSerializer(BaseSerializer):
    student_info = StudentSerializer(source='student', read_only=True)
    room_info = RoomSerializer(source='room', read_only=True)
    exam_info = ExamSerializer(source='exam', read_only=True)
    exam_group_info = ExamGroupSerializer(source='exam_group', read_only=True)
    class Meta:
        model = Seating
        fields = ['_id', 'id', 'student', 'room', 'exam', 'exam_group', 'row', 'seat_position', 'student_info', 'room_info', 'exam_info', 'exam_group_info', 'created_at']

class AttendanceSerializer(BaseSerializer):
    exam_info = ExamSerializer(source='exam', read_only=True)
    room_info = RoomSerializer(source='room', read_only=True)
    class Meta:
        model = Attendance
        fields = ['_id', 'id', 'exam', 'room', 'exam_info', 'room_info', 'created_at']

class AttendanceEntrySerializer(BaseSerializer):
    student_info = StudentSerializer(source='student', read_only=True)
    class Meta:
        model = AttendanceEntry
        fields = ['_id', 'id', 'attendance', 'student', 'student_info', 'present', 'booklet_number']
