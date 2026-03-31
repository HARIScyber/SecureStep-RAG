import { useEffect, useState } from 'react';
import { TrustBar } from '../components/TrustBar';
import { BenchmarkDoc, BenchmarkResponse } from '../types';

export function TrustInspector() {
  const [threshold, setThreshold] = useState(60);
  const [docs, setDocs] = useState<BenchmarkDoc[]>([]);
  const [filteredDocs, setFilteredDocs] = useState<BenchmarkDoc[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedDoc, setSelectedDoc] = useState<BenchmarkDoc | null>(null);
  const [filter, setFilter] = useState<'all' | 'clean' | 'adversarial'>('all');

  // Fetch benchmark docs
  useEffect(() => {
    const fetchDocs = async () => {
      try {
        setLoading(true);
        const response = await fetch('http://localhost:8000/api/benchmark/docs?type=all');
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data: BenchmarkResponse = await response.json();
        setDocs(data.docs);
      } catch (err) {
        setError(
          `Failed to load documents: ${
            err instanceof Error ? err.message : 'Unknown error'
          }`
        );
      } finally {
        setLoading(false);
      }
    };

    fetchDocs();
  }, []);

  // Filter and sort docs
  useEffect(() => {
    let filtered = docs;

    if (filter === 'clean') {
      filtered = filtered.filter(d => !d.adversarial);
    } else if (filter === 'adversarial') {
      filtered = filtered.filter(d => d.adversarial);
    }

    // Sort by credibility descending
    filtered.sort((a, b) => b.credibility - a.credibility);
    setFilteredDocs(filtered);
  }, [docs, filter]);

  // Simulate trust scoring for display
  const getTrustScore = (doc: BenchmarkDoc) => ({
    semantic_score: doc.adversarial ? 40 + Math.random() * 30 : 70 + Math.random() * 25,
    source_score: doc.credibility * 100,
    injection_score: doc.adversarial ? 20 + Math.random() * 40 : 80 + Math.random() * 20,
    hop_score: 70,
    overall: doc.credibility * 100,
  });

  const docStats = {
    total: filteredDocs.length,
    wouldPass: filteredDocs.filter(d => getTrustScore(d).overall >= threshold).length,
    wouldBlock: filteredDocs.filter(d => getTrustScore(d).overall < threshold).length,
  };

  return (
    <div className="flex-1 overflow-auto bg-slate-50">
      <div className="max-w-6xl mx-auto p-6 space-y-6">
        {/* Header */}
        <div className="space-y-2">
          <h1 className="text-4xl font-bold text-slate-900">🔍 Trust Inspector</h1>
          <p className="text-slate-600">
            Inspect and tune the trust threshold to control document inclusion
          </p>
        </div>

        {/* Main Layout */}
        <div className="grid grid-cols-3 gap-6">
          {/* Left: Threshold Control */}
          <div className="col-span-1 space-y-4">
            {/* Threshold Slider */}
            <div className="bg-white p-6 rounded-lg shadow space-y-4">
              <div>
                <label className="block text-sm font-semibold text-slate-900 mb-2">
                  Trust Threshold: <span className="text-blue-600 text-lg">{threshold}</span>
                </label>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={threshold}
                  onChange={(e) => setThreshold(parseInt(e.target.value))}
                  className="w-full"
                />
                <div className="flex justify-between text-xs text-slate-500 mt-2">
                  <span>0</span>
                  <span>50</span>
                  <span>100</span>
                </div>
              </div>

              {/* Stats */}
              <div className="grid grid-cols-3 gap-2 pt-4 border-t border-slate-200">
                <div className="text-center">
                  <p className="text-xs text-slate-600">Total</p>
                  <p className="text-2xl font-bold text-slate-900">{docStats.total}</p>
                </div>
                <div className="text-center">
                  <p className="text-xs text-slate-600">Pass</p>
                  <p className="text-2xl font-bold text-green-600">
                    {docStats.wouldPass}
                  </p>
                </div>
                <div className="text-center">
                  <p className="text-xs text-slate-600">Block</p>
                  <p className="text-2xl font-bold text-red-600">{docStats.wouldBlock}</p>
                </div>
              </div>

              {/* Percentage */}
              <div className="bg-slate-100 p-3 rounded text-center">
                <p className="text-xs text-slate-600">Inclusion Rate</p>
                <p className="text-xl font-bold text-slate-900">
                  {((docStats.wouldPass / docStats.total) * 100).toFixed(1)}%
                </p>
              </div>
            </div>

            {/* Filter */}
            <div className="bg-white p-6 rounded-lg shadow space-y-3">
              <p className="text-sm font-semibold text-slate-900">Document Type</p>
              <div className="space-y-2">
                {(['all', 'clean', 'adversarial'] as const).map((type) => (
                  <label
                    key={type}
                    className="flex items-center gap-2 cursor-pointer"
                  >
                    <input
                      type="radio"
                      checked={filter === type}
                      onChange={() => setFilter(type)}
                      className="w-4 h-4"
                    />
                    <span className="text-sm capitalize">
                      {type === 'all' && '📋 All'}
                      {type === 'clean' && '✓ Clean'}
                      {type === 'adversarial' && '⚠️ Adversarial'}
                    </span>
                  </label>
                ))}
              </div>
            </div>

            {/* Info */}
            <div className="bg-blue-50 p-4 rounded-lg border border-blue-300 text-sm text-blue-900">
              <p className="font-semibold mb-2">💡 Tip</p>
              <p>
                Adjust the threshold to see how many documents would be included or
                blocked at different trust levels.
              </p>
            </div>
          </div>

          {/* Right: Document List */}
          <div className="col-span-2 space-y-4">
            {loading && (
              <div className="flex items-center justify-center h-96">
                <p className="text-slate-500">⟳ Loading documents...</p>
              </div>
            )}

            {error && (
              <div className="p-4 bg-red-50 border border-red-300 rounded-lg text-red-800">
                ⚠️ {error}
              </div>
            )}

            {!loading && !error && filteredDocs.length === 0 && (
              <div className="p-8 bg-slate-100 rounded-lg text-center text-slate-500">
                No documents found
              </div>
            )}

            {!loading &&
              !error &&
              filteredDocs.map((doc) => {
                const trustScore = getTrustScore(doc);
                const wouldPass = trustScore.overall >= threshold;

                return (
                  <button
                    key={doc.id}
                    onClick={() => setSelectedDoc(doc)}
                    className={`w-full text-left p-4 rounded-lg border-2 transition-all ${
                      selectedDoc?.id === doc.id
                        ? 'border-blue-500 bg-blue-50'
                        : wouldPass
                        ? 'border-green-300 bg-green-50 hover:border-green-400'
                        : 'border-red-300 bg-red-50 hover:border-red-400'
                    }`}
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex-1">
                        <p className="font-semibold text-slate-900">
                          {doc.id.substring(0, 40)}...
                        </p>
                        <p className="text-xs text-slate-600 mt-1 line-clamp-1">
                          {doc.content.substring(0, 60)}...
                        </p>
                      </div>
                      <span
                        className={`px-2 py-1 text-xs font-bold rounded-full ${
                          wouldPass
                            ? 'bg-green-200 text-green-800'
                            : 'bg-red-200 text-red-800'
                        }`}
                      >
                        {wouldPass ? '✓' : '✗'} {trustScore.overall.toFixed(0)}
                      </span>
                    </div>
                    <div className="flex items-center gap-4 text-xs">
                      <span className="text-slate-600">
                        {doc.type.charAt(0).toUpperCase() + doc.type.slice(1)}
                      </span>
                      {doc.adversarial && (
                        <span className="text-red-600 font-semibold">⚠️ Adversarial</span>
                      )}
                    </div>
                  </button>
                );
              })}
          </div>
        </div>

        {/* Selected Doc Details */}
        {selectedDoc && (
          <div className="bg-white p-6 rounded-lg shadow border border-slate-200">
            <div className="flex justify-between items-start mb-4">
              <div>
                <h3 className="text-lg font-bold text-slate-900">
                  Document: {selectedDoc.id}
                </h3>
                <div className="flex gap-3 mt-2">
                  <span className="px-2 py-1 bg-slate-100 text-slate-700 text-xs rounded-full">
                    {selectedDoc.type}
                  </span>
                  <span className={`px-2 py-1 text-xs rounded-full ${
                    selectedDoc.adversarial
                      ? 'bg-red-100 text-red-700'
                      : 'bg-green-100 text-green-700'
                  }`}>
                    {selectedDoc.adversarial ? '⚠️ Adversarial' : '✓ Clean'}
                  </span>
                </div>
              </div>
              <button
                onClick={() => setSelectedDoc(null)}
                className="text-slate-500 hover:text-slate-700"
              >
                ✕
              </button>
            </div>

            {/* Content */}
            <div className="mb-6 p-4 bg-slate-50 rounded-lg">
              <p className="text-slate-700">{selectedDoc.content}</p>
            </div>

            {/* Metadata */}
            <div className="grid grid-cols-4 gap-4 mb-6 pb-6 border-b border-slate-200">
              <div>
                <p className="text-xs text-slate-600">Source</p>
                <p className="font-semibold text-slate-900">{selectedDoc.source}</p>
              </div>
              <div>
                <p className="text-xs text-slate-600">Type</p>
                <p className="font-semibold text-slate-900">{selectedDoc.source_type}</p>
              </div>
              <div>
                <p className="text-xs text-slate-600">Topic</p>
                <p className="font-semibold text-slate-900">{selectedDoc.topic}</p>
              </div>
              <div>
                <p className="text-xs text-slate-600">Credibility</p>
                <p className="font-semibold text-slate-900">
                  {(selectedDoc.credibility * 100).toFixed(0)}
                </p>
              </div>
            </div>

            {/* Trust Score Display */}
            <TrustBar
              score={getTrustScore(selectedDoc)}
              threshold={threshold}
              showLabel={true}
            />
          </div>
        )}
      </div>
    </div>
  );
}
