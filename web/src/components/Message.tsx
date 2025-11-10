import type { ChatSource } from '../api/client';

export type MessageRole = 'user' | 'assistant';

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  createdAt?: string;
  latencyMs?: number;
  sources?: ChatSource[];
}

interface MessageProps {
  message: ChatMessage;
}

const Message = ({ message }: MessageProps) => {
  const { role, content, sources, latencyMs, createdAt } = message;

  return (
    <div className={`message ${role}`}>
      <div className="message-bubble">
        <div className="message-content">{content}</div>
        {(createdAt || typeof latencyMs === 'number') && (
          <div className="message-meta">
            {createdAt && <span>{new Date(createdAt).toLocaleTimeString()}</span>}
            {typeof latencyMs === 'number' && (
              <span aria-label="Response latency">{Math.round(latencyMs)} ms</span>
            )}
          </div>
        )}
        {role === 'assistant' && sources && sources.length > 0 && (
          <div className="message-sources">
            <span className="sources-label">Sources</span>
            <ul>
              {sources.map((source, index) => {
                const title = source.title ?? `Source ${index + 1}`;
                return (
                  <li key={`${message.id}-source-${index}`}>
                    {source.url ? (
                      <a href={source.url} target="_blank" rel="noreferrer">
                        {title}
                      </a>
                    ) : (
                      <span>{title}</span>
                    )}
                  </li>
                );
              })}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
};

export default Message;

