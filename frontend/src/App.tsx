/**
 * Scholar-Agent — Main Application
 *
 * Simple view-based routing (no react-router needed for this SPA).
 * Views: home (project list), config (new research), workflow (running), report (detail).
 */
import { useState, useCallback } from 'react';
import { Sidebar } from './components/Sidebar';
import { ProjectList } from './components/ProjectList';
import { ResearchConfig } from './components/ResearchConfig';
import { ResearchReport } from './components/ResearchReport';
import { WorkflowStatus } from './components/WorkflowStatus';
import { createResearch } from './services/api';
import type { ResearchWeights } from './types';

type View =
  | { kind: 'home' }
  | { kind: 'config' }
  | { kind: 'workflow'; projectId: number }
  | { kind: 'report'; projectId: number };

export default function App() {
  const [view, setView] = useState<View>({ kind: 'home' });
  const [refreshKey, setRefreshKey] = useState(0);
  const [submitting, setSubmitting] = useState(false);

  const goHome = useCallback(() => {
    setRefreshKey(k => k + 1);
    setView({ kind: 'home' });
  }, []);

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

  const currentViewKind = view.kind === 'home' ? 'home' :
    view.kind === 'config' ? 'config' :
    view.kind === 'workflow' ? 'workflow' : 'report';

  return (
    <div className="flex h-screen overflow-hidden bg-[#f5f7fa] font-sans antialiased">
      <Sidebar
        currentView={currentViewKind}
        onNavigateHome={goHome}
        onSelectProject={(id) => setView({ kind: 'report', projectId: id })}
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
      </main>
    </div>
  );
}
