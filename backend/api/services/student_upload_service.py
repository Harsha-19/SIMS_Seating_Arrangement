import io
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from django.db import transaction

from api.models import Enrollment, Program, Student, derive_sem_type
from api.utils import sanitize_academic_info

logger = logging.getLogger("api.upload")

UPLOAD_HEADER_ALIASES: dict[str, tuple[str, ...]] = {
    "reg_no": (
        "reg no",
        "reg no.",
        "reg number",
        "regn no",
        "regd no",
        "register no",
        "register number",
        "registration no",
        "registration number",
        "registration id",
        "roll no",
        "roll number",
        "student id",
        "university id",
        "university no",
        "usn",
        "id",
    ),
    "name": (
        "name",
        "student name",
        "full name",
        "candidate name",
        "first name",
        "firstname",
        "student",
    ),
    "class": (
        "class",
        "class info",
        "academic info",
        "academic",
        "class name",
    ),
    "program": (
        "program",
        "programme",
        "department",
        "dept",
        "course",
        "stream",
        "branch",
    ),
    "semester": (
        "semester",
        "semester no",
        "semester number",
        "sem",
        "sem no",
        "sem number",
    ),
    "section": (
        "section",
        "sec",
        "batch",
        "group",
    ),
}
HEADER_SCAN_LIMIT = 25
PREVIEW_ROW_LIMIT = 5
SKIP_PREVIEW_LIMIT = 20
CLASS_PREVIEW_LIMIT = 10
SUPPORTED_EXTENSIONS = {".xlsx", ".xls"}


class StudentUploadError(Exception):
    """Raised when an upload cannot be processed safely."""


@dataclass
class ParsedStudentUploadRow:
    excel_row_number: int
    reg_no: str
    name: str
    academic: dict[str, Any]
    source_class_value: str
    source_values: dict[str, str]


def _import_pandas():
    try:
        import pandas as pd  # type: ignore
    except ImportError as exc:
        raise StudentUploadError(
            "Excel upload requires pandas. Add it to the backend environment and try again."
        ) from exc
    return pd


def _clean_cell_value(value: Any) -> str:
    if value is None:
        return ""

    text = str(value).strip()
    if not text:
        return ""

    lowered = text.lower()
    if lowered in {"nan", "none", "null"}:
        return ""

    if re.fullmatch(r"-?\d+\.0", text):
        text = text[:-2]

    return re.sub(r"\s+", " ", text).strip()


def _normalize_header_value(value: Any) -> str:
    header = _clean_cell_value(value).lower()
    header = re.sub(r"[^a-z0-9]+", " ", header)
    return re.sub(r"\s+", " ", header).strip()


def _score_header_match(header_value: str, alias: str) -> int:
    if not header_value:
        return 0

    normalized_header = header_value.strip().lower()
    normalized_alias = alias.strip().lower()
    compact_header = normalized_header.replace(" ", "")
    compact_alias = normalized_alias.replace(" ", "")

    if normalized_header == normalized_alias:
        return 100
    if compact_header == compact_alias:
        return 95
    if normalized_alias in normalized_header or compact_alias in compact_header:
        return 80

    header_tokens = set(normalized_header.split())
    alias_tokens = set(normalized_alias.split())
    if alias_tokens and alias_tokens.issubset(header_tokens):
        return 75

    overlap = header_tokens & alias_tokens
    if overlap:
        return 40 + (len(overlap) * 10)

    return 0


def _read_excel_preview(file_bytes: bytes, extension: str):
    pd = _import_pandas()
    engine = "xlrd" if extension == ".xls" else "openpyxl"

    try:
        preview_frame = pd.read_excel(
            io.BytesIO(file_bytes),
            header=None,
            dtype=object,
            sheet_name=0,
            engine=engine,
        )
    except ImportError as exc:
        if extension == ".xls":
            raise StudentUploadError(
                "Reading .xls files requires the xlrd package. Add xlrd to the backend environment and try again."
            ) from exc
        raise StudentUploadError("Excel upload dependencies are missing. Please verify pandas and openpyxl.") from exc
    except ValueError as exc:
        raise StudentUploadError(f"Unable to read the uploaded Excel file: {exc}") from exc
    except Exception as exc:
        raise StudentUploadError(f"Unable to parse the uploaded Excel file: {exc}") from exc

    if preview_frame.empty:
        raise StudentUploadError("The uploaded Excel file is empty.")

    return preview_frame


