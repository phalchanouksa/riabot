import React from 'react';
import { useTranslation } from 'react-i18next';

const ChatInput = ({ 
  inputMessage, 
  setInputMessage, 
  loading, 
  onSendMessage, 
  messages 
}) => {
  const { t } = useTranslation();

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      onSendMessage();
    }
  };

  return (
    <div className={`chat-input-area ${messages.length === 0 ? 'centered' : 'bottom'}`}>
      <div className="chat-input">
        <textarea
          placeholder={t('enterPrompt')}
          value={inputMessage}
          onChange={(e) => setInputMessage(e.target.value)}
          onKeyPress={handleKeyPress}
        />
        <button onClick={onSendMessage} disabled={!inputMessage.trim() || loading}>
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="24" height="24">
            <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
          </svg>
        </button>
      </div>
    </div>
  );
};

export default ChatInput;
