import React, { useState, useEffect, useCallback, memo } from 'react';
import FileSelector from './FileSelector';

// Memoize the component to prevent unnecessary re-renders
const BrowserView = memo(({ browserData, onNavigate }) => {
  const [url, setUrl] = useState('');
  const [content, setContent] = useState('');
  const [htmlContent, setHtmlContent] = useState('');
  const [displayType, setDisplayType] = useState('url'); // 'url', 'html', or 'file'
  const [isLoading, setIsLoading] = useState(false);
  const [localFileName, setLocalFileName] = useState('');

  // Define handleFileSelect first, before using it in useEffect
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
        setHtmlContent(data.content); // Add this line to set the HTML content
        setDisplayType('html'); // Set display type to HTML for local files
        
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

  // Then use it in useEffect
  useEffect(() => {
    if (browserData) {
      console.log('BrowserView received browserData:', browserData);
      
      if (browserData.type === 'browser_content' && browserData.content?.html) {
        console.log('Setting HTML content from browser_content');
        setHtmlContent(browserData.content.html);
        setDisplayType('html');
      } else if (browserData.type === 'browser_event' && browserData.content?.url) {
        console.log('Setting URL from browser_event:', browserData.content.url);
        const url = browserData.content.url;
        
        // For Google Search HTML files in the static/temp directory
        if (url.includes('/static/temp/search_results_')) {
          console.log('Loading Google search results from static file');
          fetch(url.replace('file://', 'http://localhost:8001/'))
            .then(response => response.text())
            .then(html => {
              setHtmlContent(html);
              setDisplayType('html');
            })
            .catch(err => console.error('Error fetching search results:', err));
        } 
        // For regular file:// URLs
        else if (url.startsWith('file://')) {
          console.log('Loading local file:', url);
          const fileName = url.split('/').pop();
          setUrl(url);
          setDisplayType('url');
          handleFileSelect(url, fileName);
        } 
        // For regular web URLs
        else {
          setUrl(url);
          setDisplayType('url');
        }
      }
    }
  }, [browserData, handleFileSelect]);

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
        <div style={{display: 'flex', gap: '8px'}}>
          <button 
            onClick={() => window.history.back()}
            style={{
              background: 'none',
              border: '1px solid #ddd',
              borderRadius: '4px',
              padding: '4px 8px',
              cursor: 'pointer'
            }}
          >
            ←
          </button>
          <button 
            onClick={() => displayType === 'url' ? window.location.reload() : setHtmlContent(htmlContent)}
            style={{
              background: 'none',
              border: '1px solid #ddd',
              borderRadius: '4px',
              padding: '4px 8px',
              cursor: 'pointer'
            }}
          >
            ↻
          </button>
        </div>
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
        {displayType === 'html' && (
          <iframe
            srcDoc={htmlContent}
            style={{
              width: '100%',
              height: '100%',
              border: 'none'
            }}
            sandbox="allow-same-origin allow-scripts"
          />
        )}
        {displayType === 'url' && url ? (
          <iframe
            src={url}
            style={{
              width: '100%',
              height: '100%',
              border: 'none'
            }}
            sandbox="allow-same-origin allow-scripts"
          />
        ) : null}
      </div>
    </div>
  );
});

export default BrowserView; 