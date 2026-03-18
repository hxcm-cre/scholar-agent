import { useState, useCallback, useEffect } from 'react';
import { Sidebar } from './components/Sidebar';
import { ProjectList } from './components/ProjectList';
import { ResearchConfig } from './components/ResearchConfig';
import { ResearchReport } from './components/ResearchReport';
import { WorkflowStatus } from './components/WorkflowStatus';
import { createResearch } from './services/api';
import { getCurrentUser, logout } from './services/auth';
import { Login } from './components/Auth/Login';
import { Register } from './components/Auth/Register';
import { AdminPanel } from './components/Admin/AdminPanel';
import type { ResearchWeights, User } from './types';

type View =
  | { kind: 'home' }
  | { kind: 'config' }
  | { kind: 'workflow'; projectId: number }
  | { kind: 'report'; projectId: number }
  | { kind: 'admin' };

type AuthState = 'loading' | 'unauthenticated' | 'authenticated' | 'registering';

export default function App() {
  const [authState, setAuthState] = useState<AuthState>('loading');
  const [user, setUser] = useState<User | null>(null);
  const [view, setView] = useState<View>({ kind: 'home' });
  const [refreshKey, setRefreshKey] = useState(0);
  const [submitting, setSubmitting] = useState(false);

  // Check auth on mount
  useEffect(() => {
    getCurrentUser()
      .then(u => {
        setUser(u);
        setAuthState('authenticated');
      })
      .catch(() => {
        setAuthState('unauthenticated');
      });
  }, []);

  const goHome = useCallback(() => {
    setRefreshKey(k => k + 1);
    setView({ kind: 'home' });
  }, []);

  const handleLogout = () => {
    logout();
    setUser(null);
    setAuthState('unauthenticated');
  };

  const handleLoginSuccess = async () => {
    const u = await getCurrentUser();
    setUser(u);
    setAuthState('authenticated');
    setView({ kind: 'home' });
  };

  const handleSubmit = async (
    query: string,
    modelName: string,
    weights: ResearchWeights,
    useOcr: boolean,
    csvData: string | null,
  ) => {
    setSubmitting(true);
    try {
      const project = await createResearch({
        query,
        model_name: modelName,
        weights,
        use_ocr: useOcr,
        csv_data: csvData,
      });
      setView({ kind: 'workflow', projectId: project.id });
    } catch (e) {
      console.error('Failed to create research', e);
      alert('创建研究任务失败，请检查后端是否运行');
    } finally {
      setSubmitting(false);
    }
  };

  if (authState === 'loading') {
    return (
      <div className="h-screen bg-[#0f172a] flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#22d3ee]"></div>
          <p className="text-slate-400 text-sm font-medium">正在初始化研究环境...</p>
        </div>
      </div>
    );
  }

  if (authState === 'unauthenticated') {
    return <Login onSuccess={handleLoginSuccess} onNavigateToRegister={() => setAuthState('registering')} />;
  }

  if (authState === 'registering') {
    return <Register onSuccess={() => setAuthState('unauthenticated')} onNavigateToLogin={() => setAuthState('unauthenticated')} />;
  }

  const currentViewKind = view.kind === 'home' ? 'home' :
    view.kind === 'config' ? 'config' :
    view.kind === 'workflow' ? 'workflow' :
    view.kind === 'admin' ? 'home' : 'report';

  return (
    <div className="flex h-screen overflow-hidden bg-[#f5f7fa] font-sans antialiased">
      <Sidebar
        currentView={currentViewKind}
        onNavigateHome={goHome}
        onSelectProject={(id) => setView({ kind: 'report', projectId: id })}
        user={user}
        onLogout={handleLogout}
        onNavigateAdmin={() => setView({ kind: 'admin' })}
      />

      <main className="flex-1 flex flex-col overflow-hidden">
        {view.kind === 'home' && (
          <ProjectList
            refreshKey={refreshKey}
            onSelect={(id) => setView({ kind: 'report', projectId: id })}
            onNew={() => setView({ kind: 'config' })}
          />
        )}

        {view.kind === 'config' && (
          <ResearchConfig
            onSubmit={handleSubmit}
            onBack={goHome}
            isSubmitting={submitting}
          />
        )}

        {view.kind === 'workflow' && (
          <WorkflowStatus
            projectId={view.projectId}
            onComplete={() => setView({ kind: 'report', projectId: view.projectId })}
          />
        )}

        {view.kind === 'report' && (
          <ResearchReport
            projectId={view.projectId}
            onBack={goHome}
          />
        )}

        {view.kind === 'admin' && (
          <AdminPanel
            onBack={goHome}
          />
        )}
      </main>
    </div>
  );
}

