import React, { useEffect, useState, useRef } from 'react';
import { CheckCircle2, Loader2, Circle, AlertTriangle } from 'lucide-react';
import type { NodeStatusEvent } from '../types';
import { connectWebSocket } from '../services/api';

interface WorkflowStatusProps {
  projectId: number;
  onComplete: () => void;
}

const MolecularAnimation = () => (
  <div className="absolute inset-0 overflow-hidden pointer-events-none opacity-40">
    <svg className="w-full h-full" viewBox="0 0 400 200" preserveAspectRatio="none">
      <defs>
        <radialGradient id="particleGrad" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#00b5ad" stopOpacity="0.8" />
          <stop offset="100%" stopColor="#1a2b4c" stopOpacity="0" />
        </radialGradient>
      </defs>
      {[...Array(15)].map((_, i) => (
        <circle key={i} r={Math.random() * 3 + 1} fill="url(#particleGrad)">
          <animate 
            attributeName="cx" 
            from={`${Math.random() * 100}%`} 
            to={`${Math.random() * 100}%`} 
            dur={`${Math.random() * 10 + 5}s`} 
            repeatCount="indefinite" 
          />
          <animate 
            attributeName="cy" 
            from={`${Math.random() * 100}%`} 
            to={`${Math.random() * 100}%`} 
            dur={`${Math.random() * 10 + 5}s`} 
            repeatCount="indefinite" 
          />
          <animate 
            attributeName="r" 
            values="1;4;1" 
            dur={`${Math.random() * 4 + 2}s`} 
            repeatCount="indefinite" 
          />
        </circle>
      ))}
      {/* Connections briefly appearing */}
      {[...Array(8)].map((_, i) => (
        <line key={`l-${i}`} stroke="#00b5ad" strokeWidth="0.5" strokeDasharray="4 4" opacity="0.3">
          <animate attributeName="x1" values="20%;80%;20%" dur="15s" repeatCount="indefinite" />
          <animate attributeName="y1" values="10%;90%;10%" dur="12s" repeatCount="indefinite" />
          <animate attributeName="x2" values="90%;10%;90%" dur="18s" repeatCount="indefinite" />
          <animate attributeName="y2" values="80%;20%;80%" dur="14s" repeatCount="indefinite" />
          <animate attributeName="opacity" values="0;0.4;0" dur="4s" repeatCount="indefinite" begin={`${i * 0.5}s`} />
        </line>
      ))}
    </svg>
  </div>
);

// Pipeline definition
const PIPELINE_NODES = [
  { key: 'assistant',        label: '分析用户研究意图',         labelEn: 'Intent Analysis' },
  { key: 'zotero',           label: '检索 Zotero 本地文献库',   labelEn: 'Zotero Search' },
  { key: 'query_expansion',  label: '生成扩展搜索关键词',       labelEn: 'Query Expansion' },
  { key: 'cloud_search',     label: '执行云端学术数据库检索',   labelEn: 'Cloud Search' },
  { key: 'filter',           label: '过滤高价值论文',           labelEn: 'Paper Filtering' },
  { key: 'evaluator',        label: 'SOTA 指标对标',            labelEn: 'Benchmark Evaluation' },
];

type NodeState = 'pending' | 'running' | 'done';

