/**
 * API service for communicating with the FastAPI backend.
 * Replaces the previous geminiService.ts (direct Gemini calls).
 */

import type { Project, ProjectDetail, ResearchRequest, NodeStatusEvent } from '../types';

// ---------------------------------------------------------------------------
// Base URL — in production read from VITE_API_URL, in dev use Vite proxy
// ---------------------------------------------------------------------------
const VITE_API_URL = import.meta.env.VITE_API_URL as string | undefined;
const API_BASE = VITE_API_URL ? `${VITE_API_URL.replace(/\/+$/, '')}/api` : '/api';

/**
 * Derive WebSocket base from the API URL.
 *  - Production: https://api.example.com → wss://api.example.com
 *  - Dev:        '' (empty) → use current page host with Vite proxy
 */
function wsBase(): string {
  if (VITE_API_URL) {
    const url = new URL(VITE_API_URL);
    const proto = url.protocol === 'https:' ? 'wss' : 'ws';
    return `${proto}://${url.host}`;
  }
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
  return `${proto}://${window.location.host}`;
}

// ---------------------------------------------------------------------------
// REST helpers
// ---------------------------------------------------------------------------
async function request<T>(path: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
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
  const ws = new WebSocket(`${wsBase()}/ws/research/${projectId}`);

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
