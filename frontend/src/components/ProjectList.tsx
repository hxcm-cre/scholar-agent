import React, { useEffect, useState } from 'react';
import { Plus, Search, Trash2, Clock, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';
import type { Project } from '../types';
import { getProjects, deleteProject } from '../services/api';

interface ProjectListProps {
  onSelect: (id: number) => void;
  onNew: () => void;
  refreshKey: number;
}

const STATUS_CONFIG = {
  pending: { icon: Clock, color: 'text-amber-500', bg: 'bg-amber-50 border-amber-200', label: '排队中' },
  running: { icon: Loader2, color: 'text-blue-500', bg: 'bg-blue-50 border-blue-200', label: '运行中', animate: true },
  done:    { icon: CheckCircle2, color: 'text-emerald-500', bg: 'bg-emerald-50 border-emerald-200', label: '已完成' },
  error:   { icon: AlertCircle, color: 'text-red-500', bg: 'bg-red-50 border-red-200', label: '失败' },
} as const;

export const ProjectList: React.FC<ProjectListProps> = ({ onSelect, onNew, refreshKey }) => {
  const [projects, setProjects] = useState<Project[]>([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);

  const load = async () => {
    try {
      const data = await getProjects();
      setProjects(data);
    } catch (e) {
      console.error('Failed to load projects', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [refreshKey]);

  // Auto-refresh when there are running tasks
  useEffect(() => {
    const hasRunning = projects.some(p => p.status === 'running' || p.status === 'pending');
    if (!hasRunning) return;
    const timer = setInterval(load, 5000);
    return () => clearInterval(timer);
  }, [projects]);

  const filtered = projects.filter(p =>
    p.query.toLowerCase().includes(search.toLowerCase())
  );

  const handleDelete = async (e: React.MouseEvent, id: number) => {
    e.stopPropagation();
    if (!confirm('确定删除此研究任务？')) return;
    await deleteProject(id);
    load();
  };

  const grouped = {
    running: filtered.filter(p => p.status === 'running' || p.status === 'pending'),
    done: filtered.filter(p => p.status === 'done'),
    error: filtered.filter(p => p.status === 'error'),
  };

  return (
    <div className="flex-1 overflow-y-auto p-8 custom-scrollbar">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h2 className="text-2xl font-bold text-[#1a2b4c]">研究任务看板</h2>
            <p className="text-sm text-slate-500 mt-1">管理你的所有学术研究任务</p>
          </div>
          <button
            onClick={onNew}
            className="bg-[#22d3ee] hover:bg-cyan-400 text-[#1a2b4c] font-bold py-3 px-6 rounded-xl flex items-center gap-2 shadow-lg shadow-cyan-500/20 transition-all transform hover:-translate-y-0.5"
          >
            <Plus size={20} />
            新建研究
          </button>
        </div>

        {/* Search */}
        <div className="relative mb-6">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="搜索研究任务..."
            className="w-full h-12 bg-white border border-slate-200 rounded-xl px-4 pr-10 text-sm focus:border-[#1a2b4c] focus:ring-0 outline-none placeholder:text-slate-400 transition-colors shadow-sm"
          />
          <Search className="absolute right-3 top-3.5 text-slate-300" size={18} />
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="animate-spin text-slate-400" size={32} />
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-20 text-slate-400">
            <p className="text-lg mb-2">暂无研究任务</p>
            <p className="text-sm">点击"新建研究"开始你的第一个学术调研</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Running column */}
            <Column title="进行中" count={grouped.running.length} color="blue">
              {grouped.running.map(p => (
                <ProjectCard key={p.id} project={p} onClick={() => onSelect(p.id)} onDelete={handleDelete} />
              ))}
            </Column>
            {/* Done column */}
            <Column title="已完成" count={grouped.done.length} color="emerald">
              {grouped.done.map(p => (
                <ProjectCard key={p.id} project={p} onClick={() => onSelect(p.id)} onDelete={handleDelete} />
              ))}
            </Column>
            {/* Error column */}
            <Column title="失败" count={grouped.error.length} color="red">
              {grouped.error.map(p => (
                <ProjectCard key={p.id} project={p} onClick={() => onSelect(p.id)} onDelete={handleDelete} />
              ))}
            </Column>
          </div>
        )}
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------
const Column: React.FC<{ title: string; count: number; color: string; children: React.ReactNode }> = ({ title, count, color, children }) => (
  <div>
    <div className="flex items-center gap-2 mb-4">
      <div className={`w-2 h-2 rounded-full bg-${color}-500`} />
      <h3 className="text-sm font-bold text-slate-600 uppercase tracking-wider">{title}</h3>
      <span className="text-xs text-slate-400 ml-auto">{count}</span>
    </div>
    <div className="space-y-3 min-h-[120px]">
      {children}
    </div>
  </div>
);

const ProjectCard: React.FC<{
  project: Project;
  onClick: () => void;
  onDelete: (e: React.MouseEvent, id: number) => void;
}> = ({ project, onClick, onDelete }) => {
  const cfg = STATUS_CONFIG[project.status] || STATUS_CONFIG.pending;
  const Icon = cfg.icon;
  const time = new Date(project.created_at).toLocaleString('zh-CN', {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
  });

  return (
    <div
      onClick={onClick}
      className={`p-4 rounded-xl border cursor-pointer transition-all hover:shadow-md hover:-translate-y-0.5 bg-white ${cfg.bg.split(' ')[1] || 'border-slate-200'}`}
    >
      <div className="flex items-start justify-between mb-2">
        <Icon size={16} className={`${cfg.color} mt-0.5 ${'animate' in cfg ? 'animate-spin' : ''}`} />
        <button
          onClick={(e) => onDelete(e, project.id)}
          className="text-slate-300 hover:text-red-400 transition-colors p-1 -m-1"
        >
          <Trash2 size={14} />
        </button>
      </div>
      <p className="text-sm font-semibold text-[#1a2b4c] line-clamp-2 mb-2">{project.query}</p>
      <div className="flex items-center justify-between text-[10px] text-slate-400">
        <span>{project.model_name}</span>
        <span>{time}</span>
      </div>
    </div>
  );
};
