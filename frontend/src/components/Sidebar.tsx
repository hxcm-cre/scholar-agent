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
import type { Project, User } from '../types';
import { getProjects } from '../services/api';
import { LogOut, ShieldCheck } from 'lucide-react';

interface SidebarProps {
  currentView: 'home' | 'config' | 'workflow' | 'report';
  onNavigateHome: () => void;
  onSelectProject: (id: number) => void;
  user: User | null;
  onLogout: () => void;
  onNavigateAdmin: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ 
  currentView, 
  onNavigateHome, 
  onSelectProject, 
  user,
  onLogout,
  onNavigateAdmin 
}) => {
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

        {user?.is_admin && (
          <button
            onClick={onNavigateAdmin}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
              currentView === 'home' && false // placeholder for admin view check
                ? 'bg-white/10 text-white'
                : 'text-slate-400 hover:text-white hover:bg-white/5'
            }`}
          >
            <ShieldCheck size={18} />
            后台管理
          </button>
        )}
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

      {/* Footer / User Profile */}
      <div className="p-4 border-t border-white/10 bg-black/10">
        <div className="flex items-center gap-3 px-2 mb-4">
          <div className="size-8 bg-[#22d3ee] rounded-full flex items-center justify-center text-[#1a2b4c] font-bold text-xs shrink-0">
            {user?.username.charAt(0).toUpperCase()}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold truncate">{user?.username}</p>
            <p className="text-[10px] text-slate-400 truncate">{user?.is_admin ? '管理员' : '研究员'}</p>
          </div>
          <button
            onClick={onLogout}
            className="p-1.5 text-slate-500 hover:text-red-400 hover:bg-red-400/10 rounded-md transition-all"
            title="退出登录"
          >
            <LogOut size={16} />
          </button>
        </div>

        <div className="flex items-center justify-between px-2">
          <div className="flex gap-3 text-slate-500">
            <span title="LangGraph Engine"><Network size={16} className="hover:text-[#22d3ee] cursor-help" /></span>
            <span title="Docling Parser"><FileText size={16} className="hover:text-[#22d3ee] cursor-help" /></span>
            <span title="Local LLM Enabled"><Cpu size={16} className="hover:text-[#22d3ee] cursor-help" /></span>
          </div>
          <a href="https://github.com" target="_blank" rel="noopener noreferrer" className="text-slate-500 hover:text-white">
            <Github size={18} />
          </a>
        </div>
      </div>
    </aside>
  );
};
