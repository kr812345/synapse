"use client";

import React, { useState, useEffect } from 'react';

export default function Dashboard() {
  const [agents] = useState([
    { id: 1, identity: 'System Kernel', status: 'executing', task: 'Bootstrapping modules' },
    { id: 2, identity: 'Network Router', status: 'pending', task: 'Awaiting connections' },
    { id: 3, identity: 'Memory Manager', status: 'completed', task: 'Loaded pgvector' },
    { id: 4, identity: 'Model Router', status: 'executing', task: 'Warming up Gemini adapter' },
  ]);
  
  const [logs, setLogs] = useState<string[]>([
    "[10:00:01] [OS] Boot sequence initiated...",
    "[10:00:02] [Kernel] Module manager online.",
    "[10:00:03] [EventBus] Routing configured.",
  ]);

  // Mock a WebSocket client connecting to the OS
  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8080/ws');
    
    ws.onopen = () => {
      setLogs(prev => [...prev, "[WS] Connected to AI OS Live Dashboard"]);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'log') {
          setLogs(prev => [...prev, data.message].slice(-50));
        }
      } catch (err) {}
    };

    ws.onerror = () => {
      setLogs(prev => [...prev, "[WS] Connection failed (Server offline). Operating in mock mode."]);
    };

    return () => ws.close();
  }, []);

  return (
    <main className="min-h-screen bg-neutral-950 text-white p-6 font-sans selection:bg-blue-500/30">
      <header className="flex justify-between items-center mb-10 pb-6 border-b border-white/10">
        <div>
          <h1 className="text-3xl font-light tracking-tight bg-gradient-to-r from-blue-400 to-emerald-400 bg-clip-text text-transparent">
            Synapse OS
          </h1>
          <p className="text-sm text-neutral-400 mt-1">Live Telemetry & Dashboard</p>
        </div>
        <div className="flex items-center gap-3 bg-white/5 px-4 py-2 rounded-full border border-white/10">
          <span className="flex h-2.5 w-2.5 relative">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
          </span>
          <span className="text-sm font-medium text-emerald-400">System Online</span>
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left Column: Agents & Tasks */}
        <div className="lg:col-span-2 space-y-6">
          <section className="bg-white/5 border border-white/10 rounded-2xl p-6 backdrop-blur-xl">
            <h2 className="text-xl font-medium mb-6 flex items-center gap-2">
              <svg className="w-5 h-5 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 002-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
              </svg>
              Active Agents
            </h2>
            <div className="grid gap-4">
              {agents.map(agent => (
                <div key={agent.id} className="p-4 rounded-xl bg-black/40 border border-white/5 flex items-center justify-between hover:bg-black/60 transition-colors group">
                  <div>
                    <h3 className="font-medium text-neutral-200 group-hover:text-white transition-colors">{agent.identity}</h3>
                    <p className="text-sm text-neutral-500 mt-0.5">{agent.task}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`px-3 py-1 rounded-full text-xs font-medium border tracking-wide ${
                      agent.status === 'executing' ? 'bg-blue-500/10 text-blue-400 border-blue-500/20' :
                      agent.status === 'completed' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
                      'bg-neutral-500/10 text-neutral-400 border-neutral-500/20'
                    }`}>
                      {agent.status.toUpperCase()}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* System Control Panel */}
          <section className="bg-gradient-to-br from-indigo-500/10 via-purple-500/5 to-black/20 border border-indigo-500/20 rounded-2xl p-6 backdrop-blur-xl">
            <h2 className="text-xl font-medium mb-2 text-indigo-100">CEO Control Panel</h2>
            <p className="text-sm text-indigo-200/60 mb-6">Execute overrides and intervene in the AI OS Scheduler.</p>
            <div className="flex gap-4">
              <button className="px-6 py-2.5 bg-indigo-500 hover:bg-indigo-600 text-white rounded-lg text-sm font-medium transition-all shadow-lg shadow-indigo-500/20 active:scale-95">
                Submit Task
              </button>
              <button className="px-6 py-2.5 bg-white/5 hover:bg-white/10 text-neutral-300 border border-white/10 rounded-lg text-sm font-medium transition-all active:scale-95">
                Approve Tool Usage
              </button>
              <button className="px-6 py-2.5 bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/20 rounded-lg text-sm font-medium transition-all active:scale-95 ml-auto">
                Halt Scheduler
              </button>
            </div>
          </section>
        </div>

        {/* Right Column: Live Logs */}
        <div className="lg:col-span-1 h-[600px]">
          <section className="bg-[#0a0a0a] border border-white/10 rounded-2xl p-4 flex flex-col h-full shadow-2xl relative overflow-hidden group">
            <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-emerald-500/50 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
            <h2 className="text-sm font-medium text-neutral-400 mb-4 px-2 uppercase tracking-wider flex items-center gap-2">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
              Live Terminal
            </h2>
            <div className="flex-1 overflow-y-auto font-mono text-[13px] text-neutral-300 space-y-1.5 p-2">
              {logs.map((log, i) => (
                <div key={i} className="break-all opacity-80 hover:opacity-100 transition-opacity">
                  <span className="text-emerald-500/60 mr-2">❯</span>
                  {log}
                </div>
              ))}
            </div>
          </section>
        </div>

      </div>
    </main>
  );
}
