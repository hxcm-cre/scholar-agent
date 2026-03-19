import React, { useEffect, useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import ReactMarkdown from 'react-markdown';
import { Download, BarChart3, ShieldCheck, ArrowLeft, Loader2, BookOpen, X, ExternalLink, Highlighter } from 'lucide-react';
import type { ProjectDetail, LiteratureItem } from '../types';
import { getProject } from '../services/api';

interface ResearchReportProps {
  projectId: number;
  onBack: () => void;
}

export const ResearchReport: React.FC<ResearchReportProps> = ({ projectId, onBack }) => {
  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedPaper, setSelectedPaper] = useState<LiteratureItem | null>(null);


  const load = async () => {
    try {
      const data = await getProject(projectId);
      setProject(data);
    } catch (e) {
      console.error('Failed to load project', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [projectId]);

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <Loader2 className="animate-spin text-slate-400" size={32} />
      </div>
    );
  }

  if (!project) {
    return (
      <div className="flex-1 flex items-center justify-center text-slate-400">
        项目不存在
      </div>
    );
  }

  const report = project.reports?.[0];
  const reportContent = report?.content_markdown || '';
  let metricsData: { name: string; value: number; type: string }[] = [];
  try {
    const parsed = JSON.parse(report?.metrics_json || '{}');
    // Build chart data from node_durations
    if (parsed.node_durations) {
      metricsData = Object.entries(parsed.node_durations).map(([k, v]) => ({
        name: k, value: Number(v), type: 'reference',
      }));
    }
  } catch { /* no metrics */ }

  const handleDownload = () => {
    const blob = new Blob([reportContent], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `scholar_report_${projectId}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <section className="flex-1 overflow-y-auto bg-[#f5f7fa] custom-scrollbar">
      <div className="max-w-5xl mx-auto p-8">
        {/* Back */}
        <button onClick={onBack} className="flex items-center gap-1 text-sm text-slate-500 hover:text-[#1a2b4c] mb-6 transition-colors">
          <ArrowLeft size={16} /> 返回任务列表
        </button>

        {/* Report header */}
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-xl font-bold text-[#1a2b4c] flex items-center gap-2">
            <BarChart3 className="text-[#22d3ee]" size={24} />
            研究报告
          </h3>
          {reportContent && (
            <button
              onClick={handleDownload}
              className="flex items-center gap-2 bg-[#1a2b4c] text-white text-xs font-bold px-4 py-2 rounded-lg hover:bg-slate-800 transition-colors"
            >
              <Download size={14} /> 下载 Markdown
            </button>
          )}
        </div>

        {/* Project info */}
        <div className="bg-white rounded-xl border border-slate-200 p-4 mb-6">
          <p className="text-sm text-slate-500">研究问题</p>
          <p className="text-lg font-semibold text-[#1a2b4c]">{project.query}</p>
          <div className="flex gap-4 mt-2 text-xs text-slate-400">
            <span>模型: {project.model_name}</span>
            <span>状态: {project.status}</span>
            <span>创建: {new Date(project.created_at + (project.created_at.endsWith('Z') ? '' : 'Z')).toLocaleString('zh-CN')}</span>
          </div>
        </div>

        {/* Literature list */}
        {project.literature.length > 0 && (
          <div className="bg-white rounded-xl border border-slate-200 p-6 mb-6">
            <h4 className="text-sm font-bold text-[#1a2b4c] uppercase tracking-widest flex items-center gap-2 mb-4">
              <BookOpen size={16} className="text-[#22d3ee]" />
              检索到的论文 ({project.literature.length})
            </h4>
            <div className="space-y-3 max-h-80 overflow-y-auto custom-scrollbar">
              {project.literature.map((lit: LiteratureItem) => (
                <div key={lit.id} className="p-3 rounded-lg bg-slate-50 border border-slate-100 hover:border-slate-200 transition-colors">
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0 mr-4">
                      <p className="text-sm font-semibold text-[#1a2b4c] line-clamp-1">
                        {lit.url ? <a href={lit.url} target="_blank" rel="noopener noreferrer" className="hover:text-[#22d3ee] transition-colors">{lit.title}</a> : lit.title}
                      </p>
                      <p className="text-[11px] text-slate-400 mt-0.5">
                        {lit.authors && <span>{lit.authors} · </span>}
                        {lit.year && <span>{lit.year} · </span>}
                        {lit.venue && <span>{lit.venue}</span>}
                      </p>
                    </div>
                    <div className="flex flex-col items-end gap-2 shrink-0">
                      <div className="flex gap-3 text-[10px] text-slate-400">
                        {lit.citations > 0 && <span>🔗 {lit.citations}</span>}
                        {lit.score > 0 && <span>⭐ {lit.score.toFixed(2)}</span>}
                      </div>
                      <button
                        onClick={() => setSelectedPaper(lit)}
                        className="flex items-center gap-1 text-[10px] bg-[#22d3ee]/10 text-[#22d3ee] px-2 py-1 rounded hover:bg-[#22d3ee]/20 transition-colors"
                      >
                        <Highlighter size={10} /> 查看原文
                      </button>
                    </div>
                  </div>
                </div>
              ))}

            </div>
          </div>
        )}

        {/* Report content */}
        {reportContent ? (
          <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-10 min-h-[400px] text-slate-800 leading-relaxed">
            <div className="prose prose-slate max-w-none">
              <ReactMarkdown
                components={{
                  h2: ({node, ...props}) => <h2 className="text-xl font-bold text-[#1a2b4c] mt-8 mb-4" {...props} />,
                  h3: ({node, ...props}) => <h3 className="text-lg font-semibold text-[#1a2b4c] mt-6 mb-2" {...props} />,
                  ul: ({node, ...props}) => <ul className="list-disc pl-5 space-y-2 text-slate-700" {...props} />,
                  li: ({node, ...props}) => <li {...props} />,
                  strong: ({node, ...props}) => <strong className="font-bold text-[#1a2b4c]" {...props} />,
                  blockquote: ({node, ...props}) => {
                    const { cite, ...rest } = props as any;
                    return (
                      <div className="my-6 p-5 bg-[#22d3ee]/10 border-l-4 border-[#22d3ee] rounded-r-xl">
                        <h4 className="font-bold text-[#1a2b4c] flex items-center gap-2 mb-2">
                          <ShieldCheck size={16} />
                          Performance Comparison
                        </h4>
                        <div className="text-[#1a2b4c]/80 font-medium italic" {...rest} />
                      </div>
                    );
                  },
                  code: ({node, className, children, ...props}) => {
                    if (className) {
                      return <pre className="bg-slate-50 p-4 rounded-xl text-sm overflow-x-auto"><code className={className} {...props}>{children}</code></pre>;
                    }
                    return <code className="bg-slate-100 px-1.5 py-0.5 rounded text-sm font-mono text-[#1a2b4c]" {...props}>{children}</code>;
                  }
                }}
              >
                {reportContent}
              </ReactMarkdown>
            </div>

            {/* Metrics chart */}
            {metricsData.length > 0 && (
              <div className="mt-8">
                <h3 className="text-lg font-semibold text-[#1a2b4c] mb-4">节点耗时分布 (秒)</h3>
                <div className="w-full h-64 bg-slate-50 rounded-xl border border-slate-100 p-4">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={metricsData} margin={{ top: 10, right: 30, left: 20, bottom: 20 }}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                      <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: '#94a3b8', fontSize: 10 }} dy={10} />
                      <YAxis hide />
                      <Tooltip
                        cursor={{ fill: 'transparent' }}
                        content={({ active, payload }) => {
                          if (active && payload && payload.length) {
                            return (
                              <div className="bg-white border border-slate-200 p-2 rounded shadow-sm text-xs font-mono">
                                {Number(payload[0].value).toFixed(2)}s
                              </div>
                            );
                          }
                          return null;
                        }}
                      />
                      <Bar dataKey="value" radius={[4, 4, 0, 0]} barSize={48}>
                        {metricsData.map((_, i) => (
                          <Cell key={`cell-${i}`} fill={i % 2 === 0 ? '#1a2b4c' : '#22d3ee'} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="bg-white rounded-xl border border-slate-200 p-10 text-center text-slate-400">
            {project.status === 'error'
              ? <p className="text-red-500">❌ 任务执行失败: {project.error_message}</p>
              : <p>报告生成中，请稍候...</p>}
          </div>
        )}

      </div>

      {/* Side Drawer */}
      {selectedPaper && (
        <div className="fixed inset-0 z-50 flex justify-end">
          <div className="absolute inset-0 bg-slate-900/40 backdrop-blur-sm" onClick={() => setSelectedPaper(null)} />
          <div className="relative w-full max-w-6xl bg-white shadow-2xl flex flex-col animate-drawer-in">
            {/* Drawer Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 bg-slate-50/50">
              <div className="flex-1 min-w-0">
                <h2 className="text-lg font-bold text-[#1a2b4c] truncate">{selectedPaper.title}</h2>
                <p className="text-xs text-slate-400 mt-0.5">
                  {selectedPaper.authors} · {selectedPaper.year} · {selectedPaper.venue}
                </p>
              </div>
              <div className="flex items-center gap-3 ml-4">
                {selectedPaper.url && (
                  <a
                    href={selectedPaper.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-[#22d3ee] transition-colors"
                  >
                    <ExternalLink size={14} /> 源文件
                  </a>
                )}
                <button
                  onClick={() => setSelectedPaper(null)}
                  className="p-2 hover:bg-slate-200 rounded-full text-slate-400 hover:text-slate-600 transition-colors"
                >
                  <X size={20} />
                </button>
              </div>
            </div>

            {/* Split View Content */}
            <div className="flex-1 flex overflow-hidden">
              {/* Left Column: AI Summary/Metrics */}
              <div className="w-[400px] border-r border-slate-100 bg-slate-50/30 overflow-y-auto p-6 custom-scrollbar">
                <h3 className="text-sm font-bold text-[#1a2b4c] uppercase tracking-wider mb-4 flex items-center gap-2">
                  <ShieldCheck size={16} className="text-[#22d3ee]" />
                  AI 提取指标 & 摘要
                </h3>
                
                <div className="space-y-6">
                  <section>
                    <h4 className="text-xs font-semibold text-slate-400 uppercase mb-2">摘要 (Abstract)</h4>
                    <div className="text-sm text-slate-600 leading-relaxed bg-white p-4 rounded-xl border border-slate-100">
                      {selectedPaper.abstract || '暂无摘要'}
                    </div>
                  </section>

                  {/* Show matching metrics from the report if any */}
                  {(() => {
                    const metrics = JSON.parse(report?.metrics_json || '{}');
                    // Find if there are specific paper metrics for this title
                    // Note: This requires the backend to store metrics per paper title or ID
                    // For now, we can show general project metrics or search key info
                    return (
                      <section>
                        <h4 className="text-xs font-semibold text-slate-400 uppercase mb-2">研究指标</h4>
                        <div className="bg-white p-4 rounded-xl border border-slate-100 space-y-3">
                          <div className="flex items-center justify-between">
                            <span className="text-xs text-slate-500">论文评分</span>
                            <span className="text-xs font-bold text-[#1a2b4c] bg-slate-100 px-2 py-0.5 rounded">
                              {selectedPaper.score.toFixed(2)}
                            </span>
                          </div>
                          <div className="flex items-center justify-between">
                            <span className="text-xs text-slate-500">引用量</span>
                            <span className="text-xs font-bold text-[#1a2b4c]">{selectedPaper.citations}</span>
                          </div>
                          <div className="flex items-center justify-between">
                            <span className="text-xs text-slate-500">发布平台/分级</span>
                            <span className="text-xs font-bold text-[#22d3ee]">{selectedPaper.venue}</span>
                          </div>
                        </div>
                      </section>
                    );
                  })()}
                </div>
              </div>

              {/* Right Column: Full Markdown with Highlighting */}
              <div className="flex-1 overflow-y-auto p-10 custom-scrollbar bg-white">
                <div className="prose prose-slate max-w-none">
                  <ReactMarkdown
                    components={{
                      code: ({node, className, children, ...props}) => {
                        const content = String(children);
                        // Simple highlighting within code blocks if needed, 
                        // but usually it's better to keep code clean.
                        return <code className={className} {...props}>{children}</code>;
                      },
                      // We can use a custom renderer for text to implement highlighting
                      p: ({children}) => {
                        return <p>{highlightText(children, project?.query || '', project?.user_metrics || '')}</p>;
                      },
                      li: ({children}) => {
                        return <li>{highlightText(children, project?.query || '', project?.user_metrics || '')}</li>;
                      },
                      h1: ({children}) => <h1 className="text-2xl font-bold text-[#1a2b4c] mt-8 mb-4">{highlightText(children, project?.query || '', project?.user_metrics || '')}</h1>,
                      h2: ({children}) => <h2 className="text-xl font-bold text-[#1a2b4c] mt-6 mb-3">{highlightText(children, project?.query || '', project?.user_metrics || '')}</h2>,
                      h3: ({children}) => <h3 className="text-lg font-bold text-[#1a2b4c] mt-4 mb-2">{highlightText(children, project?.query || '', project?.user_metrics || '')}</h3>,
                    }}
                  >
                    {selectedPaper.full_text || '> ⚠️ 未提取到全文内容，仅展示摘要。\n\n' + selectedPaper.abstract}
                  </ReactMarkdown>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </section>
  );
};

/**
 * Helper to highlight keywords and metrics in text
 */
function highlightText(children: any, query: string, metrics: string) {
  if (typeof children !== 'string') return children;

  const queryStr = query || '';
  const metricsStr = metrics || '';

  const keywords = [
    ...queryStr.split(/\s+/).filter(k => k.length > 2),
    ...metricsStr.split(/[,，]/).map(m => m.trim()).filter(m => m.length > 0)
  ];

  if (keywords.length === 0) return children;

  // Create a regex to match any of the keywords
  const regex = new RegExp(`(${keywords.map(k => k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')})`, 'gi');
  const parts = children.split(regex);

  return parts.map((part, i) => 
    regex.test(part) ? (
      <mark key={i} className="bg-yellow-200 text-[#1a2b4c] px-0.5 rounded font-medium">
        {part}
      </mark>
    ) : part
  );
}