def _detect_header_row(preview_frame) -> tuple[int, dict[str, int], list[str]]:
    best_candidate: tuple[int, dict[str, int], list[str], int, int] | None = None

    for row_index in range(min(len(preview_frame.index), HEADER_SCAN_LIMIT)):
        row_values = list(preview_frame.iloc[row_index].tolist())
        normalized_cells = [_normalize_header_value(value) for value in row_values]
        if not any(normalized_cells):
            continue

        row_mapping: dict[str, int] = {}
        total_score = 0

        for logical_key, aliases in UPLOAD_HEADER_ALIASES.items():
            best_score_for_key = 0
            best_column_index: int | None = None
            for column_index, cell_value in enumerate(normalized_cells):
                cell_score = max((_score_header_match(cell_value, alias) for alias in aliases), default=0)
                if cell_score > best_score_for_key:
                    best_score_for_key = cell_score
                    best_column_index = column_index

            if best_column_index is not None and best_score_for_key >= 60:
                row_mapping[logical_key] = best_column_index
                total_score += best_score_for_key

        has_identity_columns = "reg_no" in row_mapping and "name" in row_mapping
        has_academic_columns = any(key in row_mapping for key in ("class", "program", "semester"))
        if not (has_identity_columns and has_academic_columns):
            continue

        matched_columns = len(row_mapping)
        candidate = (
            row_index,
            row_mapping,
            [_clean_cell_value(value) for value in row_values],
            matched_columns,
            total_score,
        )

        if best_candidate is None:
            best_candidate = candidate
            continue

        _, _, _, best_match_count, best_total_score = best_candidate
        if matched_columns > best_match_count or (
            matched_columns == best_match_count and total_score > best_total_score
        ):
            best_candidate = candidate

    if best_candidate is None:
        raise StudentUploadError(
            "Could not detect the student Excel headers. Expected columns like Reg No, Name, Class, Dept, or Semester."
        )

    header_row_index, header_mapping, header_labels, _, _ = best_candidate
    return header_row_index, header_mapping, header_labels


def _row_is_effectively_empty(row_values: list[str]) -> bool:
    return not any(value for value in row_values)


def _row_looks_like_repeated_header(row_values: list[str], header_labels: list[str]) -> bool:
    normalized_row = {_normalize_header_value(value) for value in row_values if _normalize_header_value(value)}
    normalized_headers = {_normalize_header_value(value) for value in header_labels if _normalize_header_value(value)}
    if not normalized_row or not normalized_headers:
        return False

    overlap_count = len(normalized_row & normalized_headers)
    return overlap_count >= 2 and overlap_count >= min(3, len(normalized_row))


def _get_row_value(row_values: list[str], header_mapping: dict[str, int], logical_key: str) -> str:
    column_index = header_mapping.get(logical_key)
    if column_index is None or column_index >= len(row_values):
        return ""
    return row_values[column_index]


def _build_academic_candidates(row_values: list[str], header_mapping: dict[str, int]) -> list[str]:
    class_value = _get_row_value(row_values, header_mapping, "class")
    program_value = _get_row_value(row_values, header_mapping, "program")
    semester_value = _get_row_value(row_values, header_mapping, "semester")
    section_value = _get_row_value(row_values, header_mapping, "section")

    raw_candidates: list[str] = []

    if class_value:
        raw_candidates.append(class_value)

    if class_value and program_value and program_value.upper() not in class_value.upper():
        raw_candidates.append(" ".join(part for part in [class_value, program_value, section_value] if part))
        raw_candidates.append(" ".join(part for part in [program_value, class_value, section_value] if part))

    if semester_value:
        semester_token = semester_value if "SEM" in semester_value.upper() else f"{semester_value} SEM"
        if program_value:
            raw_candidates.append(" ".join(part for part in [program_value, semester_token, section_value] if part))
            raw_candidates.append(" ".join(part for part in [semester_token, program_value, section_value] if part))
        else:
            raw_candidates.append(" ".join(part for part in [semester_token, section_value] if part))

    if program_value or semester_value or section_value:
        raw_candidates.append(" ".join(part for part in [program_value, semester_value, section_value] if part))

    full_row_value = " ".join(value for value in row_values if value)
    if full_row_value:
        raw_candidates.append(full_row_value)

    deduped_candidates: list[str] = []
    seen_candidates: set[str] = set()
    for candidate in raw_candidates:
        cleaned = re.sub(r"\s+", " ", candidate).strip()
        normalized = cleaned.upper()
        if not cleaned or normalized in seen_candidates:
            continue
        seen_candidates.add(normalized)
        deduped_candidates.append(cleaned)

    return deduped_candidates


