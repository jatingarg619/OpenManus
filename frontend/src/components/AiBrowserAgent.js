import React, { useState, useEffect, useRef } from 'react';
import BrowserView from './BrowserView';

const AiBrowserAgent = () => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isThinking, setIsThinking] = useState(false);
  const [browserUrl, setBrowserUrl] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [localFiles, setLocalFiles] = useState(new Map());
  const [isConnected, setIsConnected] = useState(true);
  const messagesEndRef = useRef(null);
  const wsRef = useRef(null);

  // Auto scroll to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Reset thinking state if component unmounts
  useEffect(() => {
    return () => {
      setIsThinking(false);
    };
  }, []);

  // Connect to WebSocket
  useEffect(() => {
    const connectWebSocket = () => {
      try {
        wsRef.current = new WebSocket('ws://localhost:8000/ws');
        
        wsRef.current.onopen = () => {
          console.log('Connected to WebSocket server');
          setIsConnected(true);
          setMessages(prev => [...prev, {
            type: 'system',
            content: 'Connected to AI agent. What would you like me to help you with?'
          }]);
        };
        
        wsRef.current.onclose = () => {
          console.log('Disconnected from WebSocket server');
          setTimeout(connectWebSocket, 3000);
        };
        
        wsRef.current.onerror = (error) => {
          console.error('WebSocket error:', error);
        };
        
        wsRef.current.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            console.log('WebSocket message received:', data);
            
            if (data.type === 'browser_event') {
              // Handle browser events
              if (data.content?.url) {
                setBrowserUrl(data.content.url);
              }
            } else if (data.type === 'thinking') {
              // Show AI's thought process
              setIsThinking(true);
              setMessages(prev => [...prev, {
                type: 'thinking',
                content: data.content
              }]);
            } else if (data.type === 'progress') {
              // Show progress updates
              setMessages(prev => [...prev, {
                type: 'progress',
                content: data.content
              }]);
            } else if (data.type === 'result') {
              // Show final results with attachments
              setIsThinking(false);
              setMessages(prev => [...prev, {
                type: 'result',
                content: data.content,
                files: data.files
              }]);
            } else if (data.type === 'error') {
              // Show error messages
              setIsThinking(false);
              setMessages(prev => [...prev, {
                type: 'error',
                content: data.content
              }]);
            }
          } catch (error) {
            console.error('Error processing message:', error);
            setIsThinking(false);
          }
        };
      } catch (error) {
        console.error('Error setting up WebSocket:', error);
      }
    };
    
    connectWebSocket();
    
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    // Add user message
    setMessages(prev => [...prev, {
      type: 'user',
      content: input
    }]);

    // Send to server
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'user_input',
        content: input
      }));
      
      // Clear input and set thinking state
      setInput('');
      setIsThinking(true);
    } else {
      // Show connection error message
      setMessages(prev => [...prev, {
        type: 'error',
        content: 'Not connected to server. Please wait for reconnection...'
      }]);
    }
  };

  // Add file click handler
  const handleFileClick = (file) => {
    // Handle file opening based on type
    if (file.type === 'html') {
      handleNavigate({
        type: 'local',
        url: `file://${file.path}`,
        fileName: file.name
      });
    } else {
      // Handle other file types or download
      console.log('Opening file:', file);
    }
  };

  // Add this function to enhance browser communication
  const sendActionToAI = (action, details) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      const message = {
        type: 'browser_action',
        action: action,
        details: details
      };
      
      wsRef.current.send(JSON.stringify(message));
      
      // Also add to messages for user feedback
      setMessages(prev => [...prev, {
        type: 'system',
        content: `Browser ${action}: ${JSON.stringify(details)}`
      }]);
    }
  };
  
  // Enhanced handleNavigate
  const handleNavigate = (navInfo) => {
    setIsLoading(true);

    if (navInfo.type === 'local') {
      // Handle local file
      if (!localFiles.has(navInfo.url)) {
        localFiles.set(navInfo.url, navInfo.fileName);
        setLocalFiles(new Map(localFiles));
      }
      
      // Get served URL for local file
      fetch('http://localhost:8001/api/browser/open-local-file', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          file_path: navInfo.url.replace('file://', '')
        })
      })
      .then(response => response.json())
      .then(data => {
        // Navigate to served URL
        return fetch('http://localhost:8001/api/browser/action', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            action: 'navigate',
            url: data.url
          })
        });
      })
      .then(response => response.json())
      .then(data => {
        console.log('Navigation request sent:', data);
        sendActionToAI('navigate', { 
          type: 'local',
          fileName: navInfo.fileName,
          url: navInfo.url 
        });
      })
      .catch(error => {
        console.error('Error navigating:', error);
        setIsLoading(false);
      });
    } else {
      // Handle web URL
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
  
  return (
    <div style={{
      display: 'flex',
      height: '100vh',
      width: '100%'
    }}>
      {/* Chat panel */}
      <div style={{
        width: '50%',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        padding: '20px',
        backgroundColor: '#fff'
      }}>
        {/* Connection status indicator */}
        <div style={{
          padding: '4px 8px',
          borderRadius: '4px',
          backgroundColor: isConnected ? '#e8f5e9' : '#ffebee',
          color: isConnected ? '#2e7d32' : '#c62828',
          marginBottom: '10px',
          fontSize: '14px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center'
        }}>
          <span style={{
            height: '10px',
            width: '10px',
            borderRadius: '50%',
            backgroundColor: isConnected ? '#4caf50' : '#f44336',
            display: 'inline-block',
            marginRight: '8px'
          }}></span>
          {isConnected ? 'Connected to AI' : 'Disconnected - Trying to reconnect...'}
        </div>
        
        {/* Messages */}
        <div style={{
          flexGrow: 1,
          overflowY: 'auto',
          marginBottom: '20px'
        }}>
          {messages.map((msg, idx) => (
            <div key={idx} style={{
              marginBottom: '12px',
              display: 'flex',
              flexDirection: 'column'
            }}>
              {/* Message header */}
              <div style={{
                fontWeight: 'bold',
                marginBottom: '4px',
                color: msg.type === 'user' ? '#2196f3' : '#666'
              }}>
                {msg.type === 'user' ? 'You' : 'Manus'}
              </div>
              
              {/* Message content */}
              <div style={{
                padding: '12px',
                borderRadius: '8px',
                backgroundColor: 
                  msg.type === 'thinking' ? '#f5f5f5' :
                  msg.type === 'progress' ? '#e3f2fd' :
                  msg.type === 'result' ? '#e8f5e9' :
                  msg.type === 'error' ? '#ffebee' : '#fff',
                border: '1px solid #eee'
              }}>
                {msg.content}
                
                {/* Show files if present */}
                {msg.files && (
                  <div style={{ marginTop: '12px' }}>
                    {msg.files.map((file, fidx) => (
                      <div key={fidx} style={{
                        padding: '8px',
                        backgroundColor: '#f5f5f5',
                        borderRadius: '4px',
                        marginBottom: '8px',
                        cursor: 'pointer'
                      }} onClick={() => handleFileClick(file)}>
                        {file.name} - {file.type} · {file.size}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        {/* Input form */}
        <form onSubmit={handleSubmit} style={{
          display: 'flex',
          flexDirection: 'row'
        }}>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Tell the AI what to do..."
            style={{
              flexGrow: 1,
              padding: '12px',
              borderRadius: '4px',
              border: '1px solid #ccc',
              marginRight: '8px'
            }}
          />
          <button
            type="submit"
            disabled={!input.trim()}
            style={{
              padding: '12px 24px',
              borderRadius: '4px',
              border: 'none',
              backgroundColor: '#2196f3',
              color: 'white',
              cursor: !input.trim() ? 'not-allowed' : 'pointer',
              opacity: !input.trim() ? 0.7 : 1
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
        borderLeft: '1px solid #eee'
      }}>
        <BrowserView 
          onNavigate={handleNavigate}
          isLoading={isLoading}
        />
      </div>
    </div>
  );
};

export default AiBrowserAgent; 