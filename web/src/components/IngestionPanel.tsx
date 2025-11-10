import { useState } from 'react';
import type { FormEvent } from 'react';
import {
  ApiError,
  ingestWikipediaTopics,
  ingestWikipediaUrls,
  type WikipediaIngestResponse,
} from '../api/client';

interface IngestionFeedback extends WikipediaIngestResponse {
  mode: 'topics' | 'urls';
}

const parseMultilineInput = (value: string) =>
  value
    .split('\n')
    .map((entry) => entry.trim())
    .filter(Boolean);

const IngestionPanel = () => {
  const [topicsInput, setTopicsInput] = useState('');
  const [urlsInput, setUrlsInput] = useState('');
  const [feedback, setFeedback] = useState<IngestionFeedback | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleTopicsSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const topics = parseMultilineInput(topicsInput);
    if (!topics.length) {
      setError('Enter at least one topic to search on Wikipedia.');
      return;
    }
    await submitIngestion(async () => {
      const response = await ingestWikipediaTopics({ topics });
      setFeedback({ mode: 'topics', ...response });
      setTopicsInput('');
    });
  };

  const handleUrlsSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const urls = parseMultilineInput(urlsInput);
    if (!urls.length) {
      setError('Enter at least one Wikipedia URL.');
      return;
    }
    await submitIngestion(async () => {
      const response = await ingestWikipediaUrls({ urls });
      setFeedback({ mode: 'urls', ...response });
      setUrlsInput('');
    });
  };

  const submitIngestion = async (action: () => Promise<void>) => {
    setError(null);
    setFeedback(null);
    setIsSubmitting(true);
    try {
      await action();
    } catch (err) {
      if (err instanceof ApiError) {
        let message = err.message;
        try {
          const parsed = JSON.parse(err.message);
          if (parsed && typeof parsed === 'object' && 'detail' in parsed) {
            message = String(parsed.detail);
          }
        } catch {
          // ignore JSON parsing issues
        }
        setError(message || 'Ingestion failed. Check backend logs for details.');
      } else {
        setError('Unexpected error while ingesting content.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <section className="ingestion-panel" aria-label="Wikipedia ingestion controls">
      <header className="ingestion-header">
        <h2>Populate Knowledge Base</h2>
        <p>
          Pull fresh content into Qdrant by searching topics or pasting specific Wikipedia links.
          These chunks will be used as cited sources in chat responses.
        </p>
      </header>

      <div className="ingestion-grid">
        <form className="ingestion-card" onSubmit={handleTopicsSubmit}>
          <h3>Search by Topic</h3>
          <p className="ingestion-muted">
            Enter one topic per line. The backend fetches up to five relevant pages for each.
          </p>
          <label htmlFor="ingest-topics" className="sr-only">
            Topics
          </label>
          <textarea
            id="ingest-topics"
            placeholder={'Example:\nretrieval-augmented generation\nvector database'}
            value={topicsInput}
            onChange={(event) => setTopicsInput(event.target.value)}
            rows={5}
            disabled={isSubmitting}
          />
          <button type="submit" disabled={isSubmitting}>
            {isSubmitting ? 'Ingesting…' : 'Ingest Topics'}
          </button>
        </form>

        <form className="ingestion-card" onSubmit={handleUrlsSubmit}>
          <h3>Ingest Specific Articles</h3>
          <p className="ingestion-muted">
            Paste full Wikipedia URLs to embed exact articles. Perfect for curated reading lists.
          </p>
          <label htmlFor="ingest-urls" className="sr-only">
            Wikipedia URLs
          </label>
          <textarea
            id="ingest-urls"
            placeholder={'Example:\nhttps://en.wikipedia.org/wiki/Retrieval-augmented_generation'}
            value={urlsInput}
            onChange={(event) => setUrlsInput(event.target.value)}
            rows={5}
            disabled={isSubmitting}
          />
          <button type="submit" disabled={isSubmitting}>
            {isSubmitting ? 'Ingesting…' : 'Ingest URLs'}
          </button>
        </form>
      </div>

      {feedback && (
        <div className="ingestion-feedback" role="status">
          <strong>
            {feedback.mode === 'topics' ? 'Topic ingestion complete.' : 'URL ingestion complete.'}
          </strong>
          <span>
            Processed {feedback.processed_pages} page{feedback.processed_pages === 1 ? '' : 's'} and
            embedded {feedback.embedded_chunks} chunk
            {feedback.embedded_chunks === 1 ? '' : 's'} (skipped {feedback.skipped_pages}).
          </span>
        </div>
      )}

      {error && (
        <div className="ingestion-error" role="alert">
          {error}
        </div>
      )}
    </section>
  );
};

export default IngestionPanel;

