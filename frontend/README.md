# SecureStep-RAG Frontend Dashboard

A modern React 18 + TypeScript + Tailwind CSS dashboard for real-time visualization and control of the SecureStep-RAG attack detection system.

## 📋 Table of Contents

- [Features](#features)
- [Setup](#setup)
- [Development](#development)
- [Structure](#structure)
- [Pages](#pages)
- [Components](#components)
- [API Integration](#api-integration)

## ✨ Features

- **Real-time WebSocket Streaming** - Live pipeline execution with instant updates
- **6 Full Pages** - Comprehensive system monitoring and control
- **Interactive Components** - Trust score visualization, hop tracing, document inspection
- **Type-Safe** - Full TypeScript support with complete type definitions
- **Modern UI** - Tailwind CSS styling with responsive design
- **Chart Visualization** - Recharts integration for evaluation metrics
- **Dark-Mode Ready** - Extensible color system
- **Production Ready** - Error handling, loading states, accessibility

## 🚀 Setup

### Prerequisites

- Node.js 16+ (recommended 18+)
- npm or yarn

### Installation

1. **Navigate to frontend directory**
   ```bash
   cd frontend
   ```

2. **Install dependencies**
   ```bash
   npm install
   # or
   yarn install
   ```

3. **Start development server**
   ```bash
   npm run dev
   # Server runs on http://localhost:3000
   ```

4. **Build for production**
   ```bash
   npm run build
   ```

5. **Preview build**
   ```bash
   npm run preview
   ```

## 🛠️ Development

### Project Structure

```
frontend/
├── src/
│   ├── pages/              # 6 main pages
│   │   ├── Pipeline.tsx    # Live execution
│   │   ├── AttackStudio.tsx # Attack injection
│   │   ├── TrustInspector.tsx # Threshold control
│   │   ├── Evaluation.tsx  # Results charts
│   │   ├── Benchmark.tsx   # Document browser
│   │   └── Status.tsx      # Health metrics
│   ├── components/         # Reusable components
│   │   ├── Sidebar.tsx     # Navigation
│   │   ├── TrustBar.tsx    # Signal visualization
│   │   └── HopTrace.tsx    # Retrieval timeline
│   ├── hooks/              # Custom hooks
│   │   └── usePipeline.ts  # WebSocket management
│   ├── types/              # TypeScript interfaces
│   │   └── index.ts        # All type definitions
│   ├── App.tsx             # Router setup
│   ├── main.tsx            # Entry point
│   └── index.css           # Global styles
├── index.html              # HTML template
├── package.json            # Dependencies
├── vite.config.ts          # Vite configuration
├── tsconfig.json           # TypeScript config
├── tailwind.config.js      # Tailwind config
└── postcss.config.js       # PostCSS config
```

### File Organization

- **Pages** - Full-screen views with layout and logic
- **Components** - Reusable UI components (Sidebar, TrustBar, HopTrace)
- **Hooks** - Custom React hooks (usePipeline manages WebSocket)
- **Types** - Centralized TypeScript interfaces for backend communication

## 📄 Pages

### Pipeline (/)
Live real-time pipeline execution with:
- Query input and execution controls
- Attack/defense toggles
- Animated hop trace timeline
- Document filtering (passed vs blocked)
- Trust score detailed view
- Final answer display with statistics

### Attack Studio (/attack-studio)
Create and inject adversarial documents:
- 4 attack types (cascade, drift, hijack, amplification)
- Topic and target selection
- Batch injection control
- Real-time injection feedback
- Quick example buttons

### Trust Inspector (/trust-inspector)
Interactive threshold tuning and inspection:
- Threshold slider (0-100%)
- Live document filtering based on threshold
- Trust score visualization for each signal
- Document list with pass/block preview
- Credibility and source analysis

### Evaluation (/evaluation)
Ablation study results and charts:
- 4 different chart types (Recharts)
- Faithfulness score comparison
- Attack success rate by condition
- Documents blocked metrics
- Latency analysis
- Detailed results table
- W&B report link

### Benchmark (/benchmark)
Browse benchmark dataset:
- Filter by document type (clean, cascade, drift, hijack, amplification)
- Full-text search
- Document type badges
- Detailed metadata view
- Credibility visualization
- Content preview

### Status (/status)
System health and monitoring:
- Overall system status indicator
- 5 service health checks
- Latency metrics per service
- Uptime tracking
- Health percentage
- System information panel

## 🎨 Components

### Sidebar
- Navigation with active route highlighting
- System branding
- Connection status indicator

### TrustBar
Displays 4 trust signals:
- Semantic (blue) - Content relevance
- Source (green) - Credibility
- Injection (orange) - Injection risk
- Hop (purple) - Multi-hop drift

Modes:
- Full view with threshold comparison
- Compact view for lists (1-line)

### HopTrace
Animated hop timeline:
- Visual hop progression
- Timing per hop
- Completion status indicator
- Statistics cards
- Directional connectors

## 🔌 API Integration

### WebSocket Connection

**Endpoint**: `ws://localhost:8000/ws/pipeline`

**Flow**:
1. Connect to WebSocket
2. Send query with settings: `{query, attack_enabled, defence_enabled}`
3. Receive streaming events: `hop_start`, `doc_blocked`, `doc_retrieved`, `answer`, `complete`
4. Display events in real-time

### REST Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/status` | Server health |
| POST | `/api/attack/inject` | Inject adversarial docs |
| GET | `/api/eval/results` | Ablation results |
| GET | `/api/benchmark/docs` | Benchmark documents |
| GET | `/api/config` | System configuration |

## 📊 Data Types

All TypeScript interfaces in `src/types/index.ts`:

- `WebSocketMessage` - Events from backend
- `HopInfo` - Retrieval hop data
- `BlockedDoc` - Filtered document info
- `RetrievedDoc` - Retrieved document data
- `TrustScore` - 4-signal breakdown
- `EvalResult` - Evaluation metrics
- `BenchmarkDoc` - Benchmark dataset documents

## 🎯 Key Features

- **Type Safety** - Full TypeScript coverage
- **Error Handling** - Graceful fallbacks and UI messages
- **Loading States** - Skeleton-like loading indicators
- **Responsive** - Mobile-friendly (on larger screens optimized)
- **Accessibility** - Proper ARIA labels and semantic HTML
- **Performance** - Optimized re-renders with React hooks

## 🔄 WebSocket Hook (usePipeline)

Manages connection and message parsing:

```typescript
const {
  hops,
  blockedDocs,
  retrievedDocs,
  answer,
  stats,
  isConnected,
  isStreaming,
  error,
  sendQuery,
  reset,
} = usePipeline();

// Send query
sendQuery({
  query: "What is zero trust?",
  attack_enabled: false,
  defence_enabled: true,
});
```

## 🚀 Deployment

### Build
```bash
npm run build
# Creates optimized dist/ folder
```

### Serve
```bash
npm run preview
# Test production build locally
```

### Docker
```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "run", "preview"]
```

## 📝 Environment Setup

The frontend connects to backend at `localhost:8000`. To use different backends:
- Edit WebSocket URL in `src/hooks/usePipeline.ts`
- Edit API URLs in page files (search for `localhost:8000`)

## 🤝 Contributing

1. Keep components small and focused
2. Use TypeScript types for all props
3. Follow Tailwind naming conventions
4. Add docstrings to custom hooks
5. Test in multiple browsers

## 📄 License

MIT

---

**Enjoy building with SecureStep-RAG!** 🛡️
