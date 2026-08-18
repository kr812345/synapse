"use client";

import React, { useState, useEffect, useRef } from 'react';
import { Terminal, Activity, Cpu, Play, CheckCircle, Clock, Send, Server, StopCircle, RefreshCw, MessageSquare } from 'lucide-react';

interface Agent {
  id: string;
  identity: string;
  department: string;
  status: 'executing' | 'completed' | 'pending' | 'idle';
  task: string;
}

interface LogEntry {
  id: string;
  timestamp: string;
  source: string;
  event_type: string;
  message: string;
}

interface ChatMessage {
  id: string;
  role: 'user' | 'system' | 'assistant';
  content: string;
}

const ASCII_AVATARS = {
  idle: `╭─────── Synapse ───────╮\n│                       │\n│      [ ^ _ ^ ]        │\n│      Waiting...       │\n│                       │\n╰───────────────────────╯`,
  thinking: `╭─────── Synapse ───────╮\n│                       │\n│      [ @ _ @ ]        │\n│     Processing...     │\n│                       │\n╰───────────────────────╯`,
  happy: `╭─────── Synapse ───────╮\n│                       │\n│      [ ^ 0 ^ ]        │\n│       Done!           │\n│                       │\n╰───────────────────────╯`
};

export default function Dashboard() {
  const [agents, setAgents] = useState<Agent[]>([
    { id: 'kernel', identity: 'Kernel', department: 'System', status: 'idle', task: 'Awaiting events' },
    { id: 'eng_1', identity: 'Engineering Manager', department: 'Engineering', status: 'idle', task: 'Ready' },
    { id: 'rm_1', identity: 'Research Manager', department: 'Research', status: 'idle', task: 'Ready' },
    { id: 'mkt_1', identity: 'Marketing Manager', department: 'Marketing', status: 'idle', task: 'Ready' },
  ]);
  
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const [connected, setConnected] = useState(false);
  const [taskInput, setTaskInput] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [avatarState, setAvatarState] = useState<'idle' | 'thinking' | 'happy'>('idle');
  const [activeTab, setActiveTab] = useState<'cli' | 'telemetry'>('cli');
  
  const logsEndRef = useRef<HTMLDivElement>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs, activeTab]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatHistory, activeTab]);

  useEffect(() => {
    let ws: WebSocket;
    let reconnectTimer: NodeJS.Timeout;

    const connect = () => {
      const host = window.location.hostname;
      ws = new WebSocket(`ws://${host}:8000/ws`);
      
      ws.onopen = () => {
        setConnected(true);
        addLog('System', 'connection.success', 'Connected to Synapse OS Cloud Agent.');
        setChatHistory(prev => [...prev, { id: 'init', role: 'system', content: 'Synapse OS Booted Successfully. Connection established.' }]);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          const { source, event_type, payload } = data;
          
          addLog(source || 'Kernel', event_type || 'unknown', JSON.stringify(payload || data));
          
          if (event_type === 'task.create') {
            updateAgent('kernel', 'executing', 'Routing task');
            setAvatarState('thinking');
          } else if (event_type === 'model.generate') {
             updateAgent(source, 'executing', 'Generating response...');
             setAvatarState('thinking');
          } else if (event_type === 'task.complete' && data.destination === 'web_ui') {
             updateAgent('kernel', 'idle', 'Awaiting events');
             setAvatarState('happy');
             
             // Extract text result for chat
             let resultText = "Task completed.";
             if (payload?.result?.output) {
               resultText = payload.result.output;
               if (typeof resultText !== 'string') resultText = JSON.stringify(resultText);
             } else if (payload?.result) {
               resultText = JSON.stringify(payload.result);
             }
             
             setChatHistory(prev => [...prev, { id: Math.random().toString(), role: 'assistant', content: resultText }]);
             
             setTimeout(() => setAvatarState('idle'), 2000);
          }
        } catch (err) {
          addLog('System', 'error', 'Failed to parse incoming WebSocket message.');
        }
      };

      ws.onclose = () => {
        setConnected(false);
        addLog('System', 'connection.lost', 'Connection lost. Retrying in 5s...');
        setAvatarState('idle');
        reconnectTimer = setTimeout(connect, 5000);
      };

      ws.onerror = () => {};
    };

    connect();

    return () => {
      clearTimeout(reconnectTimer);
      if (ws) ws.close();
    };
  }, []);

  const addLog = (source: string, type: string, message: string) => {
    setLogs(prev => {
      const newLogs = [...prev, {
        id: Math.random().toString(36).substring(7),
        timestamp: new Date().toLocaleTimeString(),
        source,
        event_type: type,
        message
      }];
      return newLogs.slice(-100);
    });
  };

  const updateAgent = (id: string, status: Agent['status'], task: string) => {
    setAgents(prev => prev.map(a => 
      a.id === id || a.identity.includes(id) ? { ...a, status, task } : a
    ));
  };

  const submitTask = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!taskInput.trim()) return;

    const userInput = taskInput;
    setTaskInput('');
    setIsSubmitting(true);
    setAvatarState('thinking');
    
    setChatHistory(prev => [...prev, { id: Math.random().toString(), role: 'user', content: userInput }]);

    try {
      addLog('WebUI', 'task.submit', `Submitting: ${userInput}`);
      const host = window.location.hostname;
      const res = await fetch(`http://${host}:8000/api/task`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task: userInput })
      });
      const data = await res.json();
      if (data.status !== 'success') {
        addLog('WebUI', 'error', `Failed: ${data.message}`);
        setAvatarState('idle');
      }
    } catch (err) {
      addLog('WebUI', 'error', 'Failed to contact API server.');
      setAvatarState('idle');
    } finally {
      setIsSubmitting(false);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'executing': return <RefreshCw className="w-4 h-4 text-blue-500 animate-spin" />;
      case 'completed': return <CheckCircle className="w-4 h-4 text-emerald-500" />;
      case 'pending': return <Clock className="w-4 h-4 text-yellow-500" />;
      default: return <StopCircle className="w-4 h-4 text-zinc-500" />;
    }
  };

  return (
    <div className="flex h-screen bg-background text-foreground overflow-hidden font-sans">
      
      {/* Sidebar - Agents & Status */}
      <aside className="w-80 flex-shrink-0 border-r border-border bg-[#0f0f13] flex flex-col hidden md:flex">
        <div className="p-6 border-b border-border">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center shadow-lg">
              <Activity className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-semibold tracking-tight">Synapse OS</h1>
              <div className="flex items-center gap-2 text-xs">
                <span className="relative flex h-2 w-2">
                  {connected && <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>}
                  <span className={`relative inline-flex rounded-full h-2 w-2 ${connected ? 'bg-emerald-500' : 'bg-red-500'}`}></span>
                </span>
                <span className="text-zinc-400">{connected ? 'Cloud Agent Online' : 'Connecting...'}</span>
              </div>
            </div>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-4">
          <div className="mb-6">
            <h2 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-3 flex items-center gap-2">
              <Cpu className="w-4 h-4" /> Core Modules
            </h2>
            <div className="space-y-2">
              {agents.map(agent => (
                <div key={agent.id} className="p-3 rounded-lg border border-border bg-[#18181b] hover:border-zinc-700 transition-colors">
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-medium text-sm">{agent.identity}</span>
                    {getStatusIcon(agent.status)}
                  </div>
                  <div className="text-xs text-zinc-400 flex items-center justify-between">
                    <span className="truncate pr-2">{agent.task}</span>
                    <span className="px-2 py-0.5 rounded-full bg-zinc-800 text-[10px] uppercase font-medium">{agent.status}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col h-full bg-[#0a0a0c]">
        
        {/* Top Control Bar */}
        <header className="h-16 border-b border-border flex items-center px-6 justify-between shrink-0 bg-[#0f0f13]/80 backdrop-blur-sm z-10">
          <div className="flex bg-black/40 rounded-lg p-1 border border-zinc-800/60">
            <button 
              onClick={() => setActiveTab('cli')}
              className={`flex items-center gap-2 px-4 py-1.5 text-sm font-medium rounded-md transition-colors ${activeTab === 'cli' ? 'bg-indigo-600 text-white' : 'text-zinc-400 hover:text-white'}`}
            >
              <MessageSquare className="w-4 h-4" /> Web CLI
            </button>
            <button 
              onClick={() => setActiveTab('telemetry')}
              className={`flex items-center gap-2 px-4 py-1.5 text-sm font-medium rounded-md transition-colors ${activeTab === 'telemetry' ? 'bg-zinc-800 text-white' : 'text-zinc-400 hover:text-white'}`}
            >
              <Terminal className="w-4 h-4" /> Telemetry
            </button>
          </div>
          <div className="flex gap-2">
            <button className="px-3 py-1.5 text-xs font-medium bg-red-950/30 text-red-400 hover:bg-red-900/40 rounded-md border border-red-900/50 transition-colors">
              Halt All Tasks
            </button>
          </div>
        </header>

        {/* Tab Content */}
        <div className="flex-1 overflow-hidden relative flex flex-col p-6">
          <div className="flex-1 rounded-xl border border-border bg-black/40 shadow-2xl flex flex-col overflow-hidden relative">
            
            {activeTab === 'cli' && (
              <div className="flex-1 flex flex-col overflow-hidden">
                <div className="h-48 border-b border-border/50 bg-[#0f0f13] flex items-center justify-center shrink-0">
                  <pre className="text-emerald-400 font-mono text-sm leading-[1.1] animate-pulse-slow">
                    {ASCII_AVATARS[avatarState]}
                  </pre>
                </div>
                
                <div className="flex-1 overflow-y-auto p-6 font-mono space-y-4">
                  {chatHistory.map(msg => (
                    <div key={msg.id} className={\`max-w-[85%] \${msg.role === 'user' ? 'ml-auto' : 'mr-auto'}\`}>
                      <div className="text-[10px] text-zinc-500 mb-1 uppercase tracking-wider">
                        {msg.role === 'system' ? 'System' : msg.role === 'user' ? 'You' : 'Synapse'}
                      </div>
                      <div className={\`p-4 rounded-xl text-sm leading-relaxed \${msg.role === 'user' ? 'bg-indigo-600/20 border border-indigo-500/30 text-indigo-100' : msg.role === 'system' ? 'bg-zinc-800/50 text-zinc-400 border border-zinc-700/50 italic' : 'bg-zinc-800 border border-zinc-700 text-zinc-200'}\`}>
                        {msg.content}
                      </div>
                    </div>
                  ))}
                  <div ref={chatEndRef} />
                </div>
              </div>
            )}

            {activeTab === 'telemetry' && (
              <div className="flex-1 overflow-y-auto p-4 font-mono text-[13px] leading-relaxed space-y-1.5">
                {logs.length === 0 ? (
                  <div className="text-zinc-600 italic">Waiting for events...</div>
                ) : (
                  logs.map((log) => (
                    <div key={log.id} className="flex hover:bg-white/5 rounded px-1 -mx-1 transition-colors group/log">
                      <span className="text-zinc-600 mr-3 shrink-0 select-none">[{log.timestamp}]</span>
                      <span className="text-indigo-400 font-medium mr-3 w-20 shrink-0 truncate" title={log.source}>{log.source}</span>
                      <span className="text-emerald-500/80 mr-3 w-32 shrink-0 truncate" title={log.event_type}>{log.event_type}</span>
                      <span className="text-zinc-300 break-words group-hover/log:text-white transition-colors">{log.message}</span>
                    </div>
                  ))
                )}
                <div ref={logsEndRef} />
              </div>
            )}
          </div>
        </div>

        {/* Command Input Area */}
        <div className="p-6 pt-0 shrink-0">
          <form onSubmit={submitTask} className="relative">
            <input
              type="text"
              value={taskInput}
              onChange={(e) => setTaskInput(e.target.value)}
              placeholder="Give Synapse a task... e.g. 'Research the latest developments in AI agents'"
              className="w-full bg-[#18181b] border border-zinc-800 rounded-xl pl-4 pr-12 py-4 text-sm focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all shadow-lg placeholder:text-zinc-600"
              disabled={!connected || isSubmitting}
            />
            <button 
              type="submit"
              disabled={!connected || !taskInput.trim() || isSubmitting}
              className="absolute right-2 top-2 bottom-2 aspect-square flex items-center justify-center bg-indigo-600 hover:bg-indigo-500 disabled:bg-zinc-800 disabled:text-zinc-600 text-white rounded-lg transition-colors"
            >
              {isSubmitting ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            </button>
          </form>
          <div className="mt-2 text-[10px] text-zinc-500 text-center">
            The AI Agent continues to execute on the cloud even if you close this window.
          </div>
        </div>

      </main>
    </div>
  );
}
