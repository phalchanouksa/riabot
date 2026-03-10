import api from './authService';

export const chatService = {
  // Send message to chatbot natively through Rasa
  sendMessage: async (message, sessionId = null) => {
    // FIX #1: Generate or retrieve a persistent anonymous session ID for Concurrency
    let persistentSessionId = sessionId;
    if (!persistentSessionId) {
      persistentSessionId = localStorage.getItem('ria_chat_session_id');
      if (!persistentSessionId) {
        // Create a unique ID for this guest user to prevent Rasa mixing answers
        persistentSessionId = 'guest_' + Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
        localStorage.setItem('ria_chat_session_id', persistentSessionId);
      }
    }

    try {
      const response = await fetch('http://localhost:5005/webhooks/rest/webhook', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          sender: persistentSessionId, // Now every user has a unique ID!
          message: message
        }),
      });
      return await response.json();
    } catch (error) {
      console.error("Failed to connect to Rasa REST Channel:", error);
      throw error;
    }
  },

  // Get chat sessions
  getChatSessions: async () => {
    const response = await api.get('/chat/sessions/');
    return response.data;
  },

  // Get chat history
  getChatHistory: async (sessionId) => {
    const response = await api.get(`/chat/history/${sessionId}/`);
    return response.data;
  },

  // Delete chat session
  deleteSession: async (sessionId) => {
    const response = await api.delete(`/chat/sessions/${sessionId}/delete/`);
    return response.data;
  },
};
