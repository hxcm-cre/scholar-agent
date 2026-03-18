import React, { useState } from 'react';
import { GraduationCap, Lock, User, ArrowLeft, Loader2, CheckCircle } from 'lucide-react';
import { register } from '../../services/auth';

interface RegisterProps {
  onSuccess: () => void;
  onNavigateToLogin: () => void;
}

export const Register: React.FC<RegisterProps> = ({ onSuccess, onNavigateToLogin }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (password !== confirmPassword) {
      setError('两次输入的密码不一致');
      return;
    }

    if (password.length < 6) {
      setError('密码长度至少为 6 位');
      return;
    }

    setLoading(true);

    try {
      await register(username, password);
      setIsSuccess(true);
      setTimeout(() => {
        onNavigateToLogin();
      }, 2000);
    } catch (err: any) {
      setError(err.message || '注册失败，该用户名可能已被占用');
    } finally {
      setLoading(false);
    }
  };

  if (isSuccess) {
    return (
      <div className="min-h-screen bg-[#0f172a] flex items-center justify-center p-4">
        <div className="w-full max-w-md bg-[#1a2b4c]/40 backdrop-blur-xl border border-white/10 rounded-2xl p-8 shadow-2xl text-center">
          <div className="size-20 bg-emerald-500/20 rounded-full flex items-center justify-center text-emerald-400 mx-auto mb-6">
            <CheckCircle size={48} />
          </div>
          <h1 className="text-2xl font-bold text-white mb-2">注册成功！</h1>
          <p className="text-slate-400 mb-8">账户已创建，正在为您跳转到登录页面...</p>
          <div className="flex justify-center">
            <Loader2 className="animate-spin text-[#22d3ee]" size={24} />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0f172a] flex items-center justify-center p-4 relative overflow-hidden">
      {/* Background blobs */}
      <div className="absolute top-[-10%] right-[-10%] w-[40%] h-[40%] bg-blue-500/10 blur-[120px] rounded-full" />
      <div className="absolute bottom-[-10%] left-[-10%] w-[40%] h-[40%] bg-cyan-500/10 blur-[120px] rounded-full" />

      <div className="w-full max-w-md bg-[#1a2b4c]/40 backdrop-blur-xl border border-white/10 rounded-2xl p-8 shadow-2xl relative z-10">
        <button
          onClick={onNavigateToLogin}
          className="absolute top-8 left-4 p-2 text-slate-400 hover:text-white transition-colors"
        >
          <ArrowLeft size={20} />
        </button>

        <div className="flex flex-col items-center mb-8">
          <div className="size-14 bg-[#22d3ee] rounded-xl flex items-center justify-center text-[#1a2b4c] mb-4 shadow-lg shadow-cyan-500/20">
            <GraduationCap size={32} strokeWidth={2.5} />
          </div>
          <h1 className="text-2xl font-bold text-white mb-2">创建新账户</h1>
          <p className="text-slate-400 text-sm">开启智能学术研究之旅</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
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
                placeholder="设置您的用户名"
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
                placeholder="设置 6 位以上密码"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider ml-1">确认密码</label>
            <div className="relative group">
              <div className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-[#22d3ee] transition-colors">
                <Lock size={18} />
              </div>
              <input
                type="password"
                required
                className="w-full bg-black/20 border border-white/5 rounded-xl py-3 pl-10 pr-4 text-white placeholder:text-slate-600 focus:outline-none focus:border-[#22d3ee]/50 focus:ring-1 focus:ring-[#22d3ee]/50 transition-all font-medium"
                placeholder="请再次确认您的密码"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
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
            className="w-full bg-[#22d3ee] hover:bg-[#22d3ee]/90 text-[#1a2b4c] font-bold py-3.5 rounded-xl transition-all shadow-lg shadow-cyan-500/20 active:scale-[0.98] disabled:opacity-50 disabled:active:scale-100 flex items-center justify-center"
          >
            {loading ? <Loader2 className="animate-spin" size={20} /> : '立即注册并获取内测资格'}
          </button>
        </form>

        <div className="mt-8 text-center pt-6 border-t border-white/5">
          <p className="text-slate-400 text-sm">
            已有账号？{' '}
            <button
              onClick={onNavigateToLogin}
              className="text-[#22d3ee] font-semibold hover:underline decoration-2 underline-offset-4"
            >
              去登录
            </button>
          </p>
        </div>
      </div>
    </div>
  );
};
