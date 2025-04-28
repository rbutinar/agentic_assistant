# Agentic Assistant

A new project for developing an agentic AI coding assistant. This project will serve as a foundation for experimenting with agentic workflows, autonomous code generation, and advanced LLM-driven automation.

## Structure
- The initial structure will include a backend (Python/FastAPI) and a frontend (React).
- The backend will focus on agent orchestration, tool integration, and API endpoints.
- The frontend will provide a modern, interactive UI for user interaction and agent management.

## Setup
### Backend Setup (Step 1)

#### Requirements
- Python 3.8+
- [pip](https://pip.pypa.io/en/stable/)

#### Installation
1. Clone the repository and navigate to the project directory.
2. Install dependencies:
   ```sh
   python3 -m pip install -r requirements.txt
   ```

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

## Goals
- Modular agentic architecture
- Extensible tool/plugin system
- Secure, auditable interaction and logging
- Modern, user-friendly interface

---

*Continue building the agentic assistant by following the step-by-step implementation plan!*
