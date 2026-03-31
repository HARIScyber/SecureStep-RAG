/**
 * PipelineStreamer.tsx - React component for real-time RAG pipeline streaming
 * 
 * Example usage in Dashboard:
 * 
 * import { PipelineStreamer } from './PipelineStreamer';
 * 
 * export function Dashboard() {
 *   return <PipelineStreamer />;
 * }
 */

import { useEffect, useRef, useState } from 'react';

interface HopInfo {
  hop: number;
  query: string;
  startTime: number;
}

interface BlockedDoc {
  docId: string;
  docTitle: string;
  reason: string;
  hop: number;
}

interface PipelineStats {
  totalHops: number;
  totalBlocked: number;
  totalRetrieved: number;
  processingTimeMs: number;
}

export function PipelineStreamer() {
  const [query, setQuery] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hops, setHops] = useState<HopInfo[]>([]);
  const [blockedDocs, setBlockedDocs] = useState<BlockedDoc[]>([]);
  const [answer, setAnswer] = useState('');
  const [stats, setStats] = useState<PipelineStats | null>(null);
  const [attackEnabled, setAttackEnabled] = useState(false);
  const [defenceEnabled, setDefenceEnabled] = useState(true);
  const [attackType, setAttackType] = useState<string | null>(null);
  
  const wsRef = useRef<WebSocket | null>(null);

  // Stream pipeline execution
  const streamPipeline = (userQuery: string) => {
    if (!userQuery.trim()) {
      setError('Please enter a query');
      return;
    }

    setIsStreaming(true);
    setError(null);
    setHops([]);
    setBlockedDocs([]);
    setAnswer('');
    setStats(null);

    // Connect to WebSocket
    const ws = new WebSocket('ws://localhost:8000/ws/pipeline');

    ws.onopen = () => {
      console.log('WebSocket connected');
      
      // Send initial message
      ws.send(JSON.stringify({
        query: userQuery,
        attack_enabled: attackEnabled,
        defence_enabled: defenceEnabled,
        attack_type: attackType,
      }));
    };

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        console.log('Received:', message.type, message);

        switch (message.type) {
          case 'status':
            console.log('Status:', message.message);
            break;

          case 'hop_start':
            setHops((prev) => [
              ...prev,
              {
                hop: message.hop,
                query: message.query,
                startTime: Date.now(),
              },
            ]);
            break;

          case 'doc_blocked':
            setBlockedDocs((prev) => [
              ...prev,
              {
                docId: message.doc_id,
                docTitle: message.doc_title,
                reason: message.reason,
                hop: message.hop,
              },
            ]);
            break;

          case 'answer':
            setAnswer(message.text);
            setStats({
              totalHops: message.total_hops,
              totalBlocked: message.total_blocked,
              totalRetrieved: message.total_retrieved,
              processingTimeMs: message.processing_time_ms,
            });
            break;

          case 'complete':
            console.log('Pipeline complete');
            setIsStreaming(false);
            break;

          case 'error':
            setError(message.message);
            setIsStreaming(false);
            break;
        }
      } catch (err) {
        console.error('Error parsing message:', err);
      }
    };

    ws.onerror = (event) => {
      const errorMsg = 'WebSocket error occurred';
      setError(errorMsg);
      console.error('WebSocket error:', event);
      setIsStreaming(false);
    };

    ws.onclose = () => {
      console.log('WebSocket disconnected');
      if (isStreaming) {
        setIsStreaming(false);
      }
    };

    wsRef.current = ws;
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  return (
    <div className="pipeline-streamer">
      <style>{`
        .pipeline-streamer {
          max-width: 1200px;
          margin: 0 auto;
          padding: 20px;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }

        .input-section {
          margin-bottom: 30px;
          padding: 20px;
          background: #f5f5f5;
          border-radius: 8px;
        }

        .query-input {
          display: flex;
          gap: 10px;
          margin-bottom: 15px;
        }

        .query-input input {
          flex: 1;
          padding: 12px;
          border: 1px solid #ddd;
          border-radius: 4px;
          font-size: 16px;
        }

        .query-input button {
          padding: 12px 24px;
          background: #0066cc;
          color: white;
          border: none;
          border-radius: 4px;
          cursor: pointer;
          font-weight: 600;
          disabled: opacity 0.5;
        }

        .query-input button:hover:not(:disabled) {
          background: #0052a3;
        }

        .options {
          display: flex;
          gap: 20px;
          flex-wrap: wrap;
        }

        .checkbox-group {
          display: flex;
          gap: 8px;
          align-items: center;
        }

        .checkbox-group input {
          cursor: pointer;
        }

        .attack-type-select {
          padding: 8px;
          border: 1px solid #ddd;
          border-radius: 4px;
        }

        .error {
          padding: 12px;
          background: #fee;
          color: #c33;
          border: 1px solid #fcc;
          border-radius: 4px;
          margin-bottom: 20px;
        }

        .streaming-section {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 20px;
        }

        .hops-panel {
          background: #f9f9f9;
          border: 1px solid #eee;
          border-radius: 8px;
          padding: 15px;
        }

        .hops-panel h3 {
          margin-top: 0;
          color: #333;
        }

        .hop-item {
          padding: 10px;
          background: white;
          border: 1px solid #e0e0e0;
          border-radius: 4px;
          margin-bottom: 10px;
          animation: slideIn 0.3s ease-out;
        }

        @keyframes slideIn {
          from {
            opacity: 0;
            transform: translateY(-10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        .hop-item strong {
          color: #0066cc;
        }

        .blocked-docs-panel {
          background: #fff5f5;
          border: 1px solid #ffcccc;
          border-radius: 8px;
          padding: 15px;
          max-height: 500px;
          overflow-y: auto;
        }

        .blocked-docs-panel h3 {
          margin-top: 0;
          color: #c33;
        }

        .blocked-doc {
          padding: 10px;
          background: #ffe6e6;
          border-left: 3px solid #c33;
          margin-bottom: 10px;
          border-radius: 2px;
        }

        .blocked-doc-title {
          font-weight: 600;
          color: #c33;
          margin-bottom: 4px;
        }

        .blocked-doc-reason {
          font-size: 12px;
          color: #666;
        }

        .answer-section {
          margin-top: 30px;
          padding: 20px;
          background: #f0f7ff;
          border: 1px solid #99ccff;
          border-radius: 8px;
        }

        .answer-section h3 {
          margin-top: 0;
          color: #0066cc;
        }

        .answer-text {
          line-height: 1.6;
          color: #333;
          margin: 15px 0;
        }

        .stats {
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          gap: 15px;
          margin-top: 15px;
        }

        .stat-item {
          background: white;
          padding: 12px;
          border-radius: 4px;
          text-align: center;
          border: 1px solid #ddd;
        }

        .stat-label {
          font-size: 12px;
          color: #666;
          margin-bottom: 4px;
        }

        .stat-value {
          font-size: 20px;
          font-weight: 600;
          color: #0066cc;
        }

        .loading {
          text-align: center;
          padding: 20px;
          color: #666;
        }

        .spinner {
          display: inline-block;
          width: 20px;
          height: 20px;
          border: 3px solid #f3f3f3;
          border-top: 3px solid #0066cc;
          border-radius: 50%;
          animation: spin 1s linear infinite;
        }

        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>

      <h1>SecureStep-RAG Pipeline Inspector</h1>

      {/* Input Section */}
      <div className="input-section">
        <div className="query-input">
          <input
            type="text"
            placeholder="Enter your query..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && streamPipeline(query)}
            disabled={isStreaming}
          />
          <button
            onClick={() => streamPipeline(query)}
            disabled={isStreaming}
          >
            {isStreaming ? 'Executing...' : 'Execute'}
          </button>
        </div>

        <div className="options">
          <div className="checkbox-group">
            <input
              type="checkbox"
              id="attackEnabled"
              checked={attackEnabled}
              onChange={(e) => setAttackEnabled(e.target.checked)}
              disabled={isStreaming}
            />
            <label htmlFor="attackEnabled">Attack Enabled</label>
          </div>

          <div className="checkbox-group">
            <input
              type="checkbox"
              id="defenceEnabled"
              checked={defenceEnabled}
              onChange={(e) => setDefenceEnabled(e.target.checked)}
              disabled={isStreaming}
            />
            <label htmlFor="defenceEnabled">Defence Enabled</label>
          </div>

          {attackEnabled && (
            <select
              className="attack-type-select"
              value={attackType || ''}
              onChange={(e) => setAttackType(e.target.value || null)}
              disabled={isStreaming}
            >
              <option value="">-- Attack Type --</option>
              <option value="cascade">Cascade</option>
              <option value="drift">Drift</option>
              <option value="hijack">Hijack</option>
              <option value="amplification">Amplification</option>
            </select>
          )}
        </div>
      </div>

      {/* Error Display */}
      {error && <div className="error">{error}</div>}

      {/* Streaming Results */}
      {isStreaming && (
        <div className="loading">
          <div className="spinner"></div>
          <p>Executing pipeline...</p>
        </div>
      )}

      {(hops.length > 0 || blockedDocs.length > 0) && (
        <div className="streaming-section">
          {/* Hops Panel */}
          <div className="hops-panel">
            <h3>Retrieval Hops ({hops.length})</h3>
            {hops.map((hop) => (
              <div key={hop.hop} className="hop-item">
                <strong>Hop {hop.hop}:</strong> {hop.query}
              </div>
            ))}
          </div>

          {/* Blocked Docs Panel */}
          <div className="blocked-docs-panel">
            <h3>Blocked Documents ({blockedDocs.length})</h3>
            {blockedDocs.length === 0 ? (
              <p style={{ color: '#666' }}>No documents blocked</p>
            ) : (
              blockedDocs.map((doc, idx) => (
                <div key={idx} className="blocked-doc">
                  <div className="blocked-doc-title">{doc.docTitle}</div>
                  <div className="blocked-doc-reason">{doc.reason}</div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Answer Section */}
      {answer && (
        <div className="answer-section">
          <h3>Generated Answer</h3>
          <div className="answer-text">{answer}</div>

          {stats && (
            <div className="stats">
              <div className="stat-item">
                <div className="stat-label">Total Hops</div>
                <div className="stat-value">{stats.totalHops}</div>
              </div>
              <div className="stat-item">
                <div className="stat-label">Documents Blocked</div>
                <div className="stat-value">{stats.totalBlocked}</div>
              </div>
              <div className="stat-item">
                <div className="stat-label">Documents Retrieved</div>
                <div className="stat-value">{stats.totalRetrieved}</div>
              </div>
              <div className="stat-item">
                <div className="stat-label">Processing Time</div>
                <div className="stat-value">{stats.processingTimeMs.toFixed(0)}ms</div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default PipelineStreamer;
