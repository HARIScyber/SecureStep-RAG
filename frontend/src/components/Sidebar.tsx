import { Link, useLocation } from 'react-router-dom';

const routes = [
  { path: '/', name: 'Pipeline', icon: '🔄' },
  { path: '/attack-studio', name: 'Attack Studio', icon: '⚔️' },
  { path: '/trust-inspector', name: 'Trust Inspector', icon: '🔍' },
  { path: '/evaluation', name: 'Evaluation', icon: '📊' },
  { path: '/benchmark', name: 'Benchmark', icon: '📈' },
  { path: '/status', name: 'Status', icon: '✓' },
];

export function Sidebar() {
  const location = useLocation();

  return (
    <div className="w-64 bg-gradient-to-b from-slate-900 to-slate-800 text-white min-h-screen flex flex-col shadow-lg">
      {/* Header */}
      <div className="p-6 border-b border-slate-700">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          🛡️ SecureStep-RAG
        </h1>
        <p className="text-xs text-slate-400 mt-2">Real-time Attack Detection</p>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-2">
        {routes.map((route) => {
          const isActive = location.pathname === route.path;
          return (
            <Link
              key={route.path}
              to={route.path}
              className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-all ${
                isActive
                  ? 'bg-blue-600 text-white shadow-lg'
                  : 'text-slate-300 hover:bg-slate-700'
              }`}
            >
              <span className="text-xl">{route.icon}</span>
              <span className="font-medium">{route.name}</span>
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-slate-700 text-xs text-slate-400">
        <p>v1.0.0</p>
        <p>FastAPI Backend</p>
        <p className="mt-2">Status: 🟢 Connected</p>
      </div>
    </div>
  );
}
