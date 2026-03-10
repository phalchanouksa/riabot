import React, { useState } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { useTheme } from '../../contexts/ThemeContext';
import { useNavigate } from 'react-router-dom';
import logo from '../../assets/logo.png';
import auBuilding from '../../assets/au_building.png';

const Register = () => {
  const [formData, setFormData] = useState({
    email: '',
    username: '',
    first_name: '',
    last_name: '',
    password: '',
    password_confirm: '',
  });
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const { register } = useAuth();
  const navigate = useNavigate();
  const { theme, toggleTheme } = useTheme();

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    if (formData.password !== formData.password_confirm) {
      setError("Passwords don't match");
      setLoading(false);
      return;
    }

    try {
      await register(formData);
      navigate('/');
    } catch (error) {
      setError(error.response?.data?.email?.[0] || error.response?.data?.username?.[0] || 'Registration failed');
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

      {/* Floating transparent register form */}
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
            <div className="input-group-row-glass">
              <div className="input-group-glass">
                <label htmlFor="first_name">First Name</label>
                <input id="first_name" name="first_name" required autoComplete="given-name" value={formData.first_name} onChange={handleChange} />
              </div>
              <div className="input-group-glass">
                <label htmlFor="last_name">Last Name</label>
                <input id="last_name" name="last_name" required autoComplete="family-name" value={formData.last_name} onChange={handleChange} />
              </div>
            </div>

            <div className="input-group-glass">
              <label htmlFor="username">Username</label>
              <input id="username" name="username" required autoComplete="username" value={formData.username} onChange={handleChange} />
            </div>

            <div className="input-group-glass">
              <label htmlFor="email">Email Address</label>
              <input id="email" name="email" type="email" required autoComplete="email" value={formData.email} onChange={handleChange} />
            </div>

            <div className="input-group-glass">
              <label htmlFor="password">Password</label>
              <div className="password-input-glass">
                <input id="password" name="password" type={showPassword ? 'text' : 'password'} required autoComplete="new-password" value={formData.password} onChange={handleChange} />
                <button type="button" onClick={() => setShowPassword(!showPassword)}>{showPassword ? '🙈' : '👁️'}</button>
              </div>
            </div>

            <div className="input-group-glass">
              <label htmlFor="password_confirm">Confirm Password</label>
              <input id="password_confirm" name="password_confirm" type={showPassword ? 'text' : 'password'} required value={formData.password_confirm} onChange={handleChange} />
            </div>

            <button type="submit" className="btn-primary-glass" disabled={loading}>
              {loading ? 'Creating…' : 'Create Account'}
            </button>

            <div className="auth-footer-glass">
              <button type="button" onClick={() => navigate('/login')}>
                Already have an account? Sign In
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default Register;
