import React, { createContext, useState, useContext, useEffect } from 'react';
import { authService } from '../services/authService';
import { initializeCSRFToken } from '../utils/csrf';

const AuthContext = createContext(null);

const initialState = {
  isAuthenticated: false,
  user: null,
  loading: true,
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [state, setState] = useState(initialState);

  useEffect(() => {
    const checkAuthStatus = async () => {
      try {
        // Initialize CSRF token first
        await initializeCSRFToken();
        
        // Since JWT cookies are httpOnly, we can't access them via JavaScript
        // Instead, directly check with the server if user is authenticated
        console.log('Checking authentication with server (httpOnly cookies)...');
        const isAuthenticated = await authService.isAuthenticated();
        console.log('Server authentication result:', isAuthenticated);
        
        if (isAuthenticated) {
          const user = await authService.getCurrentUser();
          console.log('User data retrieved:', user);
          setState({ isAuthenticated: true, user, loading: false });
        } else {
          console.log('Authentication failed, setting unauthenticated');
          setState({ ...initialState, loading: false });
        }
      } catch (error) {
        console.error('Auth check error:', error);
        setState({ ...initialState, loading: false });
      }
    };

    checkAuthStatus();
  }, []);

  const login = async (email, password, rememberMe = false) => {
    try {
      const response = await authService.login(email, password, rememberMe);
      setState({ isAuthenticated: true, user: response.user, loading: false });
      return response;
    } catch (error) {
      throw error;
    }
  };

  const register = async (userData) => {
    try {
      const response = await authService.register(userData);
      setState({ isAuthenticated: true, user: response.user, loading: false });
      return response;
    } catch (error) {
      throw error;
    }
  };

  const logout = async () => {
    try {
      await authService.logout();
      setState({ ...initialState, loading: false });
    } catch (error) {
      console.error('Logout error:', error);
      setState({ ...initialState, loading: false });
    }
  };

  const setUser = (user) => {
    setState(prevState => ({ ...prevState, user }));
  };

  return (
    <AuthContext.Provider value={{ ...state, login, register, logout, setUser }}>
      {children}
    </AuthContext.Provider>
  );
};
