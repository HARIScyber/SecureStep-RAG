import { useEffect, useState } from 'react';
import {
    Bar,
    BarChart,
    CartesianGrid,
    Line,
    LineChart,
    ResponsiveContainer,
    Tooltip,
    XAxis,
    YAxis
} from 'recharts';
import { EvalResult, EvalResultsResponse } from '../types';

export function Evaluation() {
  const [results, setResults] = useState<EvalResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchResults = async () => {
      try {
        setLoading(true);
        const response = await fetch('http://localhost:8000/api/eval/results');
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data: EvalResultsResponse = await response.json();
        setResults(data.conditions);
      } catch (err) {
        setError(
          `Failed to load results: ${err instanceof Error ? err.message : 'Unknown error'}`
        );
      } finally {
        setLoading(false);
      }
    };

    fetchResults();
  }, []);

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center bg-slate-50">
        <p className="text-slate-500">⟳ Loading evaluation results...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex-1 overflow-auto bg-slate-50 p-6">
        <div className="max-w-4xl mx-auto">
          <p className="p-4 bg-red-50 border border-red-300 rounded-lg text-red-800">
            ⚠️ {error}
          </p>
        </div>
      </div>
    );
  }

  // Prepare chart data
  const chartData = results.map(r => ({
    condition: r.condition.replace(/_/g, ' '),
    faithfulness: parseFloat(r.faithfulness_score.toFixed(2)),
    attackSuccess: r.attack_success_rate,
    blocked: r.blocked_count,
    latency: r.avg_latency_ms,
  }));

  return (
    <div className="flex-1 overflow-auto bg-slate-50">
      <div className="max-w-6xl mx-auto p-6 space-y-6">
        {/* Header */}
        <div className="space-y-2">
          <h1 className="text-4xl font-bold text-slate-900">📊 Evaluation</h1>
          <p className="text-slate-600">
            Ablation study results showing effectiveness of defense mechanisms
          </p>
        </div>

        {/* Summary Stats */}
        <div className="grid grid-cols-4 gap-4">
          <div className="bg-white p-6 rounded-lg shadow">
            <p className="text-xs text-slate-600 uppercase">Conditions</p>
            <p className="text-3xl font-bold text-slate-900 mt-1">{results.length}</p>
          </div>
          {results.length > 0 && (
            <>
              <div className="bg-white p-6 rounded-lg shadow">
                <p className="text-xs text-slate-600 uppercase">Avg Faithfulness</p>
                <p className="text-3xl font-bold text-blue-600 mt-1">
                  {(results.reduce((sum, r) => sum + r.faithfulness_score, 0) / results.length).toFixed(2)}
                </p>
              </div>
              <div className="bg-white p-6 rounded-lg shadow">
                <p className="text-xs text-slate-600 uppercase">Avg Attack Success</p>
                <p className="text-3xl font-bold text-red-600 mt-1">
                  {(results.reduce((sum, r) => sum + r.attack_success_rate, 0) / results.length).toFixed(1)}%
                </p>
              </div>
              <div className="bg-white p-6 rounded-lg shadow">
                <p className="text-xs text-slate-600 uppercase">Total Blocked</p>
                <p className="text-3xl font-bold text-orange-600 mt-1">
                  {results.reduce((sum, r) => sum + r.blocked_count, 0)}
                </p>
              </div>
            </>
          )}
        </div>

        {/* Charts */}
        <div className="grid grid-cols-2 gap-6">
          {/* Faithfulness Chart */}
          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="text-lg font-semibold text-slate-900 mb-4">
              RAGAS Faithfulness Score
            </h3>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="condition"
                  angle={-45}
                  textAnchor="end"
                  height={100}
                  interval={0}
                  tick={{ fontSize: 12 }}
                />
                <YAxis domain={[0, 1]} />
                <Tooltip
                  formatter={(value) =>
                    typeof value === 'number' ? value.toFixed(3) : value
                  }
                />
                <Bar dataKey="faithfulness" fill="#3b82f6" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Attack Success Rate */}
          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="text-lg font-semibold text-slate-900 mb-4">
              Attack Success Rate
            </h3>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="condition"
                  angle={-45}
                  textAnchor="end"
                  height={100}
                  interval={0}
                  tick={{ fontSize: 12 }}
                />
                <YAxis domain={[0, 100]} />
                <Tooltip formatter={(value) => `${value}%`} />
                <Bar dataKey="attackSuccess" fill="#ef4444" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Blocked Documents */}
          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="text-lg font-semibold text-slate-900 mb-4">
              Documents Blocked
            </h3>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="condition"
                  angle={-45}
                  textAnchor="end"
                  height={100}
                  interval={0}
                  tick={{ fontSize: 12 }}
                />
                <YAxis />
                <Tooltip />
                <Bar dataKey="blocked" fill="#f97316" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Latency */}
          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="text-lg font-semibold text-slate-900 mb-4">
              Average Latency (ms)
            </h3>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="condition"
                  angle={-45}
                  textAnchor="end"
                  height={100}
                  interval={0}
                  tick={{ fontSize: 12 }}
                />
                <YAxis />
                <Tooltip formatter={(value) => `${value}ms`} />
                <Line
                  type="monotone"
                  dataKey="latency"
                  stroke="#8b5cf6"
                  strokeWidth={2}
                  dot={{ fill: '#8b5cf6', r: 4 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Results Table */}
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="p-6 border-b border-slate-200">
            <h3 className="text-lg font-semibold text-slate-900">
              Detailed Results
            </h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 border-b border-slate-200">
                <tr>
                  <th className="px-6 py-3 text-left font-semibold text-slate-900">
                    Condition
                  </th>
                  <th className="px-6 py-3 text-left font-semibold text-slate-900">
                    Faithfulness
                  </th>
                  <th className="px-6 py-3 text-left font-semibold text-slate-900">
                    Attack Success
                  </th>
                  <th className="px-6 py-3 text-left font-semibold text-slate-900">
                    Blocked Docs
                  </th>
                  <th className="px-6 py-3 text-left font-semibold text-slate-900">
                    Avg Latency
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {results.map((result) => (
                  <tr key={result.condition} className="hover:bg-slate-50">
                    <td className="px-6 py-4 font-medium text-slate-900">
                      {result.condition.replace(/_/g, ' ')}
                    </td>
                    <td className="px-6 py-4">
                      <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-xs font-semibold">
                        {result.faithfulness_score.toFixed(3)}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
                        result.attack_success_rate > 50
                          ? 'bg-red-100 text-red-800'
                          : 'bg-green-100 text-green-800'
                      }`}>
                        {result.attack_success_rate.toFixed(1)}%
                      </span>
                    </td>
                    <td className="px-6 py-4 text-slate-700">
                      {result.blocked_count}
                    </td>
                    <td className="px-6 py-4 text-slate-700">
                      {result.avg_latency_ms.toFixed(1)}ms
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* W&B Embed */}
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-semibold text-slate-900 mb-4">
            📈 Weights & Biases Report
          </h3>
          <p className="text-slate-600 mb-4">
            To view detailed results and artifacts in Weights & Biases, visit:
          </p>
          <a
            href="https://wandb.ai"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 px-4 py-2 bg-yellow-100 text-yellow-800 rounded-lg font-semibold hover:bg-yellow-200 transition-colors"
          >
            🔗 Open Weights & Biases
          </a>
        </div>
      </div>
    </div>
  );
}
