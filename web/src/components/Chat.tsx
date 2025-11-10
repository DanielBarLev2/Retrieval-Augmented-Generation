import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import Message, { type ChatMessage } from './Message';
import {
  ApiError,
  getChatSessionMessages,
  postChat,
  type ChatHistoryTurn,
} from '../api/client';

const createMessageId = () =>
  typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function'
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(16).slice(2)}`;

interface ChatProps {
  activeSessionId: string | null;
  onSessionChange: (sessionId: string | null) => void;
  onRefreshSessions: () => void;
}

const Chat = ({ activeSessionId, onSessionChange, onRefreshSessions }: ChatProps) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isHistoryLoading, setIsHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const endOfMessagesRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    endOfMessagesRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
    setIsLoading(false);

    if (!activeSessionId) {
      setMessages([]);
      setHistoryError(null);
      return;
    }

    const controller = new AbortController();
    let cancelled = false;

    const loadHistory = async () => {
      setIsHistoryLoading(true);
      setHistoryError(null);
      setError(null);
      try {
        const response = await getChatSessionMessages(activeSessionId, controller.signal);
        if (cancelled) {
          return;
        }

        const hydratedMessages: ChatMessage[] = response.messages.map((message) => ({
          id: message.id,
          role: message.role,
          content: message.content,
          createdAt: message.created_at,
          sources: message.sources,
          latencyMs: message.latency_ms ?? undefined,
        }));
        setMessages(hydratedMessages);
      } catch (err) {
        if (cancelled || (err as Error).name === 'AbortError') {
          return;
        }
        if (err instanceof ApiError) {
          if (err.status === 404) {
            setHistoryError('Session no longer exists. Starting a new chat.');
            setMessages([]);
            onSessionChange(null);
            return;
          }
          setHistoryError(
            err.status >= 500
              ? 'Unable to load chat history from the server.'
              : 'Unable to load chat history.',
          );
        } else {
          setHistoryError('Network error while loading chat history.');
        }
        setMessages([]);
      } finally {
        if (!cancelled) {
          setIsHistoryLoading(false);
        }
      }
    };

    void loadHistory();

    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [activeSessionId, onSessionChange]);

  const historyPayload = useMemo<ChatHistoryTurn[]>(() => {
    return messages.map((message) => ({
      role: message.role,
      content: message.content,
    }));
  }, [messages]);

  const handleSubmit = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      const trimmed = input.trim();
      if (!trimmed || isLoading) {
        return;
      }

      setError(null);
      setIsLoading(true);

      const userMessage: ChatMessage = {
        id: createMessageId(),
        role: 'user',
        content: trimmed,
      };

      setMessages((prev) => [...prev, userMessage]);
      setInput('');

      abortControllerRef.current?.abort();
      abortControllerRef.current = new AbortController();

      try {
        const response = await postChat(
          {
            message: trimmed,
            session_id: activeSessionId,
            history: historyPayload,
          },
          abortControllerRef.current.signal,
        );

        const assistantMessage: ChatMessage = {
          id: createMessageId(),
          role: 'assistant',
          content: response.answer,
          latencyMs: response.latency_ms,
          createdAt: response.created_at,
          sources: response.sources,
        };

        if (response.session_id !== activeSessionId) {
          onSessionChange(response.session_id);
        }
        setMessages((prev) => [...prev, assistantMessage]);
        onRefreshSessions();
      } catch (err) {
        if (err instanceof ApiError) {
          setError(
            err.status >= 500
              ? 'Server error. Please check that the backend is running.'
              : 'Unable to send message. Please verify your request and try again.',
          );
        } else if ((err as Error).name !== 'AbortError') {
          setError('Network error. Please verify the backend is reachable.');
        }
      } finally {
        abortControllerRef.current = null;
        setIsLoading(false);
      }
    },
    [activeSessionId, historyPayload, input, isLoading, onRefreshSessions, onSessionChange],
  );

  const handleStop = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
      setIsLoading(false);
    }
  };

  return (
    <div className="chat-container">
      <header className="chat-header">
        <div>
          <h1>Local RAG Chat</h1>
          <p className="chat-subtitle">
            Ask questions about the ingested Wikipedia topics. Responses cite retrieved sources.
          </p>
        </div>
        <div className="session-badge" aria-live="polite">
          <span className="session-label">Session</span>
          <span className="session-id">{activeSessionId ?? 'pending'}</span>
        </div>
      </header>

      <main className="chat-messages" role="log" aria-live="polite">
        {isHistoryLoading && <div className="chat-history-loading">Loading chat history…</div>}
        {historyError && <div className="chat-history-error">{historyError}</div>}
        {!isHistoryLoading && !historyError && messages.length === 0 && (
          <div className="chat-empty-state">
            <p>Welcome! Ask the assistant anything about Retrieval-Augmented Generation topics.</p>
          </div>
        )}
        {messages.map((message) => (
          <Message key={message.id} message={message} />
        ))}
        <div ref={endOfMessagesRef} />
      </main>

      <form className="chat-input" onSubmit={handleSubmit}>
        <label htmlFor="chat-message" className="sr-only">
          Message
        </label>
        <textarea
          id="chat-message"
          name="message"
          rows={3}
          placeholder="Type your question..."
          value={input}
          onChange={(event) => setInput(event.target.value)}
          disabled={isLoading || isHistoryLoading}
        />
        <div className="chat-actions">
          {error && <div className="chat-error">{error}</div>}
          <div className="chat-buttons">
            {isLoading && (
              <button type="button" onClick={handleStop} className="secondary">
                Stop
              </button>
            )}
            <button type="submit" disabled={isLoading || isHistoryLoading || !input.trim()}>
              {isLoading ? 'Sending…' : isHistoryLoading ? 'Loading…' : 'Send'}
            </button>
          </div>
        </div>
      </form>
    </div>
  );
};

export default Chat;

