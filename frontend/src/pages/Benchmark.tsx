import { useEffect, useState } from 'react';
import { BenchmarkDoc, BenchmarkResponse } from '../types';

type DocType = 'all' | 'clean' | 'cascade' | 'drift' | 'hijack' | 'amplification';

const docTypeColors: Record<string, string> = {
  clean: 'bg-green-100 text-green-800',
  cascade: 'bg-blue-100 text-blue-800',
  drift: 'bg-purple-100 text-purple-800',
  hijack: 'bg-orange-100 text-orange-800',
  amplification: 'bg-red-100 text-red-800',
};

const docTypeIcons: Record<string, string> = {
  clean: '✓',
  cascade: '⟳',
  drift: '↗',
  hijack: '🎯',
  amplification: '📈',
};

export function Benchmark() {
  const [docs, setDocs] = useState<BenchmarkDoc[]>([]);
  const [filteredDocs, setFilteredDocs] = useState<BenchmarkDoc[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedDoc, setSelectedDoc] = useState<BenchmarkDoc | null>(null);
  const [filter, setFilter] = useState<DocType>('all');
  const [searchQuery, setSearchQuery] = useState('');

  // Fetch documents
  useEffect(() => {
    const fetchDocs = async () => {
      try {
        setLoading(true);
        const response = await fetch(
          `http://localhost:8000/api/benchmark/docs?type=${filter === 'all' ? 'all' : filter}`
        );
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
  }, [filter]);

  // Filter and search
  useEffect(() => {
    let filtered = docs;

    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        d =>
          d.id.toLowerCase().includes(query) ||
          d.content.toLowerCase().includes(query) ||
          d.topic.toLowerCase().includes(query) ||
          d.source.toLowerCase().includes(query)
      );
    }

    setFilteredDocs(filtered);
  }, [docs, searchQuery]);

  // Stats
  const stats = {
    total: docs.length,
    clean: docs.filter(d => !d.adversarial).length,
    adversarial: docs.filter(d => d.adversarial).length,
  };

  return (
    <div className="flex-1 overflow-auto bg-slate-50">
      <div className="max-w-6xl mx-auto p-6 space-y-6">
        {/* Header */}
        <div className="space-y-2">
          <h1 className="text-4xl font-bold text-slate-900">📈 Benchmark</h1>
          <p className="text-slate-600">
            Browse the benchmark dataset with clean and adversarial documents
          </p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-white p-6 rounded-lg shadow border-l-4 border-slate-400">
            <p className="text-xs text-slate-600 uppercase">Total Documents</p>
            <p className="text-3xl font-bold text-slate-900 mt-2">{stats.total}</p>
          </div>
          <div className="bg-white p-6 rounded-lg shadow border-l-4 border-green-500">
            <p className="text-xs text-slate-600 uppercase">Clean Documents</p>
            <p className="text-3xl font-bold text-green-600 mt-2">{stats.clean}</p>
          </div>
          <div className="bg-white p-6 rounded-lg shadow border-l-4 border-red-500">
            <p className="text-xs text-slate-600 uppercase">Adversarial</p>
            <p className="text-3xl font-bold text-red-600 mt-2">
              {stats.adversarial}
            </p>
          </div>
        </div>

        {/* Filter and Search */}
        <div className="bg-white p-6 rounded-lg shadow space-y-4">
          {/* Type Filter */}
          <div>
            <label className="block text-sm font-semibold text-slate-900 mb-3">
              Document Type
            </label>
            <div className="flex flex-wrap gap-2">
              {(['all', 'clean', 'cascade', 'drift', 'hijack', 'amplification'] as const).map((type) => (
                <button
                  key={type}
                  onClick={() => {
                    setFilter(type);
                    setSearchQuery('');
                  }}
                  className={`px-4 py-2 rounded-full font-medium transition-all ${
                    filter === type
                      ? 'bg-blue-600 text-white'
                      : 'bg-slate-200 text-slate-700 hover:bg-slate-300'
                  }`}
                >
                  {type === 'all' && '📋 All'}
                  {type === 'clean' && '✓ Clean'}
                  {type === 'cascade' && '⟳ Cascade'}
                  {type === 'drift' && '↗ Drift'}
                  {type === 'hijack' && '🎯 Hijack'}
                  {type === 'amplification' && '📈 Amplification'}
                </button>
              ))}
            </div>
          </div>

          {/* Search */}
          <div>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by ID, content, topic, or source..."
              className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
        </div>

        {/* Content */}
        <div className="grid grid-cols-3 gap-6">
          {/* List */}
          <div className="col-span-2 space-y-2">
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
              <div className="p-12 bg-slate-100 rounded-lg text-center text-slate-500">
                No documents found
              </div>
            )}

            {!loading &&
              !error &&
              filteredDocs.map((doc) => (
                <button
                  key={doc.id}
                  onClick={() => setSelectedDoc(doc)}
                  className={`w-full text-left p-4 rounded-lg border-2 transition-all ${
                    selectedDoc?.id === doc.id
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-slate-200 bg-white hover:border-slate-300'
                  }`}
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex-1">
                      <p className="font-mono text-xs text-slate-500">
                        {doc.id}
                      </p>
                      <p className="font-semibold text-slate-900 mt-1 line-clamp-2">
                        {doc.content.substring(0, 80)}...
                      </p>
                    </div>
                    <span
                      className={`px-2 py-1 text-xs font-semibold rounded-full ml-2 whitespace-nowrap ${
                        docTypeColors[doc.type] || docTypeColors.clean
                      }`}
                    >
                      {docTypeIcons[doc.type]} {doc.type}
                    </span>
                  </div>
                  <div className="flex flex-wrap gap-2 text-xs">
                    <span className="text-slate-600">{doc.source}</span>
                    <span className="text-slate-600">•</span>
                    <span className="text-slate-600">{doc.topic}</span>
                    {doc.adversarial && (
                      <>
                        <span className="text-slate-600">•</span>
                        <span className="text-red-600 font-semibold">⚠️ Adversarial</span>
                      </>
                    )}
                  </div>
                </button>
              ))}
          </div>

          {/* Details */}
          <div className="col-span-1">
            {selectedDoc ? (
              <div className="bg-white p-6 rounded-lg shadow sticky top-6 space-y-4">
                <div className="flex justify-between items-start mb-4">
                  <h3 className="font-bold text-slate-900">Details</h3>
                  <button
                    onClick={() => setSelectedDoc(null)}
                    className="text-slate-500 hover:text-slate-700"
                  >
                    ✕
                  </button>
                </div>

                {/* Type Badge */}
                <div>
                  <p className="text-xs text-slate-600 uppercase mb-2">Type</p>
                  <span
                    className={`inline-block px-3 py-1 text-xs font-bold rounded-full ${
                      docTypeColors[selectedDoc.type] || docTypeColors.clean
                    }`}
                  >
                    {docTypeIcons[selectedDoc.type]} {selectedDoc.type}
                  </span>
                </div>

                {/* Metadata */}
                <div className="space-y-3 border-t border-slate-200 pt-4">
                  <div>
                    <p className="text-xs text-slate-600 uppercase">Adversarial</p>
                    <p className="font-semibold text-slate-900">
                      {selectedDoc.adversarial ? '⚠️ Yes' : '✓ No'}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-600 uppercase">Source</p>
                    <p className="font-semibold text-slate-900">
                      {selectedDoc.source}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-600 uppercase">Source Type</p>
                    <p className="font-semibold text-slate-900">
                      {selectedDoc.source_type}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-600 uppercase">Topic</p>
                    <p className="font-semibold text-slate-900">
                      {selectedDoc.topic}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-600 uppercase">Credibility</p>
                    <div className="flex items-center gap-2 mt-1">
                      <div className="flex-1 bg-slate-200 rounded-full h-2">
                        <div
                          className="bg-blue-600 h-2 rounded-full"
                          style={{ width: `${selectedDoc.credibility * 100}%` }}
                        />
                      </div>
                      <span className="font-semibold text-slate-900 text-sm">
                        {(selectedDoc.credibility * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>
                </div>

                {/* Content Preview */}
                <div className="border-t border-slate-200 pt-4">
                  <p className="text-xs text-slate-600 uppercase mb-2">Content</p>
                  <div className="bg-slate-50 p-3 rounded text-sm text-slate-700 max-h-48 overflow-y-auto">
                    {selectedDoc.content}
                  </div>
                </div>
              </div>
            ) : (
              <div className="bg-slate-100 p-6 rounded-lg text-center text-slate-500">
                Select a document to view details
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
