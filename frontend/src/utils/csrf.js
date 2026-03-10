import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

let csrfToken = null;

/**
 * Get CSRF token from the server
 */
export const getCSRFToken = async () => {
  if (csrfToken) {
    return csrfToken;
  }

  try {
    const response = await axios.get(`${API_BASE_URL}/auth/csrf-token/`, {
      withCredentials: true,
    });
    csrfToken = response.data.csrfToken;
    return csrfToken;
  } catch (error) {
    console.error('Failed to get CSRF token:', error);
    // Try to get from cookie as fallback
    const cookieToken = getCSRFTokenFromCookie();
    if (cookieToken) {
      csrfToken = cookieToken;
      return csrfToken;
    }
    throw error;
  }
};

/**
 * Get CSRF token from cookie (fallback method)
 */
export const getCSRFTokenFromCookie = () => {
  const name = 'csrftoken';
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
};

/**
 * Clear cached CSRF token
 */
export const clearCSRFToken = () => {
  csrfToken = null;
};

/**
 * Initialize CSRF token on app start
 */
export const initializeCSRFToken = async () => {
  try {
    await getCSRFToken();
    console.log('CSRF token initialized');
  } catch (error) {
    console.warn('Failed to initialize CSRF token:', error);
  }
};
