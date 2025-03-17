import React from 'react';
import { Box } from '@mui/material';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { atomDark } from 'react-syntax-highlighter/dist/esm/styles/prism';

const MessageComponent = ({ message, theme }) => {
  const getMessageStyle = (type) => ({
    user: {
      bgcolor: theme.palette.primary.light,
      color: theme.palette.primary.contrastText,
      boxShadow: theme.shadows[1],
    },
    thinking: {
      bgcolor: theme.palette.grey[100],
      fontStyle: 'italic',
      borderLeft: `4px solid ${theme.palette.warning.main}`,
    },
    action: {
      bgcolor: theme.palette.background.paper,
      borderLeft: `4px solid ${theme.palette.success.main}`,
    },
    error: {
      bgcolor: theme.palette.error.light,
      color: theme.palette.error.contrastText,
      borderLeft: `4px solid ${theme.palette.error.main}`,
    },
    result: {
      bgcolor: theme.palette.background.paper,
      borderLeft: `4px solid ${theme.palette.primary.main}`,
    },
    status: {
      bgcolor: theme.palette.grey[100],
      color: theme.palette.text.secondary,
      textAlign: 'center',
    },
  }[type] || { bgcolor: theme.palette.background.paper });

  const renderContent = (content) => {
    if (typeof content !== 'string') {
      return JSON.stringify(content, null, 2);
    }

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
          },
        }}
      >
        {content}
      </ReactMarkdown>
    );
  };

  return (
    <Box 
      sx={{ 
        mb: 2,
        p: 2,
        borderRadius: 1,
        maxWidth: '85%',
        ml: message.type === 'user' ? 'auto' : 0,
        ...getMessageStyle(message.type)
      }}
    >
      {renderContent(message.content)}
    </Box>
  );
};

export default MessageComponent; 