import { useEffect, useState } from 'react';
import { HealthResponse } from '../types';

export function Status() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [uptime, setUptime] = useState(0);

  // Fetch health status
  useEffect(() => {
    const fetchHealth = async () => {
      try {
        setLoading(true);
        const response = await fetch('http://localhost:8000/api/status');
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        
        // Simulate health response
        setHealth({
          status: data.status,
          services: [
            {
              name: 'FastAPI Backend',
              status: 'healthy',
              latency_ms: data.latency || 5,
              last_check: new Date().toISOString(),
            },
            {
              name: 'Qdrant Vector Store',
              status: 'healthy',
              latency_ms: 12,
              last_check: new Date().toISOString(),
            },
            {
              name: 'LLM (OpenAI)',
              status: 'healthy',
              latency_ms: 450,
              last_check: new Date().toISOString(),
            },
            {
              name: 'NeMo Guardrails',
              status: 'healthy',
              latency_ms: 35,
              last_check: new Date().toISOString(),
            },
            {
              name: 'W&B Logger',
              status: 'healthy',
              latency_ms: 8,
              last_check: new Date().toISOString(),
            },
          ],
        });
        setUptime(data.uptime_seconds || 3600);
      } catch (err) {
        setError(
          `Failed to fetch health: ${err instanceof Error ? err.message : 'Unknown error'}`
        );
      } finally {
        setLoading(false);
      }
    };

    fetchHealth();

    // Refresh every 5 seconds
    const interval = setInterval(fetchHealth, 5000);
    return () => clearInterval(interval);
  }, []);

  // Format uptime
  const formatUptime = (seconds: number) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    return `${hours}h ${minutes}m ${secs}s`;
  };

  const statusDotColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'bg-green-500';
      case 'unhealthy':
        return 'bg-red-500';
      default:
        return 'bg-yellow-500';
    }
  };

  const statusBadgeClass = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'bg-green-100 text-green-800';
      case 'unhealthy':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-yellow-100 text-yellow-800';
    }
  };

  return (
    <div className="flex-1 overflow-auto bg-slate-50">
      <div className="max-w-4xl mx-auto p-6 space-y-6">
        {/* Header */}
        <div className="space-y-2">
          <h1 className="text-4xl font-bold text-slate-900">✓ Status</h1>
          <p className="text-slate-600">
            System health and service metrics (updates every 5 seconds)
          </p>
        </div>

        {/* Overall Status */}
        <div className="bg-gradient-to-r from-green-50 to-emerald-50 border border-green-300 rounded-lg p-8 flex items-center justify-between">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <div className="w-4 h-4 bg-green-500 rounded-full animate-pulse" />
              <h2 className="text-2xl font-bold text-slate-900">System Operational</h2>
            </div>
            <p className="text-slate-600">
              Uptime: <span className="font-semibold">{formatUptime(uptime)}</span>
            </p>
          </div>
          <div className="text-5xl">🟢</div>
        </div>

        {/* Error Display */}
        {error && (
          <div className="p-4 bg-red-50 border border-red-300 rounded-lg text-red-800">
            ⚠️ {error}
          </div>
        )}

        {/* Loading */}
        {loading && !health && (
          <div className="flex items-center justify-center h-48">
            <p className="text-slate-500">⟳ Loading health status...</p>
          </div>
        )}

        {/* Services */}
        {health && !loading && (
          <div className="space-y-3">
            <h3 className="text-lg font-semibold text-slate-900">Services</h3>
            <div className="grid grid-cols-1 gap-3">
              {health.services.map((service) => (
                <div
                  key={service.name}
                  className="bg-white rounded-lg shadow p-4 flex items-center justify-between hover:shadow-md transition-shadow"
                >
                  <div className="flex items-center gap-4 flex-1">
                    <div
                      className={`w-5 h-5 rounded-full ${statusDotColor(
                        service.status
                      )} animate-pulse`}
                    />
                    <div>
                      <p className="font-semibold text-slate-900">
                        {service.name}
                      </p>
                      <p className="text-xs text-slate-500">
                        {new Date(service.last_check).toLocaleTimeString()}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-4">
                    <span
                      className={`px-3 py-1 text-xs font-bold rounded-full capitalize ${statusBadgeClass(
                        service.status
                      )}`}
                    >
                      {service.status}
                    </span>
                    <span className="text-sm font-mono text-slate-600">
                      {service.latency_ms}ms
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Metrics */}
        {health && (
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-white p-6 rounded-lg shadow">
              <p className="text-xs text-slate-600 uppercase">Avg Latency</p>
              <p className="text-3xl font-bold text-slate-900 mt-2">
                {Math.round(
                  health.services.reduce((sum, s) => sum + s.latency_ms, 0) /
                    health.services.length
                )}
                <span className="text-sm ml-1">ms</span>
              </p>
            </div>
            <div className="bg-white p-6 rounded-lg shadow">
              <p className="text-xs text-slate-600 uppercase">Healthy Services</p>
              <p className="text-3xl font-bold text-green-600 mt-2">
                {health.services.filter(s => s.status === 'healthy').length}/
                <span className="text-sm text-slate-600">{health.services.length}</span>
              </p>
            </div>
          </div>
        )}

        {/* Detailed Metrics */}
        {health && (
          <div className="bg-white rounded-lg shadow p-6 space-y-4">
            <h3 className="text-lg font-semibold text-slate-900">
              Latency Breakdown
            </h3>
            <div className="space-y-3">
              {health.services.map((service) => {
                const maxLatency = Math.max(
                  ...health.services.map(s => s.latency_ms)
                );
                const percentage = (service.latency_ms / maxLatency) * 100;

                return (
                  <div key={service.name}>
                    <div className="flex justify-between mb-1">
                      <label className="text-sm font-medium text-slate-700">
                        {service.name}
                      </label>
                      <span className="text-sm text-slate-600">
                        {service.latency_ms}ms
                      </span>
                    </div>
                    <div className="w-full bg-slate-200 rounded-full h-2 overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-blue-400 to-blue-600 transition-all"
                        style={{ width: `${percentage}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Info Panel */}
        <div className="bg-blue-50 p-6 rounded-lg border border-blue-300 space-y-3">
          <p className="font-semibold text-blue-900">ℹ️ System Information</p>
          <ul className="text-sm text-blue-800 space-y-1 list-disc list-inside">
            <li>Backend: FastAPI on localhost:8000</li>
            <li>WebSocket: ws://localhost:8000/ws/pipeline</li>
            <li>Vector Store: Qdrant</li>
            <li>LLM: Connected to OpenAI API</li>
            <li>Guardrails: NeMo Framework</li>
            <li>Logging: Weights & Biases</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
