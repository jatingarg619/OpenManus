import React, { useState, useEffect, useRef } from 'react';
import BrowserView from './BrowserView';
import TaskProgress from './TaskProgress';
import ReactMarkdown from 'react-markdown';

const AiBrowserAgent = () => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isThinking, setIsThinking] = useState(false);
  const [browserUrl, setBrowserUrl] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [localFiles, setLocalFiles] = useState(new Map());
  const wsRef = useRef(null);
  const messagesEndRef = useRef(null);
  const [browserData, setBrowserData] = useState(null);

  // Auto scroll to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Connect to WebSocket
  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8000/ws');
    
    ws.onopen = () => {
      console.log('Connected to WebSocket server');
      setMessages(prev => [...prev, {
        type: 'system',
        content: 'Connected to AI agent. What would you like me to help you with?'
      }]);
    };
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log('WebSocket message received:', data);

        // Handle browser content specifically
        if (data.type === 'browser_content') {
          console.log('Received browser_content message with HTML');
          setBrowserData(data);
          return; // Don't process as a regular message
        } else if (data.type === 'browser_event') {
          console.log('Received browser_event message');
          setBrowserData(data);
        }
        // Handle special message types
        else if (data.type === 'api' || data.type === 'app') {
          // Skip logging messages
          return;
        }

        // Handle INFO messages with emojis
        if (data.content?.includes('✨') || 
            data.content?.includes('🛠️') || 
            data.content?.includes('🧰') || 
            data.content?.includes('🔧') || 
            data.content?.includes('🎯')) {
          
          setMessages(prev => [...prev, {
            type: 'thinking',
            task: data.content.split('\n')[0], // First line as task
            content: data.content.split('\n').slice(1).join('\n'), // Rest as content
            status: 'in_progress'
          }]);
        }
        // Handle tool results
        else if (data.content?.startsWith('Observed output')) {
          setMessages(prev => [...prev, {
            type: 'thinking',
            task: '🔧 Tool Result',
            content: data.content,
            status: 'completed'
          }]);
        }
        // Handle regular messages
        else {
          setMessages(prev => [...prev, {
            type: data.type || 'thinking',
            content: data.content,
            files: data.files
          }]);
        }
      } catch (e) {
        console.error('Error processing message:', e);
      }
    };
    
    wsRef.current = ws;
    return () => ws.close();
  }, []);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!input.trim()) return;
    
    // Add user message
    setMessages(prev => [...prev, {
      type: 'user',
      content: input
    }]);
    
    // Send message to server
    wsRef.current?.send(JSON.stringify({
      type: 'user_input',
      content: input
    }));
    
    setInput('');
    setIsThinking(true);
  };

  const handleNavigate = (navInfo) => {
    setIsLoading(true);
    
    if (navInfo.type === 'local') {
      // Handle local file navigation
      if (!localFiles.has(navInfo.url)) {
        localFiles.set(navInfo.url, navInfo.fileName);
        setLocalFiles(new Map(localFiles));
      }
      
      // Send local file info to AI
      sendActionToAI('navigate', { 
        type: 'local',
        fileName: navInfo.fileName,
        content: navInfo.content 
      });
    } else {
      // Handle web URL navigation
      fetch('http://localhost:8001/api/browser/action', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          action: 'navigate',
          url: navInfo.url
        })
      })
      .then(response => response.json())
      .then(data => {
        console.log('Navigation request sent:', data);
        sendActionToAI('navigate', { url: navInfo.url });
      })
      .catch(error => {
        console.error('Error navigating:', error);
        setIsLoading(false);
      });
    }
  };

  const sendActionToAI = (action, data) => {
    wsRef.current?.send(JSON.stringify({
      type: 'browser_action',
      action: action,
      data: data
    }));
  };

  const renderMessage = (msg, idx) => {
    switch (msg.type) {
      case 'user':
        return (
          <div style={{
            padding: '12px',
            borderRadius: '8px',
            backgroundColor: '#e3f2fd',
            border: '1px solid #e0e0e0',
            maxWidth: '90%',
            alignSelf: 'flex-end'
          }}>
            {msg.content}
          </div>
        );

      case 'thinking':
        return (
          <TaskProgress 
            task={msg.task} 
            status={msg.status}
          >
            {msg.content && (
              <div style={{ whiteSpace: 'pre-wrap' }}>
                <ReactMarkdown>{msg.content}</ReactMarkdown>
              </div>
            )}
          </TaskProgress>
        );

      default:
        return (
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '12px',
            maxWidth: '90%',
            alignSelf: 'flex-start'
          }}>
            <div style={{
              padding: '12px',
              borderRadius: '8px',
              backgroundColor: '#1e1e1e',
              color: '#fff',
              fontFamily: 'monospace'
            }}>
              <div style={{ whiteSpace: 'pre-wrap' }}>
                <ReactMarkdown>{msg.content}</ReactMarkdown>
              </div>
              {msg.files && msg.files.length > 0 && (
                <div style={{ 
                  marginTop: '12px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '8px'
                }}>
                  {msg.files.map((file, fileIdx) => (
                    <div 
                      key={fileIdx}
                      style={{
                        padding: '8px 12px',
                        backgroundColor: '#2d2d2d',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                        fontSize: '14px'
                      }}
                      onClick={() => handleNavigate({ 
                        type: 'local', 
                        url: `file://${file.path}`,
                        fileName: file.name
                      })}
                    >
                      <span style={{ color: '#fff' }}>{file.name}</span>
                      <span style={{ color: '#888' }}>
                        {file.type} · {file.size}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        );
    }
  };

  return (
    <div style={{
      display: 'flex',
      height: '100vh',
      padding: '20px',
      gap: '20px',
      backgroundColor: '#f5f5f5'
    }}>
      {/* Chat panel */}
      <div style={{
        width: '50%',
        display: 'flex',
        flexDirection: 'column',
        gap: '20px',
        backgroundColor: 'white',
        borderRadius: '8px',
        padding: '20px',
        boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
      }}>
        {/* Messages container */}
        <div style={{
          flexGrow: 1,
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column',
          gap: '12px'
        }}>
          {messages.map((msg, idx) => renderMessage(msg, idx))}
          <div ref={messagesEndRef} />
        </div>
        
        {/* Input form */}
        <form onSubmit={handleSubmit} style={{
          display: 'flex',
          gap: '12px'
        }}>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask me anything..."
            style={{
              flexGrow: 1,
              padding: '12px',
              borderRadius: '8px',
              border: '1px solid #e0e0e0',
              fontSize: '16px'
            }}
          />
          <button
            type="submit"
            disabled={isThinking}
            style={{
              padding: '12px 24px',
              borderRadius: '8px',
              border: 'none',
              backgroundColor: '#2196f3',
              color: 'white',
              cursor: isThinking ? 'not-allowed' : 'pointer',
              opacity: isThinking ? 0.7 : 1,
              fontSize: '16px',
              fontWeight: 500
            }}
          >
            {isThinking ? 'Thinking...' : 'Send'}
          </button>
        </form>
      </div>
      
      {/* Browser panel */}
      <div style={{
        width: '50%',
        height: '100%',
        backgroundColor: 'white',
        borderRadius: '8px',
        overflow: 'hidden',
        boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
      }}>
        <BrowserView 
          onNavigate={handleNavigate} 
          isLoading={isLoading}
          browserData={browserData}
        />
      </div>
    </div>
  );
};

export default AiBrowserAgent; 