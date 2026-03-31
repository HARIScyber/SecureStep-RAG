# Frontend Setup & Deployment Guide

## Quick Start (60 Seconds)

### Windows
```batch
cd frontend
start.bat
# Opens https://localhost:3000
```

### macOS/Linux
```bash
cd frontend
chmod +x start.sh
./start.sh
# Opens https://localhost:3000
```

### Manual
```bash
cd frontend
npm install
npm run dev
```

## System Requirements

- **Node.js** 16.0.0 or higher
- **npm** 7.0.0 or higher (or yarn 1.22.0+)
- **Disk Space** ~500 MB for node_modules
- **RAM** 512 MB minimum
- **Browser** Chrome/Firefox/Safari (ES2020 support)

## Installation Steps

### 1. Prerequisites

Ensure you have Node.js installed:
```bash
node --version  # Should be v16+
npm --version   # Should be v7+
```

### 2. Navigate to Frontend Directory

```bash
cd frontend
```

### 3. Install Dependencies

```bash
npm install
# or with yarn
yarn install
```

This installs:
- React 18.2.0
- React Router v6
- Recharts 2.10.3
- Tailwind CSS 3.3.6
- TypeScript 5.2.2
- Vite 5.0.8

### 4. Run Development Server

```bash
npm run dev
```

The dashboard will open at `http://localhost:3000`

## Development

### Available Scripts

```bash
# Start dev server with auto-reload
npm run dev

# Build for production
npm run build

# Preview production build locally
npm run preview

# Type-check TypeScript
npm run type-check

# Lint code
npm run lint
```

### Environment Variables

Create `.env` or `.env.local`:

```env
# Backend API (default: http://localhost:8000)
VITE_API_URL=http://localhost:8000

# WebSocket (default: ws://localhost:8000)
VITE_WS_URL=ws://localhost:8000

# W&B embed
VITE_WANDB_URL=https://wandb.ai
```

## Folder Structure

```
frontend/
├── src/
│   ├── pages/               # 6 main pages
│   │   ├── Pipeline.tsx     # Live execution (1000+ lines)
│   │   ├── AttackStudio.tsx # Attack injection
│   │   ├── TrustInspector.tsx # Threshold control
│   │   ├── Evaluation.tsx   # Results visualization
│   │   ├── Benchmark.tsx    # Document browser
│   │   └── Status.tsx       # Health metrics
│   ├── components/          # Reusable components
│   │   ├── Sidebar.tsx      # Navigation (100 lines)
│   │   ├── TrustBar.tsx     # Signal display (200 lines)
│   │   └── HopTrace.tsx     # Timeline animation (150 lines)
│   ├── hooks/               # Custom React hooks
│   │   └── usePipeline.ts   # WebSocket + state mgmt (300+ lines)
│   ├── types/               # TypeScript interfaces
│   │   └── index.ts         # All type definitions (200+ lines)
│   ├── App.tsx              # Router (50 lines)
│   ├── main.tsx             # Entry point (15 lines)
│   └── index.css            # Global styles (100+ lines)
├── configs/
│   ├── tsconfig.json        # TypeScript config
│   ├── tailwind.config.js   # Tailwind config
│   ├── vite.config.ts       # Vite config
│   └── postcss.config.js    # PostCSS config
├── index.html               # HTML template
├── package.json             # Dependencies
├── README.md                # Documentation
├── start.sh                 # Linux/Mac quick start
├── start.bat                # Windows quick start
└── .gitignore               # Git ignore rules
```

## Building for Production

### 1. Optimize Build

```bash
npm run build
```

Output: `dist/` folder (~200 KB gzipped)

### 2. Preview Production Build

```bash
npm run preview
```

### 3. Deploy to Server

**Option A: Static File Server (Nginx)**
```nginx
server {
    listen 80;
    root /var/www/securestep-rag/frontend/dist;
    
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

**Option B: Vercel**
```bash
npm install -g vercel
vercel
```

**Option C: Netlify**
```bash
npm run build
# Drag dist/ folder to Netlify
```

**Option D: Docker**
```dockerfile
FROM node:18-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

