import React from 'react';

const ChatHeader = ({ onToggleSidebar }) => {
  return (
    <>
      <div className="chat-header">
        <button className="menu-btn" onClick={onToggleSidebar}>
          <span></span>
          <span></span>
          <span></span>
        </button>
      </div>
    </>
  );
};

export default ChatHeader;
