import { TrustScore } from '../types';

interface TrustBarProps {
  score: TrustScore;
  threshold?: number;
  showLabel?: boolean;
  compact?: boolean;
}

interface Signal {
  name: string;
  value: number;
  color: string;
  description: string;
}

export function TrustBar({ 
  score, 
  threshold = 60, 
  showLabel = true,
  compact = false 
}: TrustBarProps) {
  const signals: Signal[] = [
    {
      name: 'Semantic',
      value: score.semantic_score,
      color: 'from-blue-400 to-blue-600',
      description: 'Content relevance',
    },
    {
      name: 'Source',
      value: score.source_score,
      color: 'from-green-400 to-green-600',
      description: 'Source credibility',
    },
    {
      name: 'Injection',
      value: score.injection_score,
      color: 'from-orange-400 to-orange-600',
      description: 'Injection risk',
    },
    {
      name: 'Hop',
      value: score.hop_score,
      color: 'from-purple-400 to-purple-600',
      description: 'Multi-hop drift',
    },
  ];

  const overall = score.overall;
  const isPassed = overall >= threshold;

  if (compact) {
    return (
      <div className="flex items-center gap-2">
        <div className="flex gap-1">
          {signals.map((signal) => (
            <div
              key={signal.name}
              className="h-2 w-8 rounded-full bg-slate-200"
              style={{
                background: `linear-gradient(to right, var(--color-${signal.name.toLowerCase()}))`,
                opacity: signal.value / 100,
              }}
              title={`${signal.name}: ${signal.value.toFixed(0)}`}
            />
          ))}
        </div>
        <span
          className={`text-sm font-bold ${
            isPassed ? 'text-green-600' : 'text-red-600'
          }`}
        >
          {overall.toFixed(0)}
        </span>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {/* Overall Score */}
      <div className="flex items-center justify-between">
        <h4 className="font-semibold text-slate-900">Trust Score</h4>
        <div className="flex items-center gap-2">
          <span
            className={`text-2xl font-bold ${
              isPassed ? 'text-green-600' : 'text-red-600'
            }`}
          >
            {overall.toFixed(0)}
          </span>
          <span className="text-xs text-slate-500">
            / 100
          </span>
          <span
            className={`ml-2 px-2 py-1 text-xs font-bold rounded-full ${
              isPassed
                ? 'bg-green-100 text-green-800'
                : 'bg-red-100 text-red-800'
            }`}
          >
            {isPassed ? '✓ PASS' : '✗ BLOCK'}
          </span>
        </div>
      </div>

      {/* Signal Bars */}
      <div className="space-y-3">
        {signals.map((signal) => {
          const percentage = (signal.value / 100) * 100;
          return (
            <div key={signal.name}>
              {showLabel && (
                <div className="flex justify-between mb-1">
                  <label className="text-sm font-medium text-slate-700">
                    {signal.name}
                  </label>
                  <span className="text-sm text-slate-600">
                    {signal.value.toFixed(0)}/100
                  </span>
                </div>
              )}
              <div className="w-full bg-slate-200 rounded-full h-3 overflow-hidden">
                <div
                  className={`h-full bg-gradient-to-r ${signal.color} transition-all duration-300`}
                  style={{ width: `${percentage}%` }}
                  title={signal.description}
                />
              </div>
            </div>
          );
        })}
      </div>

      {/* Threshold Line */}
      {showLabel && (
        <div className="mt-3 p-2 bg-slate-100 rounded text-xs text-slate-600">
          <p>
            Threshold: <span className="font-semibold">{threshold}/100</span>
          </p>
          <p className="text-slate-500 mt-1">
            {isPassed
              ? '✓ Document will be included in context'
              : '✗ Document will be blocked from context'}
          </p>
        </div>
      )}
    </div>
  );
}
