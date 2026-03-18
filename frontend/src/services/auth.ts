import type { User, AuthResponse } from '../types';

const API_ROOT = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');
const API_BASE = `${API_ROOT}/api/auth`;
const ADMIN_BASE = `${API_ROOT}/api/admin`;

export async function login(username: string, password: string): Promise<AuthResponse> {
  const formData = new URLSearchParams();
  formData.append('username', username);
  formData.append('password', password);

  const res = await fetch(`${API_BASE}/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: formData,
  });

  if (!res.ok) {
    const contentType = res.headers.get('content-type') || '';
    if (contentType.includes('application/json')) {
      const error = await res.json();
      throw new Error(error.detail || 'Login failed');
    } else {
      throw new Error(`连接服务器失败 (${res.status})。请检查 VITE_API_BASE_URL 配置。`);
    }
  }

  const data = await res.json();
  localStorage.setItem('token', data.access_token);
  return data;
}

export async function register(username: string, password: string): Promise<User> {
  const res = await fetch(`${API_BASE}/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });

  if (!res.ok) {
    const contentType = res.headers.get('content-type') || '';
    if (contentType.includes('application/json')) {
      const error = await res.json();
      throw new Error(error.detail || 'Registration failed');
    } else {
      throw new Error(`注册失败 (${res.status})：服务器返回了非 JSON 响应。请确保后端 URL 正确。`);
    }
  }

  return res.json();
}


export async function getCurrentUser(): Promise<User> {
  const token = localStorage.getItem('token');
  if (!token) throw new Error('No token found');

  const res = await fetch(`${API_BASE}/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!res.ok) {
    localStorage.removeItem('token');
    throw new Error('Session expired');
  }

  return res.json();
}

export function logout() {
  localStorage.removeItem('token');
}

export function getToken(): string | null {
  return localStorage.getItem('token');
}

export async function getAdminUsers(): Promise<User[]> {
  const token = localStorage.getItem('token');
  const res = await fetch(`${ADMIN_BASE}/users`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!res.ok) {
    throw new Error('Failed to fetch users');
  }

  return res.json();
}
