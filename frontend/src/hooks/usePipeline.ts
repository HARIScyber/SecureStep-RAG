import { useCallback, useEffect, useRef, useState } from 'react';
import {
    BlockedDoc,
    HopInfo,
    PipelineRequest,
    PipelineStats,
    RetrievedDoc,
    WebSocketMessage
} from '../types';

interface PipelineState {
  hops: HopInfo[];
  blockedDocs: BlockedDoc[];
  retrievedDocs: RetrievedDoc[];
  answer: string;
  stats: PipelineStats | null;
  isConnected: boolean;
  isStreaming: boolean;
  error: string | null;
  currentHop: number;
}

const initialState: PipelineState = {
  hops: [],
  blockedDocs: [],
  retrievedDocs: [],
  answer: '',
  stats: null,
  isConnected: false,
  isStreaming: false,
  error: null,
  currentHop: 0,
};

export function usePipeline(onMessage?: (msg: WebSocketMessage) => void) {
  const [state, setState] = useState<PipelineState>(initialState);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const messageQueueRef = useRef<PipelineRequest | null>(null);

  // Connect to WebSocket
  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    try {
      const wsUrl = `ws://${window.location.hostname}:8000/ws/pipeline`;
      wsRef.current = new WebSocket(wsUrl);

      wsRef.current.onopen = () => {
        setState(prev => ({ ...prev, isConnected: true, error: null }));
        
        // Send queued message if any
        if (messageQueueRef.current && wsRef.current?.readyState === WebSocket.OPEN) {
          wsRef.current.send(JSON.stringify(messageQueueRef.current));
          messageQueueRef.current = null;
        }
      };

      wsRef.current.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          onMessage?.(message);

          setState(prev => {
            const newState = { ...prev };

            switch (message.type) {
              case 'hop_start':
                newState.hops = [
                  ...prev.hops,
                  {
                    hop: message.hop!,
                    query: message.query!,
                    startTime: Date.now(),
                  },
                ];
                newState.currentHop = message.hop!;
                break;

              case 'doc_retrieved':
                newState.retrievedDocs = [
                  ...prev.retrievedDocs,
                  {
                    docId: message.doc_id || '',
                    docTitle: message.doc_title || '',
                    trustScore: message.trust_score || 0,
                    passed: message.passed || false,
                    signals: message.signals || {},
                    hop: message.hop || 0,
                  },
                ];
                break;

              case 'doc_blocked':
                newState.blockedDocs = [
                  ...prev.blockedDocs,
                  {
                    docId: message.doc_id || '',
                    docTitle: message.doc_title || '',
                    reason: message.reason || '',
                    hop: message.hop || 0,
                    trustScore: message.trust_score || 0,
                    signals: message.signals || {},
                  },
                ];
                // Also add to retrieved docs for tracking
                newState.retrievedDocs = [
                  ...prev.retrievedDocs,
                  {
                    docId: message.doc_id || '',
                    docTitle: message.doc_title || '',
                    trustScore: message.trust_score || 0,
                    passed: false,
                    signals: message.signals || {},
                    hop: message.hop || 0,
                  },
                ];
                break;

              case 'hop_complete':
                newState.hops = newState.hops.map(h =>
                  h.hop === message.hop
                    ? {
                        ...h,
                        duration: Date.now() - h.startTime,
                        passedCount: message.passed_count,
                        blockedCount: message.blocked_count,
                      }
                    : h
                );
                break;

              case 'answer':
                newState.answer = message.text || '';
                newState.stats = {
                  totalHops: message.total_hops || 0,
                  totalBlocked: message.total_blocked || 0,
                  totalRetrieved: prev.retrievedDocs.length,
                  processingTimeMs: message.latency_ms || 0,
                };
                break;

              case 'complete':
                newState.isStreaming = false;
                break;

              case 'error':
                newState.error = message.message || 'Unknown error';
                newState.isStreaming = false;
                break;
            }

            return newState;
          });
        } catch (err) {
          console.error('Error parsing WebSocket message:', err);
        }
      };

      wsRef.current.onerror = (err) => {
        console.error('WebSocket error:', err);
        setState(prev => ({
          ...prev,
          error: 'Connection error',
          isConnected: false,
        }));
      };

      wsRef.current.onclose = () => {
        setState(prev => ({ ...prev, isConnected: false }));
        
        // Attempt reconnect after 3 seconds
        reconnectTimeoutRef.current = setTimeout(() => {
          connect();
        }, 3000);
      };
    } catch (err) {
      setState(prev => ({
        ...prev,
        error: `Connection failed: ${err instanceof Error ? err.message : 'unknown'}`,
      }));
    }
  }, [onMessage]);

  // Disconnect from WebSocket
  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  // Send pipeline request
  const sendQuery = useCallback((request: PipelineRequest) => {
    messageQueueRef.current = request;
    
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(request));
      setState(prev => ({
        ...prev,
        isStreaming: true,
        error: null,
        hops: [],
        blockedDocs: [],
        retrievedDocs: [],
        answer: '',
        stats: null,
        currentHop: 0,
      }));
    } else if (!wsRef.current) {
      // Connect and queue message
      connect();
    }
  }, [connect]);

  // Reset state
  const reset = useCallback(() => {
    setState(initialState);
  }, []);

  // Connect on mount
  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  return {
    ...state,
    sendQuery,
    disconnect,
    connect,
    reset,
  };
}
