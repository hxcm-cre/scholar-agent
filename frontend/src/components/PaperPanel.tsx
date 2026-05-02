import React, { useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  X,
  ExternalLink,
  Loader2,
  BookOpen,
  Calendar,
  Users,
  Award,
} from 'lucide-react';
import type { LiteratureItem } from '../types';
import { getLiterature } from '../services/api';

interface PaperPanelProps {
  paperId: number;
  onClose: () => void;
}

export const PaperPanel: React.FC<PaperPanelProps> = ({ paperId, onClose }) => {
  const [paper, setPaper] = useState<LiteratureItem | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getLiterature(paperId)
      .then(data => setPaper(data))
      .catch(() => setPaper(null))
      .finally(() => setLoading(false));
  }, [paperId]);

  if (loading) {
    return (
      <div className="w-[500px] border-l border-white/5 bg-[#0d1321] flex items-center justify-center">
        <Loader2 className="animate-spin text-white/20" size={28} />
      </div>
    );
  }

  if (!paper) {
    return (
      <div className="w-[500px] border-l border-white/5 bg-[#0d1321] flex items-center justify-center text-white/30 text-sm">
        论文未找到
      </div>
    );
  }

  const content = paper.full_text || paper.abstract || '暂无内容';

  return (
    <div className="w-[500px] border-l border-white/5 bg-[#0d1321] flex flex-col h-full animate-slide-in-right">
      {/* Header */}
      <div className="p-5 border-b border-white/5 bg-white/[0.02]">
        <div className="flex items-start justify-between gap-3 mb-4">
          <h2 className="text-base font-black text-white/90 leading-tight tracking-tight line-clamp-2">
            {paper.title}
          </h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-white/5 rounded-xl text-white/30 hover:text-white/60 transition-all shrink-0"
          >
            <X size={18} />
          </button>
        </div>

        {/* Meta tags */}
        <div className="flex flex-wrap gap-2 mb-3">
          {paper.venue && (
            <span className="flex items-center gap-1 px-2 py-1 bg-cyan-400/10 text-cyan-400/80 rounded-lg text-[10px] font-black uppercase tracking-wider">
              <Award size={10} />
              {paper.venue}
            </span>
          )}
          {paper.year && (
            <span className="flex items-center gap-1 px-2 py-1 bg-white/5 text-white/40 rounded-lg text-[10px] font-bold">
              <Calendar size={10} />
              {paper.year}
            </span>
          )}
          {paper.citations > 0 && (
            <span className="flex items-center gap-1 px-2 py-1 bg-white/5 text-white/40 rounded-lg text-[10px] font-bold">
              <ExternalLink size={10} />
              引用 {paper.citations}
            </span>
          )}
          {paper.score > 0 && (
            <span className="px-2 py-1 bg-amber-400/10 text-amber-400/80 rounded-lg text-[10px] font-bold">
              ⭐ {paper.score.toFixed(2)}
            </span>
          )}
        </div>

        {/* Authors */}
        {paper.authors && (
          <div className="flex items-center gap-1.5 text-[11px] text-white/30 font-medium">
            <Users size={12} />
            <span className="truncate">{paper.authors}</span>
          </div>
        )}

        {/* Link */}
        {paper.url && (
          <a
            href={paper.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 mt-3 text-[11px] font-bold text-cyan-400/60 hover:text-cyan-400 transition-colors"
          >
            <ExternalLink size={12} />
            查看原文
          </a>
        )}
      </div>

      {/* Scrollable Content Area */}
      <div className="flex-1 overflow-y-auto custom-scrollbar">
        {/* Abstract */}
        {paper.abstract && (
          <div className="px-5 py-4 border-b border-white/5">
            <h3 className="text-[10px] font-black text-white/20 uppercase tracking-widest mb-2 flex items-center gap-1.5">
              <BookOpen size={12} />
              摘要
            </h3>
            <p className="text-xs text-white/50 leading-relaxed">{paper.abstract}</p>
          </div>
        )}

        {/* Full Text */}
        <div className="px-5 py-4">
          <h3 className="text-[10px] font-black text-white/20 uppercase tracking-widest mb-3">
            全文内容
          </h3>
          <div className="prose prose-invert prose-sm max-w-none
            prose-p:text-white/50 prose-p:leading-relaxed prose-p:text-xs
            prose-headings:text-white/70 prose-headings:font-black prose-headings:tracking-tight
            prose-strong:text-white/60
            prose-li:text-white/50 prose-li:text-xs
            prose-code:text-cyan-400/60 prose-code:bg-white/5 prose-code:px-1 prose-code:rounded
            prose-table:text-xs">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {content}
            </ReactMarkdown>
          </div>
        </div>
      </div>
    </div>
  );
};
