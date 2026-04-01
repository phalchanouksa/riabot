import React, { useState, useRef, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../contexts/AuthContext';
import { useTheme } from '../../contexts/ThemeContext';
import ContextMenu from '../ContextMenu/ContextMenu';
import { authService } from '../../services/authService';
import { chatService } from '../../services/chatService';
import Sidebar from './Sidebar';
import ChatHeader from './ChatHeader';
import MessageList from './MessageList';
import ChatInput from './ChatInput';
import ProfileEditModal from '../Profile/ProfileEditModal';


const ChatInterface = () => {
  const { t, i18n } = useTranslation();
  const { setTheme } = useTheme();
  const { logout, setUser } = useAuth();
  const [updateError, setUpdateError] = useState('');
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const profileTriggerRef = useRef(null);
  const settingsTriggerRef = useRef(null);
  const [isThemeMenuOpen, setIsThemeMenuOpen] = useState(false);
  const [isLangMenuOpen, setIsLangMenuOpen] = useState(false);
  const [editProfileOpen, setEditProfileOpen] = useState(false);
  const [profileFormData, setProfileFormData] = useState({ firstName: '', lastName: '' });
  const [isSidebarOpen, setIsSidebarOpen] = useState(localStorage.getItem('isSidebarOpen') !== 'false');
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [copyStatus, setCopyStatus] = useState('idle');

  useEffect(() => {
    // Always start with a fresh session
    startNewChat(true);
  }, []);

  useEffect(() => {
    document.documentElement.lang = i18n.language;
  }, [i18n.language]);

  useEffect(() => {
    localStorage.setItem('isSidebarOpen', isSidebarOpen);
  }, [isSidebarOpen]);

  // Add beforeunload event listener to warn about losing progress
  useEffect(() => {
    const handleBeforeUnload = (e) => {
      if (messages.length > 0) {
        const message = 'You have an active chat session. If you leave or refresh, you will lose your progress. Are you sure?';
        e.preventDefault();
        e.returnValue = message;
        return message;
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);

    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
    };
  }, [messages]);

  const startNewChat = () => {
    const newSessionId = `user_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
    setSessionId(newSessionId);
    setMessages([]);
    return newSessionId;
  };

  const handleSendMessage = async (overrideMessage = null) => {
    // If it's a click event (not an override string), use inputMessage
    const isSyntheticEvent = overrideMessage && typeof overrideMessage === 'object' && overrideMessage._reactName;
    const textToSend = (!overrideMessage || isSyntheticEvent) ? inputMessage : overrideMessage;

    if (!textToSend.trim() || loading) return;

    const userMessage = {
      id: Date.now(),
      content: textToSend,
      type: 'user',
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);

    // Only clear input if we were sending what was in the input box
    if (!overrideMessage || isSyntheticEvent) {
      setInputMessage('');
    }
    setLoading(true);

    try {
      // Always use the per-chat session id so a fresh chat never reuses an old Rasa tracker.
      const activeUserId = sessionId || startNewChat();

      const botResponses = await chatService.sendMessage(textToSend, activeUserId);

      // Rasa returns an array of response objects [ { recipient_id: "user_id", text: "..." }, ... ]
      if (Array.isArray(botResponses)) {
        botResponses.forEach((botResponse, index) => {
          setTimeout(() => {
            const botMessage = {
              id: Date.now() + index + 1,
              content: botResponse.text || '',
              custom: botResponse.custom || null,
              buttons: botResponse.buttons || null, // Capture payload buttons
              type: 'bot',
              timestamp: new Date(),
            };
            setMessages(prev => [...prev, botMessage]);
          }, index * 500);
        });
      }

    } catch (error) {
      console.error('Failed to send message:', error);
      const errorMessage = {
        id: Date.now(),
        content: t('errorMessage'),
        type: 'bot',
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handleButtonSubmit = (payload) => {
    handleSendMessage(payload);
  };

  const serializeMessageForDebug = (message) => {
    const role = String(message.type || 'unknown').toUpperCase();
    const timestamp = message.timestamp ? new Date(message.timestamp).toISOString() : '';
    const lines = [`[${role}] ${timestamp}`, message.content || ''];

    if (Array.isArray(message.buttons) && message.buttons.length > 0) {
      lines.push(`Buttons: ${JSON.stringify(message.buttons, null, 2)}`);
    }

    if (message.custom) {
      lines.push(`Custom: ${JSON.stringify(message.custom, null, 2)}`);
    }

    return lines.join('\n');
  };

  const buildDebugTranscript = () => {
    const debugPayload = [
      'RiaBot Chat Debug Log',
      `Exported At: ${new Date().toISOString()}`,
      `Session ID: ${sessionId || 'unknown'}`,
      `Message Count: ${messages.length}`,
      '',
      ...messages.map((message, index) => `${index + 1}.\n${serializeMessageForDebug(message)}`),
    ];

    return debugPayload.join('\n\n');
  };

  const copyTextToClipboard = async (text) => {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      return;
    }

    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.setAttribute('readonly', '');
    textArea.style.position = 'absolute';
    textArea.style.left = '-9999px';
    document.body.appendChild(textArea);
    textArea.select();
    document.execCommand('copy');
    document.body.removeChild(textArea);
  };

  const handleCopyChatLog = async () => {
    if (messages.length === 0) return;

    try {
      await copyTextToClipboard(buildDebugTranscript());
      setCopyStatus('copied');
      window.setTimeout(() => setCopyStatus('idle'), 2000);
    } catch (error) {
      console.error('Failed to copy chat log:', error);
      setCopyStatus('error');
      window.setTimeout(() => setCopyStatus('idle'), 2000);
    }
  };


  const handleProfileUpdate = async (formData) => {
    setUpdateError('');
    try {
      const updatedUser = await authService.updateProfile({
        first_name: formData.firstName,
        last_name: formData.lastName
      });
      setUser(updatedUser);
      setEditProfileOpen(false);
    } catch (error) {
      setUpdateError(error.response?.data?.detail || 'Failed to update profile.');
    }
  };


  return (
    <div className={`chat-container ${isSidebarOpen ? 'sidebar-open' : ''}`}>
      <Sidebar
        isSidebarOpen={isSidebarOpen}
        profileTriggerRef={profileTriggerRef}
        settingsTriggerRef={settingsTriggerRef}
        onProfileClick={() => { setProfileOpen(p => !p); setIsSettingsOpen(false); }}
        onSettingsClick={() => { setIsSettingsOpen(p => !p); setProfileOpen(false); }}
      />

      <div className="main-chat">
        <ChatHeader
          isSidebarOpen={isSidebarOpen}
          onToggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)}
          onStartNewChat={startNewChat}
          onCopyChatLog={handleCopyChatLog}
          canCopyChatLog={messages.length > 0}
          copyStatus={copyStatus}
        />

        <MessageList
          messages={messages}
          loading={loading}
          onButtonSubmit={handleButtonSubmit}
        />

        <ChatInput
          inputMessage={inputMessage}
          setInputMessage={setInputMessage}
          loading={loading}
          onSendMessage={handleSendMessage}
          messages={messages}
        />
      </div>

      <ContextMenu isOpen={profileOpen} triggerRef={profileTriggerRef} onClose={() => setProfileOpen(false)}>
        <div className="menu-item" onClick={() => { setEditProfileOpen(true); setProfileOpen(false); }}>{t('editProfile')}</div>
        <div className="menu-item" onClick={logout}>{t('logout')}</div>
      </ContextMenu>

      <ContextMenu isOpen={isSettingsOpen} triggerRef={settingsTriggerRef} onClose={() => setIsSettingsOpen(false)}>
        <div className="language-menu-container" onMouseEnter={() => setIsLangMenuOpen(true)} onMouseLeave={() => setIsLangMenuOpen(false)}>
          <div className="menu-item language-menu-toggle">{t('language')} <span>▸</span></div>
          {isLangMenuOpen && (
            <div className="language-submenu">
              <div className="menu-item" onClick={() => { i18n.changeLanguage('en'); setIsSettingsOpen(false); }}>{t('english')}</div>
              <div className="menu-item" onClick={() => { i18n.changeLanguage('km'); setIsSettingsOpen(false); }}>{t('khmer')}</div>
            </div>
          )}
        </div>
        <div className="theme-menu-container" onMouseEnter={() => setIsThemeMenuOpen(true)} onMouseLeave={() => setIsThemeMenuOpen(false)}>
          <div className="menu-item theme-menu-toggle">{t('theme')} <span>▸</span></div>
          {isThemeMenuOpen && (
            <div className="theme-submenu">
              <div className="menu-item" onClick={() => { setTheme('light'); setIsSettingsOpen(false); }}>{t('light')}</div>
              <div className="menu-item" onClick={() => { setTheme('dark'); setIsSettingsOpen(false); }}>{t('dark')}</div>
            </div>
          )}
        </div>
      </ContextMenu>

      <ProfileEditModal
        isOpen={editProfileOpen}
        onClose={() => setEditProfileOpen(false)}
        onUpdate={handleProfileUpdate}
        updateError={updateError}
      />
    </div>
  );
}

export default ChatInterface;
