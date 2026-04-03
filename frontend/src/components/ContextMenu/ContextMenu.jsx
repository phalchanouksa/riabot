import React, { useLayoutEffect, useRef } from 'react';
import ReactDOM from 'react-dom';
import './ContextMenu.css';

const ContextMenu = ({ isOpen, children, triggerRef, onClose, className = '' }) => {
  const menuRef = useRef(null);

  useLayoutEffect(() => {
    if (isOpen && triggerRef.current && menuRef.current) {
      const menu = menuRef.current;
      const triggerRect = triggerRef.current.getBoundingClientRect();
      const menuRect = menu.getBoundingClientRect();

      const { innerWidth, innerHeight } = window;
      const margin = 5; // 5px margin from viewport edges

      let top = triggerRect.bottom;
      let left = triggerRect.left;

      // Check vertical overflow
      if (triggerRect.bottom + menuRect.height > innerHeight) {
        top = triggerRect.top - menuRect.height;
      }

      // Check horizontal overflow
      if (triggerRect.left + menuRect.width > innerWidth) {
        left = triggerRect.right - menuRect.width;
      }

      // Ensure it's not off-screen top or left
      if (top < 0) top = margin;
      if (left < 0) left = margin;

      menu.style.top = `${top}px`;
      menu.style.left = `${left}px`;
    }
  }, [isOpen, triggerRef]);

  // Effect to handle clicks outside the menu
  useLayoutEffect(() => {
    const handleClickOutside = (event) => {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    } else {
      document.removeEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return ReactDOM.createPortal(
    <div ref={menuRef} className={`context-menu ${className}`.trim()}>
      {children}
    </div>,
    document.body
  );
};

export default ContextMenu;
