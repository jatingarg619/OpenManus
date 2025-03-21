import React, { useState, useEffect, useRef, lazy, Suspense } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { 
  Container, 
  TextField, 
  Button, 
  Paper, 
  Typography,
  Box,
  CircularProgress,
  AppBar,
  Toolbar,
  IconButton,
  Drawer,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Divider,
  useTheme
} from '@mui/material';
import {
  Menu as MenuIcon,
  Send as SendIcon,
  History as HistoryIcon,
  Delete as DeleteIcon,
  Settings as SettingsIcon,
  GitHub as GitHubIcon
} from '@mui/icons-material';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { atomDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import BrowserView from './components/BrowserView';
import MessageComponent from './components/MessageComponent';

const WS_URL = process.env.REACT_APP_WS_URL || 'ws://localhost:8000/ws';
const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Use React.lazy for code splitting
const BrowserViewLazy = lazy(() => import('./components/BrowserView'));
const AiBrowserAgent = lazy(() => import('./components/AiBrowserAgent'));

function App() {
  const [prompt, setPrompt] = useState('');
  const [messages, setMessages] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [conversations, setConversations] = useState([]);
  const wsRef = useRef(null);
  const messagesEndRef = useRef(null);
  const retryCount = useRef(0);
  const theme = useTheme();
  const [browserData, setBrowserData] = useState(null);
  const [showBrowser, setShowBrowser] = useState(false);

  const checkServerHealth = async () => {
    try {
      const response = await fetch(`${API_URL}/health`);
      return response.ok;
    } catch (error) {
      console.error('Health check failed:', error);
      return false;
    }
  };

  const connectWebSocket = async () => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return; // Already connected
    }

    // Check server health before attempting connection
    const isHealthy = await checkServerHealth();
    if (!isHealthy) {
      setMessages(prev => [...prev, {
        type: 'error',
        content: 'Server is not available. Retrying...'
      }]);
      
      // Retry after delay
      const backoffDelay = Math.min(1000 * Math.pow(2, retryCount.current), 30000);
      retryCount.current += 1;
      setTimeout(connectWebSocket, backoffDelay);
      return;
    }

    const ws = new WebSocket(WS_URL);
    
    ws.onopen = () => {
      setIsConnected(true);
      setMessages(prev => [...prev, {
        type: 'status',
        content: 'Connected to server'
      }]);
      console.log('Connected to WebSocket');
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log('Received WebSocket message:', data.type);
        
        // Handle all browser-related updates
        if (data.type === 'browser_content' || data.type === 'browser_event') {
          console.log('Setting browser data:', data.type, data.content ? Object.keys(data.content) : 'no content');
          setBrowserData(data);
          setShowBrowser(true);
        }
        
        // Handle other message types...
        if (data.type === 'thinking') {
          setMessages(prev => [...prev, { type: 'thinking', content: data.content }]);
        } else if (data.type === 'action') {
          setMessages(prev => [...prev, { type: 'action', content: data.content }]);
        } else if (data.type === 'result') {
          setIsLoading(false);
          setMessages(prev => [...prev, { type: 'result', content: data.content }]);
        } else if (data.type === 'status') {
          setMessages(prev => [...prev, { type: 'status', content: data.content }]);
        } else if (data.type === 'error') {
          setIsLoading(false);
          setMessages(prev => [...prev, { type: 'error', content: data.content }]);
        }
      } catch (error) {
        console.error('Error processing message:', error);
      }
    };

    ws.onclose = () => {
      setIsConnected(false);
      setMessages(prev => [...prev, {
        type: 'status',
        content: 'Disconnected from server. Attempting to reconnect...'
      }]);
      console.log('Disconnected from WebSocket');
      
      // Exponential backoff for reconnection
      const backoffDelay = Math.min(1000 * Math.pow(2, retryCount.current), 30000);
      retryCount.current += 1;
      
      setTimeout(connectWebSocket, backoffDelay);
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      setMessages(prev => [...prev, {
        type: 'error',
        content: 'Connection error occurred'
      }]);
    };

    wsRef.current = ws;
  };

  // Initialize connection
  useEffect(() => {
    const initConnection = async () => {
      try {
        await connectWebSocket();
      } catch (error) {
        console.error('Connection initialization failed:', error);
      }
    };

    initConnection();
    
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  // Reset retry count when successfully connected
  useEffect(() => {
    if (isConnected) {
      retryCount.current = 0;
    }
  }, [isConnected]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!prompt.trim() || !isConnected || isLoading) return;

    try {
      setIsLoading(true);
      wsRef.current.send(JSON.stringify({ prompt }));
      setMessages(prev => [...prev, { type: 'user', content: prompt }]);
      setPrompt('');
    } catch (error) {
      console.error('Error sending message:', error);
      setMessages(prev => [...prev, {
        type: 'error',
        content: 'Failed to send message'
      }]);
      setIsLoading(false);
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(scrollToBottom, [messages]);

  const handleNewConversation = () => {
    setMessages([]);
    setDrawerOpen(false);
  };

  const MessageContent = ({ content, type }) => {
    if (type === 'action' || type === 'thinking') {
      return (
        <ReactMarkdown
          components={{
            code({ node, inline, className, children, ...props }) {
              const match = /language-(\w+)/.exec(className || '');
              return !inline && match ? (
                <SyntaxHighlighter
                  style={atomDark}
                  language={match[1]}
                  PreTag="div"
                  {...props}
                >
                  {String(children).replace(/\n$/, '')}
                </SyntaxHighlighter>
              ) : (
                <code className={className} {...props}>
                  {children}
                </code>
              );
            }
          }}
        >
          {content}
        </ReactMarkdown>
      );
    }
    return <Typography>{content}</Typography>;
  };

  return (
    <Router>
      <Box sx={{ 
        display: 'flex', 
        flexDirection: 'column', 
        height: '100vh' 
      }}>
        <AppBar position="static">
          <Toolbar>
            <IconButton
              size="large"
              edge="start"
              color="inherit"
              onClick={() => setDrawerOpen(true)}
              sx={{ mr: 2 }}
            >
              <MenuIcon />
            </IconButton>
            <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
              OpenManus
            </Typography>
          </Toolbar>
        </AppBar>

        <Routes>
          <Route path="/" element={
            <Box sx={{ 
              display: 'flex', 
              flexGrow: 1,
              overflow: 'hidden'
            }}>
              {/* Chat Section */}
              <Box sx={{ 
                width: '50%',
                height: '100%', 
                display: 'flex',
                flexDirection: 'column',
                p: 2
              }}>
                <Box sx={{ 
                  flexGrow: 1, 
                  overflow: 'auto', 
                  mb: 2,
                  borderRadius: 1,
                  bgcolor: 'background.paper',
                  p: 2
                }}>
                  {messages.map((msg, index) => (
                    <MessageComponent key={index} message={msg} theme={theme} />
                  ))}
                  <div ref={messagesEndRef} />
                </Box>

                <Paper 
                  component="form" 
                  onSubmit={handleSubmit}
                  sx={{ 
                    p: 1, 
                    display: 'flex', 
                    alignItems: 'center' 
                  }}
                >
                  <TextField
                    fullWidth
                    variant="outlined"
                    placeholder="Enter your message..."
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                    disabled={!isConnected || isLoading}
                    size="small"
                    sx={{ mr: 1 }}
                  />
                  <Button 
                    type="submit" 
                    variant="contained" 
                    disabled={!isConnected || isLoading || !prompt.trim()}
                    endIcon={<SendIcon />}
                  >
                    Send
                  </Button>
                </Paper>
              </Box>

              {/* Browser Section */}
              <Box sx={{ 
                width: '50%', 
                height: '100%',
                p: 2,
                display: 'flex',
                flexDirection: 'column',
                position: 'relative',
                borderLeft: 1,
                borderColor: 'divider'
              }}>
                <Typography variant="subtitle1" gutterBottom>
                  Web Browser {browserData?.type === 'browser_content' ? '(HTML Content)' : ''}
                </Typography>
                <Box sx={{ flexGrow: 1 }}>
                  <Suspense fallback={<div>Loading browser...</div>}>
                    <BrowserViewLazy browserData={browserData} />
                  </Suspense>
                </Box>
              </Box>
            </Box>
          } />
          <Route path="/browser" element={
            <Suspense fallback={<div>Loading AI Browser...</div>}>
              <AiBrowserAgent />
            </Suspense>
          } />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>

        {/* Drawer for settings & history */}
        <Drawer
          anchor="left"
          open={drawerOpen}
          onClose={() => setDrawerOpen(false)}
        >
          <Box sx={{ width: 250 }}>
            <List>
              <ListItem button onClick={handleNewConversation}>
                <ListItemIcon><HistoryIcon /></ListItemIcon>
                <ListItemText primary="New Conversation" />
              </ListItem>
              <Divider />
              {conversations.map((conv, index) => (
                <ListItem button key={index}>
                  <ListItemIcon><HistoryIcon /></ListItemIcon>
                  <ListItemText primary={conv.title} />
                </ListItem>
              ))}
            </List>
          </Box>
        </Drawer>
      </Box>
    </Router>
  );
}

export default App; 