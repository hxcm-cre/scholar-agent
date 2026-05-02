import { useState, useCallback } from 'react';
import { Sidebar } from './components/Sidebar';
import { ChatView } from './components/ChatView';
import { PaperPanel } from './components/PaperPanel';
import { createChatSession } from './services/api';

export default function App() {
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [selectedPaperId, setSelectedPaperId] = useState<number | null>(null);

  const handleNewSession = useCallback(async () => {
    try {
      const session = await createChatSession();
      setActiveSessionId(session.id);
      setSelectedPaperId(null);
      setRefreshKey(k => k + 1);
    } catch (e) {
      console.error('Failed to create session', e);
    }
  }, []);

  const handleSelectSession = useCallback((id: string) => {
    setActiveSessionId(id);
    setSelectedPaperId(null);
  }, []);

  const handlePaperSelect = useCallback((paperId: number) => {
    setSelectedPaperId(paperId);
  }, []);

  const handleSessionUpdate = useCallback(() => {
    setRefreshKey(k => k + 1);
  }, []);

  return (
    <div className="flex h-screen overflow-hidden bg-[#0f1729] font-sans antialiased">
      <Sidebar
        activeSessionId={activeSessionId}
        onSelectSession={handleSelectSession}
        onNewSession={handleNewSession}
        refreshKey={refreshKey}
      />

      <main className="flex-1 flex overflow-hidden">
        {activeSessionId ? (
          <ChatView
            sessionId={activeSessionId}
            onPaperSelect={handlePaperSelect}
            onSessionUpdate={handleSessionUpdate}
          />
        ) : (
          /* Welcome Screen */
          <div className="flex-1 flex flex-col items-center justify-center text-center px-8">
            <div className="size-24 rounded-3xl bg-gradient-to-br from-cyan-400/10 to-indigo-500/10 flex items-center justify-center mb-8 border border-white/5">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-cyan-400/40">
                <path d="M22 10v6M2 10l10-5 10 5-10 5z" />
                <path d="M6 12v5c3 3 9 3 12 0v-5" />
              </svg>
            </div>
            <h1 className="text-3xl font-black text-white/80 mb-3 tracking-tight">
              Scholar-Agent
            </h1>
            <p className="text-base text-white/30 mb-10 font-medium max-w-md">
              你的 AI 学术研究助手。搜索论文、阅读全文、获取研究洞察——一切尽在对话中。
            </p>
            <button
              onClick={handleNewSession}
              className="px-8 py-4 bg-gradient-to-r from-cyan-500 to-indigo-500
                text-white font-bold rounded-2xl text-sm
                hover:shadow-xl hover:shadow-cyan-500/20 hover:-translate-y-0.5
                transition-all duration-300 active:scale-95"
            >
              ✨ 开始新对话
            </button>
          </div>
        )}

        {/* Paper Detail Panel */}
        {selectedPaperId && (
          <PaperPanel
            paperId={selectedPaperId}
            onClose={() => setSelectedPaperId(null)}
          />
        )}
      </main>
    </div>
  );
}
