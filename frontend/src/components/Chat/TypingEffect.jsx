import React, { useState, useEffect, useMemo } from 'react';
import ReactMarkdown from 'react-markdown';

const TypingEffect = ({ fullText, onComplete, typingSpeed = 30 }) => {
  const [displayedText, setDisplayedText] = useState('');

  useEffect(() => {
    if (fullText) {
      setDisplayedText('');
      let i = 0;
      const intervalId = setInterval(() => {
        if (i < fullText.length) {
          setDisplayedText(prev => prev + fullText.charAt(i));
          i++;
        } else {
          clearInterval(intervalId);
          if (onComplete) onComplete();
        }
      }, typingSpeed);

      return () => clearInterval(intervalId);
    }
  }, [fullText, typingSpeed, onComplete]);

  const memoizedMarkdown = useMemo(() => {
    return <ReactMarkdown>{displayedText}</ReactMarkdown>;
  }, [displayedText]);

  return memoizedMarkdown;
};

export default TypingEffect;
