import React, { useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../contexts/AuthContext';
import TypingEffect from './TypingEffect';
import UniversityRecommendationsCard from './UniversityRecommendationsCard';

const isNumericSurveyButtons = (buttons) =>
  Array.isArray(buttons) &&
  buttons.length > 0 &&
  buttons.every((button) => /^-?\d+$/.test(String(button?.title ?? '').trim()));

const MessageList = ({ messages, loading, onButtonSubmit }) => {
  const [animatedMessages, setAnimatedMessages] = useState(new Set());
  const { t } = useTranslation();
  const { user } = useAuth();
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleAnimationComplete = (messageId) => {
    setAnimatedMessages((prev) => new Set(prev).add(messageId));
  };

  const shouldAnimateMessage = (message, index) => {
    if (message.type !== 'bot' || index !== messages.length - 1) {
      return false;
    }

    if (animatedMessages.has(message.id)) {
      return false;
    }

    return Boolean((message.content || '').trim());
  };

  const renderMessage = (message, index) => {
    const isUser = message.type === 'user';
    const isSystem = message.type === 'system';
    const hasUniversityRecommendations =
      message.custom?.type === 'university_recommendations' &&
      Array.isArray(message.custom?.data);
    const hasSurveyChoices = isNumericSurveyButtons(message.buttons);
    const isAnimatingMessage = shouldAnimateMessage(message, index);

    const messageClass = isUser ? 'user-message' : 'bot-message';
    const avatarContent = isUser ? ' ' : (isSystem ? ' ' : '');
    const bubbleClass = `message-bubble ${isSystem ? 'system-bubble' : ''} ${hasUniversityRecommendations ? 'structured-bubble' : ''} ${hasSurveyChoices ? 'survey-bubble' : ''}`;

    return (
      <div key={message.id} className={`message ${messageClass}`}>
        {!isUser && <div className="message-avatar">{avatarContent}</div>}
        <div className={bubbleClass}>
          {isAnimatingMessage ? (
            <TypingEffect
              fullText={message.content}
              onComplete={() => handleAnimationComplete(message.id)}
            />
          ) : (
            <ReactMarkdown>{message.content}</ReactMarkdown>
          )}

          {hasUniversityRecommendations && (
            <UniversityRecommendationsCard
              data={message.custom.data}
              title={message.custom.title}
              subtitle={message.custom.subtitle}
              showConfidence={message.custom.show_confidence}
            />
          )}

          {message.buttons && message.buttons.length > 0 && (!hasSurveyChoices || !isAnimatingMessage) && (
            <div className={`message-buttons ${hasSurveyChoices ? 'survey-buttons' : 'nav-buttons'}`}>
              {message.buttons.map((btn, i) => (
                <button
                  key={i}
                  onClick={() => onButtonSubmit(btn.payload)}
                  className={`interactive-btn ${hasSurveyChoices ? 'survey-choice-btn' : 'nav-chip-btn'}`}
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
