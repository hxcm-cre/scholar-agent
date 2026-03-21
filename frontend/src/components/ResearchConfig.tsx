import React, { useRef, useState, useEffect } from 'react';
import { Search, UploadCloud, Rocket, ChevronDown, ArrowLeft } from 'lucide-react';
import { getAvailableModels } from '../services/api';
import type { ResearchWeights, ModelOption } from '../types';

interface ResearchConfigProps {
  onSubmit: (query: string, modelName: string, weights: ResearchWeights, useOcr: boolean, userMetrics: string, runBenchmark: boolean, csvData: string | null) => void;
  onBack: () => void;
  isSubmitting: boolean;
}

// Models are now fetched from the backend

export const ResearchConfig: React.FC<ResearchConfigProps> = ({ onSubmit, onBack, isSubmitting }) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [query, setQuery] = useState('');
  const [userMetrics, setUserMetrics] = useState('');
  const [modelOptions, setModelOptions] = useState<ModelOption[]>([]);
  const [model, setModel] = useState('');
  const [customModel, setCustomModel] = useState('');
  const [useOcr, setUseOcr] = useState(false);
  const [runBenchmark, setRunBenchmark] = useState(false);
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [weights, setWeights] = useState<ResearchWeights>({
    relevance: 0.5,
    venue: 0.3,
    citation: 0.1,
    repro: 0.1,
  });

  useEffect(() => {
    async function loadModels() {
      try {
        const { models } = await getAvailableModels();
        setModelOptions(models);
        if (models.length > 0) setModel(models[0].id);
      } catch (e) {
        console.error('Failed to load models', e);
      }
    }
    loadModels();
  }, []);

  const finalModel = customModel || model;

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) setCsvFile(file);
  };

  const handleSubmit = async () => {
    if (!query.trim()) return;
    let csvData: string | null = null;
    if (csvFile) {
      const buf = await csvFile.arrayBuffer();
      csvData = btoa(String.fromCharCode(...new Uint8Array(buf)));
    }
    onSubmit(query, finalModel, weights, useOcr, userMetrics, runBenchmark, csvData);
  };

  const wSlider = (label: string, key: keyof ResearchWeights) => (
    <div className="space-y-1.5">
      <div className="flex justify-between text-xs">
        <span className="text-slate-600">{label}</span>
        <span className="font-mono text-[#22d3ee]">{weights[key].toFixed(2)}</span>
      </div>
      <input
        type="range" min="0" max="1" step="0.05"
        value={weights[key]}
        onChange={(e) => setWeights(prev => ({ ...prev, [key]: parseFloat(e.target.value) }))}
        className="w-full h-1 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-[#22d3ee]"
      />
    </div>
  );

  return (
    <section className="flex-1 overflow-y-auto p-8 custom-scrollbar">
      <div className="max-w-3xl mx-auto">
        {/* Back */}
        <button onClick={onBack} className="flex items-center gap-1 text-sm text-slate-500 hover:text-[#1a2b4c] mb-6 transition-colors">
          <ArrowLeft size={16} /> 返回任务列表
        </button>

        <h2 className="text-2xl font-bold text-[#1a2b4c] mb-8">新建研究任务</h2>

        {/* Query */}
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="text-xs font-bold text-[#1a2b4c] uppercase tracking-widest mb-2 block">
                研究问题 / 关键词
              </label>
              <div className="relative">
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="例如：EKF state estimation for UAVs"
                  className="w-full h-14 bg-white border border-slate-200 rounded-xl px-4 pr-12 text-lg focus:border-[#1a2b4c] focus:ring-0 outline-none placeholder:text-slate-400 transition-colors shadow-sm"
                />
                <Search className="absolute right-4 top-4 text-slate-300" size={24} />
              </div>
            </div>

            <div>
              <label className="text-xs font-bold text-[#1a2b4c] uppercase tracking-widest mb-2 block">
                核心关注指标 (可选，逗号分隔)
              </label>
              <div className="relative">
                <input
                  type="text"
                  value={userMetrics}
                  onChange={(e) => setUserMetrics(e.target.value)}
                  placeholder="例如：RMSE, ATE, Runtime"
                  className="w-full h-14 bg-white border border-slate-200 rounded-xl px-4 text-lg focus:border-[#1a2b4c] focus:ring-0 outline-none placeholder:text-slate-400 transition-colors shadow-sm"
                />
              </div>
            </div>
          </div>

          {/* Two column layout */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Left: Model & OCR */}
            <div className="space-y-5">
              <div>
                <label className="text-xs font-bold text-[#1a2b4c] uppercase tracking-widest mb-2 block">
                  LLM 模型
                </label>
                <div className="relative">
                  <select
                    value={model}
                    onChange={(e) => setModel(e.target.value)}
                    className="w-full bg-white border border-slate-200 rounded-lg py-2.5 px-3 text-sm appearance-none outline-none focus:border-[#1a2b4c]"
                  >
                    {modelOptions.map(m => <option key={m.id} value={m.id}>{m.label}</option>)}
                  </select>
                  <ChevronDown size={16} className="absolute right-3 top-3 text-slate-400 pointer-events-none" />
                </div>
                <input
                  type="text"
                  value={customModel}
                  onChange={(e) => setCustomModel(e.target.value)}
                  placeholder="或手动输入模型 ID"
                  className="w-full mt-2 bg-white border border-slate-200 rounded-lg py-2 px-3 text-xs outline-none focus:border-[#1a2b4c] placeholder:text-slate-400"
                />
              </div>

              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" checked={useOcr} onChange={(e) => setUseOcr(e.target.checked)}
                  className="accent-[#22d3ee] w-4 h-4" />
                <span className="text-sm text-slate-600">启用 OCR (扫描件/图片)</span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer bg-cyan-50/50 p-2 rounded-lg border border-cyan-100/50 hover:bg-cyan-50 transition-colors">
                <input type="checkbox" checked={runBenchmark} onChange={(e) => setRunBenchmark(e.target.checked)}
                  className="accent-[#22d3ee] w-4 h-4" />
                <span className="text-sm font-medium text-slate-700">关联实验数据进行 SOTA 对标</span>
              </label>
            </div>

            {/* Right: Weights */}
            <div className="space-y-4">
              <label className="text-xs font-bold text-[#1a2b4c] uppercase tracking-widest mb-1 block">
                论文过滤权重
              </label>
              {wSlider('匹配度 (Relevance)', 'relevance')}
              {wSlider('期刊等级 (Venue)', 'venue')}
              {wSlider('引用次数 (Citation)', 'citation')}
              {wSlider('开源权重 (Repro)', 'repro')}
            </div>
          </div>

          {/* CSV upload */}
          <div>
            <input type="file" ref={fileInputRef} className="hidden" accept=".csv" onChange={handleFileChange} />
            <div
              onClick={() => fileInputRef.current?.click()}
              className="border-2 border-dashed border-slate-200 rounded-xl flex flex-col items-center justify-center p-6 bg-slate-50/50 hover:bg-slate-50 transition-colors cursor-pointer group"
            >
              <UploadCloud className="text-slate-400 group-hover:text-[#1a2b4c] mb-1" size={24} />
              <p className="text-xs font-medium text-slate-600">
                {csvFile ? `📎 ${csvFile.name}` : '上传本地实验 CSV (可选)'}
              </p>
              <p className="text-[10px] text-slate-400">Max 10MB • CSV Only</p>
            </div>
          </div>

          {/* Submit */}
          <div className="flex justify-end pt-4">
            <button
              onClick={handleSubmit}
              disabled={isSubmitting || !query.trim()}
              className="bg-[#22d3ee] hover:bg-cyan-400 disabled:opacity-50 disabled:cursor-not-allowed text-[#1a2b4c] font-bold py-3 px-8 rounded-xl flex items-center gap-3 shadow-lg shadow-cyan-500/20 transition-all transform hover:-translate-y-0.5 active:translate-y-0"
            >
              <span>{isSubmitting ? '提交中...' : '🚀 开始研究'}</span>
              <Rocket size={20} className={isSubmitting ? 'animate-bounce' : ''} />
            </button>
          </div>
        </div>
      </div>
    </section>
  );
};
