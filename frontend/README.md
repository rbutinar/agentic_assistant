# Agentic Assistant Frontend

This is the React-based web interface for the Agentic Assistant.

## Setup & Run

1. Navigate to the `frontend` directory:
   ```sh
   cd frontend
   ```
2. Install dependencies:
   ```sh
   npm install
   ```
3. Start the development server:
   ```sh
   npm start
   ```
   The app will be available at [http://localhost:3000](http://localhost:3000)

## Features
- ChatGPT-like interface for interacting with the backend agent.
- Button to start a new session (resets conversation context).
- Displays chat history with clear user/assistant roles.

## Configuration
- The frontend expects the backend API to be running at `http://localhost:8000` by default. You can change the `API_BASE` variable in `src/App.js` if needed.

## Testing
### Unit/Integration (Jest + React Testing Library)
- Run all component tests:
  ```sh
  npm test
  ```
- Example test: `src/App.test.js` (renders chat UI, mocks backend, simulates user interaction)

### End-to-End (Playwright)
1. Install Playwright:
   ```sh
   npm install --save-dev @playwright/test
   npx playwright install
   ```
2. Run E2E tests:
   ```sh
   npx playwright test
   ```
- Example test: `e2e/chat.spec.js` (verifies user can start session and chat)