export const WorkflowStatus: React.FC<WorkflowStatusProps> = ({ projectId, onComplete }) => {
  const [nodeStates, setNodeStates] = useState<Record<string, NodeState>>(() => {
    const init: Record<string, NodeState> = {};
    PIPELINE_NODES.forEach(n => { init[n.key] = 'pending'; });
    return init;
  });
  const [progress, setProgress] = useState(0);
  const [errorMsg, setErrorMsg] = useState('');
  const [completed, setCompleted] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const ws = connectWebSocket(
      projectId,
      (evt: NodeStatusEvent) => {
        if (evt.type === 'node_status') {
          setNodeStates(prev => ({ ...prev, [evt.node_name]: 'done' }));
          setProgress(evt.progress);

          // Mark next node as running
          const idx = PIPELINE_NODES.findIndex(n => n.key === evt.node_name);
          if (idx < PIPELINE_NODES.length - 1) {
            const next = PIPELINE_NODES[idx + 1].key;
            setNodeStates(prev => prev[next] === 'done' ? prev : { ...prev, [next]: 'running' });
          }
        } else if (evt.type === 'complete') {
          setProgress(1);
          setCompleted(true);
          setTimeout(() => onComplete(), 1500);
        } else if (evt.type === 'error') {
          setErrorMsg(evt.detail);
        }
      },
      () => {
        // on close
      },
    );
    wsRef.current = ws;

    // Mark first node as running
    setNodeStates(prev => ({ ...prev, [PIPELINE_NODES[0].key]: 'running' }));

    return () => {
      ws.close();
    };
  }, [projectId]);

  return (
    <div className="h-full overflow-y-auto custom-scrollbar silicone-grain">
      <div className="max-w-2xl mx-auto p-8 pt-12 pb-24">
      {/* Progress bar */}
      <div className="mb-12 p-8 silicone-flat rounded-[2rem] border border-white/50 relative overflow-hidden">
        {!completed && !errorMsg && <MolecularAnimation />}
        <div className="relative z-10">
          <div className="flex items-center justify-between mb-4">
          <span className="text-sm font-black text-[#1a2b4c] tracking-tight uppercase">
            {completed ? '🎉 研究任务已圆满完成' : errorMsg ? '❌ 系统指令执行中断' : '🚀 智行 Agent 深度研析中...'}
          </span>
          <span className="text-sm font-black text-[#00b5ad] bg-[#00b5ad]/10 px-3 py-1 rounded-full">{Math.round(progress * 100)}%</span>
        </div>
        <div className="w-full h-3 bg-white/50 rounded-full overflow-hidden border border-white p-0.5 shadow-inner">
          <div
            className={`h-full rounded-full transition-all duration-1000 ease-in-out shadow-sm ${
              errorMsg ? 'bg-gradient-to-r from-red-400 to-red-600' : completed ? 'bg-gradient-to-r from-emerald-400 to-emerald-600' : 'bg-gradient-to-r from-[#1a2b4c] to-[#00b5ad]'
            }`}
            style={{ width: `${progress * 100}%` }}
          />
        </div>
        </div>
      </div>

      {errorMsg && (
        <div className="mb-8 p-6 bg-red-50 border border-red-100 rounded-3xl text-sm text-red-700 flex items-start gap-3 shadow-sm animate-bounce">
          <AlertTriangle size={20} className="shrink-0" />
          <p className="font-medium">{errorMsg}</p>
        </div>
      )}

      {/* Pipeline visualization */}
      <div className="space-y-4">
        {PIPELINE_NODES.map((node, i) => {
          const state = nodeStates[node.key];
          return (
            <div key={node.key} className="relative">
              {/* Connector line background */}
               {i < PIPELINE_NODES.length - 1 && (
                <div className="absolute left-[29px] top-[50px] w-0.5 h-10 bg-slate-200" />
              )}

              <div className={`relative flex items-center gap-6 p-6 rounded-[2rem] transition-all duration-500 border border-white/50 ${
                state === 'done' ? 'bg-white shadow-sm scale-[0.98] opacity-80' :
                state === 'running' ? 'silicone-pressed scale-[1.02] z-10' :
                'silicone-flat'
              }`}>
                {/* Icon Container */}
                <div className={`shrink-0 size-14 rounded-2xl flex items-center justify-center transition-all duration-500 ${
                    state === 'done' ? 'bg-emerald-100 text-emerald-500' :
                    state === 'running' ? 'silicone-convex text-[#00b5ad]' :
                    'bg-slate-100 text-slate-300'
                }`}>
                  {state === 'done' ? (
                    <CheckCircle2 size={28} strokeWidth={2.5} />
                  ) : state === 'running' ? (
                    <Loader2 size={28} strokeWidth={2.5} className="animate-spin" />
                  ) : (
                    <Circle size={24} strokeWidth={2.5} />
                  )}
                </div>

                {/* Label */}
                <div className="flex-1 min-w-0">
                  <p className={`text-base font-black tracking-tight ${
                    state === 'done' ? 'text-slate-500 line-through decoration-emerald-500/30' :
                    state === 'running' ? 'text-[#1a2b4c]' :
                    'text-slate-400'
                  }`}>
                    {node.label}
                  </p>
                  <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mt-1">{node.labelEn}</p>
                </div>

                {/* Status indicator */}
                <div className="shrink-0">
                  {state === 'done' && (
                    <div className="bg-emerald-500/10 text-emerald-600 text-[10px] font-black px-3 py-1 rounded-full uppercase tracking-tighter shadow-sm">
                        Verified
                    </div>
                  )}
                  {state === 'running' && (
                    <div className="bg-[#00b5ad] text-white text-[10px] font-black px-3 py-1 rounded-full uppercase tracking-tighter animate-pulse shadow-md">
                        Processing
                    </div>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  </div>
  );
};
