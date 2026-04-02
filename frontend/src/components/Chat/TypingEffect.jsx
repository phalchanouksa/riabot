import React, { useEffect, useMemo, useState } from 'react';
import ReactMarkdown from 'react-markdown';

const STEP_INTERVAL_MS = 18;
const MIN_STEPS = 12;
const MAX_STEPS = 48;
const INSTANT_TEXT_LENGTH = 24;

const TypingEffect = ({ fullText, onComplete }) => {
  const [displayedText, setDisplayedText] = useState('');

  useEffect(() => {
    const text = fullText || '';

    if (!text) {
      setDisplayedText('');
      if (onComplete) onComplete();
      return;
    }

    if (text.length <= INSTANT_TEXT_LENGTH) {
      setDisplayedText(text);
      if (onComplete) onComplete();
      return;
    }

    let currentIndex = 0;
    const targetSteps = Math.max(
      MIN_STEPS,
      Math.min(MAX_STEPS, Math.ceil(text.length / 4))
    );
    const charsPerStep = Math.max(1, Math.ceil(text.length / targetSteps));

    setDisplayedText('');

    const intervalId = window.setInterval(() => {
      currentIndex = Math.min(text.length, currentIndex + charsPerStep);
      setDisplayedText(text.slice(0, currentIndex));

      if (currentIndex >= text.length) {
        window.clearInterval(intervalId);
        if (onComplete) onComplete();
      }
    }, STEP_INTERVAL_MS);

    return () => window.clearInterval(intervalId);
  }, [fullText, onComplete]);

  const memoizedMarkdown = useMemo(() => (
    <ReactMarkdown>{displayedText}</ReactMarkdown>
  ), [displayedText]);

  return memoizedMarkdown;
};

export default TypingEffect;
