import React, { useState, useEffect, useCallback, memo } from 'react';
import FileSelector from './FileSelector';

// Memoize the component to prevent unnecessary re-renders
const BrowserView = memo(({ browserData, onNavigate }) => {
  const [url, setUrl] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [content, setContent] = useState('');
  const [localFileName, setLocalFileName] = useState('');

  // Define handleFileSelect first
  const handleFileSelect = useCallback(async (fileUrl, fileName) => {
    setIsLoading(true);
    setLocalFileName(fileName);
    
    try {
      const response = await fetch('http://localhost:8001/api/browser/open-local-file', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          file_path: fileUrl.replace('file://', '')
        })
      });

      if (response.ok) {
        const data = await response.json();
        setContent(data.content);
        
        if (onNavigate) {
          onNavigate({
            type: 'local',
            fileName: fileName,
            content: data.content
          });
        }
      } else {
        console.error('Failed to load file:', await response.text());
      }
    } catch (error) {
      console.error('Error loading file:', error);
    } finally {
      setIsLoading(false);
    }
  }, [onNavigate]);

  // Then define fetchUrl using handleFileSelect
  const fetchUrl = useCallback(async () => {
    try {
      setIsLoading(true);
      const response = await fetch('http://localhost:8001/api/browser/current-url');
      if (response.ok) {
        const data = await response.json();
        if (data.url && data.url !== url) {
          // Handle file:// URLs
          if (data.url.startsWith('file://')) {
            const filepath = data.url.substring(7);
            const fileName = filepath.split('/').pop();
            handleFileSelect(data.url, fileName);
          } else {
            setUrl(data.url);
          }
        }
      }
    } catch (error) {
      console.error('Error fetching URL:', error);
    } finally {
      setIsLoading(false);
    }
  }, [url, handleFileSelect]);

  // Set up polling
  useEffect(() => {
    fetchUrl();
    const intervalId = setInterval(fetchUrl, 2000);
    return () => clearInterval(intervalId);
  }, [fetchUrl]);

  // Display either the URL or local filename
  const displayUrl = localFileName || url || 'No content loaded';

  return (
    <div style={{ 
      width: '100%', 
      height: '100%', 
      display: 'flex',
      flexDirection: 'column',
      border: '1px solid #ccc', 
      borderRadius: '4px', 
      overflow: 'hidden'
    }}>
      <FileSelector onFileSelect={handleFileSelect} />
      
      <div style={{ 
        padding: '8px', 
        borderBottom: '1px solid #ccc', 
        display: 'flex', 
        alignItems: 'center',
        backgroundColor: '#f5f5f5',
        justifyContent: 'space-between'
      }}>
        <div style={{ 
          overflow: 'hidden', 
          textOverflow: 'ellipsis', 
          whiteSpace: 'nowrap',
          maxWidth: '70%'
        }}>
          {isLoading ? 'Loading...' : displayUrl}
        </div>
      </div>
      
      <div style={{
        width: '100%',
        height: 'calc(100% - 80px)',
        overflow: 'auto',
        backgroundColor: 'white'
      }}>
        {content ? (
          <iframe
            srcDoc={content}
            style={{
              width: '100%',
              height: '100%',
              border: 'none'
            }}
            sandbox="allow-same-origin allow-scripts allow-forms allow-modals allow-popups allow-presentation"
            allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture"
          />
        ) : url ? (
          <iframe 
            src={url} 
            style={{ 
              width: '100%', 
              height: '100%',
              border: 'none'
            }}
            sandbox="allow-same-origin allow-scripts allow-forms allow-modals allow-popups allow-presentation"
            allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture"
          />
        ) : null}
      </div>
    </div>
  );
});

export default BrowserView; 