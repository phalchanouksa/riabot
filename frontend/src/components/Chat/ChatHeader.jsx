import React from 'react';
import { useTranslation } from 'react-i18next';

const ChatHeader = ({ 
  isSidebarOpen, 
  onToggleSidebar, 
  chatSessionExpired, 
  onStartNewChat, 
  onContinueChat 
}) => {
  const { t } = useTranslation();

  return (
    <>
      {chatSessionExpired && (
        <div className="banner">
          <div>
            <strong>{t('chatSessionExpired.title')}</strong> {t('chatSessionExpired.body')}
          </div>
          <div className="actions">
            <button className="btn" onClick={onStartNewChat}>{t('newChat')}</button>
            <button className="btn btn-outline" onClick={onContinueChat}>{t('continue')}</button>
          </div>
        </div>
      )}
      
      <div className="chat-header">
        <button className="menu-btn" onClick={onToggleSidebar}>
          <span></span>
          <span></span>
          <span></span>
        </button>
      </div>
    </>
  );
};

export default ChatHeader;
