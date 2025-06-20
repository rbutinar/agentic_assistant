# Agentic Assistant

A new project for developing an agentic AI coding assistant. This project will serve as a foundation for experimenting with agentic workflows, autonomous code generation, and advanced LLM-driven automation.

## Structure
- The initial structure will include a backend (Python/FastAPI) and a frontend (React).
- The backend will focus on agent orchestration, tool integration, and API endpoints.
- The frontend will provide a modern, interactive UI for user interaction and agent management.

## Features
- **Autonomous Coding Agent:** Advanced agentic workflows for code generation and automation.
- **Tool Integration:** Modular tool system for extending agent capabilities.
- **Browser Use Agent:** Seamlessly automates browser tasks using a dedicated agent powered by Azure OpenAI. This agent can perform goal-oriented actions online, such as searching, navigating, and interacting with web content, all via secure Azure OpenAI credentials.
- **Modern UI:** Interactive React frontend for chat, session management, and agent control.


## Setup
### Backend Setup (Step 1)

#### Requirements
- Python 3.8+
- [pip](https://pip.pypa.io/en/stable/)

#### Installation
1. Clone the repository and navigate to the project directory.
2. Create and activate a virtual environment (recommended):
   ```sh
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```
3. Install dependencies and local packages:
   ```sh
   python3 -m pip install -r requirements.txt
   ```
   
   This will automatically install the local `browser_use` package in development mode.

#### Installazione dei browser Playwright
Dopo aver installato le dipendenze Python, esegui anche:
```sh
playwright install
```
Questo comando scarica i browser necessari per l’automazione (Chromium, Firefox, WebKit).

#### Running the Backend
Start the FastAPI server with:
```sh
uvicorn main:app --reload
```

Check the health endpoint at: [http://localhost:8000/health](http://localhost:8000/health)

#### Running Tests
To run backend tests:
```sh
pytest test_health.py
```

### Frontend Setup (React)

#### Requirements
- Node.js 18+
- npm (Node package manager)

#### Installation
1. In the terminal, go to the `frontend` folder:
   ```sh
   cd frontend
   ```
2. Install the main dependencies and libraries for markdown rendering:
   ```sh
   npm install
   npm install react-markdown remark-gfm rehype-sanitize
   ```

#### Starting the frontend
Run:
```sh
npm start
```

#### Additional React libraries used
- `react-markdown`: for safe and flexible markdown rendering in assistant responses
- `remark-gfm`: for support of tables, task lists, and other GitHub Flavored Markdown extensions
- `rehype-sanitize`: for secure HTML/markdown rendering

Tables, code, and other markdown elements will be displayed correctly and securely in the frontend.

## Backend: Conversation & Session Management (Step 2)

### Endpoints
- `POST /session` — Start a new chat session. Returns a session ID.
- `POST /chat` — Send a message and receive a response. Requires a session ID and message.

### Example Usage
```python
import requests

# Start a session
resp = requests.post('http://localhost:8000/session')
session_id = resp.json()['session_id']

# Send a chat message
payload = {"session_id": session_id, "message": "Hello, agent!"}
resp = requests.post('http://localhost:8000/chat', json=payload)
print(resp.json())
```

### Running Tests
To test session and chat endpoints:
```sh
pytest test_chat.py
```

## Backend: Azure OpenAI Integration (Step 3)

### Environment Variables
Create a `.env` file in the project root with the following (replace with your values):
```
AZURE_OPENAI_ENDPOINT=https://<your-resource-name>.openai.azure.com
AZURE_OPENAI_KEY=<your-api-key>
AZURE_OPENAI_DEPLOYMENT=<your-deployment-name>
AZURE_OPENAI_API_VERSION=2023-03-15-preview  # Optional, default provided
```

### How it Works
- If Azure OpenAI is configured, chat responses are generated using your Azure OpenAI deployment.
- If not configured, a simulated response is returned for development/testing.

### Error Handling
- If the Azure OpenAI API call fails, the assistant will reply with an error message in the chat.

## Semantic Knowledge Retrieval

This agent supports **semantic knowledge retrieval** using the `sentence-transformers` library and cosine similarity. The knowledge base consists of `.txt` files in the `knowledge/` directory. When a user asks a question, the agent:

- Embeds the user query and all knowledge topics.
- Uses cosine similarity to find the most relevant topic.
- Injects the matching knowledge into its reasoning context.
- Logs every knowledge retrieval event (including the query, matched topic, and a snippet) in `agent/agent_session.log`.

### Adding Knowledge
- Place new `.txt` files in the `knowledge/` directory. The filename (without `.txt`) is used as the topic.
- Example: `knowledge/whoami.txt` provides terminal instructions for identifying the current user.

### Dependencies
- `sentence-transformers` (for semantic embeddings)
- `numpy` (for vector similarity)

Both are included in `requirements.txt`.

## Safe Mode & Terminal Commands

- The agent can execute terminal commands via the backend.
- **Safe Mode ON**: Commands require explicit user confirmation.
- **Safe Mode OFF**: Commands execute directly (use with caution).
- All command attempts and confirmations are logged.

## Logging
- All agent actions, knowledge retrievals, and tool usage are logged in `agent/agent_session.log`.
- Logging is session-aware and includes timestamps, session IDs, and event data.

## Docker Usage

### 🐳 Running with Docker

For detailed Docker setup and lifecycle instructions, see [docker_fab_local_setup.md](./docker_fab_local_setup.md).

- Quick start: `docker run ...`
- Start/stop existing container: `docker start` / `docker stop`
- To change ports/env/image: remove and re-create the container.

## Open Points / TODO

- **Azure OpenAI Key Support:**
  - ✅ The agent and browser use agent now support Azure OpenAI credentials and endpoints for LLM tasks.

- **Agent Stop/Kill Logic:**
  - Implement a robust mechanism to stop or kill the browser agent process, especially for long-running or stuck executions. This may involve async cancellation, timeout handling, or explicit kill signals.

- **General:**
  - The browser agent is now successfully integrated and returns results to the main agent. Further improvements should address the above open points for production robustness.

## Goals
- Modular agentic architecture
- Extensible tool/plugin system
- Secure, auditable interaction and logging
- Modern, user-friendly interface

---

*Continue building the agentic assistant by following the step-by-step implementation plan!*
