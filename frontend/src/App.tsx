import { Route, BrowserRouter as Router, Routes } from 'react-router-dom';
import { Sidebar } from './components/Sidebar';
import { AttackStudio } from './pages/AttackStudio';
import { Benchmark } from './pages/Benchmark';
import { Evaluation } from './pages/Evaluation';
import { Pipeline } from './pages/Pipeline';
import { Status } from './pages/Status';
import { TrustInspector } from './pages/TrustInspector';

export function App() {
  return (
    <Router>
      <div className="flex h-screen bg-slate-100">
        {/* Sidebar */}
        <Sidebar />

        {/* Main Content */}
        <Routes>
          <Route path="/" element={<Pipeline />} />
          <Route path="/attack-studio" element={<AttackStudio />} />
          <Route path="/trust-inspector" element={<TrustInspector />} />
          <Route path="/evaluation" element={<Evaluation />} />
          <Route path="/benchmark" element={<Benchmark />} />
          <Route path="/status" element={<Status />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