## Troubleshooting

### Port 3000 Already in Use

```bash
# Windows
netstat -ano | findstr :3000
taskkill /PID <PID> /F

# macOS/Linux
lsof -i :3000
kill -9 <PID>
```

### Backend Connection Error

1. Ensure FastAPI server running: `python main.py`
2. Check backend on http://localhost:8000/docs
3. Verify CORS enabled in backend
4. Check browser console for WebSocket errors

### Build Fails with TypeScript Errors

```bash
npm run type-check  # Identify errors
npm install         # Ensure all libs installed
```

### Slow Performance

```bash
# Check bundle size
npm run build -- --report

# Clear node_modules and reinstall
rm -rf node_modules package-lock.json
npm install
```

## Architecture

### Component Hierarchy

```
App (Router)
├── Sidebar (Navigation)
└── Route Components
    ├── Pipeline (WebSocket + Real-time)
    ├── AttackStudio (REST POST)
    ├── TrustInspector (Interactive)
    ├── Evaluation (Charts)
    ├── Benchmark (Data Grid)
    └── Status (Health Metrics)
```

### Data Flow

```
User Input
    ↓
Component (Page/Hook)
    ↓
API/WebSocket Call
    ↓
Backend (FastAPI)
    ↓
State Update (React)
    ↓
Re-render
    ↓
UI Display
```

### WebSocket Flow

```
WebSocket Connect
    ↓
Listen for Messages
    ↓
Parse JSON Events
    ↓
Update React State
    ↓
Trigger Re-render
    ↓
UI Update
```

## Performance Optimization

### Code Splitting (Automatic with Vite)
Each route component lazy-loaded:
```typescript
// Automatic with React Router v6
const Pipeline = lazy(() => import('./pages/Pipeline'));
```

### Assets
- Images: WebP with fallback
- Fonts: System stack (no external)
- CSS: Tailwind JIT (only used classes)

### Bundle Size
- React: ~42 KB (gzip)
- React Router: ~14 KB (gzip)
- Recharts: ~18 KB (gzip)
- Total: ~150 KB (gzip)

## Debugging

### Browser DevTools

1. **React DevTools** - Component tree inspection
2. **Redux DevTools** - State management (if added)
3. **Network Tab** - API calls and WebSocket
4. **Console** - Error messages and logs

### Source Maps

Build includes source maps for easy debugging:
```bash
npm run build
# vite/dist contains .map files
```

## Customization

### Changing Colors
Edit `frontend/tailwind.config.js`:
```javascript
colors: {
  brand: '#0066cc',
}
```

### Adding Pages
1. Create `frontend/src/pages/NewPage.tsx`
2. Add route to `frontend/src/App.tsx`
3. Add navigation link to `frontend/src/components/Sidebar.tsx`

### Custom Components
Create in `frontend/src/components/` following naming:
- `ComponentName.tsx` - Component file
- Export as `export function ComponentName() { ... }`

## Security

- No secrets in code (use environment variables)
- CORS configured for specific origins
- Input sanitization on all forms
- HTTPS recommended for production
- CSP headers recommended

## Monitoring

### Sentry Integration (Optional)

```bash
npm install @sentry/react
```

```typescript
import * as Sentry from "@sentry/react";

Sentry.init({
  dsn: process.env.VITE_SENTRY_DSN,
  environment: process.env.NODE_ENV,
});

export default Sentry.withProfiler(App);
```

### Analytics (Optional)

```bash
npm install @react-google-analytics/core
```

## Support & Resources

- **React Docs**: https://react.dev
- **Tailwind CSS**: https://tailwindcss.com
- **Recharts**: https://recharts.org
- **Vite**: https://vitejs.dev
- **TypeScript**: https://www.typescriptlang.org

---

**Dashboard Ready!** 🚀

Your SecureStep-RAG frontend dashboard is now running and connected to your backend at `http://localhost:8000`.
