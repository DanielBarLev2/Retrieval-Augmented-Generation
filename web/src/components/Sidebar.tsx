import { useState } from 'react';
import type { FormEvent } from 'react';
import type { ChatSessionSummary } from '../api/client';

interface SidebarProps {
  sessions: ChatSessionSummary[];
  activeSessionId: string | null;
  isLoading: boolean;
  error: string | null;
  onSelectSession: (sessionId: string) => void;
  onStartNewChat: () => void;
  onDeleteSession: (sessionId: string) => Promise<void> | void;
  onRenameSession: (sessionId: string, title: string) => Promise<void>;
  onOpenIngestion: () => void;
  onOpenReferences: () => void;
  onRefreshSessions: () => void;
}

const formatTimestamp = (value: string) => {
  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
};

const Sidebar = ({
  sessions,
  activeSessionId,
  isLoading,
  error,
  onSelectSession,
  onStartNewChat,
  onDeleteSession,
  onRenameSession,
  onOpenIngestion,
  onOpenReferences,
  onRefreshSessions,
}: SidebarProps) => {
  const [editingSessionId, setEditingSessionId] = useState<string | null>(null);
  const [draftTitle, setDraftTitle] = useState('');
  const [renamingSessionId, setRenamingSessionId] = useState<string | null>(null);
  const [renameError, setRenameError] = useState<string | null>(null);

  const startEditing = (session: ChatSessionSummary) => {
    setEditingSessionId(session.session_id);
    setDraftTitle(session.title?.trim() || 'New Conversation');
    setRenameError(null);
  };

  const cancelEditing = () => {
    setEditingSessionId(null);
    setDraftTitle('');
    setRenamingSessionId(null);
    setRenameError(null);
  };

  const submitRename = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!editingSessionId) {
      return;
    }
    const trimmed = draftTitle.trim();
    if (!trimmed) {
      setRenameError('Title cannot be empty.');
      return;
    }

    setRenamingSessionId(editingSessionId);
    setRenameError(null);

    try {
      await onRenameSession(editingSessionId, trimmed);
      setEditingSessionId(null);
      setDraftTitle('');
    } catch (err) {
      if (err instanceof Error) {
        let message = err.message || 'Unable to rename chat.';
        try {
          const parsed = JSON.parse(err.message);
          if (parsed && typeof parsed === 'object' && 'detail' in parsed) {
            message = String(parsed.detail);
          }
        } catch {
          // ignore parsing issues
        }
        setRenameError(message);
      } else {
        setRenameError('Unable to rename chat.');
      }
    } finally {
      setRenamingSessionId(null);
    }
  };

  return (
    <aside className="sidebar" aria-label="Application navigation">
      <header className="sidebar-header">
        <div>
          <h1>RAG Control Center</h1>
          <p>Manage chat history and the knowledge base.</p>
        </div>
        <button type="button" className="sidebar-refresh" onClick={onRefreshSessions}>
          Refresh
        </button>
      </header>

      <section className="sidebar-section" aria-label="Chat history">
        <div className="sidebar-section-header">
          <h2>Chat History</h2>
          <button type="button" className="sidebar-action secondary" onClick={onStartNewChat}>
            New chat
          </button>
        </div>

        {isLoading && <div className="sidebar-muted">Loading sessions…</div>}
        {!isLoading && error && <div className="sidebar-error">{error}</div>}

        {!isLoading && !error && sessions.length === 0 && (
          <div className="sidebar-empty">No chats yet. Start a conversation to see it here.</div>
        )}

        {!isLoading && !error && sessions.length > 0 && (
          <ul className="history-list">
            {sessions.map((session) => {
              const isActive = session.session_id === activeSessionId;
              const title =
                session.title?.trim() || session.last_message_preview?.trim() || 'Untitled conversation';
              const subtitle =
                session.message_count === 1
                  ? '1 message'
                  : `${session.message_count} messages`;
              const isEditing = session.session_id === editingSessionId;

              return (
                <li key={session.session_id} className={`history-item${isActive ? ' active' : ''}`}>
                  {isEditing ? (
                    <form className="history-rename-form" onSubmit={submitRename}>
                      <label htmlFor={`rename-${session.session_id}`} className="sr-only">
                        Rename chat
                      </label>
                      <input
                        id={`rename-${session.session_id}`}
                        className="history-rename-input"
                        value={draftTitle}
                        onChange={(event) => {
                          setDraftTitle(event.target.value);
                          if (renameError) {
                            setRenameError(null);
                          }
                        }}
                        maxLength={120}
                        autoFocus
                        disabled={renamingSessionId === session.session_id}
                      />
                      <div className="history-rename-actions">
                        <button
                          type="submit"
                          disabled={renamingSessionId === session.session_id || !draftTitle.trim()}
                        >
                          {renamingSessionId === session.session_id ? 'Saving…' : 'Save'}
                        </button>
                        <button type="button" className="secondary" onClick={cancelEditing}>
                          Cancel
                        </button>
                      </div>
                      {renameError && <div className="history-rename-error">{renameError}</div>}
                    </form>
                  ) : (
                    <>
                      <button
                        type="button"
                        className="history-button"
                        onClick={() => onSelectSession(session.session_id)}
                        aria-current={isActive ? 'true' : undefined}
                      >
                        <span className="history-title" title={title}>
                          {title}
                        </span>
                        <span className="history-meta">
                          {subtitle} · {formatTimestamp(session.last_message_at)}
                        </span>
                      </button>
                      <div className="history-item-actions">
                        <button
                          type="button"
                          className="history-edit"
                          onClick={(event) => {
                            event.stopPropagation();
                            startEditing(session);
                          }}
                          aria-label={`Rename chat ${title}`}
                        >
                          ✎
                        </button>
                        <button
                          type="button"
                          className="history-delete"
                          onClick={(event) => {
                            event.stopPropagation();
                            onDeleteSession(session.session_id);
                          }}
                          aria-label={`Delete chat ${title}`}
                        >
                          ×
                        </button>
                      </div>
                    </>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </section>

      <section className="sidebar-section" aria-label="Knowledge base actions">
        <h2>Knowledge Base</h2>
        <div className="sidebar-actions">
          <button type="button" className="sidebar-action" onClick={onOpenIngestion}>
            Populate Knowledge Base
          </button>
          <button type="button" className="sidebar-action" onClick={onOpenReferences}>
            Manage References
          </button>
        </div>
      </section>
    </aside>
  );
};

export default Sidebar;


