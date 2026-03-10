import axios from 'axios';
import { getCSRFToken, getCSRFTokenFromCookie, clearCSRFToken } from '../utils/csrf';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, // Enable cookies for cross-origin requests
});

// Request interceptor to add CSRF token
api.interceptors.request.use(
  async (config) => {
    // Add CSRF token for state-changing requests
    if (['post', 'put', 'patch', 'delete'].includes(config.method?.toLowerCase())) {
      try {
        // Always try to get fresh CSRF token for critical auth endpoints
        let csrfToken = getCSRFTokenFromCookie();
        if (!csrfToken || config.url?.includes('/auth/')) {
          csrfToken = await getCSRFToken();
        }
        if (csrfToken) {
          config.headers['X-CSRFToken'] = csrfToken;
        }
      } catch (error) {
        console.warn('Failed to get CSRF token:', error);
      }
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor to handle token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // Only attempt refresh for 401 errors, not already retried, and not for auth endpoints
    if (error.response?.status === 401 && 
        !originalRequest._retry && 
        !originalRequest.url?.includes('/auth/login') &&
        !originalRequest.url?.includes('/auth/register') &&
        !originalRequest.url?.includes('/auth/csrf-token')) {
      
      originalRequest._retry = true;

      try {

        // Try to refresh token using cookie-based refresh
        const response = await axios.post(`${API_BASE_URL}/auth/token/refresh/`, {}, {
          withCredentials: true,
          headers: {
            'X-CSRFToken': getCSRFTokenFromCookie() || await getCSRFToken(),
          }
        });

        if (response.status === 200) {
          // Token refreshed successfully, retry original request
          return api(originalRequest);
        }
      } catch (refreshError) {
        // Refresh failed, clear tokens and redirect to login only if not already on login page
        clearCSRFToken();
        if (!window.location.pathname.includes('/login')) {
          window.location.href = '/login';
        }
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

export const authService = {
  // Register
  register: async (userData) => {
    // Ensure CSRF token is available before registration
    await getCSRFToken();
    const response = await api.post('/auth/register/', userData);
    return response.data;
  },

  // Login
  login: async (email, password, rememberMe = false) => {
    // Ensure CSRF token is available before login
    await getCSRFToken();
    const response = await api.post('/auth/login/', { email, password, remember_me: rememberMe });
    return response.data;
  },

  // Logout
  logout: async () => {
    try {
      await api.post('/auth/logout/');
      clearCSRFToken();
    } catch (error) {
      console.error('Logout error:', error);
      // Clear tokens anyway
      clearCSRFToken();
    }
  },

  // Check if user is authenticated by making server request (httpOnly cookies sent automatically)
  isAuthenticated: async () => {
    try {
      // Since cookies are httpOnly, we can't check them in JavaScript
      // Just make a request to the server - cookies will be sent automatically
      console.log('isAuthenticated - Checking with server (httpOnly cookies)...');
      const response = await api.get('/auth/profile/');
      console.log('isAuthenticated - Server response:', response.status);
      return true;
    } catch (error) {
      console.error('isAuthenticated - Error:', error.response?.status, error.message);
      return false;
    }
  },

  // Get current user profile
  getCurrentUser: async () => {
    try {
      const response = await api.get('/auth/profile/');
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  // Update user profile
  updateProfile: async (userData) => {
    const response = await api.put('/auth/profile/', userData);
    return response.data;
  },

  // Change password
  changePassword: async (passwordData) => {
    const response = await api.post('/auth/change-password/', passwordData);
    return response.data;
  },
};

export default api;
