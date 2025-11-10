import { useCallback, useEffect, useState } from 'react';

import { ApiError, deleteKnowledgeReference, listKnowledgeReferences } from '../api/client';
import type { KnowledgeReference } from '../api/client';

interface KnowledgeReferencesPanelProps {
  onClose: () => void;
}

const KnowledgeReferencesPanel = ({ onClose }: KnowledgeReferencesPanelProps) => {
  const [references, setReferences] = useState<KnowledgeReference[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<number | null>(null);

  const fetchReferences = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await listKnowledgeReferences();
      setReferences(data);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message || 'Unable to load references.');
      } else {
        setError('Unable to load references.');
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchReferences();
  }, [fetchReferences]);

  const handleDelete = async (pageId: number) => {
    setDeleting(pageId);
    setError(null);
    try {
      await deleteKnowledgeReference(pageId);
      await fetchReferences();
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message || 'Failed to delete reference.');
      } else {
        setError('Failed to delete reference.');
      }
    } finally {
      setDeleting(null);
    }
  };

  return (
    <section className="overlay-panel-content" aria-label="Knowledge base references">
      <header className="overlay-panel-header">
        <div>
          <h2>Knowledge Base References</h2>
          <p>Review ingested articles and remove ones you no longer need.</p>
        </div>
        <div className="overlay-panel-controls">
          <button type="button" className="sidebar-refresh" onClick={() => void fetchReferences()}>
            Refresh
          </button>
          <button type="button" className="overlay-close" onClick={onClose}>
            Close
          </button>
        </div>
      </header>

      {isLoading && <div className="overlay-muted">Loading references…</div>}
      {!isLoading && error && <div className="overlay-error">{error}</div>}

      {!isLoading && !error && references.length === 0 && (
        <div className="overlay-muted">No references found. Ingest content to populate the knowledge base.</div>
      )}

      {!isLoading && !error && references.length > 0 && (
        <ul className="references-list">
          {references.map((reference) => (
            <li key={reference.page_id} className="reference-item">
              <div className="reference-details">
                <h3>{reference.title ?? 'Untitled article'}</h3>
                <p>
                  {reference.topic && <span className="reference-topic">{reference.topic}</span>}
                  {reference.url && (
                    <a href={reference.url} target="_blank" rel="noreferrer">
                      View source
                    </a>
                  )}
                </p>
                <span className="reference-meta">
                  {reference.chunk_count} chunk{reference.chunk_count === 1 ? '' : 's'}
                </span>
              </div>
              <button
                type="button"
                className="reference-delete"
                disabled={deleting === reference.page_id}
                onClick={() => void handleDelete(reference.page_id)}
              >
                {deleting === reference.page_id ? 'Removing…' : 'Remove'}
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
};

export default KnowledgeReferencesPanel;


