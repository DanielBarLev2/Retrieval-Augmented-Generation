const DEFAULT_API_BASE_URL = 'http://localhost:8000';

const apiBaseUrl =
  (typeof import.meta !== 'undefined' && import.meta.env?.VITE_API_URL) ||
  DEFAULT_API_BASE_URL;

export type ChatRole = 'user' | 'assistant';

export interface ChatSource {
  title?: string | null;
  url?: string | null;
  chunk_index?: number | null;
  score?: number | null;
  page_id?: number | null;
  topic?: string | null;
}

export interface ChatResponsePayload {
  session_id: string;
  answer: string;
  sources: ChatSource[];
  latency_ms: number;
  created_at: string;
}

export interface ChatHistoryTurn {
  role: ChatRole;
  content: string;
}

export interface ChatRequestPayload {
  message: string;
  session_id?: string | null;
  history?: ChatHistoryTurn[];
  top_k?: number;
  model?: string;
  temperature?: number;
}

export interface WikipediaIngestResponse {
  topics: string[];
  processed_pages: number;
  embedded_chunks: number;
  skipped_pages: number;
  dry_run: boolean;
}

export interface WikipediaTopicsIngestRequest {
  topics: string[];
  max_pages_per_topic?: number;
  language?: string;
  chunk_size?: number;
  chunk_overlap?: number;
  dry_run?: boolean;
}

export interface WikipediaUrlIngestRequest {
  urls: string[];
  language?: string;
  chunk_size?: number;
  chunk_overlap?: number;
  dry_run?: boolean;
}

class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

export const postChat = async (
  payload: ChatRequestPayload,
  signal?: AbortSignal,
): Promise<ChatResponsePayload> => {
  const response = await fetch(`${apiBaseUrl}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
    signal,
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new ApiError(response.status, errorText || 'Failed to fetch chat response');
  }

  const data = (await response.json()) as ChatResponsePayload;
  return data;
};

export { ApiError };

const postJson = async <TBody, TResult>(
  path: string,
  payload: TBody,
  signal?: AbortSignal,
): Promise<TResult> => {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
    signal,
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new ApiError(response.status, errorText || 'Request failed');
  }

  return (await response.json()) as TResult;
};

export const ingestWikipediaTopics = async (
  payload: WikipediaTopicsIngestRequest,
  signal?: AbortSignal,
) => postJson<WikipediaTopicsIngestRequest, WikipediaIngestResponse>('/ingest/wikipedia', payload, signal);

export const ingestWikipediaUrls = async (
  payload: WikipediaUrlIngestRequest,
  signal?: AbortSignal,
) =>
  postJson<WikipediaUrlIngestRequest, WikipediaIngestResponse>(
    '/ingest/wikipedia/by-url',
    payload,
    signal,
  );

