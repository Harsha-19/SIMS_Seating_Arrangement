import axios from "axios";

const rawBaseURL = (import.meta.env.VITE_API_BASE_URL || "/api").trim();
const normalizedBaseURL = rawBaseURL.endsWith("/") ? rawBaseURL : `${rawBaseURL}/`;

const api = axios.create({
  baseURL: normalizedBaseURL,
  headers: {
    "Content-Type": "application/json",
  },
});

// Response interceptor to unwrap axios 'data' wrapper
api.interceptors.response.use(
  (response) => response.data,
  (error) => Promise.reject(error)
);

export default api;
