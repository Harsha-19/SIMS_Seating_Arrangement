import React, { useDeferredValue, useEffect, useRef, useState } from 'react';
import {
  Users,
  Search,
  Plus,
  AlertCircle,
  Loader2,
  Trash2,
  Edit2,
  Upload,
  FileSpreadsheet,
  CheckCircle2,
  Filter,
  XCircle,
  ChevronDown,
} from 'lucide-react';

import { studentApi, normalizeArrayResponse } from '../api';

import Modal from '../components/Modal';

const ACCEPTED_FILE_EXTENSIONS = ['.xlsx', '.xls'];
const SEMESTER_OPTIONS = [
  { value: '', label: 'All Semesters' },
  ...Array.from({ length: 6 }, (_, index) => ({
    value: String(index + 1),
    label: `Semester ${index + 1}`,
  })),
];

const isSupportedSpreadsheet = (file) => {
  if (!file?.name) return false;
  const normalizedName = file.name.toLowerCase();
  return ACCEPTED_FILE_EXTENSIONS.some((extension) => normalizedName.endsWith(extension));
};

const resolveUploadPayload = (payload) => {
  if (payload?.data && typeof payload?.count === 'undefined') {
    return payload.data;
  }
  return payload;
};

const extractApiMessage = (error, fallbackMessage = 'Something went wrong.') => {
  const responseData = error?.response?.data;
  if (typeof responseData?.message === 'string' && responseData.message.trim()) {
    return responseData.message;
  }
  if (typeof responseData?.error === 'string' && responseData.error.trim()) {
    return responseData.error;
  }
  if (Array.isArray(responseData?.errors)) {
    return responseData.errors.join(', ');
  }
  if (responseData?.errors && typeof responseData.errors === 'object') {
    const firstError = Object.values(responseData.errors).flat().find(Boolean);
    if (firstError) {
      return String(firstError);
    }
  }
  return error?.message || fallbackMessage;
};

const buildStudentQueryParams = (semester, search) => {
  const params = {};
  const normalizedSearch = String(search || '').trim();

  if (semester) {
    params.semester = semester;
  }
  if (normalizedSearch) {
    params.search = normalizedSearch;
  }

  return params;
};

const getSemesterLabel = (semester) => {
  return SEMESTER_OPTIONS.find((option) => option.value === String(semester || ''))?.label || 'All Semesters';
};

const getPrimaryEnrollment = (student) => student?.enrollments?.[0] || null;

