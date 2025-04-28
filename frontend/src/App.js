import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import './App.css';

const API_BASE = 'http://localhost:8000';

function App() {
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [pendingTerminal, setPendingTerminal] = useState(null); // {command: string, idx: number}
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

  // Helper: detect if a message is a terminal command request from the agent
  function parseTerminalCommand(msg) {
    // This logic can be improved if you use a more structured format in the backend
    // For now, look for a pattern like: [TERMINAL COMMAND]: <command>
    const match = msg.content.match(/\[TERMINAL COMMAND\]: ([^\n]+)/i);
    if (match) {
      return match[1].trim();
    }
    return null;
  }

  const sendMessage = async (e) => {
    e.preventDefault();
    if (!input.trim() || !sessionId) return;
    setLoading(true);
    setPendingTerminal(null);
    try {
      const resp = await axios.post(`${API_BASE}/chat`, {
        session_id: sessionId,
        message: input.trim(),
      });
      // Check if the last assistant message is a terminal command request
      const newMessages = resp.data.messages;
      const lastMsg = newMessages[newMessages.length - 1];
      const cmd = lastMsg && lastMsg.role === 'assistant' ? parseTerminalCommand(lastMsg) : null;
      setMessages(newMessages);
      setInput('');
      if (cmd) {
        setPendingTerminal({ command: cmd, idx: newMessages.length - 1 });
      }
    } finally {
      setLoading(false);
    }
  };

  // Handler for terminal command confirmation/rejection
  const handleTerminalConfirm = async (accept) => {
    if (!pendingTerminal) return;
    setLoading(true);
    try {
      const userReply = accept
        ? `[TERMINAL CONFIRM]: Yes, run: ${pendingTerminal.command}`
        : `[TERMINAL CONFIRM]: No, do not run: ${pendingTerminal.command}`;
      const resp = await axios.post(`${API_BASE}/chat`, {
        session_id: sessionId,
        message: userReply,
      });
      setMessages(resp.data.messages);
      setPendingTerminal(null);
      setInput('');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // Start a session on first load
    if (!sessionId) {
      startSession();
    }
    // eslint-disable-next-line
  }, []);

  return (
    <div className="app-container">
      <header>
        <h1>Agentic Assistant</h1>
        <button onClick={startSession} disabled={loading} className="new-session-btn">
          New Session
        </button>
      </header>
      <div className="chat-window">
        {messages.map((msg, idx) => {
          // If this is a pending terminal command, show with terminal style and buttons
          const isPending = pendingTerminal && pendingTerminal.idx === idx;
          const termCmd = parseTerminalCommand(msg);
          if (msg.role === 'assistant' && termCmd) {
            return (
              <div key={idx} className={`chat-message assistant terminal-request`}>
                <span className="role">Assistant (Terminal):</span>
                <pre className="terminal-block">{termCmd}</pre>
                {isPending && (
                  <span className="terminal-actions">
                    <button onClick={() => handleTerminalConfirm(true)} disabled={loading} className="accept-btn">Accept</button>
                    <button onClick={() => handleTerminalConfirm(false)} disabled={loading} className="reject-btn">Reject</button>
                  </span>
                )}
              </div>
            );
          }
          return (
            <div key={idx} className={`chat-message ${msg.role}`}>
              <span className="role">{msg.role === 'user' ? 'You' : 'Assistant'}:</span>
              <span className="content">{msg.content}</span>
            </div>
          );
        })}
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
