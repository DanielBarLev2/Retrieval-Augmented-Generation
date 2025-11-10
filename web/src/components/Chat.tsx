import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import Message, { type ChatMessage } from './Message';
import { ApiError, postChat, type ChatHistoryTurn } from '../api/client';

const SESSION_STORAGE_KEY = 'rag-chat-session-id';

const createMessageId = () =>
  typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function'
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(16).slice(2)}`;

const Chat = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [sessionId, setSessionId] = useState<string | null>(() => {
    if (typeof window === 'undefined') {
      return null;
    }

    const stored = window.localStorage.getItem(SESSION_STORAGE_KEY);
    return stored && stored.length > 0 ? stored : null;
  });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const endOfMessagesRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (typeof window !== 'undefined' && sessionId) {
      window.localStorage.setItem(SESSION_STORAGE_KEY, sessionId);
    }
  }, [sessionId]);

  useEffect(() => {
    endOfMessagesRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

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
            session_id: sessionId,
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

        setSessionId(response.session_id);
        setMessages((prev) => [...prev, assistantMessage]);
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
    [historyPayload, input, isLoading, sessionId],
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
          <span className="session-id">{sessionId ?? 'pending'}</span>
        </div>
      </header>

      <main className="chat-messages" role="log" aria-live="polite">
        {messages.length === 0 && (
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
          disabled={isLoading}
        />
        <div className="chat-actions">
          {error && <div className="chat-error">{error}</div>}
          <div className="chat-buttons">
            {isLoading && (
              <button type="button" onClick={handleStop} className="secondary">
                Stop
              </button>
            )}
            <button type="submit" disabled={isLoading || !input.trim()}>
              {isLoading ? 'Sending…' : 'Send'}
            </button>
          </div>
        </div>
      </form>
    </div>
  );
};

export default Chat;

