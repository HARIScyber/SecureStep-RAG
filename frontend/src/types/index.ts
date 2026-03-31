// WebSocket Event Types
export type WebSocketEventType = 
  | 'hop_start' 
  | 'doc_blocked' 
  | 'doc_retrieved' 
  | 'hop_complete' 
  | 'answer' 
  | 'complete' 
  | 'error';

export interface WebSocketMessage {
  type: WebSocketEventType;
  hop?: number;
  query?: string;
  doc_title?: string;
  doc_id?: string;
  trust_score?: number;
  passed?: boolean;
  signals?: Record<string, number>;
  reason?: string;
  passed_count?: number;
  blocked_count?: number;
  text?: string;
  total_hops?: number;
  total_blocked?: number;
  message?: string;
  latency_ms?: number;
}

export interface HopInfo {
  hop: number;
  query: string;
  startTime: number;
  duration?: number;
  passedCount?: number;
  blockedCount?: number;
}

export interface BlockedDoc {
  docId: string;
  docTitle: string;
  reason: string;
  hop: number;
  trustScore: number;
  signals: Record<string, number>;
}

export interface RetrievedDoc {
  docId: string;
  docTitle: string;
  trustScore: number;
  passed: boolean;
  signals: Record<string, number>;
  hop: number;
}

export interface PipelineStats {
  totalHops: number;
  totalBlocked: number;
  totalRetrieved: number;
  processingTimeMs: number;
}

export interface PipelineRequest {
  query: string;
  attack_enabled: boolean;
  defence_enabled: boolean;
  attack_type?: string;
}

export interface StatusResponse {
  status: string;
  uptime_seconds: number;
  message: string;
}

export interface HealthResponse {
  status: string;
  services: ServiceHealth[];
}

export interface ServiceHealth {
  name: string;
  status: 'healthy' | 'unhealthy' | 'unknown';
  latency_ms: number;
  last_check: string;
}

export interface AttackInjectionRequest {
  attack_type: 'cascade' | 'drift' | 'hijack' | 'amplification';
  topic: string;
  target?: string;
  n_docs?: number;
}

export interface AttackInjectionResponse {
  success: boolean;
  message: string;
  docs_injected?: number;
  chain_id?: string;
}

export interface EvalResult {
  condition: string;
  faithfulness_score: number;
  attack_success_rate: number;
  blocked_count: number;
  avg_latency_ms: number;
}

export interface EvalResultsResponse {
  conditions: EvalResult[];
  timestamp: string;
  model?: string;
}

export interface BenchmarkDoc {
  id: string;
  content: string;
  source: string;
  source_type: string;
  credibility: number;
  topic: string;
  type: 'clean' | 'cascade' | 'drift' | 'hijack' | 'amplification';
  adversarial: boolean;
  attack_type?: string;
}

export interface BenchmarkResponse {
  docs: BenchmarkDoc[];
  total: number;
  type: string;
}

export interface TrustScore {
  semantic_score: number;
  source_score: number;
  injection_score: number;
  hop_score: number;
  overall: number;
}

export interface SignalBreakdown {
  name: string;
  score: number;
  weight: number;
  description: string;
}

export interface TrustFilterConfig {
  threshold: number;
  weights: {
    semantic: number;
    source: number;
    injection: number;
    hop: number;
  };
}

export interface ConfigResponse {
  trust_threshold: number;
  trust_weights: Record<string, number>;
  model_provider: string;
  vector_store: string;
  embedding_model: string;
}
