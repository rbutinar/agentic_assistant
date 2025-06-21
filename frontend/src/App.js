import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import './App.css';
import MarkdownMessage from './MarkdownMessage';

const API_BASE = "";

function App() {
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [safeMode, setSafeMode] = useState(true);
  const [pendingTerminal, setPendingTerminal] = useState(null);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  };

  const startSession = async () => {
    setLoading(true);
    try {
      const resp = await axios.post(`${API_BASE}/session`);
      setSessionId(resp.data.session_id);
      setMessages([]);
      setPendingTerminal(null);
    } finally {
      setLoading(false);
    }
  };

  const sendMessage = async (e) => {
    e.preventDefault();
    if (!input.trim() || !sessionId || loading || pendingTerminal) return;
    setLoading(true);

    const currentInput = input.trim();
    
    // Add user message immediately to prevent it from disappearing
    const userMessage = { role: 'user', content: currentInput };
    setMessages(prevMessages => [...prevMessages, userMessage]);
    setInput('');

    try {
      const resp = await axios.post(`${API_BASE}/chat`, {
        session_id: sessionId,
        message: currentInput,
        safe_mode: safeMode,
      });

      // Only add new assistant messages, don't replace all messages
      const newAssistantMessages = resp.data.messages.filter(msg => 
        msg.role === 'assistant' && 
        !messages.some(existingMsg => 
          existingMsg.role === 'assistant' && existingMsg.content === msg.content
        )
      );
      
      setMessages(prevMessages => [...prevMessages, ...newAssistantMessages]);

      if (resp.data.pending_command) {
        setPendingTerminal({ command: resp.data.pending_command });
      } else {
        setPendingTerminal(null);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleTerminalConfirm = async (accept) => {
    if (!pendingTerminal || loading) return;
    setLoading(true);

    const userReply = accept ? "[terminal confirm]: yes" : "[terminal confirm]: no";

    try {
      const resp = await axios.post(`${API_BASE}/chat`, {
        session_id: sessionId,
        message: userReply,
        safe_mode: safeMode,
      });
      
      // Filter out any error messages that come after confirmation
      const filteredMessages = resp.data.messages.filter(msg => 
        !(msg.role === 'user' && 
          typeof msg.content === 'string' && 
          msg.content.startsWith('Error: Could not process confirmation'))
      );
      
      setMessages(filteredMessages);

      // Find the last assistant message in the response
      const lastAssistantMsg = filteredMessages.slice().reverse().find(
        m => m.role === "assistant"
      );
      
      // Only clear pendingTerminal if a valid assistant message is present
      if (lastAssistantMsg) {
        setPendingTerminal(null);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!sessionId) {
      startSession();
    }
  }, []);

  return (
    <div className="app-container">
      <header>
        <h1>Agentic Assistant</h1>
        <div>
          <label className="safe-mode-toggle">
            <input
              type="checkbox"
              checked={safeMode}
              onChange={(e) => setSafeMode(e.target.checked)}
              disabled={loading || !!pendingTerminal}
            />
            Safe Mode
          </label>
          <button onClick={startSession} disabled={loading} className="new-session-btn">
            New Session
          </button>
        </div>
      </header>
      <div className="chat-window">
        {messages.map((msg, idx) => (
          <div key={idx} className={`chat-message ${msg.role}`}>
            <span className="role">{msg.role === 'user' ? 'You' : 'Assistant'}:</span>
            {msg.role === 'assistant' ? (
              <MarkdownMessage content={msg.content} />
            ) : (
              <span className="content">{msg.content}</span>
            )}
          </div>
        ))}
        {pendingTerminal && (
          <div className="chat-message assistant terminal-request">
            <span className="role">Assistant (Needs Confirmation):</span>
            <p>The agent wants to run the following command:</p>
            <pre className="terminal-block">{pendingTerminal.command}</pre>
            <div className="terminal-actions">
              <button onClick={() => handleTerminalConfirm(true)} disabled={loading} className="confirm-btn">Confirm</button>
              <button onClick={() => handleTerminalConfirm(false)} disabled={loading} className="dismiss-btn">Dismiss</button>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>
      <form className="input-form" onSubmit={sendMessage}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type your message..."
          disabled={!sessionId || loading || !!pendingTerminal}
        />
        <button type="submit" disabled={!input.trim() || loading || !sessionId || !!pendingTerminal}>
          Send
        </button>
      </form>
    </div>
  );
}

export default App;
