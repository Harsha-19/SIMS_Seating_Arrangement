import api from './client';

export const normalizeArrayResponse = (payload, keys = []) => {
  if (Array.isArray(payload)) return payload;

  for (const key of keys) {
    if (Array.isArray(payload?.[key])) {
      return payload[key];
    }
  }

  return [];
};

export const studentApi = {
  getStudents: (params = {}, config = {}) => api.get('students/', { ...config, params }),
  create: (data) => api.post('students/', data),
  update: (reg_no, data) => api.put(`students/${reg_no}/`, data),
  upload: (formData, config = {}) => api.post('students/upload/', formData, {
    headers: { 'Content-Type': 'multipart/form-data', ...(config.headers || {}) },
    ...config,
  }),
  delete: (reg_no) => api.delete(`students/${reg_no}/`),
};

export const roomApi = {
  getRooms: () => api.get('rooms/'),
  create: (data) => api.post('rooms/', data),
  delete: (id) => api.delete(`rooms/${id}/`),
};


export const subjectApi = {
  getSubjects: () => api.get('subjects/'),
  create: (data) => api.post('subjects/', data),
};

export const examScheduleApi = {
  getExamSchedules: () => api.get('exam-schedules/'),
  create: (data) => api.post('exam-schedules/', data),
  delete: (id) => api.delete(`exam-schedules/${id}/`),
};

export const seatingApi = {
  generateSeating: (data) => api.post('seating/generate/', data),
  getPlans: (params) => api.get('plans/', { params }),
  move: (planId, data) => api.patch(`plans/${planId}/move/`, data),
  swap: (planId, data) => api.patch(`plans/${planId}/swap/`, data),
  exportExcel: (planId) => api.get(`plans/${planId}/export_excel/`, { responseType: 'blob' }),
  exportPdf: (planId) => api.get(`plans/${planId}/export_pdf/`, { responseType: 'blob' }),
  exportAttendance: (planId) => api.get(`plans/${planId}/export_attendance/`, { responseType: 'blob' }),
  exportHallTickets: (planId) => api.get(`plans/${planId}/export_hall_tickets/`, { responseType: 'blob' }),
};

export const programApi = {
  getPrograms: () => api.get('programs/'),
};

export const analyticsApi = {

  getStats: () => api.get('analytics/'),
};

export default api;
