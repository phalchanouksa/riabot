import React, { useState, useRef, useEffect } from 'react';
import TypingEffect from './TypingEffect';
import ReactMarkdown from 'react-markdown';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../contexts/AuthContext';
import UniversityRecommendationsCard from './UniversityRecommendationsCard';

const MessageList = ({ messages, loading, onButtonSubmit }) => {
  const [animatedMessages, setAnimatedMessages] = useState(new Set());
  const { t } = useTranslation();
  const { user } = useAuth();
  const messagesEndRef = useRef(null);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleAnimationComplete = (messageId) => {
    setAnimatedMessages(prev => new Set(prev).add(messageId));
  };

  const renderMessage = (message, index) => {
    const isUser = message.type === 'user';
    const isSystem = message.type === 'system';
    const hasUniversityRecommendations =
      message.custom?.type === 'university_recommendations' &&
      Array.isArray(message.custom?.data);

    const messageClass = isUser ? 'user-message' : 'bot-message';
    const avatarContent = isUser ? ' ' : (isSystem ? ' ' : '');
    const bubbleClass = `message-bubble ${isSystem ? 'system-bubble' : ''} ${hasUniversityRecommendations ? 'structured-bubble' : ''}`;

    return (
      <div key={message.id} className={`message ${messageClass}`}>
        {!isUser && <div className="message-avatar">{avatarContent}</div>}
        <div className={bubbleClass}>
          {
            message.type === 'bot' && index === messages.length - 1 && !animatedMessages.has(message.id) ? (
              <TypingEffect
                fullText={message.content}
                onComplete={() => handleAnimationComplete(message.id)}
              />
            ) : (
              <ReactMarkdown>{message.content}</ReactMarkdown>
            )
          }
          {hasUniversityRecommendations && (
            <UniversityRecommendationsCard
              data={message.custom.data}
              title={message.custom.title}
              subtitle={message.custom.subtitle}
              showConfidence={message.custom.show_confidence}
            />
          )}
          {message.buttons && message.buttons.length > 0 && (
            <div className="message-buttons" style={{ marginTop: '10px', display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              {message.buttons.map((btn, i) => (
                <button
                  key={i}
                  onClick={() => onButtonSubmit(btn.payload)}
                  className="interactive-btn"
                  style={{
                    padding: '8px 16px',
                    borderRadius: '20px',
                    background: 'var(--primary-color, #4A90E2)',
                    color: 'white',
                    border: 'none',
                    cursor: 'pointer',
                    fontSize: '14px',
                    fontFamily: 'inherit',
                    transition: 'opacity 0.2s',
                  }}
                  onMouseOver={(e) => e.target.style.opacity = 0.8}
                  onMouseOut={(e) => e.target.style.opacity = 1}
                >
                  {btn.title}
                </button>
              ))}
            </div>
          )}
        </div>
        {isUser && <div className="message-avatar">{avatarContent}</div>}
      </div>
    );
  };

  return (
    <div className="messages-scroll-container">
      <div className="messages">
        {messages.length === 0 ? (
          <div className="empty-chat">
            <div className="logo-mark"></div>
            <h2>{`Hello, ${user?.first_name || user?.username}`}</h2>
          </div>
        ) : (
          messages.map((message, index) => renderMessage(message, index))
        )}
        {loading && (
          <div className="message bot-message">
            <div className="message-avatar"> </div>
            <div className="message-bubble loading-bubble">{t('riaBotIsThinking')}</div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>
    </div>
  );
};

export default MessageList;