def _parse_academic_info_from_row(row_values: list[str], header_mapping: dict[str, int]) -> tuple[dict[str, Any] | None, str]:
    last_candidate = ""
    for candidate in _build_academic_candidates(row_values, header_mapping):
        last_candidate = candidate
        parsed = sanitize_academic_info(candidate, debug=True)
        if parsed is not None:
            return parsed, candidate
    return None, last_candidate


def _build_preview_row_payload(row_values: list[str], header_labels: list[str]) -> dict[str, str]:
    preview: dict[str, str] = {}
    for column_index, value in enumerate(row_values[: len(header_labels)]):
        label = header_labels[column_index] if column_index < len(header_labels) else f"COLUMN_{column_index + 1}"
        if not label and not value:
            continue
        preview[label or f"COLUMN_{column_index + 1}"] = value
    return preview


def _dedupe_parsed_rows(parsed_rows: list[ParsedStudentUploadRow]) -> tuple[list[ParsedStudentUploadRow], int]:
    unique_rows: dict[tuple[str, str, int], ParsedStudentUploadRow] = {}
    duplicate_count = 0

    for row in parsed_rows:
        key = (row.reg_no, row.academic["program"], row.academic["semester"])
        existing = unique_rows.get(key)
        if existing is None:
            unique_rows[key] = row
            continue

        duplicate_count += 1
        current_section = str(existing.academic.get("section", "") or "").strip().upper()
        next_section = str(row.academic.get("section", "") or "").strip().upper()

        if next_section and not current_section:
            unique_rows[key] = row
            continue

        if len(row.name) >= len(existing.name):
            unique_rows[key] = row

    return list(unique_rows.values()), duplicate_count


