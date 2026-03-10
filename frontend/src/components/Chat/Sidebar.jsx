import React from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../contexts/AuthContext';
import logo from '../../assets/logo.png';
import squareLogo from '../../assets/au_logo_square.png';

const Sidebar = ({ 
  isSidebarOpen, 
  profileTriggerRef, 
  settingsTriggerRef, 
  onProfileClick, 
  onSettingsClick 
}) => {
  const { t } = useTranslation();
  const { user } = useAuth();

  const docLinks = [
    { id: 1, title: 'Getting Started', icon: '🚀', href: '#' },
    { id: 2, title: 'API Reference', icon: '📚', href: '#' },
    { id: 3, title: 'Community Forum', icon: '💬', href: '#' },
    { id: 4, title: 'GitHub Repository', icon: '💻', href: '#' },
  ];

  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <div className="sidebar-logo-container">
          <img src={logo} alt="RiaBot Logo" className="sidebar-logo" />
          <img src={squareLogo} alt="RiaBot Logo" className="sidebar-logo-square" />
        </div>
      </div>
      
      <div className="sidebar-content">
        <div className="resource-section">
          <h3 className="resource-title">{t('resources')}</h3>
          <ul className="resource-list">
            {docLinks.map(item => (
              <li key={item.id}>
                <a href={item.href} className="resource-link" target="_blank" rel="noopener noreferrer">
                  <span className="resource-icon">{item.icon}</span>
                  <span className="resource-text">{item.title}</span>
                </a>
              </li>
            ))}
          </ul>
        </div>
      </div>
      
      <div className="sidebar-footer">
        <div 
          ref={profileTriggerRef} 
          className="profile-section" 
          onClick={onProfileClick}
        >
          <div className="profile-avatar">
            {user?.first_name?.charAt(0).toUpperCase() || user?.username?.charAt(0).toUpperCase()}
          </div>
          <span className="profile-name">{user?.first_name || user?.username}</span>
        </div>
        
        <div className="settings-container">
          <div 
            ref={settingsTriggerRef} 
            onClick={onSettingsClick} 
            className="settings-btn"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="3"></circle>
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
            </svg>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Sidebar;
