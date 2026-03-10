import React, { useState } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { useTheme } from '../../contexts/ThemeContext';
import logo from '../../assets/logo.png';
import auBuilding from '../../assets/au_building.png';
import { authService } from '../../services/authService';
import { useNavigate } from 'react-router-dom';

const Login = () => {
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    rememberMe: false,
  });
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const auth = useAuth();
  const navigate = useNavigate();
  const { theme, toggleTheme } = useTheme();

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData({
      ...formData,
      [name]: type === 'checkbox' ? checked : value,
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      await auth.login(formData.email, formData.password, formData.rememberMe);
      navigate('/');
    } catch (error) {
      setError(error.response?.data?.error || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-fullscreen-container">
      {/* Full viewport background */}
      <div className="auth-background-wrapper">
        <img src={auBuilding} alt="AU Building" className="auth-fullscreen-bg" />
        <div className="auth-creative-overlay"></div>
      </div>

      {/* Floating transparent login form */}
      <div className="auth-floating-form">
        <button onClick={toggleTheme} className="theme-toggle-floating" aria-label="Toggle theme">
          {theme === 'dark' ? (
            <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line></svg>
          ) : (
            <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path></svg>
          )}
        </button>

        <div className="auth-glass-card">
          <div className="auth-header">
            <img src={logo} alt="RiaBot Logo" className="auth-logo" />
            <p className="auth-tagline">
              ស្វែងរកជំនាញរបស់អ្នកដោយផ្អែកលើបុគ្គលិកលក្ខណៈអ្នកដោយប្រើទ្រឹស្តី RIASEC
            </p>
          </div>

          {error && (
            <div className="error-banner-glass">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit}>
            <div className="input-group-glass">
              <label htmlFor="email">Email Address</label>
              <input
                id="email"
                name="email"
                type="email"
                required
                autoComplete="email"
                autoFocus
                value={formData.email}
                onChange={handleChange}
              />
            </div>

            <div className="input-group-glass">
              <label htmlFor="password">Password</label>
              <div className="password-input-glass">
                <input
                  id="password"
                  name="password"
                  type={showPassword ? 'text' : 'password'}
                  required
                  autoComplete="current-password"
                  value={formData.password}
                  onChange={handleChange}
                />
                <button type="button" onClick={() => setShowPassword(!showPassword)}>
                  {showPassword ? '🙈' : '👁️'}
                </button>
              </div>
            </div>

            <div className="checkbox-group-glass">
              <label className="checkbox-label-glass">
                <input
                  type="checkbox"
                  name="rememberMe"
                  checked={formData.rememberMe}
                  onChange={handleChange}
                />
                <span className="checkmark-glass"></span>
                Remember me for 30 days
              </label>
            </div>

            <button type="submit" className="btn-primary-glass" disabled={loading}>
              {loading ? 'Signing in…' : 'Sign In'}
            </button>

            <div className="auth-footer-glass">
              <button
                type="button"
                onClick={() => navigate('/register')}
              >
                Don't have an account? Sign Up
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default Login;