def _persist_rows(parsed_rows: list[ParsedStudentUploadRow]) -> dict[str, int]:
    reg_numbers = sorted({row.reg_no for row in parsed_rows})
    program_names = sorted({row.academic["program"] for row in parsed_rows})

    with transaction.atomic():
        existing_students = Student.objects.in_bulk(reg_numbers, field_name="reg_no")
        students_to_create: list[Student] = []
        students_to_update: list[Student] = []

        latest_student_names: dict[str, str] = {}
        for row in parsed_rows:
            latest_student_names[row.reg_no] = row.name

        for reg_no, name in latest_student_names.items():
            existing_student = existing_students.get(reg_no)
            if existing_student is None:
                students_to_create.append(Student(reg_no=reg_no, name=name))
                continue
            if existing_student.name != name:
                existing_student.name = name
                students_to_update.append(existing_student)

        if students_to_create:
            Student.objects.bulk_create(students_to_create, batch_size=500, ignore_conflicts=True)

        if students_to_update:
            Student.objects.bulk_update(students_to_update, ["name"], batch_size=500)

        student_lookup = Student.objects.in_bulk(reg_numbers, field_name="reg_no")

        existing_programs = Program.objects.in_bulk(program_names, field_name="name")
        programs_to_create = [Program(name=name) for name in program_names if name not in existing_programs]
        if programs_to_create:
            Program.objects.bulk_create(programs_to_create, batch_size=100, ignore_conflicts=True)

        program_lookup = Program.objects.in_bulk(program_names, field_name="name")

        existing_enrollments = {
            (enrollment.student_id, enrollment.program_id, enrollment.semester): enrollment
            for enrollment in Enrollment.objects.filter(
                student_id__in=[student.id for student in student_lookup.values()],
                program_id__in=[program.id for program in program_lookup.values()],
                semester__in=[row.academic["semester"] for row in parsed_rows],
            )
        }

        enrollments_to_create: list[Enrollment] = []
        enrollments_to_update: list[Enrollment] = []

        for row in parsed_rows:
            student = student_lookup[row.reg_no]
            program = program_lookup[row.academic["program"]]
            key = (student.id, program.id, row.academic["semester"])
            section = str(row.academic.get("section", "") or "").strip().upper()
            sem_type = derive_sem_type(row.academic["semester"])

            existing_enrollment = existing_enrollments.get(key)
            if existing_enrollment is None:
                enrollments_to_create.append(
                    Enrollment(
                        student_id=student.id,
                        program_id=program.id,
                        semester=row.academic["semester"],
                        section=section,
                        sem_type=sem_type,
                    )
                )
                continue

            if section and (existing_enrollment.section or "").strip().upper() != section:
                existing_enrollment.section = section
                existing_enrollment.sem_type = sem_type
                enrollments_to_update.append(existing_enrollment)

        if enrollments_to_create:
            Enrollment.objects.bulk_create(enrollments_to_create, batch_size=500, ignore_conflicts=True)

        if enrollments_to_update:
            Enrollment.objects.bulk_update(enrollments_to_update, ["section", "sem_type"], batch_size=500)

    return {
        "created_students": len(students_to_create),
        "updated_students": len(students_to_update),
        "created_programs": len(programs_to_create),
        "created_enrollments": len(enrollments_to_create),
        "updated_enrollments": len(enrollments_to_update),
        "existing_enrollments": max(len(parsed_rows) - len(enrollments_to_create), 0),
    }


