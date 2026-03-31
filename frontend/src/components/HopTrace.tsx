import { HopInfo } from '../types';

interface HopTraceProps {
  hops: HopInfo[];
  currentHop: number;
  maxHops?: number;
}

export function HopTrace({ hops, currentHop, maxHops = 4 }: HopTraceProps) {
  if (hops.length === 0) {
    return (
      <div className="p-4 bg-slate-50 rounded-lg border border-slate-200 text-center text-slate-500">
        Waiting for pipeline execution...
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h3 className="font-semibold text-slate-900">Retrieval Hops</h3>
      
      <div className="flex items-center justify-between">
        {Array.from({ length: maxHops }).map((_, idx) => {
          const hop = hops.find(h => h.hop === idx + 1);
          const isActive = currentHop === idx + 1;
          const isCompleted = hop && hop.duration !== undefined;

          return (
            <div key={idx + 1} className="flex flex-col items-center flex-1">
              {/* Hop Node */}
              <div
                className={`w-12 h-12 rounded-full flex items-center justify-center font-bold text-lg transition-all ${
                  isCompleted
                    ? 'bg-green-500 text-white'
                    : isActive
                    ? 'bg-blue-500 text-white scale-110 shadow-lg'
                    : 'bg-slate-300 text-slate-700'
                }`}
              >
                {isCompleted && (
                  <span className="text-xl">✓</span>
                )}
                {isActive && !isCompleted && (
                  <span className="animate-spin">⟳</span>
                )}
                {!isActive && !isCompleted && (
                  <span>{idx + 1}</span>
                )}
              </div>

              {/* Info */}
              {hop && (
                <div className="mt-2 text-center text-xs max-w-32">
                  <p className="font-mono text-slate-600 truncate">
                    {hop.query.substring(0, 20)}...
                  </p>
                  {isCompleted && (
                    <div className="mt-1 space-y-0.5">
                      <p className="text-green-600 font-semibold">
                        +{hop.passedCount || 0} / -{hop.blockedCount || 0}
                      </p>
                      <p className="text-slate-500">
                        {hop.duration}ms
                      </p>
                    </div>
                  )}
                </div>
              )}

              {/* Connector */}
              {idx < maxHops - 1 && (
                <div
                  className={`h-1 flex-1 mt-4 ${
                    isCompleted ? 'bg-green-500' : 'bg-slate-300'
                  }`}
                  style={{
                    minWidth: '24px',
                  }}
                />
              )}
            </div>
          );
        })}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-2 mt-4">
        <div className="bg-blue-50 p-3 rounded-lg">
          <p className="text-xs text-slate-600">Completed Hops</p>
          <p className="text-2xl font-bold text-blue-600">
            {hops.filter(h => h.duration !== undefined).length}/{maxHops}
          </p>
        </div>
        <div className="bg-slate-50 p-3 rounded-lg">
          <p className="text-xs text-slate-600">Total Time</p>
          <p className="text-2xl font-bold text-slate-600">
            {hops.reduce((sum, h) => sum + (h.duration || 0), 0)}ms
          </p>
        </div>
      </div>
    </div>
  );
}
