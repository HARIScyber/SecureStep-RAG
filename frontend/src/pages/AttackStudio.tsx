import { useState } from 'react';
import { AttackInjectionRequest, AttackInjectionResponse } from '../types';

type AttackType = 'cascade' | 'drift' | 'hijack' | 'amplification';

interface AttackConfig {
  type: AttackType;
  topic: string;
  target: string;
  nDocs: number;
}

export function AttackStudio() {
  const [config, setConfig] = useState<AttackConfig>({
    type: 'cascade',
    topic: '',
    target: '',
    nDocs: 3,
  });
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AttackInjectionResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const attackDescriptions: Record<AttackType, string> = {
    cascade: 'Hijack hop-1 document to redirect to unrelated topic in hop-2',
    drift: 'Gradually shift query topic across multiple hops',
    hijack: 'Embed redirect instruction inside document',
    amplification: 'Place coordinated adversarial docs at hops 1-4 with escalating strength',
  };

  const attackExamples: Record<AttackType, { topic: string; target: string }> = {
    cascade: { topic: 'zero trust architecture', target: 'password reset' },
    drift: { topic: 'API security', target: 'cryptocurrency' },
    hijack: { topic: 'identity management', target: 'admin credentials' },
    amplification: { topic: 'security compliance', target: 'data exfiltration' },
  };

  const handleInject = async () => {
    if (!config.topic.trim() || !config.target.trim()) {
      setError('Please fill in all fields');
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const request: AttackInjectionRequest = {
        attack_type: config.type,
        topic: config.topic,
        target: config.target,
        n_docs: config.nDocs,
      };

      const response = await fetch('http://localhost:8000/api/attack/inject', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data: AttackInjectionResponse = await response.json();
      setResult(data);
    } catch (err) {
      setError(
        `Injection failed: ${err instanceof Error ? err.message : 'Unknown error'}`
      );
    } finally {
      setLoading(false);
    }
  };

  const setExample = (type: AttackType) => {
    const example = attackExamples[type];
    setConfig({
      ...config,
      type,
      topic: example.topic,
      target: example.target,
    });
  };

  return (
    <div className="flex-1 overflow-auto bg-slate-50">
      <div className="max-w-4xl mx-auto p-6 space-y-6">
        {/* Header */}
        <div className="space-y-2">
          <h1 className="text-4xl font-bold text-slate-900">⚔️ Attack Studio</h1>
          <p className="text-slate-600">
            Generate and inject adversarial documents to test defense mechanisms
          </p>
        </div>

        {/* Main Card */}
        <div className="bg-white rounded-lg shadow p-8 space-y-6">
          {/* Attack Type Selection */}
          <div className="space-y-3">
            <label className="block text-sm font-semibold text-slate-900">
              Attack Type
            </label>
            <div className="grid grid-cols-2 gap-3">
              {(Object.keys(attackDescriptions) as AttackType[]).map((type) => (
                <button
                  key={type}
                  onClick={() => setConfig({ ...config, type })}
                  className={`p-4 rounded-lg border-2 transition-all text-left ${
                    config.type === type
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-slate-200 bg-slate-50 hover:border-slate-300'
                  }`}
                >
                  <p className="font-semibold text-slate-900 capitalize">
                    {type === 'hijack' ? 'Query Hijack' : type.charAt(0).toUpperCase() + type.slice(1)}
                  </p>
                  <p className="text-xs text-slate-600 mt-1">
                    {attackDescriptions[type]}
                  </p>
                </button>
              ))}
            </div>
          </div>

          {/* Topic Input */}
          <div className="space-y-2">
            <label className="block text-sm font-semibold text-slate-900">
              Original Topic
            </label>
            <input
              type="text"
              value={config.topic}
              onChange={(e) => setConfig({ ...config, topic: e.target.value })}
              placeholder="e.g., Zero Trust Architecture"
              className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          {/* Target Input */}
          <div className="space-y-2">
            <label className="block text-sm font-semibold text-slate-900">
              Attack Target
            </label>
            <input
              type="text"
              value={config.target}
              onChange={(e) => setConfig({ ...config, target: e.target.value })}
              placeholder="e.g., Admin Credentials"
              className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          {/* Number of Docs */}
          <div className="space-y-2">
            <label className="block text-sm font-semibold text-slate-900">
              Number of Documents: <span className="text-blue-600">{config.nDocs}</span>
            </label>
            <input
              type="range"
              min="1"
              max="10"
              value={config.nDocs}
              onChange={(e) => setConfig({ ...config, nDocs: parseInt(e.target.value) })}
              className="w-full"
            />
          </div>

          {/* Examples */}
          <div className="p-4 bg-slate-50 rounded-lg space-y-2 border border-slate-200">
            <p className="text-sm font-semibold text-slate-900">Quick Examples:</p>
            <div className="flex flex-wrap gap-2">
              {(Object.keys(attackDescriptions) as AttackType[]).map((type) => (
                <button
                  key={type}
                  onClick={() => setExample(type)}
                  className="px-3 py-1 text-xs bg-white border border-slate-300 rounded hover:bg-slate-100 transition-colors"
                >
                  {type.capitalize?.() || type.charAt(0).toUpperCase() + type.slice(1)}
                </button>
              ))}
            </div>
          </div>

          {/* Error */}
          {error && (
            <div className="p-4 bg-red-50 border border-red-300 rounded-lg text-red-800">
              ⚠️ {error}
            </div>
          )}

          {/* Result */}
          {result && (
            <div
              className={`p-4 rounded-lg border-l-4 ${
                result.success
                  ? 'bg-green-50 border-green-500'
                  : 'bg-yellow-50 border-yellow-500'
              }`}
            >
              <p className="font-semibold text-slate-900">
                {result.success ? '✓ Injection Successful' : '⚠️ Injection Status'}
              </p>
              <p className="text-sm text-slate-700 mt-1">{result.message}</p>
              {result.docs_injected && (
                <p className="text-sm text-slate-600 mt-2">
                  Documents injected: <span className="font-bold">{result.docs_injected}</span>
                </p>
              )}
              {result.chain_id && (
                <p className="text-xs text-slate-500 mt-2 font-mono">
                  Chain ID: {result.chain_id}
                </p>
              )}
            </div>
          )}

          {/* Inject Button */}
          <button
            onClick={handleInject}
            disabled={loading}
            className="w-full px-6 py-3 bg-orange-600 text-white rounded-lg font-semibold hover:bg-orange-700 disabled:bg-slate-400 transition-colors flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <span className="animate-spin">⟳</span>
                Injecting...
              </>
            ) : (
              <>
                💉 Inject Attack
              </>
            )}
          </button>

          {/* Info */}
          <div className="p-4 bg-blue-50 border border-blue-300 rounded-lg text-sm text-blue-900">
            <p className="font-semibold mb-2">ℹ️ How to Use</p>
            <ol className="space-y-1 list-decimal list-inside">
              <li>Select an attack type from above</li>
              <li>Enter the original topic and attack target</li>
              <li>Click "Inject Attack" to poison the vector store</li>
              <li>These adversarial docs will appear in retrieval for related queries</li>
              <li>Test your defenses in the Pipeline page</li>
            </ol>
          </div>
        </div>

        {/* Attack Descriptions */}
        <div className="grid grid-cols-2 gap-4">
          {(Object.entries(attackDescriptions) as [AttackType, string][]).map(([type, desc]) => (
            <div key={type} className="bg-white p-4 rounded-lg border border-slate-200">
              <p className="font-semibold text-slate-900 capitalize mb-2">
                {type === 'hijack' ? '🎯 Query Hijack' : `🎯 ${type.charAt(0).toUpperCase() + type.slice(1)}`}
              </p>
              <p className="text-sm text-slate-600">{desc}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
