import React, { useEffect, useState } from 'react';
import {
  GraduationCap,
  MessageSquarePlus,
  MessageSquare,
  Trash2,
  Network,
  FileText,
  Cpu,
  Github,
} from 'lucide-react';
import type { ChatSession } from '../types';
import { getChatSessions, deleteChatSession } from '../services/api';

interface SidebarProps {
  activeSessionId: string | null;
  onSelectSession: (id: string) => void;
  onNewSession: () => void;
  refreshKey: number;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeSessionId,
  onSelectSession,
  onNewSession,
  refreshKey,
}) => {
  const [sessions, setSessions] = useState<ChatSession[]>([]);

  useEffect(() => {
    getChatSessions()
      .then(data => setSessions(data))
      .catch(() => {});
  }, [refreshKey, activeSessionId]);

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (!confirm('确定删除此对话？')) return;
    try {
      await deleteChatSession(id);
      setSessions(prev => prev.filter(s => s.id !== id));
      if (activeSessionId === id) {
        onNewSession();
      }
    } catch {
      // ignore
    }
  };

  return (
    <aside className="w-72 glass-sidebar text-[#e2e8f0] flex flex-col shrink-0 h-screen">
      {/* Logo */}
      <div className="p-5 pb-3">
        <div className="flex items-center gap-3 cursor-pointer group" onClick={onNewSession}>
          <div className="size-11 rounded-2xl flex items-center justify-center bg-gradient-to-br from-cyan-400 to-indigo-500 shadow-lg shadow-cyan-500/20 transition-transform group-hover:scale-105 duration-300">
            <GraduationCap size={24} strokeWidth={2.5} className="text-white" />
          </div>
          <div className="overflow-hidden">
            <h1 className="text-lg font-black leading-tight tracking-tight text-white">Scholar-Agent</h1>
            <p className="text-[9px] font-bold uppercase tracking-[0.2em] gradient-text-slogan">AI Research Assistant</p>
          </div>
        </div>
      </div>

      {/* New Chat Button */}
      <div className="px-4 pb-3">
        <button
          onClick={onNewSession}
          className="w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-bold transition-all duration-300 bg-white/10 hover:bg-white/20 text-white/90 border border-white/10 hover:border-white/20 shadow-sm"
        >
          <MessageSquarePlus size={18} strokeWidth={2.5} />
          新建对话
        </button>
      </div>

      {/* Session List */}
      <div className="flex-1 overflow-y-auto px-3 pb-4 custom-scrollbar">
        <div className="flex items-center gap-2 px-3 py-2 mb-1">
          <MessageSquare size={12} className="text-white/30" />
          <span className="text-[10px] font-bold uppercase tracking-widest text-white/30">历史对话</span>
        </div>
        <div className="space-y-1">
          {sessions.map(s => (
            <button
              key={s.id}
              onClick={() => onSelectSession(s.id)}
              className={`w-full text-left px-3 py-2.5 rounded-xl text-xs font-medium transition-all duration-200 flex items-center justify-between group ${
                activeSessionId === s.id
                  ? 'bg-white/15 text-white border border-white/20 shadow-sm'
                  : 'text-white/50 hover:text-white/80 hover:bg-white/8 border border-transparent'
              }`}
              title={s.title}
            >
              <span className="truncate flex-1 mr-2">{s.title}</span>
              <button
                onClick={(e) => handleDelete(e, s.id)}
                className="opacity-0 group-hover:opacity-100 p-1 hover:bg-white/10 rounded transition-all shrink-0"
                title="删除对话"
              >
                <Trash2 size={12} className="text-white/40 hover:text-red-400" />
              </button>
            </button>
          ))}
          {sessions.length === 0 && (
            <p className="text-[10px] text-white/20 px-3 py-4 italic font-medium text-center">
              尚无对话记录...
            </p>
          )}
        </div>
      </div>

      {/* Footer */}
      <div className="p-4 mt-auto border-t border-white/5">
        <div className="flex items-center justify-between px-1">
          <div className="flex gap-3 text-white/20">
            <span title="LangGraph Engine"><Network size={16} className="hover:text-cyan-400 cursor-help transition-colors" /></span>
            <span title="Docling Parser"><FileText size={16} className="hover:text-cyan-400 cursor-help transition-colors" /></span>
            <span title="Local LLM"><Cpu size={16} className="hover:text-cyan-400 cursor-help transition-colors" /></span>
          </div>
          <a href="https://github.com" target="_blank" rel="noopener noreferrer" className="text-white/20 hover:text-white/60 transition-colors">
            <Github size={16} />
          </a>
        </div>
      </div>
    </aside>
  );
};
