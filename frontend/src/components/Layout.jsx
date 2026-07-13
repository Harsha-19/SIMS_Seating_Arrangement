import React from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';

const Layout = () => {
  return (
    <div className="flex min-h-screen bg-slate-50 text-slate-900 font-sans">
      <Sidebar />
      <main className="flex-1 ml-64 p-8 transition-all duration-300 overflow-x-hidden">
        <header className="mb-8 flex items-center justify-between">
          <div>
            <p className="text-slate-500 font-medium">Welcome back, Administrator</p>
          </div>
          <div className="flex items-center gap-4">
            <div className="w-10 h-10 rounded-full bg-slate-200 border-2 border-white shadow-sm flex items-center justify-center font-bold text-slate-600">
              AD
            </div>
          </div>
        </header>
        <div className="max-w-7xl mx-auto">
          <Outlet />
        </div>
      </main>
    </div>
  );
};

export default Layout;
