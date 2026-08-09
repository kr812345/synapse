<div align="center">
  <img src="https://raw.githubusercontent.com/lucide-icons/lucide/main/icons/cpu.svg" alt="Synapse OS Logo" width="100" height="100" />
  <h1>Synapse AI OS</h1>
  <p>A production-ready, event-driven Artificial Intelligence Operating System.</p>

  <p>
    <a href="https://github.com/kr812345/synapse/issues"><img alt="Issues" src="https://img.shields.io/github/issues/kr812345/synapse"></a>
    <a href="https://github.com/kr812345/synapse/pulls"><img alt="Pull Requests" src="https://img.shields.io/github/issues-pr/kr812345/synapse"></a>
    <a href="./LICENSE"><img alt="License" src="https://img.shields.io/github/license/kr812345/synapse"></a>
  </p>
</div>

<hr />

## 🌟 Overview

**Synapse OS** is a highly modular, event-driven framework that treats autonomous AI agents as programs running inside a shared operating system. Instead of isolated agents, Synapse provides a shared **Event Bus**, a unified **Memory Engine** (powered by PostgreSQL and pgvector), and an automated **Task Scheduler** that orchestrates complex workflows across multiple specialized departments (Engineering, Research, Marketing, and Personal).

If you are looking to build multi-agent architectures that require true collaboration, state tracking, and live monitoring, you've found the right project.

## ✨ Key Features

- **Event-Driven Architecture**: Agents communicate by publishing and subscribing to events over a central OS Kernel.
- **Persistent Vector Memory**: Uses PostgreSQL and `pgvector` to store agent observations and build long-term memory knowledge graphs.
- **Live React Dashboard**: A beautiful, glassmorphic Next.js/Vite dashboard that streams live agent activity, logs, and DAG execution hierarchies over WebSockets.
- **Model Agnostic**: Uses `litellm` under the hood to route logic seamlessly to Gemini, OpenAI, Anthropic, or local models depending on task complexity.
- **Standard Tool Library**: Comes out-of-the-box with real implementations for GitHub crawling, Reddit indexing, and automated Web Browsing.

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- Node.js 18+ (For the Dashboard)
- PostgreSQL 16+ (with the `pgvector` extension installed)

### 1. Installation

Clone the repository and set up your Python environment:
```bash
git clone https://github.com/kr812345/synapse.git
cd synapse

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Environment Variables

Create a `.env` file at the root of the project with your API keys:
```env
# LLM Providers (Configure litellm)
GEMINI_API_KEY=your_gemini_key_here
OPENAI_API_KEY=your_openai_key_here

# External Tools
GITHUB_TOKEN=your_github_token
REDDIT_CLIENT_ID=your_reddit_id
REDDIT_CLIENT_SECRET=your_reddit_secret
RESEND_API_KEY=your_resend_api_key
```

### 3. Database Setup

Ensure PostgreSQL is running and you have created a database named `synapse`. 
The OS will automatically run migrations and create the `pgvector` extension and necessary tables on boot.

### 4. Running the OS

You can boot the OS Kernel and submit a task via the CLI:
```bash
python main.py execute "Research AI startup ideas on Reddit and HN and draft a report."
```

To run the live WebSocket server that powers the dashboard:
```bash
uvicorn api.server:app --reload
```

## 📊 Live Dashboard

To visualize the agents working in real-time, start the React dashboard:
```bash
cd dashboard
npm install
npm run dev
```
Open `http://localhost:5173` in your browser to view the Live Mission Control and Agent Registry.

## 🤝 Contributing

We welcome contributions! Synapse OS is built heavily on the principles of modularity and composition over inheritance. 

If you want to add a new Tool, a new Department, or fix a bug:
1. Please read our [Contribution Guidelines](CONTRIBUTING.md).
2. Review our [Code of Conduct](CODE_OF_CONDUCT.md).
3. Check the existing [Issues](https://github.com/kr812345/synapse/issues) or open a new one to discuss your idea.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
