/**
 * API service for communicating with the FastAPI backend.
 * Replaces the previous geminiService.ts (direct Gemini calls).
 */

import type { Project, ProjectDetail, ResearchRequest, NodeStatusEvent } from '../types';

const API_BASE = '/api';

// ---------------------------------------------------------------------------
// REST helpers
// ---------------------------------------------------------------------------
async function request<T>(path: string, opts?: RequestInit): Promise<T> {
  const token = localStorage.getItem('token');
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

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

/** POST /api/research — create a project and start agent */
export function createResearch(req: ResearchRequest): Promise<Project> {
  return request<Project>('/research', {
    method: 'POST',
    body: JSON.stringify(req),
  });
}

/** GET /api/projects — list all projects */
export function getProjects(): Promise<Project[]> {
  return request<Project[]>('/projects');
}

/** GET /api/projects/:id — full detail */
export function getProject(id: number): Promise<ProjectDetail> {
  return request<ProjectDetail>(`/projects/${id}`);
}

/** DELETE /api/projects/:id */
export function deleteProject(id: number): Promise<void> {
  return request<void>(`/projects/${id}`, { method: 'DELETE' });
}

// ---------------------------------------------------------------------------
// WebSocket
// ---------------------------------------------------------------------------
export function connectWebSocket(
  projectId: number,
  onMessage: (evt: NodeStatusEvent) => void,
  onClose?: () => void,
): WebSocket {
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
  const host = window.location.host; // works with Vite proxy
  const ws = new WebSocket(`${proto}://${host}/ws/research/${projectId}`);

  ws.onopen = () => {
    // Send a ping to keep connection alive
    ws.send('ping');
  };

  ws.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data) as NodeStatusEvent;
      onMessage(data);
    } catch {
      console.warn('WS parse error', e.data);
    }
  };

  ws.onclose = () => {
    onClose?.();
  };

  // Keep-alive ping every 25s
  const pingInterval = setInterval(() => {
    if (ws.readyState === WebSocket.OPEN) {
      ws.send('ping');
    } else {
      clearInterval(pingInterval);
    }
  }, 25_000);

  return ws;
}
