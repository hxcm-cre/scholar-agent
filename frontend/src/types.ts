// ---------------------------------------------------------------------------
// Shared TypeScript interfaces matching backend Pydantic schemas
// ---------------------------------------------------------------------------

export interface ResearchWeights {
  relevance: number;
  venue: number;
  citation: number;
  repro: number;
}

export interface ResearchRequest {
  query: string;
  model_name: string;
  weights: ResearchWeights;
  use_ocr: boolean;
  csv_data?: string | null;
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
}

export interface ReportItem {
  id: number;
  content_markdown: string;
  metrics_json: string;
  created_at: string;
}

export interface ProjectDetail extends Project {
  literature: LiteratureItem[];
  reports: ReportItem[];
}

export interface NodeStatusEvent {
  type: 'node_status' | 'complete' | 'error';
  node_name: string;
  status: string;
  detail: string;
  progress: number;
}

export interface User {
  id: number;
  username: string;
  is_admin: boolean;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
}

