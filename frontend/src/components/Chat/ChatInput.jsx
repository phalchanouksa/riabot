import React from 'react';
import { useTranslation } from 'react-i18next';

const SEGMENT_LABELS = ['ស្វែងយល់', 'បង្រួមជម្រើស', 'ស្នើលទ្ធផល'];

const ChatInput = ({ 
  inputMessage, 
  setInputMessage, 
  loading, 
  onSendMessage, 
  messages,
  activeSurveyQuestion = null
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
      {activeSurveyQuestion && (
        <div className="survey-progress-panel">
          <div className="survey-progress-copy">
            <span className="survey-progress-kicker">កំពុងធ្វើតេស្តណែនាំជំនាញ</span>
            <div className="survey-progress-meta">
              <strong>សំណួរទី {activeSurveyQuestion.number}</strong>
              <span>{activeSurveyQuestion.kindLabel}</span>
              <span>{activeSurveyQuestion.phaseLabel}</span>
            </div>
            <p>{activeSurveyQuestion.prompt}</p>
          </div>
          <div className="survey-progress-steps" aria-hidden="true">
            {SEGMENT_LABELS.map((label, index) => (
              <div
                key={label}
                className={`survey-progress-step ${index < activeSurveyQuestion.filledStages ? 'active' : ''}`}
              >
                <span>{label}</span>
              </div>
            ))}
          </div>
        </div>
      )}

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
