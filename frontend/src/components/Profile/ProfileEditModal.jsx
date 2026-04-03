import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../contexts/AuthContext';
import { authService } from '../../services/authService';
import './ProfileEditModal.css';

const ProfileEditModal = ({ isOpen, onClose, onUpdate, updateError }) => {
  const { t } = useTranslation();
  const { user } = useAuth();
  const displayName = [user?.first_name, user?.last_name].filter(Boolean).join(' ') || user?.username || 'User';
  const accountMeta = user?.email || (user?.username ? `@${user.username}` : '');
  const [activeTab, setActiveTab] = useState('profile');
  const [formData, setFormData] = useState({
    firstName: '',
    lastName: ''
  });
  const [passwordData, setPasswordData] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: ''
  });
  const [passwordError, setPasswordError] = useState('');

  useEffect(() => {
    if (isOpen && user) {
      setFormData({
        firstName: user.first_name || '',
        lastName: user.last_name || ''
      });
      setPasswordData({
        currentPassword: '',
        newPassword: '',
        confirmPassword: ''
      });
      setPasswordError('');
      setActiveTab('profile');
    }
  }, [isOpen, user]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (activeTab === 'profile') {
      onUpdate(formData);
    } else {
      handlePasswordChange();
    }
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handlePasswordChange = async () => {
    setPasswordError('');
    
    if (passwordData.newPassword !== passwordData.confirmPassword) {
      setPasswordError(t('passwordMismatch') || 'Passwords do not match');
      return;
    }
    
    if (passwordData.newPassword.length < 8) {
      setPasswordError(t('passwordTooShort') || 'Password must be at least 8 characters');
      return;
    }

    try {
      await authService.changePassword({
        current_password: passwordData.currentPassword,
        new_password: passwordData.newPassword
      });
      
      setPasswordData({
        currentPassword: '',
        newPassword: '',
        confirmPassword: ''
      });
      
      // Show success message or close modal
      onClose();
    } catch (error) {
      const errorMessage = error.response?.data?.current_password?.[0] || 
                          error.response?.data?.new_password?.[0] || 
                          error.response?.data?.detail || 
                          'Failed to change password';
      setPasswordError(errorMessage);
    }
  };

  const handlePasswordInputChange = (e) => {
    const { name, value } = e.target;
    setPasswordData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title">
            <div className="profile-avatar-large">
              {user?.first_name?.charAt(0).toUpperCase() || user?.username?.charAt(0).toUpperCase() || 'U'}
            </div>
            <div className="profile-info">
              <h2>{displayName}</h2>
              <p className="profile-email">{accountMeta}</p>
            </div>
          </div>
          <button type="button" className="modal-close" onClick={onClose}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>

        <div className="modal-tabs">
          <button
            type="button"
            className={`profile-modal-tab ${activeTab === 'profile' ? 'active' : ''}`}
            onClick={() => setActiveTab('profile')}
          >
            {t('personalInfo') || 'Personal info'}
          </button>
          <button
            type="button"
            className={`profile-modal-tab ${activeTab === 'security' ? 'active' : ''}`}
            onClick={() => setActiveTab('security')}
          >
            {t('security') || 'Security'}
          </button>
        </div>

        <div className="modal-body">
          {activeTab === 'profile' && (
            <form onSubmit={handleSubmit} className="profile-form">
              {updateError && (
                <div className="error-message">
                  {updateError}
                </div>
              )}

              <div className="form-section">
                <h3>{t('basicInfo') || 'Basic info'}</h3>
                <p className="section-description">
                  {t('basicInfoDesc') || 'Some info may be visible to other people using RiaBot services.'}
                </p>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label htmlFor="firstName">{t('firstName') || 'First name'}</label>
                  <input
                    type="text"
                    id="firstName"
                    name="firstName"
                    value={formData.firstName}
                    onChange={handleChange}
                    placeholder={t('enterFirstName') || 'First name'}
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="lastName">{t('lastName') || 'Last name'}</label>
                  <input
                    type="text"
                    id="lastName"
                    name="lastName"
                    value={formData.lastName}
                    onChange={handleChange}
                    placeholder={t('enterLastName') || 'Last name'}
                  />
                </div>
              </div>

              <div className="form-group">
                <label>{t('email') || 'Email'}</label>
                <div className="readonly-field">
                  {user?.email || user?.username}
                </div>
                <small className="field-hint">
                  {t('emailHint') || 'Contact support to change your email address'}
                </small>
              </div>

              <div className="form-actions">
                <button type="button" className="profile-modal-btn profile-modal-btn-secondary" onClick={onClose}>
                  {t('cancel') || 'Cancel'}
                </button>
                <button type="submit" className="profile-modal-btn profile-modal-btn-primary">
                  {t('save') || 'Save'}
                </button>
              </div>
            </form>
          )}

          {activeTab === 'security' && (
            <form onSubmit={handleSubmit} className="profile-form">
              {passwordError && (
                <div className="error-message">
                  {passwordError}
                </div>
              )}

              <div className="form-section">
                <h3>{t('changePassword') || 'Change password'}</h3>
                <p className="section-description">
                  {t('passwordDesc') || 'Use a strong password to keep your account secure.'}
                </p>
              </div>

              <div className="form-group">
                <label htmlFor="currentPassword">{t('currentPassword') || 'Current password'}</label>
                <input
                  type="password"
                  id="currentPassword"
                  name="currentPassword"
                  value={passwordData.currentPassword}
                  onChange={handlePasswordInputChange}
                  placeholder={t('enterCurrentPassword') || 'Enter current password'}
                />
              </div>

              <div className="form-group">
                <label htmlFor="newPassword">{t('newPassword') || 'New password'}</label>
                <input
                  type="password"
                  id="newPassword"
                  name="newPassword"
                  value={passwordData.newPassword}
                  onChange={handlePasswordInputChange}
                  placeholder={t('enterNewPassword') || 'Enter new password'}
                />
              </div>

              <div className="form-group">
                <label htmlFor="confirmPassword">{t('confirmPassword') || 'Confirm new password'}</label>
                <input
                  type="password"
                  id="confirmPassword"
                  name="confirmPassword"
                  value={passwordData.confirmPassword}
                  onChange={handlePasswordInputChange}
                  placeholder={t('confirmNewPassword') || 'Confirm new password'}
                />
              </div>

              <div className="form-actions">
                <button type="button" className="profile-modal-btn profile-modal-btn-secondary" onClick={onClose}>
                  {t('cancel') || 'Cancel'}
                </button>
                <button type="submit" className="profile-modal-btn profile-modal-btn-primary">
                  {t('changePassword') || 'Change password'}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};

export default ProfileEditModal;
