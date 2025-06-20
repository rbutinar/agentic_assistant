import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import App from './App';

// Mock axios
jest.mock('axios', () => ({
  post: jest.fn((url, payload) => {
    if (url.endsWith('/session')) {
      return Promise.resolve({ data: { session_id: 'test-session' } });
    }
    if (url.endsWith('/chat')) {
      return Promise.resolve({ data: {
        session_id: 'test-session',
        messages: [
          { role: 'user', content: payload.message },
          { role: 'assistant', content: 'Hello from the agent!' }
        ]
      }});
    }
    return Promise.reject(new Error('Unknown endpoint'));
  })
}));

test('renders chat UI and sends a message', async () => {
  render(<App />);
  expect(screen.getByText(/Agentic Assistant/i)).toBeInTheDocument();

  // Wait for session to be set
  await waitFor(() => {
    expect(screen.getByPlaceholderText(/Type your message/i)).not.toBeDisabled();
  });

  // Type and send a message
  fireEvent.change(screen.getByPlaceholderText(/Type your message/i), {
    target: { value: 'Hello agent!' }
  });
  fireEvent.click(screen.getByText(/Send/i));

  // Wait for assistant response
  await waitFor(() => {
    expect(screen.getByText(/Hello from the agent!/i)).toBeInTheDocument();
  });
});
