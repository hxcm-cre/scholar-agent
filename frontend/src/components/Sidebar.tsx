import React, { useEffect, useState } from 'react';
import {
  GraduationCap,
  Network,
  FileText,
  Cpu,
  Github,
  History,
  Home,
} from 'lucide-react';
import type { Project } from '../types';
import { getProjects } from '../services/api';

interface SidebarProps {
  currentView: 'home' | 'config' | 'workflow' | 'report';
  onNavigateHome: () => void;
  onSelectProject: (id: number) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ currentView, onNavigateHome, onSelectProject }) => {
  const [recentProjects, setRecentProjects] = useState<Project[]>([]);

  useEffect(() => {
    getProjects()
      .then(data => setRecentProjects(data.slice(0, 8)))
      .catch(() => {});
  }, [currentView]);

  return (
    <aside className="w-72 bg-[#1a2b4c] text-white flex flex-col shrink-0 h-screen">
      {/* Logo */}
      <div className="p-6 border-b border-white/10">
        <div className="flex items-center gap-3 cursor-pointer" onClick={onNavigateHome}>
          <div className="size-10 bg-[#22d3ee] rounded-lg flex items-center justify-center text-[#1a2b4c]">
            <GraduationCap size={24} strokeWidth={2.5} />
          </div>
          <div>
            <h1 className="text-lg font-bold leading-tight">Scholar-Agent</h1>
            <p className="text-xs text-slate-300">Academic Intelligence</p>
          </div>
        </div>
      </div>

      {/* Nav */}
      <div className="p-4 space-y-1">
        <button
          onClick={onNavigateHome}
          className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
            currentView === 'home'
              ? 'bg-white/10 text-white'
              : 'text-slate-400 hover:text-white hover:bg-white/5'
          }`}
        >
          <Home size={18} />
          任务看板
        </button>
      </div>

      {/* Recent projects */}
      <div className="flex-1 overflow-y-auto px-4 pb-4 custom-scrollbar">
        <div className="flex items-center gap-2 px-3 py-2 mb-1">
          <History size={14} className="text-slate-500" />
          <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">近期任务</span>
        </div>
        <div className="space-y-0.5">
          {recentProjects.map(p => (
            <button
              key={p.id}
              onClick={() => onSelectProject(p.id)}
              className="w-full text-left px-3 py-2 rounded-lg text-xs text-slate-400 hover:text-white hover:bg-white/5 transition-colors line-clamp-1"
              title={p.query}
            >
              <span className={`inline-block w-1.5 h-1.5 rounded-full mr-2 ${
                p.status === 'done' ? 'bg-emerald-400' :
                p.status === 'running' ? 'bg-blue-400' :
                p.status === 'error' ? 'bg-red-400' : 'bg-slate-500'
              }`} />
              {p.query.length > 28 ? p.query.slice(0, 28) + '…' : p.query}
            </button>
          ))}
          {recentProjects.length === 0 && (
            <p className="text-[10px] text-slate-500 px-3 py-2">暂无任务</p>
          )}
        </div>
      </div>

      {/* Footer */}
      <div className="p-6 border-t border-white/10 bg-black/10">
        <div className="flex items-center justify-between mb-4">
          <div className="flex gap-3 text-slate-400">
            <Network size={18} className="hover:text-[#22d3ee] cursor-help" title="LangGraph Engine" />
            <FileText size={18} className="hover:text-[#22d3ee] cursor-help" title="Docling Parser" />
            <Cpu size={18} className="hover:text-[#22d3ee] cursor-help" title="Local LLM Enabled" />
          </div>
          <a href="https://github.com" target="_blank" rel="noopener noreferrer" className="text-slate-400 hover:text-white">
            <Github size={20} />
          </a>
        </div>
        <div className="text-[10px] text-slate-500 font-mono">License: GPL-3.0</div>
      </div>
    </aside>
  );
};
