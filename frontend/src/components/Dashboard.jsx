import React, { useMemo } from 'react';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, 
  PieChart, Pie, Cell, LineChart, Line, AreaChart, Area
} from 'recharts';
import { Users, BookOpen, CheckCircle, AlertCircle, BarChart3, PieChart as PieChartIcon } from 'lucide-react';

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#06b6d4', '#ef4444'];

const StatCard = ({ title, value, icon: Icon, color, trend }) => (
  <div className="bg-slate-900 border border-slate-800 p-6 rounded-2xl shadow-xl hover:border-slate-700 transition-all group">
    <div className="flex items-center justify-between mb-4">
      <div className={`p-3 rounded-xl ${color} bg-opacity-10`}>
        <Icon className={`${color.replace('bg-', 'text-')} w-6 h-6`} />
      </div>
      {trend && (
        <span className={`text-xs font-bold px-2 py-1 rounded-full ${trend > 0 ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'}`}>
          {trend > 0 ? '+' : ''}{trend}%
        </span>
      )}
    </div>
    <h3 className="text-slate-400 text-sm font-medium mb-1">{title}</h3>
    <p className="text-3xl font-bold text-white">{value}</p>
  </div>
);

const Dashboard = ({ data }) => {
  // Use mock data if real data is missing
  const stats = data?.stats || { students: 1240, exams: 42, plans: 15, success_rate: 85.5 };
  const roomData = data?.room_utilization || [
    { name: 'Hall A', total: 100, used: 85, percentage: 85 },
    { name: 'Hall B', total: 80, used: 75, percentage: 93.7 },
    { name: 'Lab 1', total: 60, used: 30, percentage: 50 },
    { name: 'Seminar 1', total: 50, used: 45, percentage: 90 },
    { name: 'Library Hall', total: 200, used: 120, percentage: 60 },
  ];
  const constraintData = data?.constraint_distribution || [
    { level: 'Optimal (L1)', count: 8 },
    { level: 'Good (L2)', count: 4 },
    { level: 'Relaxed (L3)', count: 2 },
    { level: 'Warning (L4)', count: 1 },
    { level: 'Critical (L5)', count: 0 },
    { level: 'Failed (L6)', count: 0 },
  ];

  return (
    <div className="p-8 bg-slate-950 min-h-screen text-slate-100 font-sans">
      <header className="mb-10">
        <h1 className="text-4xl font-bold bg-gradient-to-r from-blue-400 via-indigo-400 to-purple-400 bg-clip-text text-transparent mb-2">
          Admin Analytics Dashboard
        </h1>
        <p className="text-slate-400">Real-time pulse of academic operations and seating efficiency.</p>
      </header>

      {/* Pulse Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-10">
        <StatCard title="Total Students" value={stats.students} icon={Users} color="bg-blue-500" trend={12} />
        <StatCard title="Active Exams" value={stats.exams} icon={BookOpen} color="bg-indigo-500" trend={5} />
        <StatCard title="Total Plans" value={stats.plans} icon={BarChart3} color="bg-purple-500" trend={-2} />
        <StatCard title="Constraint Success" value={`${stats.success_rate}%`} icon={CheckCircle} color="bg-emerald-500" trend={8.2} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Room Utilization Bar Chart */}
        <div className="bg-slate-900 border border-slate-800 p-8 rounded-3xl shadow-2xl">
          <div className="flex items-center gap-3 mb-8">
            <div className="p-2 bg-blue-500/10 rounded-lg">
              <BarChart3 className="text-blue-400 w-5 h-5" />
            </div>
            <h2 className="text-xl font-bold text-white">Room Utilization Profile</h2>
          </div>
          <div className="h-[350px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={roomData} margin={{ top: 20, right: 30, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                <XAxis dataKey="name" stroke="#64748b" fontSize={12} tickLine={false} axisLine={false} />
                <YAxis stroke="#64748b" fontSize={12} tickLine={false} axisLine={false} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '12px' }}
                  itemStyle={{ color: '#fff' }}
                />
                <Legend iconType="circle" />
                <Bar dataKey="used" fill="#3b82f6" radius={[6, 6, 0, 0]} name="Occupied Seats" barSize={35} />
                <Bar dataKey="total" fill="#1e293b" radius={[6, 6, 0, 0]} name="Total Capacity" barSize={35} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Constraint Satisfaction Pie Chart */}
        <div className="bg-slate-900 border border-slate-800 p-8 rounded-3xl shadow-2xl">
          <div className="flex items-center gap-3 mb-8">
            <div className="p-2 bg-emerald-500/10 rounded-lg">
              <PieChartIcon className="text-emerald-400 w-5 h-5" />
            </div>
            <h2 className="text-xl font-bold text-white">Layout Quality Distribution</h2>
          </div>
          <div className="h-[350px] w-full flex items-center justify-center">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={constraintData}
                  cx="50%"
                  cy="50%"
                  innerRadius={80}
                  outerRadius={120}
                  paddingAngle={5}
                  dataKey="count"
                  nameKey="level"
                >
                  {constraintData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip 
                  contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '12px' }}
                />
                <Legend verticalAlign="bottom" height={36}/>
              </PieChart>
            </ResponsiveContainer>
            
            {/* Center Text Overlay for Pie */}
            <div className="absolute flex flex-col items-center">
               <span className="text-slate-400 text-sm font-medium uppercase tracking-widest">Efficiency</span>
               <span className="text-3xl font-bold text-white">{stats.success_rate}%</span>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Insights Summary */}
      <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-slate-900/50 border border-slate-800 p-6 rounded-2xl flex items-center gap-4">
           <AlertCircle className="text-amber-500 w-8 h-8 shrink-0" />
           <div>
             <h4 className="font-bold text-white mb-0.5">Optimization Hint</h4>
             <p className="text-sm text-slate-400">Hall B is nearing critical capacity. Consider using Lib Hall for next ECE core exam.</p>
           </div>
        </div>
        <div className="bg-slate-900/50 border border-slate-800 p-6 rounded-2xl flex items-center gap-4 md:col-span-2">
           <CheckCircle className="text-emerald-500 w-8 h-8 shrink-0" />
           <div>
             <h4 className="font-bold text-white mb-0.5">Constraint Health</h4>
             <p className="text-sm text-slate-400">Overall success rate is up by 8% this week. The latest shuffling algorithm is effectively reducing department adjacency conflicts.</p>
           </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
