import api from './authService';

export const chatService = {
  sendMessage: async (message, sessionId = null) => {
    const payload = { message };
    if (sessionId) {
      payload.session_id = sessionId;
    }

    const response = await api.post('/chat/send/', payload);
    return response.data;
  },

  getChatSessions: async () => {
    const response = await api.get('/chat/sessions/');
    return response.data;
  },

  getChatHistory: async (sessionId) => {
    const response = await api.get(`/chat/history/${sessionId}/`);
    return response.data;
  },

  deleteSession: async (sessionId) => {
    const response = await api.delete(`/chat/sessions/${sessionId}/delete/`);
    return response.data;
  },
};
