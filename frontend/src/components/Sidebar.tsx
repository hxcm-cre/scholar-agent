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

export const Sidebar: React.FC<SidebarProps> = ({ 
  currentView, 
  onNavigateHome, 
  onSelectProject, 
}) => {
  const [recentProjects, setRecentProjects] = useState<Project[]>([]);

  useEffect(() => {
    getProjects()
      .then(data => setRecentProjects(data.slice(0, 8)))
      .catch(() => {});
  }, [currentView]);

  return (
    <aside className="w-72 glass-effect text-[#1a2b4c] flex flex-col shrink-0 h-screen border-r border-white/20 silicone-grain">
      {/* Logo */}
      <div className="p-6">
        <div className="flex items-center gap-3 cursor-pointer group" onClick={onNavigateHome}>
          <div className="size-12 silicone-convex rounded-2xl flex items-center justify-center text-[#1a2b4c] transition-transform group-hover:scale-105 duration-300">
            <GraduationCap size={28} strokeWidth={2.5} className="text-[#00b5ad]" />
          </div>
          <div className="overflow-hidden">
            <h1 className="text-xl font-black leading-tight tracking-tight text-[#1a2b4c]">Scholar-Agent</h1>
            <p className="text-[10px] font-bold uppercase tracking-[0.2em] gradient-text-slogan">AI Research Assistant</p>
          </div>
        </div>
      </div>

      {/* Nav */}
      <div className="p-4 space-y-2">
        <button
          onClick={onNavigateHome}
          className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-bold transition-all duration-300 ${
            currentView === 'home'
              ? 'silicone-pressed text-[#00b5ad] shadow-inner'
              : 'text-slate-500 hover:text-[#1a2b4c] hover:bg-white/40'
          }`}
        >
          <Home size={18} strokeWidth={2.5} />
          任务看板
        </button>
      </div>

      {/* Recent projects */}
      <div className="flex-1 overflow-y-auto px-4 pb-4 custom-scrollbar">
        <div className="flex items-center gap-2 px-4 py-2 mb-2">
          <History size={14} className="text-slate-400" />
          <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">历史回顾</span>
        </div>
        <div className="space-y-1.5">
          {recentProjects.map(p => (
            <button
              key={p.id}
              onClick={() => onSelectProject(p.id)}
              className="w-full text-left px-4 py-2.5 rounded-xl text-xs font-medium text-slate-500 hover:text-[#1a2b4c] hover:bg-white/40 transition-all duration-200 line-clamp-1 border border-transparent hover:border-white/20 hover:shadow-sm"
              title={p.query}
            >
              <span className={`inline-block w-2 h-2 rounded-full mr-2 shadow-sm ${
                p.status === 'done' ? 'bg-emerald-400' :
                p.status === 'running' ? 'bg-blue-400 animate-pulse' :
                p.status === 'error' ? 'bg-red-400' : 'bg-slate-300'
              }`} />
              {p.query}
            </button>
          ))}
          {recentProjects.length === 0 && (
            <p className="text-[10px] text-slate-400 px-4 py-2 italic font-medium">尚无研究足迹...</p>
          )}
        </div>
      </div>

      {/* Footer Profile */}
      <div className="p-6 mt-auto border-t border-white/10 bg-white/5 backdrop-blur-md">
        <div className="flex items-center gap-3 mb-6 p-2 rounded-2xl bg-white/20 border border-white/30 shadow-sm accent-light">
          <div className="size-10 rounded-xl bg-gradient-to-br from-[#1a2b4c] to-[#00b5ad] flex items-center justify-center text-white font-bold shadow-md">
            SR
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-bold text-[#1a2b4c] truncate">Senior Researcher</p>
            <p className="text-[10px] text-slate-500 font-medium">Free Tier</p>
          </div>
        </div>
        <div className="flex items-center justify-between px-1">
          <div className="flex gap-4 text-slate-400">
            <span title="LangGraph Engine"><Network size={18} className="hover:text-[#00b5ad] cursor-help transition-colors" /></span>
            <span title="Docling Parser"><FileText size={18} className="hover:text-[#00b5ad] cursor-help transition-colors" /></span>
            <span title="Local LLM Enabled"><Cpu size={18} className="hover:text-[#00b5ad] cursor-help transition-colors" /></span>
          </div>
          <a href="https://github.com" target="_blank" rel="noopener noreferrer" className="size-8 silicone-convex rounded-lg flex items-center justify-center text-slate-500 hover:text-[#1a2b4c] transition-all">
            <Github size={18} />
          </a>
        </div>
      </div>
    </aside>
  );
};
