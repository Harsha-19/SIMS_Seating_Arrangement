import React, { useEffect, useState } from 'react';
import { 
  Calendar, Clock, Plus, AlertCircle, MoreVertical, GraduationCap,
  Loader2, Trash2, BookOpen, Layers
} from 'lucide-react';
import { subjectApi, examScheduleApi, programApi, normalizeArrayResponse } from '../api';
import Modal from '../components/Modal';

const Exams = () => {
  const [activeTab, setActiveTab] = useState('schedules'); // 'schedules' or 'subjects'
  
  // Data states
  const [schedules, setSchedules] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [programs, setPrograms] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Modal states
  const [isScheduleModalOpen, setIsScheduleModalOpen] = useState(false);
  const [isSubjectModalOpen, setIsSubjectModalOpen] = useState(false);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [scheduleToDelete, setScheduleToDelete] = useState(null);
  
  // Mock auth state
  const isAdmin = true;
  
  // Forms
  const [scheduleForm, setScheduleForm] = useState({
    subject: '', // subject ID
    exam_type: 'REGULAR',
    exam_date: new Date().toISOString().split('T')[0],
    session: 'MORNING',
    start_time: '09:30',
    end_time: '12:30',
    status: 'UPCOMING'
  });

  const [subjectForm, setSubjectForm] = useState({
    subject_code: '',
    subject_name: '',
    department: '',
    semester: 1,
    credits: 3,
    type: 'CORE'
  });

  const fetchData = async () => {
    setLoading(true);
    try {
      const [scheduleData, subjectData, programData] = await Promise.all([
        examScheduleApi.getExamSchedules(),
        subjectApi.getSubjects(),
        programApi.getPrograms()
      ]);
      setSchedules(normalizeArrayResponse(scheduleData, ['results', 'data']));
      setSubjects(normalizeArrayResponse(subjectData, ['results', 'data']));
      setPrograms(normalizeArrayResponse(programData, ['results', 'data']));
      setError(null);
    } catch (err) {
      setError('Failed to load data.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleScheduleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      await examScheduleApi.create(scheduleForm);
      setIsScheduleModalOpen(false);
      setScheduleForm({ ...scheduleForm, subject: '' });
      fetchData();
    } catch (err) {
      const data = err.response?.data;
      let msg = err.message;
      if (data && typeof data === 'object') {
        const errors = data.errors || data;
        if (Object.keys(errors).length > 0) {
          msg = Object.entries(errors).map(([key, val]) => `${key}: ${Array.isArray(val) ? val.join(', ') : JSON.stringify(val)}`).join(' | ');
        } else if (data.message) {
          msg = data.message;
        }
      }
      alert('Failed to create schedule: ' + msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSubjectSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      const payload = { ...subjectForm };
      if (!payload.department) {
        payload.department = null;
      }
      await subjectApi.create(payload);
      setIsSubjectModalOpen(false);
      setSubjectForm({ ...subjectForm, subject_code: '', subject_name: '' });
      fetchData();
    } catch (err) {
      const data = err.response?.data;
      let msg = err.message;
      if (data && typeof data === 'object') {
        const errors = data.errors || data;
        if (Object.keys(errors).length > 0) {
          msg = Object.entries(errors).map(([key, val]) => `${key}: ${Array.isArray(val) ? val.join(', ') : JSON.stringify(val)}`).join(' | ');
        } else if (data.message) {
          msg = data.message;
        }
      }
      alert('Failed to create subject: ' + msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteClick = (id) => {
    setScheduleToDelete(id);
    setIsDeleteModalOpen(true);
  };

  const confirmDeleteSchedule = async () => {
    if (!scheduleToDelete) return;
    setIsDeleting(true);
    try {
      await examScheduleApi.delete(scheduleToDelete);
      setSchedules(schedules.filter(s => s.id !== scheduleToDelete));
      setIsDeleteModalOpen(false);
      setScheduleToDelete(null);
      alert('Exam schedule deleted successfully.');
    } catch (err) {
      const data = err.response?.data;
      let msg = err.message;
      if (data && typeof data === 'object') {
        const errors = data.errors || data;
        if (Object.keys(errors).length > 0) {
          msg = Object.entries(errors).map(([key, val]) => `${key}: ${Array.isArray(val) ? val.join(', ') : JSON.stringify(val)}`).join(' | ');
        } else if (data.message) {
          msg = data.message;
        }
      }
      alert('Failed to delete schedule: ' + msg);
    } finally {
      setIsDeleting(false);
    }
  };

  // UI Components
  const renderSchedulesTab = () => (
    <>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-bold text-slate-800">Exam Schedules</h2>
          <p className="text-slate-500 text-sm">Manage upcoming examination events.</p>
        </div>
        <button 
          onClick={() => setIsScheduleModalOpen(true)}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-xl font-medium hover:bg-indigo-700 transition-colors shadow-sm"
        >
          <Plus className="w-4 h-4" /> Schedule Exam
        </button>
      </div>

      {schedules.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {schedules.map((schedule) => (
            <div key={schedule.id} className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 hover:shadow-md transition-all group">
              <div className="flex items-start justify-between mb-4">
                <div className="p-3 rounded-xl bg-indigo-50 text-indigo-600">
                  <Calendar className="w-6 h-6" />
                </div>
                <div className="flex items-center gap-2">
                  <span className={`px-2 py-1 rounded text-xs font-bold uppercase tracking-wider ${schedule.status === 'PUBLISHED' ? 'bg-emerald-50 text-emerald-600' : 'bg-slate-100 text-slate-600'}`}>
                    {schedule.status}
                  </span>
                  {isAdmin && (
                    <button 
                      onClick={() => handleDeleteClick(schedule.id)}
                      className="p-1.5 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                      title="Delete Schedule"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  )}
                </div>
              </div>
              <div>
                <h3 className="text-lg font-bold text-slate-900 leading-tight">
                  {schedule.subject_info?.subject_name}
                </h3>
                <p className="text-slate-500 text-sm mt-1">
                  {schedule.subject_info?.subject_code} • {schedule.subject_info?.department_info?.name} • Sem {schedule.subject_info?.semester}
                </p>
              </div>
              <div className="mt-6 pt-5 border-t border-slate-50 grid grid-cols-2 gap-4 text-sm">
                <div className="flex flex-col gap-1">
                  <span className="text-slate-400 font-medium text-xs uppercase tracking-wider">Date</span>
                  <div className="flex items-center gap-1.5 font-semibold text-slate-700">
                    {new Date(schedule.exam_date).toLocaleDateString()}
                  </div>
                </div>
                <div className="flex flex-col gap-1">
                  <span className="text-slate-400 font-medium text-xs uppercase tracking-wider">Time</span>
                  <div className="flex items-center gap-1.5 font-semibold text-slate-700">
                    {schedule.start_time.substring(0, 5)} - {schedule.end_time.substring(0, 5)}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-12 text-center">
          <div className="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-4 text-slate-300">
            <Calendar className="w-8 h-8" />
          </div>
          <p className="text-slate-500 font-medium">No exam schedules found.</p>
        </div>
      )}
    </>
  );

  const renderSubjectsTab = () => (
    <>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-bold text-slate-800">Academic Subjects</h2>
          <p className="text-slate-500 text-sm">Manage subject catalog for all departments.</p>
        </div>
        <button 
          onClick={() => setIsSubjectModalOpen(true)}
          className="flex items-center gap-2 px-4 py-2 bg-slate-800 text-white rounded-xl font-medium hover:bg-slate-900 transition-colors shadow-sm"
        >
          <Plus className="w-4 h-4" /> Add Subject
        </button>
      </div>

      {subjects.length > 0 ? (
        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-100 text-slate-500 text-xs uppercase tracking-wider">
                  <th className="p-4 font-semibold">Code</th>
                  <th className="p-4 font-semibold">Subject Name</th>
                  <th className="p-4 font-semibold">Department</th>
                  <th className="p-4 font-semibold">Sem</th>
                  <th className="p-4 font-semibold">Credits</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {subjects.map(subject => (
                  <tr key={subject.id} className="hover:bg-slate-50/50 transition-colors">
                    <td className="p-4 font-mono text-sm font-medium text-slate-700">{subject.subject_code}</td>
                    <td className="p-4 font-semibold text-slate-900">{subject.subject_name}</td>
                    <td className="p-4 text-slate-600">{subject.department_info?.name}</td>
                    <td className="p-4">
                      <span className="px-2.5 py-1 bg-slate-100 text-slate-600 rounded-lg text-sm font-medium">
                        Sem {subject.semester}
                      </span>
                    </td>
                    <td className="p-4 text-slate-600 font-medium">{subject.credits}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-12 text-center">
          <div className="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-4 text-slate-300">
            <BookOpen className="w-8 h-8" />
          </div>
          <p className="text-slate-500 font-medium">No subjects found in the catalog.</p>
        </div>
      )}
    </>
  );

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-3xl font-bold text-slate-900 tracking-tight">Examinations</h2>
          <p className="text-slate-500 mt-1">Manage subjects and schedule examinations.</p>
        </div>
      </div>

      <div className="flex items-center gap-2 p-1 bg-slate-100/80 rounded-xl w-max">
        <button
          onClick={() => setActiveTab('schedules')}
          className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-bold transition-all ${
            activeTab === 'schedules' ? 'bg-white text-indigo-600 shadow-sm' : 'text-slate-500 hover:text-slate-700'
          }`}
        >
          <Calendar className="w-4 h-4" />
          Schedules
        </button>
        <button
          onClick={() => setActiveTab('subjects')}
          className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-bold transition-all ${
            activeTab === 'subjects' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'
          }`}
        >
          <BookOpen className="w-4 h-4" />
          Subjects
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-100 text-red-600 p-4 rounded-xl flex items-center gap-3">
          <AlertCircle className="w-5 h-5" />
          <p className="text-sm font-medium">{error}</p>
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 text-indigo-600 animate-spin" />
        </div>
      ) : (
        <div className="mt-6">
          {activeTab === 'schedules' ? renderSchedulesTab() : renderSubjectsTab()}
        </div>
      )}

      {/* Schedule Modal */}
      <Modal isOpen={isScheduleModalOpen} onClose={() => setIsScheduleModalOpen(false)} title="Schedule Examination">
        <form onSubmit={handleScheduleSubmit} className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-bold text-slate-700">Subject</label>
            <select
              required
              value={scheduleForm.subject}
              onChange={(e) => setScheduleForm({ ...scheduleForm, subject: e.target.value })}
              className="w-full px-4 py-3 bg-slate-50 border border-slate-100 rounded-2xl focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
            >
              <option value="">Select a subject...</option>
              {subjects.map(s => (
                <option key={s.id} value={s.id}>{s.subject_code} - {s.subject_name}</option>
              ))}
            </select>
          </div>
          
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-bold text-slate-700">Date</label>
              <input
                required type="date" value={scheduleForm.exam_date}
                onChange={(e) => setScheduleForm({ ...scheduleForm, exam_date: e.target.value })}
                className="w-full px-4 py-3 bg-slate-50 border border-slate-100 rounded-2xl focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-bold text-slate-700">Exam Type</label>
              <select
                required value={scheduleForm.exam_type}
                onChange={(e) => setScheduleForm({ ...scheduleForm, exam_type: e.target.value })}
                className="w-full px-4 py-3 bg-slate-50 border border-slate-100 rounded-2xl focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
              >
                <option value="REGULAR">REGULAR</option>
                <option value="SUPPLEMENTARY">SUPPLEMENTARY</option>
                <option value="INTERNAL">INTERNAL</option>
                <option value="PRACTICAL">PRACTICAL</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-bold text-slate-700">Start Time</label>
              <input
                required type="time" value={scheduleForm.start_time}
                onChange={(e) => setScheduleForm({ ...scheduleForm, start_time: e.target.value })}
                className="w-full px-4 py-3 bg-slate-50 border border-slate-100 rounded-2xl focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-bold text-slate-700">End Time</label>
              <input
                required type="time" value={scheduleForm.end_time}
                onChange={(e) => setScheduleForm({ ...scheduleForm, end_time: e.target.value })}
                className="w-full px-4 py-3 bg-slate-50 border border-slate-100 rounded-2xl focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
              />
            </div>
          </div>

          <button
            disabled={isSubmitting} type="submit"
            className="w-full py-4 mt-2 bg-indigo-600 text-white rounded-2xl font-bold hover:bg-indigo-700 transition-all shadow-xl shadow-indigo-500/20 flex items-center justify-center gap-2 disabled:opacity-50"
          >
            {isSubmitting ? <Loader2 className="w-5 h-5 animate-spin" /> : 'Schedule Exam'}
          </button>
        </form>
      </Modal>

      {/* Subject Modal */}
      <Modal isOpen={isSubjectModalOpen} onClose={() => setIsSubjectModalOpen(false)} title="Add New Subject">
        <form onSubmit={handleSubjectSubmit} className="space-y-4">
          <div className="grid grid-cols-3 gap-4">
            <div className="col-span-1 space-y-2">
              <label className="text-sm font-bold text-slate-700">Code</label>
              <input
                required type="text" placeholder="e.g. CS101" value={subjectForm.subject_code}
                onChange={(e) => setSubjectForm({ ...subjectForm, subject_code: e.target.value.toUpperCase() })}
                className="w-full px-4 py-3 bg-slate-50 border border-slate-100 rounded-2xl focus:outline-none focus:ring-2 focus:ring-slate-500/20 focus:border-slate-500 transition-all"
              />
            </div>
            <div className="col-span-2 space-y-2">
              <label className="text-sm font-bold text-slate-700">Subject Name</label>
              <input
                required type="text" placeholder="e.g. DATA STRUCTURES" value={subjectForm.subject_name}
                onChange={(e) => setSubjectForm({ ...subjectForm, subject_name: e.target.value.toUpperCase() })}
                className="w-full px-4 py-3 bg-slate-50 border border-slate-100 rounded-2xl focus:outline-none focus:ring-2 focus:ring-slate-500/20 focus:border-slate-500 transition-all"
              />
            </div>
          </div>
          
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-bold text-slate-700">Department</label>
              <select
                required value={subjectForm.department}
                onChange={(e) => setSubjectForm({ ...subjectForm, department: e.target.value })}
                className="w-full px-4 py-3 bg-slate-50 border border-slate-100 rounded-2xl focus:outline-none focus:ring-2 focus:ring-slate-500/20 focus:border-slate-500 transition-all"
              >
                <option value="">Select Dept</option>
                {programs.map(p => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-bold text-slate-700">Semester</label>
              <select
                required value={subjectForm.semester}
                onChange={(e) => setSubjectForm({ ...subjectForm, semester: parseInt(e.target.value) })}
                className="w-full px-4 py-3 bg-slate-50 border border-slate-100 rounded-2xl focus:outline-none focus:ring-2 focus:ring-slate-500/20 focus:border-slate-500 transition-all"
              >
                {[1, 2, 3, 4, 5, 6].map(s => (
                  <option key={s} value={s}>Sem {s}</option>
                ))}
              </select>
            </div>
          </div>

          <button
            disabled={isSubmitting} type="submit"
            className="w-full py-4 mt-2 bg-slate-800 text-white rounded-2xl font-bold hover:bg-slate-900 transition-all shadow-xl shadow-slate-900/10 flex items-center justify-center gap-2 disabled:opacity-50"
          >
            {isSubmitting ? <Loader2 className="w-5 h-5 animate-spin" /> : 'Save Subject'}
          </button>
        </form>
      </Modal>
      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={isDeleteModalOpen}
        onClose={() => !isDeleting && setIsDeleteModalOpen(false)}
        title="Delete Exam Schedule?"
      >
        <div className="space-y-6">
          <p className="text-slate-600">
            Are you sure you want to delete this exam schedule? <br />
            <span className="font-semibold text-red-600">This action cannot be undone.</span>
          </p>
          <div className="flex justify-end gap-3 pt-4 border-t border-slate-100">
            <button
              onClick={() => setIsDeleteModalOpen(false)}
              disabled={isDeleting}
              className="px-4 py-2 text-sm font-medium text-slate-600 bg-white border border-slate-200 rounded-xl hover:bg-slate-50 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={confirmDeleteSchedule}
              disabled={isDeleting}
              className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-xl hover:bg-red-700 transition-colors disabled:opacity-50"
            >
              {isDeleting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
              Delete
            </button>
          </div>
        </div>
      </Modal>

    </div>
  );
};

export default Exams;
