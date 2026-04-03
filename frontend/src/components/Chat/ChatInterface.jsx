import React, { startTransition, useEffect, useMemo, useRef, useState } from 'react';
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

const CHAT_LOG_CHEAT_CODE = 'copyallchat';
const CHEAT_CODE_TIMEOUT_MS = 1500;
const SURVEY_QUESTION_PATTERN = /^សំណួរទី\s*(\d+):\s*([^\n]+)/m;

const ChevronRightIcon = () => (
  <svg className="menu-chevron" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="none" aria-hidden="true">
    <path d="M6 3.5 10.5 8 6 12.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

const CheckIcon = () => (
  <svg className="menu-check" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="none" aria-hidden="true">
    <path d="m3.5 8.5 2.6 2.6L12.5 4.9" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

const PencilIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="none" aria-hidden="true">
    <path d="m11.9 2.5 1.6 1.6c.5.5.5 1.2 0 1.7l-6.8 6.8-2.8.8.8-2.8 6.8-6.8c.5-.5 1.2-.5 1.7 0Z" stroke="currentColor" strokeWidth="1.35" strokeLinecap="round" strokeLinejoin="round" />
    <path d="m10.8 3.6 1.6 1.6" stroke="currentColor" strokeWidth="1.35" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

const LogoutIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="none" aria-hidden="true">
    <path d="M6.5 2.75h-1a1.75 1.75 0 0 0-1.75 1.75v7a1.75 1.75 0 0 0 1.75 1.75h1" stroke="currentColor" strokeWidth="1.35" strokeLinecap="round" strokeLinejoin="round" />
    <path d="M9 5.25 12 8l-3 2.75" stroke="currentColor" strokeWidth="1.35" strokeLinecap="round" strokeLinejoin="round" />
    <path d="M12 8H6.5" stroke="currentColor" strokeWidth="1.35" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

const LanguageIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="none" aria-hidden="true">
    <path d="M2.75 4.25h6.5M6 2.5c-.1 2-1.1 4.6-3 6.7M6.1 9.2c-.7-.5-1.2-.9-1.8-1.6M8.5 12.75l2.9-7 2.9 7M9.3 10.75h4.2" stroke="currentColor" strokeWidth="1.35" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

const ThemeIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="none" aria-hidden="true">
    <path d="M12.4 10.8A5.25 5.25 0 0 1 5.2 3.6 5.75 5.75 0 1 0 12.4 10.8Z" stroke="currentColor" strokeWidth="1.35" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

const mapStoredMessageToUiMessage = (message) => {
  const metadata = message.metadata || {};
  return {
    id: message.id,
    content: message.content || '',
    custom: metadata.custom || null,
    buttons: metadata.buttons || null,
    type: message.message_type === 'user' ? 'user' : 'bot',
    timestamp: message.timestamp ? new Date(message.timestamp) : new Date(),
  };
};

const isNumericSurveyButtons = (buttons) =>
  Array.isArray(buttons) &&
  buttons.length > 0 &&
  buttons.every((button) => /^-?\d+$/.test(String(button?.title ?? '').trim()));

const parseSurveyMessage = (message) => {
  if (message?.type !== 'bot') {
    return null;
  }

  const content = message.content || '';
  const match = content.match(SURVEY_QUESTION_PATTERN);

  if (!match || !isNumericSurveyButtons(message.buttons)) {
    return null;
  }

  const number = Number(match[1]);
  const prompt = match[2]?.trim() || '';
  const isSkillQuestion = content.includes('0-3');
  const filledStages = number >= 17 ? 3 : number >= 9 ? 2 : 1;
  const phaseLabel = number >= 17 ? 'កំពុងស្នើលទ្ធផល' : number >= 9 ? 'កំពុងបង្រួមជម្រើស' : 'កំពុងស្វែងយល់';

  return {
    number,
    prompt,
    kind: isSkillQuestion ? 'skill' : 'interest',
    kindLabel: isSkillQuestion ? 'ផ្នែកជំនាញ' : 'ផ្នែកចំណាប់អារម្មណ៍',
    phaseLabel,
    filledStages,
  };
};

const ChatInterface = () => {
  const { t, i18n } = useTranslation();
  const { theme, setTheme } = useTheme();
  const { user, logout, setUser } = useAuth();
  const [updateError, setUpdateError] = useState('');
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const profileTriggerRef = useRef(null);
  const settingsTriggerRef = useRef(null);
  const [isThemeMenuOpen, setIsThemeMenuOpen] = useState(false);
  const [isLangMenuOpen, setIsLangMenuOpen] = useState(false);
  const [editProfileOpen, setEditProfileOpen] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(localStorage.getItem('isSidebarOpen') !== 'false');
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const cheatBufferRef = useRef('');
  const cheatLastKeyTimeRef = useRef(0);
  const displayName = [user?.first_name, user?.last_name].filter(Boolean).join(' ') || user?.username || 'RiaBot User';
  const profileHandle = user?.username ? `@${user.username}` : (user?.email || '');
  const profileInitial = (displayName || 'R').trim().charAt(0).toUpperCase();
  const activeLanguageLabel = i18n.language === 'km' ? t('khmer') : t('english');
  const activeThemeLabel = theme === 'dark' ? t('dark') : t('light');

  const closeSettingsMenu = () => {
    setIsSettingsOpen(false);
    setIsLangMenuOpen(false);
    setIsThemeMenuOpen(false);
  };

  const activeSurveyQuestion = useMemo(() => {
    const latestBotMessage = [...messages].reverse().find((message) => message.type === 'bot');
    return latestBotMessage ? parseSurveyMessage(latestBotMessage) : null;
  }, [messages]);

  useEffect(() => {
    document.documentElement.lang = i18n.language;
  }, [i18n.language]);

  useEffect(() => {
    localStorage.setItem('isSidebarOpen', isSidebarOpen);
  }, [isSidebarOpen]);

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
      const activeSessionId = sessionId;
      const response = await chatService.sendMessage(textToSend, activeSessionId);

      if (response?.session_id) {
        setSessionId(response.session_id);
      }

      const botResponses = Array.isArray(response?.bot_responses) ? response.bot_responses : [];
      if (botResponses.length > 0) {
        const nextMessages = botResponses.map(mapStoredMessageToUiMessage);
        startTransition(() => {
          setMessages(prev => [...prev, ...nextMessages]);
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
    if (messages.length === 0) return false;

    try {
      await copyTextToClipboard(buildDebugTranscript());
      return true;
    } catch (error) {
      console.error('Failed to copy chat log:', error);
      return false;
    }
  };

  useEffect(() => {
    const handleCheatCodeKeydown = (event) => {
      if (event.ctrlKey || event.metaKey || event.altKey || event.repeat) {
        return;
      }

      const target = event.target;
      const tagName = target?.tagName?.toLowerCase();
      const isEditable =
        target?.isContentEditable ||
        tagName === 'input' ||
        tagName === 'textarea' ||
        tagName === 'select';

      if (isEditable) {
        cheatBufferRef.current = '';
        return;
      }

      if (!/^[a-z]$/i.test(event.key)) {
        cheatBufferRef.current = '';
        return;
      }

      const now = Date.now();
      const withinWindow = now - cheatLastKeyTimeRef.current <= CHEAT_CODE_TIMEOUT_MS;
      const key = event.key.toLowerCase();
      const seededBuffer = withinWindow ? cheatBufferRef.current : '';
      const candidate = `${seededBuffer}${key}`.slice(-CHAT_LOG_CHEAT_CODE.length);

      if (CHAT_LOG_CHEAT_CODE.startsWith(candidate)) {
        cheatBufferRef.current = candidate;
      } else if (CHAT_LOG_CHEAT_CODE.startsWith(key)) {
        cheatBufferRef.current = key;
      } else {
        cheatBufferRef.current = '';
      }

      cheatLastKeyTimeRef.current = now;

      if (cheatBufferRef.current === CHAT_LOG_CHEAT_CODE) {
        cheatBufferRef.current = '';
        cheatLastKeyTimeRef.current = 0;
        handleCopyChatLog().then((copied) => {
          if (copied) {
            console.info('RiaBot chat log copied to clipboard.');
          } else {
            console.warn('No chat log was copied.');
          }
        });
      }
    };

    window.addEventListener('keydown', handleCheatCodeKeydown);
    return () => window.removeEventListener('keydown', handleCheatCodeKeydown);
  }, [messages, sessionId]);


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

  const handleChangeLanguage = (language) => {
    i18n.changeLanguage(language);
    closeSettingsMenu();
  };

  const handleChangeTheme = (nextTheme) => {
    setTheme(nextTheme);
    closeSettingsMenu();
  };


  return (
    <div className={`chat-container ${isSidebarOpen ? 'sidebar-open' : ''}`}>
      <Sidebar
        isSidebarOpen={isSidebarOpen}
        profileTriggerRef={profileTriggerRef}
        settingsTriggerRef={settingsTriggerRef}
        onProfileClick={() => {
          setProfileOpen((previous) => !previous);
          closeSettingsMenu();
        }}
        onSettingsClick={() => {
          setProfileOpen(false);
          setIsSettingsOpen((previous) => {
            const next = !previous;
            if (!next) {
              setIsLangMenuOpen(false);
              setIsThemeMenuOpen(false);
            }
            return next;
          });
        }}
      />

      <div className="main-chat">
        <ChatHeader
          onToggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)}
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
          activeSurveyQuestion={activeSurveyQuestion}
        />
      </div>

      <ContextMenu
        isOpen={profileOpen}
        triggerRef={profileTriggerRef}
        onClose={() => setProfileOpen(false)}
        className="profile-menu"
      >
        <div className="menu-profile-header">
          <div className="menu-profile-avatar">{profileInitial}</div>
          <div className="menu-profile-copy">
            <strong>{displayName}</strong>
            {profileHandle && <span>{profileHandle}</span>}
          </div>
        </div>
        <div className="menu-divider" />
        <button
          type="button"
          className="menu-item"
          onClick={() => { setEditProfileOpen(true); setProfileOpen(false); }}
        >
          <span className="menu-item-main">
            <span className="menu-item-icon"><PencilIcon /></span>
            <span className="menu-item-label">{t('editProfile')}</span>
          </span>
        </button>
        <button
          type="button"
          className="menu-item menu-item--danger"
          onClick={() => { setProfileOpen(false); logout(); }}
        >
          <span className="menu-item-main">
            <span className="menu-item-icon"><LogoutIcon /></span>
            <span className="menu-item-label">{t('logout')}</span>
          </span>
        </button>
      </ContextMenu>

      <ContextMenu
        isOpen={isSettingsOpen}
        triggerRef={settingsTriggerRef}
        onClose={closeSettingsMenu}
        className="settings-menu"
      >
        <div className="language-menu-container" onMouseEnter={() => setIsLangMenuOpen(true)} onMouseLeave={() => setIsLangMenuOpen(false)}>
          <button
            type="button"
            className={`menu-item menu-item--submenu ${isLangMenuOpen ? 'is-open' : ''}`}
            onClick={() => {
              setIsLangMenuOpen((previous) => !previous);
              setIsThemeMenuOpen(false);
            }}
          >
            <span className="menu-item-main">
              <span className="menu-item-icon"><LanguageIcon /></span>
              <span className="menu-item-label">{t('language')}</span>
            </span>
            <span className="menu-item-meta">
              <span>{activeLanguageLabel}</span>
              <ChevronRightIcon />
            </span>
          </button>
          {isLangMenuOpen && (
            <div className="language-submenu">
              <button
                type="button"
                className={`menu-item menu-item--option ${i18n.language === 'en' ? 'active' : ''}`}
                onClick={() => handleChangeLanguage('en')}
              >
                <span className="menu-item-label">{t('english')}</span>
                {i18n.language === 'en' && <CheckIcon />}
              </button>
              <button
                type="button"
                className={`menu-item menu-item--option ${i18n.language === 'km' ? 'active' : ''}`}
                onClick={() => handleChangeLanguage('km')}
              >
                <span className="menu-item-label">{t('khmer')}</span>
                {i18n.language === 'km' && <CheckIcon />}
              </button>
            </div>
          )}
        </div>
        <div className="theme-menu-container" onMouseEnter={() => setIsThemeMenuOpen(true)} onMouseLeave={() => setIsThemeMenuOpen(false)}>
          <button
            type="button"
            className={`menu-item menu-item--submenu ${isThemeMenuOpen ? 'is-open' : ''}`}
            onClick={() => {
              setIsThemeMenuOpen((previous) => !previous);
              setIsLangMenuOpen(false);
            }}
          >
            <span className="menu-item-main">
              <span className="menu-item-icon"><ThemeIcon /></span>
              <span className="menu-item-label">{t('theme')}</span>
            </span>
            <span className="menu-item-meta">
              <span>{activeThemeLabel}</span>
              <ChevronRightIcon />
            </span>
          </button>
          {isThemeMenuOpen && (
            <div className="theme-submenu">
              <button
                type="button"
                className={`menu-item menu-item--option ${theme === 'light' ? 'active' : ''}`}
                onClick={() => handleChangeTheme('light')}
              >
                <span className="menu-item-label">{t('light')}</span>
                {theme === 'light' && <CheckIcon />}
              </button>
              <button
                type="button"
                className={`menu-item menu-item--option ${theme === 'dark' ? 'active' : ''}`}
                onClick={() => handleChangeTheme('dark')}
              >
                <span className="menu-item-label">{t('dark')}</span>
                {theme === 'dark' && <CheckIcon />}
              </button>
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
