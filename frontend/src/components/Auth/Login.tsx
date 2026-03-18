import React, { useState } from 'react';
import { GraduationCap, Lock, User, ArrowRight, Loader2 } from 'lucide-react';
import { login } from '../../services/auth';

interface LoginProps {
  onSuccess: () => void;
  onNavigateToRegister: () => void;
}

export const Login: React.FC<LoginProps> = ({ onSuccess, onNavigateToRegister }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await login(username, password);
      onSuccess();
    } catch (err: any) {
      setError(err.message || '登录失败，请检查用户名和密码');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0f172a] flex items-center justify-center p-4 relative overflow-hidden">
      {/* Background blobs */}
      <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-blue-500/10 blur-[120px] rounded-full" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-cyan-500/10 blur-[120px] rounded-full" />

      <div className="w-full max-w-md bg-[#1a2b4c]/40 backdrop-blur-xl border border-white/10 rounded-2xl p-8 shadow-2xl relative z-10 transition-all">
        <div className="flex flex-col items-center mb-8">
          <div className="size-14 bg-[#22d3ee] rounded-xl flex items-center justify-center text-[#1a2b4c] mb-4 shadow-lg shadow-cyan-500/20">
            <GraduationCap size={32} strokeWidth={2.5} />
          </div>
          <h1 className="text-2xl font-bold text-white mb-2">欢迎回来</h1>
          <p className="text-slate-400 text-sm">登录以访问您的研究工作空间</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="space-y-2">
            <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider ml-1">用户名</label>
            <div className="relative group">
              <div className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-[#22d3ee] transition-colors">
                <User size={18} />
              </div>
              <input
                type="text"
                required
                className="w-full bg-black/20 border border-white/5 rounded-xl py-3 pl-10 pr-4 text-white placeholder:text-slate-600 focus:outline-none focus:border-[#22d3ee]/50 focus:ring-1 focus:ring-[#22d3ee]/50 transition-all font-medium"
                placeholder="请输入您的用户名"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
              />
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider ml-1">密码</label>
            <div className="relative group">
              <div className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-[#22d3ee] transition-colors">
                <Lock size={18} />
              </div>
              <input
                type="password"
                required
                className="w-full bg-black/20 border border-white/5 rounded-xl py-3 pl-10 pr-4 text-white placeholder:text-slate-600 focus:outline-none focus:border-[#22d3ee]/50 focus:ring-1 focus:ring-[#22d3ee]/50 transition-all font-medium"
                placeholder="请输入您的密码"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
          </div>

          {error && (
            <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-xs font-medium text-center">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-[#22d3ee] hover:bg-[#22d3ee]/90 text-[#1a2b4c] font-bold py-3.5 rounded-xl transition-all shadow-lg shadow-cyan-500/20 active:scale-[0.98] disabled:opacity-50 disabled:active:scale-100 flex items-center justify-center gap-2 group"
          >
            {loading ? (
              <Loader2 className="animate-spin" size={20} />
            ) : (
              <>
                立即登录
                <ArrowRight size={18} className="group-hover:translate-x-1 transition-transform" />
              </>
            )}
          </button>
        </form>

        <div className="mt-8 text-center pt-6 border-t border-white/5">
          <p className="text-slate-400 text-sm">
            还没有账号？{' '}
            <button
              onClick={onNavigateToRegister}
              className="text-[#22d3ee] font-semibold hover:underline decoration-2 underline-offset-4"
            >
              立即注册
            </button>
          </p>
        </div>
      </div>
    </div>
  );
};
