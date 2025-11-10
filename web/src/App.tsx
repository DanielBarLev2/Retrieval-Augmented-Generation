import { useCallback, useEffect, useMemo, useState } from 'react';

import { ApiError, deleteChatSession, listChatSessions, updateChatSession } from './api/client';
import type { ChatSessionSummary } from './api/client';
import Chat from './components/Chat';
import IngestionPanel from './components/IngestionPanel';
import KnowledgeReferencesPanel from './components/KnowledgeReferencesPanel';
import Sidebar from './components/Sidebar';
import './App.css';

const SESSION_STORAGE_KEY = 'rag-chat-session-id';

const getStoredSessionId = () => {
  if (typeof window === 'undefined') {
    return null;
  }
  const stored = window.localStorage.getItem(SESSION_STORAGE_KEY);
  return stored && stored.length > 0 ? stored : null;
};

const App = () => {
  const [sessions, setSessions] = useState<ChatSessionSummary[]>([]);
  const [sessionsLoading, setSessionsLoading] = useState(false);
  const [sessionsError, setSessionsError] = useState<string | null>(null);
  const initialSessionId = useMemo(() => getStoredSessionId(), []);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(() => initialSessionId);
  const [shouldAutoSelectSession, setShouldAutoSelectSession] = useState(() => initialSessionId === null);
  const [isIngestionOpen, setIsIngestionOpen] = useState(false);
  const [isReferencesOpen, setIsReferencesOpen] = useState(false);

  const refreshSessions = useCallback(async () => {
    setSessionsLoading(true);
    setSessionsError(null);
    try {
      const data = await listChatSessions();
      setSessions(data);

      const activeExists =
        activeSessionId !== null && data.some((session) => session.session_id === activeSessionId);
      const isPreparingNewChat = activeSessionId === null && !shouldAutoSelectSession;
      let nextActiveId = activeSessionId;

      if (!activeExists) {
        if (data.length === 0) {
          nextActiveId = null;
        } else if (!isPreparingNewChat) {
          nextActiveId = data[0].session_id;
          if (shouldAutoSelectSession) {
            setShouldAutoSelectSession(false);
          }
        }
      } else if (shouldAutoSelectSession && data.length > 0) {
        setShouldAutoSelectSession(false);
      }

      if (nextActiveId !== activeSessionId) {
        setActiveSessionId(nextActiveId);
      }
    } catch (err) {
      if (err instanceof ApiError) {
        setSessionsError(err.message || 'Unable to load chat sessions.');
      } else {
        setSessionsError('Unable to load chat sessions.');
      }
    } finally {
      setSessionsLoading(false);
    }
  }, [activeSessionId, shouldAutoSelectSession]);

  useEffect(() => {
    void refreshSessions();
  }, [refreshSessions]);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    if (activeSessionId) {
      window.localStorage.setItem(SESSION_STORAGE_KEY, activeSessionId);
    } else {
      window.localStorage.removeItem(SESSION_STORAGE_KEY);
    }
  }, [activeSessionId]);

  const handleSelectSession = useCallback((sessionId: string) => {
    setActiveSessionId(sessionId);
    setShouldAutoSelectSession(false);
  }, []);

  const handleStartNewChat = useCallback(() => {
    setActiveSessionId(null);
    setShouldAutoSelectSession(false);
  }, []);

  const handleDeleteSession = useCallback(
    async (sessionId: string) => {
      try {
        await deleteChatSession(sessionId);
        if (sessionId === activeSessionId) {
          setActiveSessionId(null);
          setShouldAutoSelectSession(true);
        }
        await refreshSessions();
      } catch (err) {
        if (err instanceof ApiError) {
          setSessionsError(err.message || 'Unable to delete chat session.');
        } else {
          setSessionsError('Unable to delete chat session.');
        }
      }
    },
    [activeSessionId, refreshSessions],
  );

  const handleRenameSession = useCallback(
    async (sessionId: string, title: string) => {
      await updateChatSession(sessionId, { title });
      await refreshSessions();
    },
    [refreshSessions],
  );

  const handleSessionChangeFromChat = useCallback(
    (sessionId: string | null) => {
      setActiveSessionId(sessionId);
      setShouldAutoSelectSession(sessionId === null);
      void refreshSessions();
    },
    [refreshSessions],
  );

  return (
    <div className="app-shell">
      <div className="app-layout">
        <Sidebar
          sessions={sessions}
          activeSessionId={activeSessionId}
          isLoading={sessionsLoading}
          error={sessionsError}
          onSelectSession={handleSelectSession}
          onStartNewChat={handleStartNewChat}
          onDeleteSession={handleDeleteSession}
          onRenameSession={handleRenameSession}
          onOpenIngestion={() => setIsIngestionOpen(true)}
          onOpenReferences={() => setIsReferencesOpen(true)}
          onRefreshSessions={() => void refreshSessions()}
        />
        <main className="main-panel">
          <Chat
            activeSessionId={activeSessionId}
            onSessionChange={handleSessionChangeFromChat}
            onRefreshSessions={() => void refreshSessions()}
          />
        </main>
      </div>

      {isIngestionOpen && (
        <div
          className="overlay"
          role="dialog"
          aria-modal="true"
          aria-label="Populate knowledge base"
          onClick={() => setIsIngestionOpen(false)}
        >
          <div
            className="overlay-panel"
            onClick={(event) => event.stopPropagation()}
            role="document"
          >
            <div className="overlay-toolbar">
              <button
                type="button"
                className="overlay-close"
                onClick={() => setIsIngestionOpen(false)}
              >
                Close
              </button>
            </div>
            <IngestionPanel />
          </div>
        </div>
      )}

      {isReferencesOpen && (
        <div
          className="overlay"
          role="dialog"
          aria-modal="true"
          aria-label="Manage knowledge base references"
          onClick={() => setIsReferencesOpen(false)}
        >
          <div
            className="overlay-panel"
            onClick={(event) => event.stopPropagation()}
            role="document"
          >
            <KnowledgeReferencesPanel onClose={() => setIsReferencesOpen(false)} />
          </div>
        </div>
      )}
    </div>
  );
};

export default App;
