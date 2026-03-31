import React, { useState } from 'react';
import { HopTrace } from '../components/HopTrace';
import { TrustBar } from '../components/TrustBar';
import { usePipeline } from '../hooks/usePipeline';
import { RetrievedDoc, WebSocketMessage } from '../types';

export function Pipeline() {
  const [query, setQuery] = useState('');
  const [attackEnabled, setAttackEnabled] = useState(false);
  const [defenceEnabled, setDefenceEnabled] = useState(true);
  const [selectedDoc, setSelectedDoc] = useState<RetrievedDoc | null>(null);
  const [expandedHop, setExpandedHop] = useState<number | null>(null);

  const {
    hops,
    blockedDocs,
    retrievedDocs,
    answer,
    stats,
    isConnected,
    isStreaming,
    error,
    currentHop,
    sendQuery,
    reset,
  } = usePipeline((msg: WebSocketMessage) => {
    // Handle live updates if needed
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    sendQuery({
      query: query.trim(),
      attack_enabled: attackEnabled,
      defence_enabled: defenceEnabled,
    });
  };

  // Group docs by hop
  const docsByHop = hops.reduce((acc, hop) => {
    acc[hop.hop] = retrievedDocs.filter(d => d.hop === hop.hop);
    return acc;
  }, {} as Record<number, RetrievedDoc[]>);

  return (
    <div className="flex-1 overflow-auto bg-slate-50">
      <div className="max-w-6xl mx-auto p-6 space-y-6">
        {/* Header */}
        <div className="space-y-2">
          <h1 className="text-4xl font-bold text-slate-900">🔄 Pipeline</h1>
          <p className="text-slate-600">
            Real-time RAG pipeline execution with defense mechanisms
          </p>
        </div>

        {/* Status Bar */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <span
              className={`w-3 h-3 rounded-full ${
                isConnected ? 'bg-green-500' : 'bg-red-500'
              }`}
            />
            <span className="text-sm font-medium">
              {isConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
          {isStreaming && (
            <span className="text-sm text-blue-600 font-medium">
              🔄 Streaming...
            </span>
          )}
        </div>

        {/* Query Input */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <label className="block text-sm font-medium text-slate-900">
              Query
            </label>
            <textarea
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Enter your question..."
              disabled={isStreaming}
              className="w-full px-4 py-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-slate-100 resize-none"
              rows={3}
            />
          </div>

          {/* Controls */}
          <div className="grid grid-cols-3 gap-4">
            <label className="flex items-center gap-3 p-3 border border-slate-300 rounded-lg cursor-pointer hover:bg-slate-50">
              <input
                type="checkbox"
                checked={attackEnabled}
                onChange={(e) => setAttackEnabled(e.target.checked)}
                disabled={isStreaming}
                className="w-5 h-5 text-orange-600"
              />
              <div>
                <p className="font-medium text-slate-900">Attack Enabled</p>
                <p className="text-xs text-slate-500">⚔️ Inject adversarial docs</p>
              </div>
            </label>

            <label className="flex items-center gap-3 p-3 border border-slate-300 rounded-lg cursor-pointer hover:bg-slate-50">
              <input
                type="checkbox"
                checked={defenceEnabled}
                onChange={(e) => setDefenceEnabled(e.target.checked)}
                disabled={isStreaming}
                className="w-5 h-5 text-green-600"
              />
              <div>
                <p className="font-medium text-slate-900">Defence Enabled</p>
                <p className="text-xs text-slate-500">🛡️ Trust filter active</p>
              </div>
            </label>

            <button
              type="submit"
              disabled={isStreaming || !isConnected || !query.trim()}
              className="px-4 py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:bg-slate-400 transition-colors"
            >
              {isStreaming ? '⟳ Running...' : '→ Execute'}
            </button>
          </div>
        </form>

        {/* Error */}
        {error && (
          <div className="p-4 bg-red-50 border border-red-300 rounded-lg text-red-800">
            ⚠️ {error}
          </div>
        )}

        {/* Main Content */}
        <div className="grid grid-cols-3 gap-6">
          {/* Left: Hop Trace */}
          <div className="col-span-1 bg-white p-6 rounded-lg shadow">
            <HopTrace hops={hops} currentHop={currentHop} maxHops={4} />
          </div>

          {/* Center: Documents */}
          <div className="col-span-2 space-y-4">
            {/* Passed Docs */}
            {hops.map((hop) => {
              const docs = docsByHop[hop.hop] || [];
              const passedDocs = docs.filter(d => d.passed);
              const blockedDocs_ = docs.filter(d => !d.passed);

              if (docs.length === 0) return null;

              return (
                <div key={hop.hop} className="space-y-2">
                  <button
                    onClick={() =>
                      setExpandedHop(expandedHop === hop.hop ? null : hop.hop)
                    }
                    className="w-full text-left p-4 bg-white rounded-lg border border-slate-200 hover:border-slate-300 transition-all"
                  >
                    <p className="font-semibold text-slate-900">
                      Hop {hop.hop}{' '}
                      <span className="text-xs text-slate-500">
                        ({passedDocs.length} passed, {blockedDocs_.length} blocked)
                      </span>
                    </p>
                    <p className="text-sm text-slate-600 mt-1 font-mono">
                      {hop.query}
                    </p>
                  </button>

                  {expandedHop === hop.hop && (
                    <div className="space-y-2 pl-4">
                      {/* Passed */}
                      {passedDocs.map((doc) => (
                        <div
                          key={doc.docId}
                          onClick={() => setSelectedDoc(doc)}
                          className="p-3 bg-green-50 border border-green-300 rounded cursor-pointer hover:shadow-md transition-all"
                        >
                          <div className="flex items-start justify-between">
                            <div className="flex-1">
                              <p className="font-medium text-slate-900">
                                {doc.docTitle}
                              </p>
                              <span className="inline-block mt-1 px-2 py-1 text-xs bg-green-200 text-green-800 rounded font-semibold">
                                ✓ PASSED
                              </span>
                            </div>
                            <span className="text-lg font-bold text-green-600">
                              {doc.trustScore.toFixed(0)}
                            </span>
                          </div>
                        </div>
                      ))}

                      {/* Blocked */}
                      {blockedDocs_.map((doc) => (
                        <div
                          key={doc.docId}
                          onClick={() => setSelectedDoc(doc)}
                          className="p-3 bg-red-50 border border-red-300 rounded cursor-pointer hover:shadow-md transition-all"
                        >
                          <div className="flex items-start justify-between">
                            <div className="flex-1">
                              <p className="font-medium text-slate-900">
                                {doc.docTitle}
                              </p>
                              <span className="inline-block mt-1 px-2 py-1 text-xs bg-red-200 text-red-800 rounded font-semibold">
                                ✗ BLOCKED
                              </span>
                            </div>
                            <span className="text-lg font-bold text-red-600">
                              {doc.trustScore.toFixed(0)}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Selected Doc Details */}
        {selectedDoc && (
          <div className="bg-white p-6 rounded-lg shadow border border-slate-200">
            <div className="flex justify-between items-start mb-4">
              <h3 className="text-lg font-bold text-slate-900">
                Document Details
              </h3>
              <button
                onClick={() => setSelectedDoc(null)}
                className="text-slate-500 hover:text-slate-700"
              >
                ✕
              </button>
            </div>
            <TrustBar score={{
              semantic_score: selectedDoc.signals.semantic || 0,
              source_score: selectedDoc.signals.source || 0,
              injection_score: selectedDoc.signals.injection || 0,
              hop_score: selectedDoc.signals.hop || 0,
              overall: selectedDoc.trustScore,
            }} />
          </div>
        )}

        {/* Answer */}
        {answer && (
          <div className="bg-white p-6 rounded-lg shadow border-l-4 border-blue-500">
            <h3 className="text-lg font-bold text-slate-900 mb-3">Final Answer</h3>
            <p className="text-slate-700 leading-relaxed">{answer}</p>
            {stats && (
              <div className="grid grid-cols-4 gap-4 mt-4 pt-4 border-t border-slate-200">
                <div>
                  <p className="text-xs text-slate-600">Hops</p>
                  <p className="text-xl font-bold text-slate-900">
                    {stats.totalHops}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-slate-600">Retrieved</p>
                  <p className="text-xl font-bold text-slate-900">
                    {stats.totalRetrieved}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-slate-600">Blocked</p>
                  <p className="text-xl font-bold text-red-600">
                    {stats.totalBlocked}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-slate-600">Time</p>
                  <p className="text-xl font-bold text-slate-900">
                    {stats.processingTimeMs}ms
                  </p>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Reset Button */}
        {(answer || error) && (
          <button
            onClick={reset}
            className="w-full px-4 py-2 bg-slate-200 text-slate-900 rounded-lg font-medium hover:bg-slate-300 transition-colors"
          >
            Clear Results
          </button>
        )}
      </div>
    </div>
  );
}
