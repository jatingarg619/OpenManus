import React from 'react';

const FileSelector = ({ onFileSelect }) => {
  const handleFileChange = async (event) => {
    const file = event.target.files[0];
    if (file) {
      try {
        // Get the file path using the webkitRelativePath or name
        const filePath = file.webkitRelativePath || file.name;
        
        // Request the server to serve this file
        const response = await fetch('http://localhost:8001/api/browser/open-local-file', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            file_path: filePath
          })
        });
        
        if (response.ok) {
          const data = await response.json();
          // Use the served URL from the server
          onFileSelect(data.url, file.name);
        } else {
          const error = await response.text();
          console.error('Failed to serve file:', error);
        }
      } catch (error) {
        console.error('Error handling file:', error);
      }
    }
  };

  return (
    <div style={{
      padding: '8px',
      borderBottom: '1px solid #ccc'
    }}>
      <input
        type="file"
        onChange={handleFileChange}
        accept=".html,.htm,.md,.txt"
        style={{ display: 'none' }}
        id="file-input"
        webkitdirectory=""
        directory=""
      />
      <label 
        htmlFor="file-input"
        style={{
          padding: '6px 12px',
          backgroundColor: '#f0f0f0',
          border: '1px solid #ccc',
          borderRadius: '4px',
          cursor: 'pointer',
          display: 'inline-block'
        }}
      >
        Open Local File
      </label>
    </div>
  );
};

export default FileSelector; 