class StudentUploadService:
    """End-to-end student Excel upload parsing and persistence."""

    @staticmethod
    def process(file_obj: Any) -> dict[str, Any]:
        file_name = getattr(file_obj, "name", "upload")
        extension = Path(file_name).suffix.lower()
        if extension not in SUPPORTED_EXTENSIONS:
            raise StudentUploadError("Unsupported file type. Please upload a .xlsx or .xls Excel file.")

        file_bytes = file_obj.read()
        if not file_bytes:
            raise StudentUploadError("The uploaded file is empty.")

        logger.info("UPLOAD API HIT")
        logger.info("FILE RECEIVED: %s", file_name)

        preview_frame = _read_excel_preview(file_bytes, extension)
        header_row_index, header_mapping, header_labels = _detect_header_row(preview_frame)

        pd = _import_pandas()
        data_frame = preview_frame.iloc[header_row_index + 1 :].copy()
        data_frame.columns = pd.Index([_clean_cell_value(label) for label in header_labels]).str.strip()
        raw_row_count = len(data_frame.index)
        logger.info("HEADERS: %s", list(data_frame.columns))
        logger.info("DETECTED HEADER MAP: %s", header_mapping)
        logger.info("TOTAL ROWS: %s", raw_row_count)

        parsed_rows: list[ParsedStudentUploadRow] = []
        skipped_rows: list[dict[str, Any]] = []
        skipped_row_count = 0
        preview_rows: list[dict[str, Any]] = []
        parsed_previews: list[dict[str, Any]] = []

        for row_offset, raw_row in enumerate(data_frame.itertuples(index=False, name=None), start=1):
            excel_row_number = header_row_index + 1 + row_offset + 1
            cleaned_values = [_clean_cell_value(value) for value in raw_row]

            if _row_is_effectively_empty(cleaned_values):
                continue

            if _row_looks_like_repeated_header(cleaned_values, header_labels):
                logger.debug("Skipping repeated header row at Excel row %s: %s", excel_row_number, cleaned_values)
                continue

            if len(preview_rows) < PREVIEW_ROW_LIMIT:
                preview_rows.append(
                    {
                        "excel_row": excel_row_number,
                        "values": _build_preview_row_payload(cleaned_values, header_labels),
                    }
                )

            reg_no = _get_row_value(cleaned_values, header_mapping, "reg_no").upper()
            name = _get_row_value(cleaned_values, header_mapping, "name").upper()

            academic, class_candidate = _parse_academic_info_from_row(cleaned_values, header_mapping)
            if class_candidate:
                logger.debug("CLASS STRING ROW %s: %s", excel_row_number, class_candidate)
            if academic is not None:
                logger.debug("PARSED ROW %s: %s", excel_row_number, academic)

            row_errors: list[str] = []
            if not reg_no:
                row_errors.append("Missing registration number")
            if not name:
                row_errors.append("Missing student name")
            if academic is None:
                row_errors.append("Could not parse academic class information")

            if row_errors:
                skipped_row_count += 1
                if len(skipped_rows) < SKIP_PREVIEW_LIMIT:
                    skipped_rows.append(
                        {
                            "excel_row": excel_row_number,
                            "errors": row_errors,
                            "row_preview": _build_preview_row_payload(cleaned_values, header_labels),
                            "class_candidate": class_candidate,
                        }
                    )
                continue

            parsed_row = ParsedStudentUploadRow(
                excel_row_number=excel_row_number,
                reg_no=reg_no.strip(),
                name=name.strip(),
                academic=academic,
                source_class_value=class_candidate,
                source_values={
                    "class": _get_row_value(cleaned_values, header_mapping, "class"),
                    "program": _get_row_value(cleaned_values, header_mapping, "program"),
                    "semester": _get_row_value(cleaned_values, header_mapping, "semester"),
                    "section": _get_row_value(cleaned_values, header_mapping, "section"),
                },
            )
            parsed_rows.append(parsed_row)

            if len(parsed_previews) < CLASS_PREVIEW_LIMIT:
                parsed_previews.append(
                    {
                        "excel_row": excel_row_number,
                        "class_string": class_candidate,
                        "parsed": academic,
                    }
                )

        if not parsed_rows:
            logger.warning("Student upload failed because no valid student rows were parsed.")
            raise StudentUploadError(
                "No valid student rows were found in the uploaded Excel file. Check the Class, Dept, Semester, Reg No, and Name columns."
            )

        deduped_rows, duplicate_rows_in_file = _dedupe_parsed_rows(parsed_rows)
        persistence_counts = _persist_rows(deduped_rows)

        logger.info("PARSED VALID ROWS: %s", len(parsed_rows))
        logger.info("DEDUPED ROWS: %s", len(deduped_rows))
        logger.info("SKIPPED ROWS: %s", skipped_row_count)
        logger.info("CREATED STUDENTS: %s", persistence_counts["created_students"])
        logger.info("UPDATED STUDENTS: %s", persistence_counts["updated_students"])
        logger.info("CREATED ENROLLMENTS: %s", persistence_counts["created_enrollments"])
        logger.info("UPDATED ENROLLMENTS: %s", persistence_counts["updated_enrollments"])
        logger.info("EXISTING ENROLLMENTS: %s", persistence_counts["existing_enrollments"])

        response_payload = {
            "success": True,
            "count": len(deduped_rows),
            "message": f"Successfully uploaded {len(deduped_rows)} students",
            "total_rows": raw_row_count,
            "valid_rows": len(parsed_rows),
            "duplicate_rows_in_file": duplicate_rows_in_file,
            "skipped_rows": skipped_row_count,
            "created_students": persistence_counts["created_students"],
            "updated_students": persistence_counts["updated_students"],
            "created_programs": persistence_counts["created_programs"],
            "created_enrollments": persistence_counts["created_enrollments"],
            "updated_enrollments": persistence_counts["updated_enrollments"],
            "existing_enrollments": persistence_counts["existing_enrollments"],
            "detected_headers": list(data_frame.columns),
            "header_row": header_row_index + 1,
            "preview_rows": preview_rows,
            "parsed_row_previews": parsed_previews,
            "skipped_row_previews": skipped_rows,
        }
        logger.info("UPLOAD SUMMARY: %s", response_payload)
        return response_payload
