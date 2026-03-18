import React, { useEffect, useState } from 'react';
import { Users, Shield, Clock, ArrowLeft, Loader2, RefreshCw } from 'lucide-react';
import { getAdminUsers } from '../../services/auth';
import type { User } from '../../types';

interface AdminPanelProps {
  onBack: () => void;
}

export const AdminPanel: React.FC<AdminPanelProps> = ({ onBack }) => {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchUsers = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await getAdminUsers();
      setUsers(data);
    } catch (err: any) {
      setError(err.message || '获取用户列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  return (
    <div className="flex-1 bg-[#f8fafc] flex flex-col h-screen overflow-hidden">
      {/* Header */}
      <header className="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-8 shrink-0">
        <div className="flex items-center gap-4">
          <button
            onClick={onBack}
            className="p-2 hover:bg-slate-100 rounded-lg text-slate-500 transition-colors"
          >
            <ArrowLeft size={20} />
          </button>
          <div className="flex items-center gap-2 text-slate-800">
            <Users size={20} className="text-[#1a2b4c]" />
            <h1 className="text-lg font-bold">用户管理后台</h1>
          </div>
        </div>
        <button
          onClick={fetchUsers}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 bg-white border border-slate-200 hover:border-[#22d3ee] hover:text-[#22d3ee] rounded-lg text-sm font-medium transition-all disabled:opacity-50"
        >
          <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
          刷新列表
        </button>
      </header>

      {/* Content */}
      <main className="flex-1 p-8 overflow-y-auto custom-scrollbar">
        <div className="max-w-5xl mx-auto">
          {error ? (
            <div className="bg-red-50 border border-red-100 p-4 rounded-xl text-red-600 text-sm mb-6 flex items-center gap-3">
              <span className="font-bold">错误:</span> {error}
            </div>
          ) : null}

          <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200">
                  <th className="px-6 py-4 text-[10px] font-bold uppercase tracking-wider text-slate-400">ID</th>
                  <th className="px-6 py-4 text-[10px] font-bold uppercase tracking-wider text-slate-400">用户名</th>
                  <th className="px-6 py-4 text-[10px] font-bold uppercase tracking-wider text-slate-400">角色</th>
                  <th className="px-6 py-4 text-[10px] font-bold uppercase tracking-wider text-slate-400">注册时间</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {loading ? (
                  <tr>
                    <td colSpan={4} className="px-6 py-12 text-center">
                      <div className="flex flex-col items-center gap-3">
                        <Loader2 className="animate-spin text-[#22d3ee]" size={32} />
                        <span className="text-sm text-slate-400 font-medium">加载中...</span>
                      </div>
                    </td>
                  </tr>
                ) : users.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="px-6 py-12 text-center text-slate-400 italic text-sm">
                      暂无注册用户
                    </td>
                  </tr>
                ) : (
                  users.map((user) => (
                    <tr key={user.id} className="hover:bg-slate-50/50 transition-colors">
                      <td className="px-6 py-4">
                        <span className="font-mono text-xs text-slate-400">#{user.id}</span>
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          <div className="size-8 bg-[#1a2b4c]/5 rounded-full flex items-center justify-center text-[#1a2b4c] font-bold text-xs">
                            {user.username.charAt(0).toUpperCase()}
                          </div>
                          <span className="font-semibold text-slate-700">{user.username}</span>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        {user.is_admin ? (
                          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-blue-50 text-blue-600 text-[10px] font-bold uppercase">
                            <Shield size={12} />
                            管理员
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-100 text-slate-500 text-[10px] font-bold uppercase">
                            普通用户
                          </span>
                        )}
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-2 text-slate-500 text-sm">
                          <Clock size={14} />
                          {new Date(user.created_at).toLocaleString('zh-CN')}
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </main>
    </div>
  );
};
