"use client";

import React, { useState, useEffect } from 'react';

export default function Dashboard() {
  const [agents] = useState([
    { id: 'agent-1', identity: 'System Kernel', status: 'executing', task: 'Bootstrapping modules' },
    { id: 'agent-2', identity: 'Network Router', status: 'pending', task: 'Awaiting connections' },
    { id: 'agent-3', identity: 'Memory Manager', status: 'completed', task: 'Loaded pgvector' },
    { id: 'agent-4', identity: 'Model Router', status: 'executing', task: 'Warming up Gemini adapter' },
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
    <main className="dashboard-container">
      <header className="dashboard-header">
        <div>
          <h1 className="title-gradient">Synapse OS</h1>
          <p className="subtitle">Live Telemetry & Dashboard</p>
        </div>
        <div className="status-badge" id="system-status">
          <span className="status-dot"></span>
          <span>System Online</span>
        </div>
      </header>

      <div className="dashboard-grid">
        
        {/* Left Column: Agents & Tasks */}
        <div className="main-column">
          <section className="glass-panel" id="active-agents-section">
            <h2 className="section-title">
              <svg className="section-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 002-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
              </svg>
              Active Agents
            </h2>
            <div className="agents-list">
              {agents.map(agent => (
                <div key={agent.id} id={agent.id} className="agent-card">
                  <div>
                    <h3 className="agent-identity">{agent.identity}</h3>
                    <p className="agent-task">{agent.task}</p>
                  </div>
                  <div>
                    <span className={`badge ${agent.status}`}>
                      {agent.status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* System Control Panel */}
          <section className="glass-panel control-panel" id="control-panel-section">
            <h2 className="section-title control-title">CEO Control Panel</h2>
            <p className="control-subtitle">Execute overrides and intervene in the AI OS Scheduler.</p>
            <div className="button-group">
              <button id="btn-submit-task" className="btn btn-primary">
                Submit Task
              </button>
              <button id="btn-approve-tool" className="btn btn-secondary">
                Approve Tool Usage
              </button>
              <button id="btn-halt-scheduler" className="btn btn-danger">
                Halt Scheduler
              </button>
            </div>
          </section>
        </div>

        {/* Right Column: Live Logs */}
        <aside>
          <section className="terminal-panel" id="live-terminal-section">
            <h2 className="terminal-title">
              <svg className="section-icon" style={{ width: '1rem', height: '1rem', color: 'var(--text-secondary)' }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
              Live Terminal
            </h2>
            <div className="terminal-logs" id="terminal-logs-container">
              {logs.map((log, i) => (
                <div key={i} className="log-entry">
                  <span className="log-prompt">❯</span>
                  {log}
                </div>
              ))}
            </div>
          </section>
        </aside>

      </div>
    </main>
  );
}
