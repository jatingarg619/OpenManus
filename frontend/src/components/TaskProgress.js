import React from 'react';

const TaskProgress = ({ task, status, children }) => {
  // Extract emoji if present
  const emoji = task.match(/^[^\w\s]+/)?.[0] || '';
  const taskText = task.replace(/^[^\w\s]+/, '').trim();

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      gap: '8px',
      padding: '12px',
      backgroundColor: '#1e1e1e',
      borderRadius: '8px',
      color: '#fff',
      fontFamily: 'monospace'
    }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '8px'
      }}>
        <span style={{ fontSize: '16px' }}>{emoji}</span>
        <span style={{ color: '#fff' }}>{taskText}</span>
      </div>
      {children && (
        <div style={{
          marginLeft: '24px',
          color: '#888',
          fontSize: '14px',
          whiteSpace: 'pre-wrap'
        }}>
          {children}
        </div>
      )}
    </div>
  );
};

export default TaskProgress; 