const Students = () => {
  const [students, setStudents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState(null);
  const [counts, setCounts] = useState({ filtered: 0 });
  const [selectedSemester, setSelectedSemester] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [reloadKey, setReloadKey] = useState(0);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [uploadFile, setUploadFile] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [uploadStatus, setUploadStatus] = useState(null);
  const [uploadSummary, setUploadSummary] = useState(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isUploadSubmitting, setIsUploadSubmitting] = useState(false);
  const [isFormSubmitting, setIsFormSubmitting] = useState(false);
  const [toasts, setToasts] = useState([]);
  const [editingStudent, setEditingStudent] = useState(null);
  const [formData, setFormData] = useState({ reg_no: '', name: '' });

  const deferredSearchTerm = useDeferredValue(searchTerm);
  const initialLoadRef = useRef(true);

  const activeSearchTerm = String(deferredSearchTerm || '').trim();
  const hasActiveFilters = Boolean(selectedSemester || String(searchTerm || '').trim());
  const selectedSemesterLabel = getSemesterLabel(selectedSemester);

  const pushToast = (type, title, description = '') => {
    const id = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
    setToasts((currentToasts) => [...currentToasts, { id, type, title, description }]);
    window.setTimeout(() => {
      setToasts((currentToasts) => currentToasts.filter((toast) => toast.id !== id));
    }, 4000);
  };

  const requestStudentRefresh = () => {
    setReloadKey((currentValue) => currentValue + 1);
  };

  const resetUploadState = () => {
    setUploadFile(null);
    setUploadStatus(null);
    setUploadSummary(null);
    setUploadProgress(0);
    setIsDragging(false);
  };

  const clearFilters = () => {
    setSelectedSemester('');
    setSearchTerm('');
  };

  useEffect(() => {
    const controller = new AbortController();
    const isInitialLoad = initialLoadRef.current;

    if (isInitialLoad) {
      setLoading(true);
    } else {
      setIsRefreshing(true);
    }
    setError(null);

    const loadStudents = async () => {
      try {
        const params = buildStudentQueryParams(selectedSemester, deferredSearchTerm);
        const data = await studentApi.getStudents(params, { signal: controller.signal });
        if (controller.signal.aborted) return;

        const normalizedStudents = normalizeArrayResponse(data, ['results', 'data', 'students']);
        setStudents(normalizedStudents);
        setCounts(data.counts || { filtered: normalizedStudents.length });
      } catch (err) {
        if (controller.signal.aborted || err?.code === 'ERR_CANCELED') {
          return;
        }
        setError(extractApiMessage(err, 'Failed to load students.'));
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
          setIsRefreshing(false);
          initialLoadRef.current = false;
        }
      }
    };

    loadStudents();

    return () => {
      controller.abort();
    };
  }, [selectedSemester, deferredSearchTerm, reloadKey]);

  const handleEdit = (student) => {
    setEditingStudent(student);
    setFormData({ reg_no: student.reg_no, name: student.name });
    setIsModalOpen(true);
  };

  const handleDelete = async (reg_no) => {
    if (!window.confirm('Are you sure you want to delete this student?')) return;
    try {
      await studentApi.delete(reg_no);
      pushToast('success', 'Student deleted', `${reg_no} was removed successfully.`);
      requestStudentRefresh();
    } catch (err) {
      pushToast('error', 'Delete failed', extractApiMessage(err, 'Failed to delete student.'));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsFormSubmitting(true);
    try {
      if (editingStudent) {
        await studentApi.update(editingStudent.reg_no, formData);
        pushToast('success', 'Student updated', `${editingStudent.reg_no} was updated successfully.`);
      } else {
        await studentApi.create(formData);
        pushToast('success', 'Student created', `${formData.reg_no} was added successfully.`);
      }
      setIsModalOpen(false);
      setEditingStudent(null);
      setFormData({ reg_no: '', name: '' });
      requestStudentRefresh();
    } catch (err) {
      pushToast(
        'error',
        editingStudent ? 'Update failed' : 'Create failed',
        extractApiMessage(err, `Failed to ${editingStudent ? 'update' : 'create'} student.`),
      );
    } finally {
      setIsFormSubmitting(false);
    }
  };

  const openAddModal = () => {
    setEditingStudent(null);
    setFormData({ reg_no: '', name: '' });
    setIsModalOpen(true);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file && isSupportedSpreadsheet(file)) {
      setUploadFile(file);
      setUploadStatus(null);
      setUploadSummary(null);
    } else {
      setUploadStatus({ type: 'error', message: 'Only .xlsx and .xls Excel files are supported.' });
      pushToast('error', 'Unsupported file', 'Choose a .xlsx or .xls Excel file.');
    }
  };

  const handleUploadSubmit = async () => {
    if (!uploadFile || isUploadSubmitting) return;
    setIsUploadSubmitting(true);
    setUploadStatus(null);
    setUploadSummary(null);
    setUploadProgress(0);
    const form = new FormData();
    form.append('file', uploadFile);

    try {
      const payload = resolveUploadPayload(await studentApi.upload(form, {
        onUploadProgress: (progressEvent) => {
          if (!progressEvent.total) return;
          setUploadProgress(Math.round((progressEvent.loaded * 100) / progressEvent.total));
        },
      }));

      setUploadProgress(100);
      setUploadSummary(payload);
      setUploadStatus({
        type: 'success',
        message: payload?.message || `Successfully uploaded ${payload?.count || 0} students.`,
      });
      pushToast(
        'success',
        'Upload complete',
        `${payload?.count || 0} student records processed. ${payload?.created_students || 0} new students created.`,
      );
      requestStudentRefresh();
    } catch (err) {
      const message = extractApiMessage(err, 'Upload failed.');
      setUploadStatus({ type: 'error', message });
      setUploadProgress(0);
      pushToast('error', 'Upload failed', message);
    } finally {
      setIsUploadSubmitting(false);
    }
  };

  const countSummary = (() => {
    const parts = [`Showing ${counts?.filtered || 0} students`];

    if (selectedSemester) {
      parts.push(`in ${selectedSemesterLabel}`);
    }
    if (activeSearchTerm) {
      parts.push(`matching "${activeSearchTerm}"`);
    }

    return `${parts.join(' ')}.`;
  })();

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      {toasts.length > 0 && (
        <div className="fixed top-4 right-4 z-[70] space-y-3">
          {toasts.map((toast) => (
            <div
              key={toast.id}
              className={`min-w-[280px] max-w-sm rounded-2xl border px-4 py-3 shadow-xl backdrop-blur ${
                toast.type === 'error'
                  ? 'border-red-200 bg-white text-red-700'
                  : 'border-emerald-200 bg-white text-emerald-700'
              }`}
            >
              <div className="flex items-start gap-3">
                {toast.type === 'error' ? (
                  <AlertCircle className="mt-0.5 h-5 w-5 shrink-0" />
                ) : (
                  <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0" />
                )}
                <div>
                  <p className="text-sm font-bold">{toast.title}</p>
                  {toast.description ? <p className="mt-1 text-sm opacity-90">{toast.description}</p> : null}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
        <div>
          <h2 className="text-3xl font-bold text-slate-900 tracking-tight">Students</h2>
          <p className="mt-1 flex flex-wrap items-center gap-2 text-slate-500">
            <span>{countSummary}</span>
            {isRefreshing ? (
              <span className="inline-flex items-center gap-1.5 rounded-full bg-indigo-50 px-3 py-1 text-xs font-semibold text-indigo-600">
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                Updating
              </span>
            ) : null}
          </p>
        </div>

        <div className="flex w-full flex-col gap-3 xl:w-auto xl:flex-row xl:items-center">
          <div className="flex w-full flex-col gap-3 sm:flex-row xl:w-auto">
            <div className="relative w-full sm:max-w-xs">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search USN or Name..."
                className="w-full rounded-xl border border-slate-200 bg-white py-2 pl-10 pr-4 text-sm transition-all focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
              />
            </div>

            <div className="relative w-full sm:max-w-[220px]">
              <Filter className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <select
                value={selectedSemester}
                onChange={(e) => setSelectedSemester(e.target.value)}
                className="w-full appearance-none rounded-xl border border-slate-200 bg-white py-2 pl-10 pr-10 text-sm font-medium text-slate-700 transition-all focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
              >
                {SEMESTER_OPTIONS.map((option) => (
                  <option key={option.label} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
              <ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            </div>

            {hasActiveFilters ? (
              <button
                onClick={clearFilters}
                className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50"
              >
                <XCircle className="h-4 w-4" />
                Clear Filters
              </button>
            ) : null}
          </div>

          <div className="flex flex-col gap-3 sm:flex-row xl:w-auto">
            <button
              onClick={() => {
                setIsUploadModalOpen(true);
                resetUploadState();
              }}
              className="flex items-center justify-center gap-2 whitespace-nowrap rounded-xl border border-slate-200 bg-white px-4 py-2 font-medium text-slate-700 shadow-sm transition-colors hover:bg-slate-50"
            >
              <Upload className="h-4 w-4" />
              Upload
            </button>
            <button
              onClick={openAddModal}
              className="flex items-center justify-center gap-2 whitespace-nowrap rounded-xl bg-indigo-600 px-4 py-2 font-medium text-white shadow-lg shadow-indigo-500/20 transition-colors hover:bg-indigo-700"
            >
              <Plus className="h-4 w-4" />
              Add Student
            </button>
          </div>
        </div>
      </div>

      <Modal
        isOpen={isUploadModalOpen}
        onClose={() => {
          if (!isUploadSubmitting) {
            setIsUploadModalOpen(false);
            resetUploadState();
          }
        }}
        title="Upload Students"
      >
        <div className="space-y-6">
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            className={`rounded-2xl border-2 border-dashed p-8 text-center transition-all ${
              isDragging ? 'border-indigo-500 bg-indigo-50' : 'border-slate-200 bg-slate-50 hover:border-slate-300 hover:bg-slate-100'
            }`}
          >
            <input
              type="file"
              accept=".xlsx,.xls"
              className="hidden"
              id="file-upload"
              onChange={(e) => {
                const file = e.target.files[0];
                if (!file) return;
                if (!isSupportedSpreadsheet(file)) {
                  setUploadStatus({ type: 'error', message: 'Only .xlsx and .xls Excel files are supported.' });
                  setUploadSummary(null);
                  pushToast('error', 'Unsupported file', 'Choose a .xlsx or .xls Excel file.');
                  return;
                }
                setUploadFile(file);
                setUploadStatus(null);
                setUploadSummary(null);
              }}
            />
            <label htmlFor="file-upload" className="flex cursor-pointer flex-col items-center">
              <div className={`mb-4 rounded-full p-4 ${uploadFile ? 'bg-indigo-100 text-indigo-600' : 'bg-white text-slate-400 shadow-sm'}`}>
                {uploadFile ? <FileSpreadsheet className="h-8 w-8" /> : <Upload className="h-8 w-8" />}
              </div>
              <h3 className="mb-1 text-lg font-bold text-slate-900">
                {uploadFile ? uploadFile.name : 'Click or drag file to this area to upload'}
              </h3>
              <p className="text-sm text-slate-500">
                {uploadFile ? `${(uploadFile.size / 1024).toFixed(2)} KB` : 'Supports .XLSX and .XLS'}
              </p>
            </label>
          </div>

          {(isUploadSubmitting || uploadProgress > 0) && (
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm font-medium text-slate-600">
                <span>Upload progress</span>
                <span>{uploadProgress}%</span>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-slate-100">
                <div
                  className="h-full rounded-full bg-indigo-600 transition-all duration-300"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
            </div>
          )}

          {uploadStatus && (
            <div className={`flex items-center gap-3 rounded-xl border p-4 text-sm font-medium ${
              uploadStatus.type === 'error' ? 'border-red-100 bg-red-50 text-red-600' : 'border-emerald-100 bg-emerald-50 text-emerald-600'
            }`}>
              {uploadStatus.type === 'error' ? <AlertCircle className="h-5 w-5 shrink-0" /> : <CheckCircle2 className="h-5 w-5 shrink-0" />}
              {uploadStatus.message}
            </div>
          )}

          {uploadSummary && (
            <div className="space-y-4 rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <div className="grid gap-3 md:grid-cols-2">
                <div className="rounded-xl bg-white p-3 shadow-sm">
                  <p className="text-xs font-bold uppercase tracking-wide text-slate-400">Processed</p>
                  <p className="mt-1 text-2xl font-bold text-slate-900">{uploadSummary.count || 0}</p>
                </div>
                <div className="rounded-xl bg-white p-3 shadow-sm">
                  <p className="text-xs font-bold uppercase tracking-wide text-slate-400">Skipped</p>
                  <p className="mt-1 text-2xl font-bold text-slate-900">{uploadSummary.skipped_rows || 0}</p>
                </div>
                <div className="rounded-xl bg-white p-3 shadow-sm">
                  <p className="text-xs font-bold uppercase tracking-wide text-slate-400">New Students</p>
                  <p className="mt-1 text-2xl font-bold text-slate-900">{uploadSummary.created_students || 0}</p>
                </div>
                <div className="rounded-xl bg-white p-3 shadow-sm">
                  <p className="text-xs font-bold uppercase tracking-wide text-slate-400">New Enrollments</p>
                  <p className="mt-1 text-2xl font-bold text-slate-900">{uploadSummary.created_enrollments || 0}</p>
                </div>
              </div>

              <div className="text-sm text-slate-600">
                <p>
                  Detected headers:{' '}
                  <span className="font-medium text-slate-900">
                    {(uploadSummary.detected_headers || []).join(', ') || 'Not available'}
                  </span>
                </p>
                <p className="mt-1">
                  Header row: <span className="font-medium text-slate-900">{uploadSummary.header_row || 'N/A'}</span>
                </p>
              </div>

              {Array.isArray(uploadSummary.skipped_row_previews) && uploadSummary.skipped_row_previews.length > 0 && (
                <div className="rounded-xl border border-amber-100 bg-amber-50 p-3 text-sm text-amber-800">
                  <p className="font-semibold">Skipped row preview</p>
                  <p className="mt-1">
                    Row {uploadSummary.skipped_row_previews[0].excel_row}:{' '}
                    {(uploadSummary.skipped_row_previews[0].errors || []).join(', ')}
                  </p>
                </div>
              )}
            </div>
          )}

          <div className="flex gap-3">
            <button
              onClick={() => {
                if (!isUploadSubmitting) {
                  setIsUploadModalOpen(false);
                  resetUploadState();
                }
              }}
              disabled={isUploadSubmitting}
              className="flex-1 rounded-2xl border border-slate-200 bg-white py-4 font-bold text-slate-700 shadow-sm transition-all hover:bg-slate-50"
            >
              Cancel
            </button>
            <button
              disabled={!uploadFile || isUploadSubmitting}
              onClick={handleUploadSubmit}
              className="flex flex-1 items-center justify-center gap-2 rounded-2xl bg-indigo-600 py-4 font-bold text-white shadow-xl shadow-indigo-500/20 transition-all hover:bg-indigo-700 disabled:opacity-50"
            >
              {isUploadSubmitting ? <Loader2 className="h-5 w-5 animate-spin" /> : 'Upload Data'}
            </button>
          </div>
        </div>
      </Modal>

      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={editingStudent ? 'Edit Student' : 'Add New Student'}
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-bold text-slate-700">USN / Registration Number</label>
            <input
              required
              type="text"
              value={formData.reg_no}
              onChange={(e) => setFormData({ ...formData, reg_no: e.target.value.toUpperCase() })}
              placeholder="e.g. 22BCA001"
              disabled={!!editingStudent}
              className="w-full rounded-2xl border border-slate-100 bg-slate-50 px-4 py-3 transition-all focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 disabled:opacity-50"
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-bold text-slate-700">Full Name</label>
            <input
              required
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="Enter student name"
              className="w-full rounded-2xl border border-slate-100 bg-slate-50 px-4 py-3 transition-all focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
            />
          </div>
          <button
            disabled={isFormSubmitting}
            type="submit"
            className="flex w-full items-center justify-center gap-2 rounded-2xl bg-indigo-600 py-4 font-bold text-white shadow-xl shadow-indigo-500/20 transition-all hover:bg-indigo-700 disabled:opacity-50"
          >
            {isFormSubmitting ? <Loader2 className="h-5 w-5 animate-spin" /> : editingStudent ? 'Update Student' : 'Create Student'}
          </button>
        </form>
      </Modal>

      {error && (
        <div className="flex items-center gap-3 rounded-xl border border-red-100 bg-red-50 p-4 text-red-600">
          <AlertCircle className="h-5 w-5" />
          <p className="text-sm font-medium">{error}</p>
        </div>
      )}

      <div className={`overflow-hidden rounded-2xl border border-slate-100 bg-white shadow-sm transition-opacity ${isRefreshing ? 'opacity-80' : 'opacity-100'}`}>
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-left">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50">
                <th className="px-6 py-4 text-xs font-bold uppercase tracking-wider text-slate-500">USN / Registration</th>
                <th className="px-6 py-4 text-xs font-bold uppercase tracking-wider text-slate-500">Full Name</th>
                <th className="px-6 py-4 text-xs font-bold uppercase tracking-wider text-slate-500">Program / Semester</th>
                <th className="px-6 py-4 text-right text-xs font-bold uppercase tracking-wider text-slate-500">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {loading ? (
                [1, 2, 3, 4, 5].map((index) => (
                  <tr key={index} className="animate-pulse">
                    <td className="px-6 py-4"><div className="h-4 w-24 rounded bg-slate-100" /></td>
                    <td className="px-6 py-4"><div className="h-4 w-48 rounded bg-slate-100" /></td>
                    <td className="px-6 py-4"><div className="h-4 w-32 rounded bg-slate-100" /></td>
                    <td className="px-6 py-4"><div className="ml-auto h-4 w-8 rounded bg-slate-100" /></td>
                  </tr>
                ))
              ) : Array.isArray(students) && students.length > 0 ? (
                students.map((student) => {
                  const primaryEnrollment = getPrimaryEnrollment(student);

                  return (
                    <tr key={student.id} className="transition-colors hover:bg-slate-50/50">
                      <td className="px-6 py-4">
                        <span className="font-mono text-sm font-bold text-indigo-600">{student.reg_no}</span>
                      </td>
                      <td className="px-6 py-4">
                        <span className="font-semibold text-slate-900">{student.name}</span>
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex flex-col">
                          <span className="text-sm text-slate-700">{primaryEnrollment?.program_info?.name || 'N/A'}</span>
                          <span className="text-xs font-medium uppercase tracking-tighter text-slate-400">
                            Semester {primaryEnrollment?.semester || 'N/A'}
                          </span>
                        </div>
                      </td>
                      <td className="px-6 py-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => handleEdit(student)}
                            className="rounded-lg p-2 text-slate-400 transition-colors hover:bg-indigo-50 hover:text-indigo-600"
                          >
                            <Edit2 className="h-5 w-5" />
                          </button>
                          <button
                            onClick={() => handleDelete(student.reg_no)}
                            className="rounded-lg p-2 text-slate-400 transition-colors hover:bg-red-50 hover:text-red-600"
                          >
                            <Trash2 className="h-5 w-5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td colSpan="4" className="px-6 py-12 text-center">
                    <div className="flex flex-col items-center">
                      <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-slate-100 text-slate-300">
                        <Users className="h-8 w-8" />
                      </div>
                      <p className="font-medium text-slate-500">
                        {hasActiveFilters ? 'No students match the selected filters.' : 'No students found.'}
                      </p>
                      <p className="mt-1 text-sm text-slate-400">
                        {hasActiveFilters ? 'Try another semester, adjust the search, or clear the filters.' : 'Try uploading an Excel file to get started.'}
                      </p>
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default Students;
