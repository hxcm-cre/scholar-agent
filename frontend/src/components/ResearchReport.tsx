import React, { useEffect, useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import ReactMarkdown from 'react-markdown';
import { Download, BarChart3, ShieldCheck, ArrowLeft, Loader2, BookOpen } from 'lucide-react';
import type { ProjectDetail, LiteratureItem } from '../types';
import { getProject } from '../services/api';

interface ResearchReportProps {
  projectId: number;
  onBack: () => void;
}

export const ResearchReport: React.FC<ResearchReportProps> = ({ projectId, onBack }) => {
  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [loading, setLoading] = useState(true);

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
            <span>创建: {new Date(project.created_at).toLocaleString('zh-CN')}</span>
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
                    <div className="flex gap-3 shrink-0 text-[10px] text-slate-400">
                      {lit.citations > 0 && <span>🔗 {lit.citations}</span>}
                      {lit.score > 0 && <span>⭐ {lit.score.toFixed(2)}</span>}
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
                  blockquote: ({node, ...props}) => (
                    <div className="my-6 p-5 bg-[#22d3ee]/10 border-l-4 border-[#22d3ee] rounded-r-xl">
                      <h4 className="font-bold text-[#1a2b4c] flex items-center gap-2 mb-2">
                        <ShieldCheck size={16} />
                        Performance Comparison
                      </h4>
                      <div className="text-[#1a2b4c]/80 font-medium italic" {...props} />
                    </div>
                  ),
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

        <div className="mt-6 text-center">
          <p className="text-slate-400 text-xs flex items-center justify-center gap-2">
            <ShieldCheck size={14} />
            All research data is processed via RAG-enabled Docling architecture.
          </p>
        </div>
      </div>
    </section>
  );
};
