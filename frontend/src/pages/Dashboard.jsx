import React, { useEffect, useState } from 'react';
import { 
  Users, 
  DoorOpen, 
  GraduationCap, 
  Grid3X3,
  RefreshCw,
  AlertCircle
} from 'lucide-react';
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend
} from 'recharts';
import { analyticsApi } from '../api';

const COLORS = ['#6366f1', '#8b5cf6', '#ec4899', '#f43f5e', '#f59e0b', '#10b981'];

const StatCard = ({ icon: Icon, label, value, color, loading }) => (
  <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 hover:shadow-md transition-shadow">
    <div className="flex items-start justify-between">
      <div className={`p-3 rounded-xl bg-${color}-50 text-${color}-600`}>
        <Icon className="w-6 h-6" />
      </div>
    </div>
    <div className="mt-4">
      <h3 className="text-slate-500 text-sm font-medium">{label}</h3>
      {loading ? (
        <div className="h-8 w-24 bg-slate-100 animate-pulse rounded-lg mt-1"></div>
      ) : (
        <p className="text-2xl font-bold text-slate-900 mt-1">{value}</p>
      )}
    </div>
  </div>
);

const Dashboard = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchStats = async () => {
    setLoading(true);
    try {
      const resp = await analyticsApi.getStats();
      setData(resp || {});
      setError(null);
    } catch (err) {
      setError('Failed to load dashboard data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold text-slate-900 tracking-tight">System Analytics</h2>
          <p className="text-slate-500 mt-2">Real-time overview of seating plan performance and institution data.</p>
        </div>
        <button 
          onClick={fetchStats}
          disabled={loading}
          className="p-2 text-slate-400 hover:text-indigo-600 transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-100 text-red-600 p-4 rounded-xl flex items-center gap-3">
          <AlertCircle className="w-5 h-5" />
          <p className="text-sm font-medium">{error}</p>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard icon={Users} label="Total Students" value={data?.stats?.students || '0'} color="blue" loading={loading} />
        <StatCard icon={DoorOpen} label="Total Rooms" value={data?.stats?.rooms || '0'} color="indigo" loading={loading} />
        <StatCard icon={GraduationCap} label="Total Exams" value={data?.stats?.exams || '0'} color="amber" loading={loading} />
        <StatCard icon={Grid3X3} label="Seating Plans" value={data?.stats?.plans || '0'} color="emerald" loading={loading} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Dept Distribution */}
        <div className="bg-white p-8 rounded-2xl shadow-sm border border-slate-100 h-[450px] flex flex-col">
          <h3 className="text-lg font-bold text-slate-900 mb-6">Department Distribution</h3>
          <div className="w-full h-[300px]">
            {loading ? (
              <div className="w-full h-full bg-slate-50 animate-pulse rounded-xl"></div>
            ) : Array.isArray(data?.departments) && data.departments.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={data.departments}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={100}
                    paddingAngle={5}
                    dataKey="value"
                  >
                    {data.departments.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip 
                    contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 10px 15px -3px rgba(0,0,0,0.1)' }}
                  />
                  <Legend verticalAlign="bottom" height={36}/>
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="w-full h-full flex items-center justify-center text-slate-400">No department data available</div>
            )}
          </div>
        </div>

        {/* Constraint Success Rate */}
        <div className="bg-white p-8 rounded-2xl shadow-sm border border-slate-100 h-[450px] flex flex-col">
          <h3 className="text-lg font-bold text-slate-900 mb-2">Constraint Level Distribution</h3>
          <p className="text-slate-400 text-sm mb-6">Distribution of plans by satisfyed constraint complexity (Level 1 = Best).</p>
          <div className="w-full h-[300px]">
            {loading ? (
              <div className="w-full h-full bg-slate-50 animate-pulse rounded-xl"></div>
            ) : Array.isArray(data?.constraints) && data.constraints.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data.constraints}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                  <XAxis 
                    dataKey="level" 
                    axisLine={false} 
                    tickLine={false} 
                    tick={{ fill: '#64748b', fontSize: 12 }}
                    label={{ value: 'Constraint Level', position: 'insideBottom', offset: -5, fontSize: 12, fill: '#94a3b8' }}
                  />
                  <YAxis axisLine={false} tickLine={false} tick={{ fill: '#64748b', fontSize: 12 }} />
                  <Tooltip 
                    cursor={{ fill: '#f8fafc' }}
                    contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 10px 15px -3px rgba(0,0,0,0.1)' }}
                  />
                  <Bar dataKey="count" fill="#6366f1" radius={[6, 6, 0, 0]} barSize={40} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="w-full h-full flex items-center justify-center text-slate-400">No constraint data available</div>
            )}
          </div>
        </div>
      </div>
      
      {/* Room Utilization */}
      <div className="bg-white p-8 rounded-2xl shadow-sm border border-slate-100">
          <h3 className="text-lg font-bold text-slate-900 mb-6">Avg Room Occupancy</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            {loading ? (
              [1, 2, 4].map(i => <div key={i} className="h-24 bg-slate-50 animate-pulse rounded-xl"></div>)
            ) : (Array.isArray(data?.room_utilization) ? data.room_utilization : []).map((room, idx) => (
              <div key={idx} className="space-y-3">
                <div className="flex justify-between items-end">
                  <span className="font-bold text-slate-700">Room {room.name}</span>
                  <span className="text-xs font-bold text-indigo-600 bg-indigo-50 px-2 py-1 rounded">{room.percentage}%</span>
                </div>
                <div className="w-full h-3 bg-slate-100 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-indigo-600 rounded-full transition-all duration-1000"
                    style={{ width: `${room.percentage}%` }}
                  ></div>
                </div>
                <div className="flex justify-between text-[10px] font-bold text-slate-400 uppercase tracking-widest">
                  <span>Used: {room.used}</span>
                  <span>Cap: {room.total}</span>
                </div>
              </div>
            ))}
          </div>
      </div>
    </div>
  );
};

export default Dashboard;
