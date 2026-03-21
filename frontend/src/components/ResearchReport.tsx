import React, { useEffect, useState, useRef } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Download, BarChart3, ShieldCheck, ArrowLeft, Loader2, BookOpen, X, ExternalLink, Highlighter, Send, MessageSquare, Plus, Sparkles, ChevronUp, ChevronDown, Brain } from 'lucide-react';
import type { ProjectDetail, LiteratureItem, ModelOption } from '../types';
import { getProject, chatPaper, savePaperNote, getAvailableModels } from '../services/api';

interface ResearchReportProps {
  projectId: number;
  onBack: () => void;
}

export const ResearchReport: React.FC<ResearchReportProps> = ({ projectId, onBack }) => {
  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedPaper, setSelectedPaper] = useState<LiteratureItem | null>(null);

  const handleSyncToReport = async (note: string) => {
    if (!selectedPaper || !project) return;
    try {
      const resp = await savePaperNote(selectedPaper.id, note);
      // Update local state to show the new note immediately
      setProject({
        ...project,
        literature: project.literature.map(lit =>
          lit.id === selectedPaper.id ? { ...lit, user_notes: resp.user_notes } : lit
        )
      });
      alert('已成功同步至研究报告！');
    } catch (e) {
      console.error('Failed to sync note', e);
      alert('同步失败，请检查网络连接。');
    }
  };


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
    <section className="flex-1 overflow-y-auto bg-[#f1f3f8] custom-scrollbar silicone-grain">
      <div className="max-w-5xl mx-auto p-12">
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
          <div className="bg-white rounded-[2.5rem] border border-slate-200 p-8 mb-12 shadow-sm">
            <h4 className="text-xs font-black text-[#1a2b4c] uppercase tracking-[0.2em] flex items-center gap-2 mb-8">
              <BookOpen size={18} className="text-[#00b5ad]" />
              检索到的核心文献 ({project.literature.length})
            </h4>
            <div className="space-y-6">
              {project.literature.map((lit: LiteratureItem) => (
                <div key={lit.id} className="p-5 rounded-2xl bg-white border border-slate-100 hover:border-[#00b5ad]/30 hover:shadow-lg transition-all duration-300 group">
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0 mr-6">
                      <p className="text-base font-bold text-[#1a2b4c] line-clamp-1 mb-1">
                        {lit.url ? <a href={lit.url} target="_blank" rel="noopener noreferrer" className="hover:text-[#00b5ad] transition-colors">{lit.title}</a> : lit.title}
                      </p>
                      <div className="flex flex-wrap gap-2 mt-2">
                        {lit.venue && <span className="px-2 py-0.5 bg-indigo-50 text-indigo-500 rounded text-[10px] font-bold uppercase tracking-wider">{lit.venue}</span>}
                        {lit.year && <span className="px-2 py-0.5 bg-slate-100 text-slate-500 rounded text-[10px] font-bold">{lit.year}</span>}
                        {lit.authors && <span className="text-[11px] text-slate-400 font-medium self-center">{lit.authors.split(',')[0]} et al.</span>}
                      </div>
                      {lit.user_notes && (
                        <details className="mt-4 group/insight overflow-hidden border border-slate-100/50 rounded-2xl bg-[#f1f3f8]/50 transition-all duration-300">
                           <summary className="list-none cursor-pointer p-4 flex items-center justify-between hover:bg-[#f1f3f8] transition-colors">
                              <div className="flex items-center gap-1.5 text-[#00b5ad] font-bold uppercase tracking-widest text-[9px]">
                                <Sparkles size={12} className="group-open/insight:animate-pulse" /> 专家深度洞察
                              </div>
                              <div className="text-slate-400 group-open/insight:rotate-180 transition-transform duration-300">
                                <ChevronDown size={14} />
                              </div>
                           </summary>
                           <div className="px-4 pb-4 text-[12px] text-slate-600 border-t border-slate-200/50 pt-3 animate-in fade-in slide-in-from-top-1">
                              <ReactMarkdown remarkPlugins={[remarkGfm]}>{lit.user_notes}</ReactMarkdown>
                           </div>
                        </details>
                      )}
                    </div>
                    <div className="flex flex-col items-end gap-3 shrink-0">
                      <div className="flex gap-4 text-[11px] font-bold text-slate-400">
                        {lit.citations > 0 && <span className="flex items-center gap-1"><ExternalLink size={10} /> {lit.citations}</span>}
                        {lit.score > 0 && <span className="flex items-center gap-1 text-[#00b5ad] bg-[#00b5ad]/10 px-2 py-0.5 rounded-full">⭐ {lit.score.toFixed(1)}</span>}
                      </div>
                      <button
                        onClick={() => setSelectedPaper(lit)}
                        className="flex items-center gap-2 text-[11px] font-bold bg-[#1a2b4c] text-white px-4 py-2 rounded-xl hover:bg-[#00b5ad] hover:shadow-md transition-all duration-300"
                      >
                        <Highlighter size={12} /> 文献透视
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
                remarkPlugins={[remarkGfm]}
                components={{
                  h2: ({ node, ...props }) => <h2 className="text-xl font-bold text-[#1a2b4c] mt-8 mb-4 border-b border-slate-100 pb-2" {...props} />,
                  h3: ({ node, ...props }) => <h3 className="text-lg font-semibold text-[#1a2b4c] mt-6 mb-2" {...props} />,
                  ul: ({ node, ...props }) => <ul className="list-disc pl-5 space-y-2 text-slate-700" {...props} />,
                  li: ({ node, ...props }) => <li {...props} />,
                  strong: ({ node, ...props }) => <strong className="font-bold text-[#1a2b4c]" {...props} />,
                  table: ({ node, ...props }) => (
                    <div className="my-8 overflow-x-auto rounded-xl border border-slate-200 shadow-sm">
                      <table className="w-full text-sm text-left border-collapse" {...props} />
                    </div>
                  ),
                  thead: ({ node, ...props }) => <thead className="bg-slate-50 border-b border-slate-200" {...props} />,
                  th: ({ node, ...props }) => <th className="px-4 py-3 font-bold text-[#1a2b4c] uppercase tracking-wider text-[10px]" {...props} />,
                  td: ({ node, ...props }) => <td className="px-4 py-3 border-b border-slate-100 text-slate-600" {...props} />,
                  blockquote: ({ node, ...props }) => {
                    const children = props.children as any;
                    const content = String(children?.[1]?.props?.children || children?.[0]?.props?.children || '');
                    
                    // Case 1: GitHub Style Alerts [!WARNING], [!NOTE], [!TIP]
                    if (content.includes('[!WARNING]') || content.includes('领域不匹配警告')) {
                      return (
                        <div className="my-6 p-5 bg-red-50 border border-red-100 rounded-2xl flex items-start gap-4 animate-in fade-in slide-in-from-top-2 duration-500">
                          <div className="p-2 bg-red-100 rounded-lg text-red-600">
                            <ShieldCheck size={20} />
                          </div>
                          <div>
                            <h4 className="text-xs font-black text-red-700 uppercase tracking-widest mb-1">Domain Mismatch Warning</h4>
                            <div className="text-sm text-red-600/90 font-medium leading-relaxed">
                              {content.replace('[!WARNING]', '').trim()}
                            </div>
                          </div>
                        </div>
                      );
                    }

                    if (content.includes('[!NOTE]') || content.includes('[!TIP]')) {
                      const isTip = content.includes('[!TIP]');
                      return (
                        <div className={`my-6 p-5 ${isTip ? 'bg-cyan-50 border-cyan-100' : 'bg-slate-50 border-slate-100'} border rounded-2xl flex items-start gap-4`}>
                          <div className={`p-2 ${isTip ? 'bg-cyan-100 text-cyan-600' : 'bg-slate-200 text-slate-500'} rounded-lg`}>
                            <Sparkles size={20} />
                          </div>
                          <div>
                            <h4 className={`text-xs font-black ${isTip ? 'text-cyan-700' : 'text-slate-700'} uppercase tracking-widest mb-1`}>
                              {isTip ? 'Expert Tip' : 'Information Note'}
                            </h4>
                            <div className={`text-sm ${isTip ? 'text-cyan-600/90' : 'text-slate-600/90'} font-medium`}>
                              {content.replace(/\[!(NOTE|TIP)\]/, '').trim()}
                            </div>
                          </div>
                        </div>
                      );
                    }

                    // Case 2: Performance Comparison Cards
                    const isComparison = content.toLowerCase().includes('sota') && (content.toLowerCase().includes('local') || content.toLowerCase().includes('rmse'));
                    
                    if (isComparison) {
                      const parts = content.split(/[,;\n]/).map(p => p.trim());
                      const metricsMap: Record<string, string> = {};
                      parts.forEach(p => {
                        const [k, v] = p.split(/[:：]/).map(s => s?.trim());
                        if (k && v) {
                           const key = k.toLowerCase();
                           if (key.includes('local')) metricsMap['local'] = v;
                           else if (key.includes('sota')) metricsMap['sota'] = v;
                           else if (key.includes('diff')) metricsMap['diff'] = v;
                           else metricsMap[key] = v;
                        }
                      });

                      if (metricsMap['local'] || metricsMap['sota']) {
                        return (
                          <div className="my-10 grid grid-cols-1 md:grid-cols-2 gap-6">
                            <div className="silicone-convex p-6 rounded-3xl border border-white/50 relative overflow-hidden">
                              <div className="absolute top-0 right-0 w-24 h-24 bg-blue-400/10 rounded-full -mr-12 -mt-12 blur-2xl" />
                              <h4 className="text-xs font-black text-slate-400 uppercase tracking-widest mb-4">Local Experiment</h4>
                              <div className="flex items-baseline gap-2">
                                <span className="text-4xl font-black text-[#1a2b4c]">{metricsMap['local'] || '0.00'}</span>
                                <span className="text-xs font-bold text-slate-400">Value</span>
                              </div>
                              <div className="mt-4 flex gap-2">
                                <span className="px-3 py-1 bg-[#1a2b4c]/5 text-[#1a2b4c] rounded-full text-[10px] font-bold">Primary Metric</span>
                              </div>
                            </div>
                            
                            <div className="silicone-flat p-6 rounded-3xl border border-slate-200/50 relative overflow-hidden">
                              <div className="absolute top-0 right-0 w-24 h-24 bg-emerald-400/10 rounded-full -mr-12 -mt-12 blur-2xl" />
                              <h4 className="text-xs font-black text-slate-400 uppercase tracking-widest mb-4">SOTA Baseline</h4>
                              <div className="flex items-baseline gap-2">
                                <span className="text-4xl font-black text-slate-400">{metricsMap['sota'] || '0.00'}</span>
                                <span className="text-xs font-bold text-slate-400">SOTA</span>
                              </div>
                              <div className="mt-4 flex flex-wrap gap-2">
                                {metricsMap['diff'] && (() => {
                                  const diffVal = parseFloat(metricsMap['diff'].replace('%', ''));
                                  const isPositive = diffVal > 0;
                                  return (
                                    <span className={`px-3 py-1 rounded-full text-[10px] font-bold flex items-center gap-1 ${
                                      isPositive ? 'bg-emerald-50 text-emerald-600' : 'bg-red-50 text-red-600'
                                    }`}>
                                      {isPositive ? '+' : ''}{diffVal}% {isPositive ? 'Gain' : 'Loss'} 
                                      {isPositive ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                                    </span>
                                  );
                                })()}
                                <span className="px-3 py-1 bg-slate-100 text-slate-500 rounded-full text-[10px] font-bold">Reference</span>
                              </div>
                            </div>
                          </div>
                        );
                      }
                    }

                    // Default Fallback: Elegant Blockquote
                    return (
                      <div className="my-8 p-6 bg-slate-50/50 rounded-3xl border-l-4 border-[#00b5ad] relative overflow-hidden accent-light">
                        <div className="text-slate-600 font-medium leading-relaxed italic">
                          {children}
                        </div>
                      </div>
                    );
                  },
                  code: ({ node, className, children, ...props }) => {
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
              <div className="mt-12 p-8 silicone-flat rounded-[2.5rem] border border-white/50">
                <div className="flex items-center justify-between mb-8">
                  <h3 className="text-lg font-black text-[#1a2b4c] tracking-tight">节点耗时分布与瓶颈分析</h3>
                  <div className="flex gap-4">
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded-full bg-gradient-to-t from-[#1a2b4c] to-[#00b5ad]" />
                      <span className="text-[10px] font-bold text-slate-400 uppercase">正常执行</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded-full bg-gradient-to-t from-[#ef4444] to-[#f87171]" />
                      <span className="text-[10px] font-bold text-slate-400 uppercase">高耗时节点</span>
                    </div>
                  </div>
                </div>
                <div className="w-full h-80 bg-white/30 backdrop-blur-sm rounded-3xl border border-white/40 p-6 shadow-inner">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={metricsData} margin={{ top: 20, right: 30, left: 10, bottom: 20 }}>
                      <defs>
                        <linearGradient id="barNormal" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="#00b5ad" stopOpacity={0.9}/>
                          <stop offset="100%" stopColor="#1a2b4c" stopOpacity={1}/>
                        </linearGradient>
                        <linearGradient id="barWarning" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="#f87171" stopOpacity={0.9}/>
                          <stop offset="100%" stopColor="#ef4444" stopOpacity={1}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="6 6" vertical={false} stroke="rgba(203, 213, 225, 0.4)" />
                      <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: '#94a3b8', fontSize: 11, fontWeight: 700 }} dy={15} />
                      <YAxis axisLine={false} tickLine={false} tick={{ fill: '#94a3b8', fontSize: 10 }} />
                      <Tooltip
                        cursor={{ fill: 'rgba(255,255,255,0.4)', radius: 12 }}
                        content={({ active, payload }) => {
                          if (active && payload && payload.length) {
                            return (
                              <div className="bg-white/90 backdrop-blur-md border border-slate-200 p-3 rounded-2xl shadow-xl text-xs font-black text-[#1a2b4c]">
                                <div className="mb-1 text-[10px] text-slate-400 uppercase tracking-widest">{payload[0].payload.name}</div>
                                <div className="text-lg">{Number(payload[0].value).toFixed(2)}s</div>
                              </div>
                            );
                          }
                          return null;
                        }}
                      />
                      <Bar dataKey="value" radius={[12, 12, 4, 4]} barSize={40}>
                        {metricsData.map((entry, i) => (
                          <Cell 
                            key={`cell-${i}`} 
                            fill={entry.value > 10 || entry.name === 'filter' ? 'url(#barWarning)' : 'url(#barNormal)'} 
                          />
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

      {/* Side Drawer with Resizable Panel */}
      {selectedPaper && (
        <DrawerWithResizable 
          paper={selectedPaper} 
          projectQuery={project.query} 
          userMetrics={project.user_metrics}
          report={report}
          onClose={() => setSelectedPaper(null)}
          onSync={handleSyncToReport}
        />
      )}
    </section>
  );
};

/**
 * Resizable Side Drawer for Paper Details
 */
const DrawerWithResizable: React.FC<{
  paper: LiteratureItem;
  projectQuery: string;
  userMetrics: string;
  report: any;
  onClose: () => void;
  onSync: (note: string) => void;
}> = ({ paper, projectQuery, userMetrics, report, onClose, onSync }) => {
  const [leftWidth, setLeftWidth] = useState(450);
  const isResizing = useRef(false);

  const startResizing = (e: React.MouseEvent) => {
    isResizing.current = true;
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', stopResizing);
    document.body.style.cursor = 'col-resize';
  };

  const stopResizing = () => {
    isResizing.current = false;
    document.removeEventListener('mousemove', handleMouseMove);
    document.removeEventListener('mouseup', stopResizing);
    document.body.style.cursor = 'default';
  };

  const handleMouseMove = (e: MouseEvent) => {
    if (!isResizing.current) return;
    const newWidth = e.clientX - (window.innerWidth - 1152); // max-w-6xl is 1152px
    if (newWidth > 300 && newWidth < 800) {
      setLeftWidth(newWidth);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div className="absolute inset-0 bg-[#1a2b4c]/40 backdrop-blur-md" onClick={onClose} />
      <div className="relative w-full max-w-6xl bg-[#f1f3f8] shadow-[0_0_50px_rgba(0,0,0,0.2)] flex flex-col animate-drawer-in silicone-grain">
        {/* Drawer Header */}
        <div className="flex items-center justify-between px-8 py-6 border-b border-white/20 bg-white/40 backdrop-blur-xl">
          <div className="flex-1 min-w-0">
            <h2 className="text-xl font-black text-[#1a2b4c] truncate tracking-tight">{paper.title}</h2>
            <div className="flex gap-3 mt-1">
              <span className="text-[10px] font-black uppercase text-[#00b5ad] bg-[#00b5ad]/10 px-2 py-0.5 rounded tracking-widest">{paper.venue}</span>
              <span className="text-[10px] font-bold text-slate-400">{paper.authors} · {paper.year}</span>
            </div>
          </div>
          <div className="flex items-center gap-4 ml-4">
            {paper.url && (
              <a
                href={paper.url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 text-xs font-bold text-slate-500 hover:text-[#00b5ad] transition-colors bg-white px-4 py-2 rounded-xl border border-slate-100 shadow-sm"
              >
                <ExternalLink size={14} /> 源文件
              </a>
            )}
            <button
              onClick={onClose}
              className="p-3 hover:bg-white rounded-2xl text-slate-400 hover:text-[#1a2b4c] transition-all shadow-sm border border-transparent hover:border-slate-100"
            >
              <X size={24} />
            </button>
          </div>
        </div>

        {/* Split View Content */}
        <div className="flex-1 flex overflow-hidden relative">
          {/* Left Column: AI Summary/Metrics */}
          <div 
            className="border-r border-white/30 bg-white/20 overflow-y-auto p-8 custom-scrollbar relative"
            style={{ width: `${leftWidth}px` }}
          >
            <h3 className="text-xs font-black text-[#1a2b4c] uppercase tracking-[0.2em] mb-8 flex items-center gap-2">
              <Sparkles size={18} className="text-[#00b5ad]" />
              AI 智能解析看板
            </h3>

            <div className="space-y-8">
              <section className="silicone-flat p-6 rounded-[2rem] border border-white soft-shadow">
                <h4 className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-4">摘要精华 (Abstract)</h4>
                <div className="text-sm text-slate-600 leading-relaxed font-medium">
                  {paper.abstract || '暂无摘要'}
                </div>
              </section>

              <section className="silicone-convex p-6 rounded-[2rem] border border-white/50 accent-light">
                <h4 className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-4">关键研究指标</h4>
                <div className="space-y-4">
                  <div className="flex items-center justify-between p-3 bg-white/40 rounded-2xl border border-white/40">
                    <span className="text-xs font-bold text-slate-500">文献质量分</span>
                    <span className="text-sm font-black text-[#1a2b4c] bg-[#00b5ad]/10 text-[#00b5ad] px-3 py-1 rounded-xl">
                      {paper.score.toFixed(2)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between p-3 bg-white/40 rounded-2xl border border-white/40">
                    <span className="text-xs font-bold text-slate-500">前沿引用量</span>
                    <span className="text-sm font-black text-[#1a2b4c]">{paper.citations}</span>
                  </div>
                </div>
              </section>
            </div>
          </div>

          {/* Resize Handle */}
          <div 
            className="w-1 hover:w-2 bg-[#00b5ad]/20 hover:bg-[#00b5ad] cursor-col-resize transition-all duration-300 z-10 relative group"
            onMouseDown={startResizing}
          >
             <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-6 h-12 bg-white rounded-full border border-slate-200 hidden group-hover:flex items-center justify-center shadow-lg">
                <div className="w-1 h-4 bg-slate-200 rounded-full" />
             </div>
          </div>

          {/* Right Column: Full Markdown */}
          <div className="flex-1 overflow-y-auto p-12 custom-scrollbar bg-white/60 backdrop-blur-sm">
            <div className="prose prose-slate max-w-none">
              <ReactMarkdown
                components={{
                  p: ({ children }) => <p className="mb-4 text-slate-700 leading-8">{highlightText(children, projectQuery, userMetrics)}</p>,
                  h1: ({ children }) => <h1 className="text-3xl font-black text-[#1a2b4c] mt-12 mb-6 tracking-tight">{highlightText(children, projectQuery, userMetrics)}</h1>,
                  h2: ({ children }) => <h2 className="text-2xl font-black text-[#1a2b4c] mt-10 mb-5 tracking-tight">{highlightText(children, projectQuery, userMetrics)}</h2>,
                  h3: ({ children }) => <h3 className="text-xl font-black text-[#1a2b4c] mt-8 mb-4 tracking-tight">{highlightText(children, projectQuery, userMetrics)}</h3>,
                }}
              >
                {paper.full_text || '> ⚠️ 未提取到全文内容，仅展示摘要。\n\n' + paper.abstract}
              </ReactMarkdown>
            </div>
          </div>
        </div>

        {/* Floating Paper Chat */}
        <PaperChat
          paper={paper}
          onSync={onSync}
        />
      </div>
    </div>
  );
};

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

/**
 * Localized AI Chat Component for a specific paper
 */
const PaperChat: React.FC<{
  paper: LiteratureItem;
  onSync: (note: string) => void;
}> = ({ paper, onSync }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<{ role: 'user' | 'ai', content: string }[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [modelOptions, setModelOptions] = useState<ModelOption[]>([]);
  const [selectedModel, setSelectedModel] = useState('');

  useEffect(() => {
    async function loadModels() {
      try {
        const { models } = await getAvailableModels();
        setModelOptions(models);
        if (models.length > 0) setSelectedModel(models[0].id);
      } catch (e) {
        console.error('Failed to load models', e);
      }
    }
    loadModels();
  }, []);

  const presets = [
    { label: '📊 总结这篇论文', query: '请总结这篇论文的核心内容。' },
  ];

  const handleSend = async (text: string) => {
    if (!text.trim() || isLoading) return;

    const newMessages = [...messages, { role: 'user', content: text }] as any;
    setMessages(newMessages);
    setInput('');
    setIsLoading(true);

    try {
      const resp = await chatPaper(
        paper.id,
        text,
        messages.map(m => ({ role: m.role === 'ai' ? 'assistant' : 'user', content: m.content })),
        selectedModel
      );
      setMessages([...newMessages, { role: 'ai', content: resp.answer }]);
    } catch (e) {
      console.error('Chat failed', e);
      setMessages([...newMessages, { role: 'ai', content: '❌ 聊天请求失败，请稍后重试。' }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className={`fixed bottom-6 right-6 z-[60] flex flex-col items-end transition-all duration-300 ${isOpen ? 'w-80 h-[500px]' : 'w-12 h-12'}`}>
      {isOpen ? (
        <div className="w-full h-full flex flex-col glass-effect rounded-2xl overflow-hidden animate-in fade-in zoom-in duration-300">
          {/* Header */}
          <div className="p-4 border-b border-white/20 flex items-center justify-between bg-[#1a2b4c]/10">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#1a2b4c] to-[#22d3ee] flex items-center justify-center text-white shadow-sm">
                <Brain size={18} />
              </div>
              <div>
                <span className="font-bold text-[#1a2b4c] text-sm block leading-none">文献助理</span>
                <select
                  value={selectedModel}
                  onChange={(e) => setSelectedModel(e.target.value)}
                  className="bg-transparent border-none text-[10px] text-slate-500 p-0 h-auto focus:ring-0 cursor-pointer hover:text-[#1a2b4c] transition-colors"
                >
                  {modelOptions.map(m => <option key={m.id} value={m.id}>{m.label}</option>)}
                </select>
              </div>
            </div>
            <button onClick={() => setIsOpen(false)} className="p-1 hover:bg-black/5 rounded text-slate-500">
              <ChevronDown size={20} />
            </button>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar">
            {messages.length === 0 && (
              <div className="text-center py-4">
                <p className="text-xs text-slate-500 mb-4">您可以询问关于这篇论文的任何细节...</p>
                <div className="space-y-2">
                  {presets.map((p, i) => (
                    <button
                      key={i}
                      onClick={() => handleSend(p.query)}
                      className="w-full text-left p-2 text-xs bg-white/50 hover:bg-white/80 border border-white/20 rounded-lg transition-colors text-slate-600 flex items-center gap-2"
                    >
                      <Sparkles size={12} className="text-[#22d3ee]" />
                      {p.label}
                    </button>
                  ))}
                </div>
              </div>
            )}
            {messages.map((m, i) => (
              <div key={i} className={`flex flex-col ${m.role === 'user' ? 'items-end' : 'items-start'}`}>
                <div className={`max-w-[85%] p-3 rounded-2xl text-xs leading-relaxed ${m.role === 'user'
                  ? 'bg-[#1a2b4c] text-white rounded-tr-none'
                  : 'bg-white/80 text-slate-800 rounded-tl-none border border-white/40'
                  }`}>
                  <ReactMarkdown>{m.content}</ReactMarkdown>
                </div>
                {m.role === 'ai' && (
                  <button
                    onClick={() => onSync(m.content)}
                    className="mt-1 flex items-center gap-1 text-[10px] text-slate-400 hover:text-[#1a2b4c] transition-colors"
                    title="同步到研究报告"
                  >
                    <Plus size={10} /> 同步至报告
                  </button>
                )}
              </div>
            ))}
            {isLoading && (
              <div className="flex items-start">
                <div className="bg-white/80 p-3 rounded-2xl rounded-tl-none border border-white/40 animate-pulse">
                  <div className="flex gap-1">
                    <div className="w-1.5 h-1.5 bg-slate-300 rounded-full animate-bounce" />
                    <div className="w-1.5 h-1.5 bg-slate-300 rounded-full animate-bounce [animation-delay:0.2s]" />
                    <div className="w-1.5 h-1.5 bg-slate-300 rounded-full animate-bounce [animation-delay:0.4s]" />
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Input */}
          <div className="p-4 bg-white/30 border-t border-white/20">
            <div className="relative flex items-center">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSend(input)}
                placeholder="在此输入问题..."
                className="w-full bg-white/80 border-none rounded-xl py-2 pl-3 pr-10 text-xs focus:ring-2 focus:ring-[#1a2b4c]/20 outline-none"
              />
              <button
                onClick={() => handleSend(input)}
                disabled={!input.trim() || isLoading}
                className="absolute right-2 p-1.5 bg-[#1a2b4c] text-white rounded-lg disabled:opacity-50"
              >
                <Send size={14} />
              </button>
            </div>
          </div>
        </div>
      ) : (
        <button
          onClick={() => setIsOpen(true)}
          className="w-14 h-14 bg-gradient-to-br from-[#1a2b4c] to-[#22d3ee] text-white rounded-full shadow-xl flex items-center justify-center hover:scale-110 transition-all duration-300 animate-pulse-subtle group border-4 border-white/50"
          title="问问 AI 助理"
        >
          <div className="relative">
            <MessageSquare size={28} className="group-hover:rotate-12 transition-transform" />
            <div className="absolute -top-1 -right-1 w-3 h-3 bg-red-500 rounded-full border-2 border-white" />
          </div>
        </button>
      )}
    </div>
  );
};
