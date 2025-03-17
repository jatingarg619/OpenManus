import React from 'react';
import { Link } from 'react-router-dom';

const Navigation = () => {
  return (
    <nav style={{
      padding: '1rem',
      backgroundColor: '#f5f5f5',
      marginBottom: '1rem'
    }}>
      <Link to="/" style={{ marginRight: '1rem' }}>Home</Link>
      <Link to="/browser">AI Browser</Link>
    </nav>
  );
};

export default Navigation; 