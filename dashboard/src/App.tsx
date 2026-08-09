import React, { useState, useEffect } from 'react';
import { Activity, Server, LayoutDashboard, Terminal, Users } from 'lucide-react';
import './index.css';

// Mocking initial agents based on the phases
const INITIAL_AGENTS = [
  { id: 'eng_manager', name: 'Engineering Manager', status: 'idle', role: 'Manager' },
  { id: 'backend_w1', name: 'Backend Worker 1', status: 'idle', role: 'Worker' },
  { id: 'mktg_manager', name: 'Marketing Manager', status: 'idle', role: 'Manager' },
  { id: 'research_manager', name: 'Research Manager', status: 'idle', role: 'Manager' },
];

function App() {
  const [agents, setAgents] = useState(INITIAL_AGENTS);
  const [logs, setLogs] = useState<string[]>([
    "[SYSTEM] AI OS Kernel initialized.",
    "[SYSTEM] PostgreSQL Memory Engine connected.",
    "[SYSTEM] WebSocket server listening on port 8080."
  ]);
  const [isConnected, setIsConnected] = useState(true);

  // Simulating websocket events for live rendering
  useEffect(() => {
    const interval = setInterval(() => {
      setAgents(currentAgents => 
        currentAgents.map(agent => ({
          ...agent,
          status: Math.random() > 0.7 ? 'running' : 'idle'
        }))
      );

      const mockEvents = [
        "[EVENT] Task scheduled for Research Department",
        "[EVENT] Engineering Manager delegating task to Backend Worker",
        "[EVENT] Memory Engine: Stored new knowledge graph embedding",
        "[EVENT] Agent backend_w1 completed task successfully"
      ];
      
      setLogs(currentLogs => {
        const newLogs = [...currentLogs, `[${new Date().toLocaleTimeString()}] ${mockEvents[Math.floor(Math.random() * mockEvents.length)]}`];
        if (newLogs.length > 50) newLogs.shift();
        return newLogs;
      });
    }, 3000);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="dashboard-container">
      {/* Sidebar: Agents Hierarchy */}
      <aside className="glass-panel">
        <header>
          <div className="logo"><Server size={24} /> Synapse OS</div>
        </header>
        
        <h2><Users size={18} /> Agent Registry</h2>
        <div className="agent-list">
          {agents.map(agent => (
            <div className="agent-card" key={agent.id}>
              <div className="agent-header">
                <span className="agent-name">{agent.name}</span>
                <span className={`status-badge status-${agent.status}`}>
                  {agent.status}
                </span>
              </div>
              <div style={{fontSize: '0.8rem', color: 'var(--text-muted)'}}>
                ID: {agent.id} | {agent.role}
              </div>
            </div>
          ))}
        </div>
      </aside>

      {/* Main Content: DAG & Logs */}
      <main>
        <header style={{ justifyContent: 'space-between' }}>
          <h2><LayoutDashboard size={20} /> Live Mission Control</h2>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem' }}>
            <div className={isConnected ? "live-indicator" : ""} style={{ background: isConnected ? "var(--success)" : "var(--danger)"}}></div>
            {isConnected ? "WS Connected" : "Disconnected"}
          </div>
        </header>

        <section className="glass-panel" style={{ marginBottom: '2rem' }}>
          <h2><Activity size={18} /> Task DAG Visualization</h2>
          <div className="dag-view">
            {/* Placeholder for actual DAG visualization (e.g. React Flow) */}
            <div style={{ color: 'var(--text-muted)', textAlign: 'center' }}>
              <Activity size={48} style={{ opacity: 0.2, marginBottom: '1rem', display: 'block', margin: '0 auto' }} />
              <p>DAG Renderer Initialized.</p>
              <p style={{ fontSize: '0.8rem', marginTop: '0.5rem' }}>Waiting for tasks to populate the graph...</p>
            </div>
          </div>
        </section>

        <section className="glass-panel">
          <h2><Terminal size={18} /> Event Log (Live)</h2>
          <div className="log-viewer">
            {logs.map((log, idx) => (
              <div key={idx} className="log-entry">
                <span className="log-time">{log.split(']')[0]}]</span>
                <span>{log.split(']')[1]}</span>
              </div>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}

export default App;
