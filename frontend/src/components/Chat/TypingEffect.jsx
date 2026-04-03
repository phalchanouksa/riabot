import React, { useEffect, useMemo, useState } from 'react';
import ReactMarkdown from 'react-markdown';

const BASE_STEP_DELAY_MS = 14;
const PUNCTUATION_DELAY_MS = 38;
const INSTANT_TEXT_LENGTH = 10;
const LONG_TEXT_THRESHOLD = 120;
const MEDIUM_TEXT_THRESHOLD = 72;
const SHORT_TEXT_THRESHOLD = 28;

const TypingEffect = ({ fullText, onComplete }) => {
  const [displayedText, setDisplayedText] = useState('');
  const [isComplete, setIsComplete] = useState(false);

  useEffect(() => {
    const text = fullText || '';
    let timeoutId;
    let currentIndex = 0;
    let cancelled = false;

    const finishTyping = () => {
      if (cancelled) return;
      setDisplayedText(text);
      setIsComplete(true);
      if (onComplete) onComplete();
    };

    if (!text) {
      setDisplayedText('');
      setIsComplete(true);
      if (onComplete) onComplete();
      return undefined;
    }

    setDisplayedText('');
    setIsComplete(false);

    if (text.length <= INSTANT_TEXT_LENGTH) {
      finishTyping();
      return undefined;
    }

    const getChunkSize = () => {
      const remaining = text.length - currentIndex;
      if (remaining > LONG_TEXT_THRESHOLD) return 7;
      if (remaining > MEDIUM_TEXT_THRESHOLD) return 6;
      if (remaining > SHORT_TEXT_THRESHOLD) return 4;
      return 2;
    };

    const scheduleNextStep = () => {
      if (cancelled) return;

      currentIndex = Math.min(text.length, currentIndex + getChunkSize());
      setDisplayedText(text.slice(0, currentIndex));

      if (currentIndex >= text.length) {
        finishTyping();
        return;
      }

      const trailingChar = text[currentIndex - 1] || '';
      const isPunctuationPause = /[.,!?;:។៖]/.test(trailingChar);
      const delay = isPunctuationPause ? PUNCTUATION_DELAY_MS : BASE_STEP_DELAY_MS;
      timeoutId = window.setTimeout(scheduleNextStep, delay);
    };

    timeoutId = window.setTimeout(scheduleNextStep, BASE_STEP_DELAY_MS);

    return () => {
      cancelled = true;
      if (timeoutId) {
        window.clearTimeout(timeoutId);
      }
    };
  }, [fullText, onComplete]);

  const memoizedMarkdown = useMemo(() => (
    <ReactMarkdown>{displayedText}</ReactMarkdown>
  ), [displayedText]);

  return (
    <div className={`typing-effect ${isComplete ? 'is-complete' : 'is-typing'}`}>
      {memoizedMarkdown}
    </div>
  );
};

export default TypingEffect;
