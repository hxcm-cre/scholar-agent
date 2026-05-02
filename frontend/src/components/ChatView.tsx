import React, { useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  Send,
  Loader2,
  Sparkles,
  BookOpen,
  ExternalLink,
  ChevronDown,
  Search,
  GraduationCap,
  Bot,
  User,
} from 'lucide-react';
import type { ChatMessage, ChatReply, ModelOption, PaperResult } from '../types';
import {
  sendChatMessage,
  getChatSession,
  getAvailableModels,
  connectChatWebSocket,
} from '../services/api';

interface ChatViewProps {
  sessionId: string;
  onPaperSelect: (paperId: number) => void;
  onSessionUpdate: () => void;
}

export const ChatView: React.FC<ChatViewProps> = ({
  sessionId,
  onPaperSelect,
  onSessionUpdate,
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [modelOptions, setModelOptions] = useState<ModelOption[]>([]);
  const [selectedModel, setSelectedModel] = useState('');
  const [sessionPapers, setSessionPapers] = useState<PaperResult[]>([]);
  const [initialLoading, setInitialLoading] = useState(true);
  const [currentStatus, setCurrentStatus] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Load models on mount
  useEffect(() => {
    getAvailableModels()
      .then(({ models }) => {
        setModelOptions(models);
        if (models.length > 0) setSelectedModel(models[0].id);
      })
      .catch(() => {});
  }, []);

  // WebSocket for progress updates
  useEffect(() => {
    if (!sessionId) return;
    const ws = connectChatWebSocket(sessionId, (data) => {
      if (data.type === 'progress') {
        setCurrentStatus(data.detail);
      }
    });
    return () => ws.close();
  }, [sessionId]);

  // Load session messages
  useEffect(() => {
    setInitialLoading(true);
    setMessages([]);
    setSessionPapers([]);
    setCurrentStatus(null);
    getChatSession(sessionId)
      .then(detail => {
        // Filter out tool messages for display
        const displayMessages = detail.messages.filter(m => m.role !== 'tool');
        setMessages(displayMessages);

        // Extract paper results from tool messages
        const papers: PaperResult[] = [];
        detail.messages
          .filter(m => m.role === 'tool' && m.tool_name === 'scholar_search')
          .forEach(m => {
            try {
              const data = JSON.parse(m.content);
              if (data.papers) papers.push(...data.papers);
            } catch { /* ignore */ }
          });
        setSessionPapers(papers);

        if (detail.model_name) setSelectedModel(detail.model_name);
      })
      .catch(() => {})
      .finally(() => setInitialLoading(false));
  }, [sessionId]);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  // Focus input on session change
  useEffect(() => {
    inputRef.current?.focus();
  }, [sessionId, isLoading]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || isLoading) return;

    // Optimistic UI: add user message immediately
    const userMsg: ChatMessage = {
      id: Date.now(),
      role: 'user',
      content: text,
      tool_name: null,
      paper_refs: [],
      created_at: new Date().toISOString(),
    };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);
    setCurrentStatus('AI 思考中...');

    try {
      const reply: ChatReply = await sendChatMessage(sessionId, text, selectedModel);

      // Add assistant reply
      const assistantMsg: ChatMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: reply.reply,
        tool_name: reply.tool_used,
        paper_refs: [],
        created_at: new Date().toISOString(),
      };
      setMessages(prev => [...prev, assistantMsg]);

      // Update session papers if search was performed
      if (reply.papers && reply.papers.length > 0) {
        setSessionPapers(prev => {
          const existing = new Set(prev.map(p => p.id));
          const newPapers = reply.papers.filter(p => !existing.has(p.id));
          return [...prev, ...newPapers];
        });
      }

      onSessionUpdate(); // refresh sidebar title
    } catch (e) {
      const errorMsg: ChatMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: '❌ 消息发送失败，请检查后端是否运行。',
        tool_name: null,
        paper_refs: [],
        created_at: new Date().toISOString(),
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
      setCurrentStatus(null);
    }
  };

  const quickActions = [
    { icon: <Search size={14} />, label: '搜索论文', prompt: '帮我搜索关于 ' },
    { icon: <BookOpen size={14} />, label: '总结论文', prompt: '请总结第 1 篇论文的核心内容' },
    { icon: <Sparkles size={14} />, label: '研究建议', prompt: '基于我搜索到的论文，给我一些研究方向的建议' },
  ];

  if (initialLoading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <Loader2 className="animate-spin text-white/20" size={32} />
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden">
      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto custom-scrollbar">
        {messages.length === 0 ? (
          /* Empty State */
          <div className="flex flex-col items-center justify-center h-full px-8">
            <div className="size-20 rounded-3xl bg-gradient-to-br from-cyan-400/20 to-indigo-500/20 flex items-center justify-center mb-6 border border-white/5">
              <GraduationCap size={40} className="text-cyan-400/60" />
            </div>
            <h2 className="text-2xl font-black text-white/80 mb-2 tracking-tight">Scholar-Agent</h2>
            <p className="text-sm text-white/30 mb-10 font-medium">你的 AI 学术研究助手，随时为你检索和分析论文</p>

            <div className="flex gap-3 flex-wrap justify-center max-w-lg">
              {quickActions.map((action, i) => (
                <button
                  key={i}
                  onClick={() => setInput(action.prompt)}
                  className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold
                    bg-white/5 hover:bg-white/10 text-white/50 hover:text-white/80
                    border border-white/5 hover:border-white/15
                    transition-all duration-200"
                >
                  {action.icon}
                  {action.label}
                </button>
              ))}
            </div>
          </div>
        ) : (
          /* Message List */
          <div className="max-w-3xl mx-auto py-6 px-4 space-y-1">
            {messages.map((msg) => (
              <MessageBubble
                key={msg.id}
                message={msg}
                sessionPapers={sessionPapers}
                onPaperSelect={onPaperSelect}
              />
            ))}

            {/* Loading indicator */}
            {isLoading && (
              <div className="flex items-start gap-3 py-4 px-2">
                <div className="size-8 rounded-xl bg-gradient-to-br from-cyan-500 to-indigo-500 flex items-center justify-center shrink-0 shadow-lg shadow-cyan-500/10">
                  <Bot size={16} className="text-white" />
                </div>
                <div className="flex flex-col gap-2">
                  <div className="bg-white/5 border border-white/10 rounded-2xl rounded-tl-md px-4 py-3 flex items-center gap-3">
                    <div className="flex gap-1.5">
                      <div className="w-1.5 h-1.5 bg-cyan-400/50 rounded-full animate-bounce" />
                      <div className="w-1.5 h-1.5 bg-cyan-400/50 rounded-full animate-bounce [animation-delay:0.15s]" />
                      <div className="w-1.5 h-1.5 bg-cyan-400/50 rounded-full animate-bounce [animation-delay:0.3s]" />
                    </div>
                    {currentStatus && (
                      <span className="text-[11px] font-bold text-white/40 animate-pulse">
                        {currentStatus}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input Area */}
      <div className="border-t border-white/5 bg-[#0f1729]/50 backdrop-blur-xl">
        <div className="max-w-3xl mx-auto px-4 py-4">
          {/* Model selector */}
          <div className="flex items-center gap-2 mb-3">
            <span className="text-[10px] font-bold text-white/20 uppercase tracking-wider">模型</span>
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="bg-transparent border border-white/10 rounded-lg text-[11px] text-white/50 px-2 py-1 focus:ring-0 focus:border-white/20 cursor-pointer hover:text-white/70 transition-colors appearance-none"
            >
              {modelOptions.map(m => (
                <option key={m.id} value={m.id} className="bg-[#1a2744]">{m.label}</option>
              ))}
            </select>
          </div>

          {/* Input box */}
          <div className="relative flex items-center">
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()}
              placeholder="输入你的研究问题..."
              disabled={isLoading}
              className="w-full bg-white/5 border border-white/10 rounded-2xl py-3.5 pl-5 pr-14
                text-sm text-white/90 placeholder:text-white/20
                focus:ring-1 focus:ring-cyan-400/30 focus:border-cyan-400/30
                outline-none transition-all disabled:opacity-50"
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || isLoading}
              className="absolute right-2 p-2.5 bg-gradient-to-r from-cyan-500 to-indigo-500
                text-white rounded-xl disabled:opacity-30 disabled:cursor-not-allowed
                hover:shadow-lg hover:shadow-cyan-500/20 transition-all duration-200
                active:scale-95"
            >
              <Send size={16} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};


// ---------------------------------------------------------------------------
// Message Bubble Sub-Component
// ---------------------------------------------------------------------------
const MessageBubble: React.FC<{
  message: ChatMessage;
  sessionPapers: PaperResult[];
  onPaperSelect: (paperId: number) => void;
}> = ({ message, sessionPapers, onPaperSelect }) => {
  const isUser = message.role === 'user';
  const isSearch = message.tool_name === 'scholar_search';

  return (
    <div className={`flex items-start gap-3 py-3 px-2 ${isUser ? 'flex-row-reverse' : ''}`}>
      {/* Avatar */}
      <div className={`size-8 rounded-xl flex items-center justify-center shrink-0 shadow-lg ${
        isUser
          ? 'bg-gradient-to-br from-indigo-500 to-purple-500 shadow-indigo-500/10'
          : 'bg-gradient-to-br from-cyan-500 to-indigo-500 shadow-cyan-500/10'
      }`}>
        {isUser ? <User size={16} className="text-white" /> : <Bot size={16} className="text-white" />}
      </div>

      {/* Content */}
      <div className={`max-w-[80%] ${isUser ? 'items-end' : 'items-start'}`}>
        <div className={`rounded-2xl px-4 py-3 text-sm leading-relaxed ${
          isUser
            ? 'bg-gradient-to-r from-indigo-500/80 to-purple-500/80 text-white rounded-tr-md'
            : 'bg-white/5 border border-white/8 text-white/80 rounded-tl-md'
        }`}>
          {isUser ? (
            <p>{message.content}</p>
          ) : (
            <div className="prose prose-invert prose-sm max-w-none prose-p:my-2 prose-headings:text-white/90 prose-strong:text-white/90 prose-li:text-white/70">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {message.content}
              </ReactMarkdown>
            </div>
          )}
        </div>

        {/* Paper cards — shown when search results are mentioned */}
        {!isUser && isSearch && sessionPapers.length > 0 && (
          <div className="mt-3 space-y-2">
            {sessionPapers.slice(-10).map(paper => (
              <PaperCard key={paper.id} paper={paper} onSelect={() => onPaperSelect(paper.id)} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};


// ---------------------------------------------------------------------------
// Paper Card Sub-Component
// ---------------------------------------------------------------------------
const PaperCard: React.FC<{
  paper: PaperResult;
  onSelect: () => void;
}> = ({ paper, onSelect }) => (
  <div
    className="p-3.5 rounded-xl bg-white/[0.03] border border-white/8 hover:border-cyan-400/20
      hover:bg-white/[0.06] transition-all duration-200 cursor-pointer group"
    onClick={onSelect}
  >
    <div className="flex items-start justify-between gap-3">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-[10px] font-black text-cyan-400 bg-cyan-400/10 px-1.5 py-0.5 rounded">
            [{paper.index}]
          </span>
          <span className="text-xs font-bold text-white/70 truncate group-hover:text-white/90 transition-colors">
            {paper.title}
          </span>
        </div>
        <div className="flex items-center gap-2 text-[10px] text-white/30">
          {paper.venue && <span className="font-bold uppercase">{paper.venue}</span>}
          {paper.year && <span>{paper.year}</span>}
          {paper.citations > 0 && (
            <span className="flex items-center gap-0.5">
              <ExternalLink size={8} /> {paper.citations}
            </span>
          )}
          {paper.score > 0 && (
            <span className="text-cyan-400/60">⭐ {paper.score.toFixed(1)}</span>
          )}
        </div>
      </div>
      <button
        onClick={(e) => { e.stopPropagation(); onSelect(); }}
        className="text-[10px] font-bold text-white/30 hover:text-cyan-400 px-2 py-1
          border border-white/10 hover:border-cyan-400/30 rounded-lg transition-all shrink-0"
      >
        <BookOpen size={12} />
      </button>
    </div>
  </div>
);
