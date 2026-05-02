/// <reference types="vite/client" />
/**
 * API service for Scholar-Agent (OpenClaw-style conversational mode).
 */

import type {
  ChatSession,
  ChatSessionDetail,
  ChatReply,
  ModelOption,
  LiteratureItem,
} from '../types';

const API_ROOT = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');
const API_BASE = `${API_ROOT}/api`;

// ---------------------------------------------------------------------------
// REST helpers
// ---------------------------------------------------------------------------
async function request<T>(path: string, opts?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  const res = await fetch(`${API_BASE}${path}`, {
    headers,
    ...opts,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API ${res.status}: ${body}`);
  }
  return res.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// Chat Session API
// ---------------------------------------------------------------------------

/** POST /api/chat/sessions — create new chat session */
export function createChatSession(modelName: string = 'qwen3-coder-30b-a3b-instruct'): Promise<ChatSession> {
  return request<ChatSession>('/chat/sessions', {
    method: 'POST',
    body: JSON.stringify({ model_name: modelName }),
  });
}

/** GET /api/chat/sessions — list all chat sessions */
export function getChatSessions(): Promise<ChatSession[]> {
  return request<ChatSession[]>('/chat/sessions');
}

/** GET /api/chat/sessions/:id — get session with messages */
export function getChatSession(id: string): Promise<ChatSessionDetail> {
  return request<ChatSessionDetail>(`/chat/sessions/${id}`);
}

/** DELETE /api/chat/sessions/:id */
export function deleteChatSession(id: string): Promise<void> {
  return request<void>(`/chat/sessions/${id}`, { method: 'DELETE' });
}

/** POST /api/chat/sessions/:id/message — send a message */
export function sendChatMessage(
  sessionId: string,
  message: string,
  modelName: string,
): Promise<ChatReply> {
  return request<ChatReply>(`/chat/sessions/${sessionId}/message`, {
    method: 'POST',
    body: JSON.stringify({ message, model_name: modelName }),
  });
}

// ---------------------------------------------------------------------------
// Models API
// ---------------------------------------------------------------------------

/** GET /api/models — list all available models */
export function getAvailableModels(): Promise<{ models: ModelOption[] }> {
  return request<{ models: ModelOption[] }>('/models');
}

// ---------------------------------------------------------------------------
// Paper API
// ---------------------------------------------------------------------------

/** GET /api/lit/:id — get a single paper */
export function getLiterature(id: number): Promise<LiteratureItem> {
  return request<LiteratureItem>(`/lit/${id}`);
}

// ---------------------------------------------------------------------------
// Chat WebSocket (for real-time progress)
// ---------------------------------------------------------------------------

export function connectChatWebSocket(
  sessionId: string,
  onMessage: (data: any) => void,
  onClose?: () => void,
): WebSocket {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  // Use current host and proxy port (8000 for backend)
  const wsUrl = `${protocol}//${window.location.hostname}:8000/ws/chat/${sessionId}`;
  
  const ws = new WebSocket(wsUrl);
  
  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      onMessage(data);
    } catch (e) {
      console.error('Failed to parse WS message', e);
    }
  };
  
  ws.onclose = () => {
    if (onClose) onClose();
  };
  
  return ws;
}
