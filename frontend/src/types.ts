// ---------------------------------------------------------------------------
// Shared TypeScript interfaces matching backend Pydantic schemas
// ---------------------------------------------------------------------------

export interface ModelOption {
  id: string;
  label: string;
}

// ---------------------------------------------------------------------------
// Chat API types
// ---------------------------------------------------------------------------
export interface ChatSession {
  id: string;
  title: string;
  model_name: string;
  created_at: string;
  updated_at: string;
}

export interface ChatMessage {
  id: number;
  role: 'user' | 'assistant' | 'tool';
  content: string;
  tool_name: string | null;
  paper_refs: number[];
  created_at: string;
}

export interface ChatSessionDetail extends ChatSession {
  messages: ChatMessage[];
  papers: LiteratureItem[];
}

export interface ChatReply {
  reply: string;
  tool_used: string | null;
  papers: PaperResult[];
  paper_detail: PaperDetail | null;
  session: ChatSession;
}

export interface PaperResult {
  id: number;
  index: number;
  title: string;
  authors: string;
  year: number | null;
  venue: string;
  abstract: string;
  citations: number;
  score: number;
  url: string;
}

export interface PaperDetail {
  id: number;
  title: string;
  authors: string;
  year: number | null;
  venue: string;
  abstract: string;
  url: string;
}

export interface LiteratureItem {
  id: number;
  title: string;
  authors: string;
  year: number | null;
  venue: string;
  doi: string;
  url: string;
  abstract: string;
  citations: number;
  score: number;
  source: string;
  full_text: string;
  user_notes: string;
}

// ---------------------------------------------------------------------------
// Legacy types (kept for compatibility)
// ---------------------------------------------------------------------------
export interface ResearchWeights {
  relevance: number;
  venue: number;
  citation: number;
  repro: number;
}

export interface Project {
  id: number;
  query: string;
  model_name: string;
  status: 'pending' | 'running' | 'done' | 'error';
  error_message: string | null;
  weights_json: string;
  created_at: string;
  updated_at: string;
}
