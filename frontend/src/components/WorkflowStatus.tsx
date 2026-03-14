import React, { useEffect, useState, useRef } from 'react';
import { CheckCircle2, Loader2, Circle, AlertTriangle } from 'lucide-react';
import type { NodeStatusEvent } from '../types';
import { connectWebSocket } from '../services/api';

interface WorkflowStatusProps {
  projectId: number;
  onComplete: () => void;
}

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
    <div className="max-w-2xl mx-auto p-8">
      {/* Progress bar */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-semibold text-[#1a2b4c]">
            {completed ? '✅ 研究任务已完成' : errorMsg ? '❌ 执行出错' : '⚙️ Agent 正在执行...'}
          </span>
          <span className="text-sm font-mono text-slate-500">{Math.round(progress * 100)}%</span>
        </div>
        <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-700 ease-out ${
              errorMsg ? 'bg-red-400' : completed ? 'bg-emerald-400' : 'bg-[#22d3ee]'
            }`}
            style={{ width: `${progress * 100}%` }}
          />
        </div>
      </div>

      {errorMsg && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700">
          <AlertTriangle size={16} className="inline mr-2" />
          {errorMsg}
        </div>
      )}

      {/* Pipeline visualization */}
      <div className="space-y-1">
        {PIPELINE_NODES.map((node, i) => {
          const state = nodeStates[node.key];
          return (
            <div key={node.key}>
              <div className={`flex items-center gap-4 p-4 rounded-xl transition-all duration-300 ${
                state === 'done' ? 'bg-emerald-50' :
                state === 'running' ? 'bg-blue-50 shadow-sm' :
                'bg-slate-50'
              }`}>
                {/* Icon */}
                <div className="shrink-0">
                  {state === 'done' ? (
                    <CheckCircle2 size={22} className="text-emerald-500" />
                  ) : state === 'running' ? (
                    <Loader2 size={22} className="text-blue-500 animate-spin" />
                  ) : (
                    <Circle size={22} className="text-slate-300" />
                  )}
                </div>

                {/* Label */}
                <div className="flex-1 min-w-0">
                  <p className={`text-sm font-semibold ${
                    state === 'done' ? 'text-emerald-700' :
                    state === 'running' ? 'text-blue-700' :
                    'text-slate-400'
                  }`}>
                    {node.label}
                  </p>
                  <p className="text-[11px] text-slate-400">{node.labelEn}</p>
                </div>

                {/* Status badge */}
                <div className="shrink-0">
                  {state === 'done' && <span className="text-[10px] font-bold text-emerald-500 uppercase">完成</span>}
                  {state === 'running' && <span className="text-[10px] font-bold text-blue-500 uppercase animate-pulse">执行中</span>}
                </div>
              </div>

              {/* Connector line */}
              {i < PIPELINE_NODES.length - 1 && (
                <div className="flex justify-start ml-[26px]">
                  <div className={`w-0.5 h-4 ${
                    state === 'done' ? 'bg-emerald-300' : 'bg-slate-200'
                  }`} />
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
