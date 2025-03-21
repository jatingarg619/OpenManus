import asyncio
from typing import List, Optional, Callable, Any
import os
import tempfile
from pathlib import Path

from googlesearch import search

from app.tool.base import BaseTool, ToolResult
from app.tool.browser_use_tool import BrowserUseTool


class GoogleSearch(BaseTool):
    name: str = "google_search"
    description: str = "Search Google for information and optionally open specific result links directly"
    event_handler: Optional[Callable] = None
    last_query: Optional[str] = None
    last_results: List[str] = []
    parameters: dict = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query to submit to Google"
            },
            "num_results": {
                "type": "integer",
                "description": "Number of results to return",
                "default": 5
            },
            "open_result": {
                "type": "integer",
                "description": "Open a specific result (1 for first result, 2 for second, etc.). Set to 0 to just view results without opening any link.",
                "default": 1
            }
        },
        "required": ["query"]
    }

    # Directory for temporary files
    temp_dir: str = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'static', 'temp')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Create temp directory if it doesn't exist
        os.makedirs(self.temp_dir, exist_ok=True)

    async def execute(self, **kwargs) -> ToolResult:
        try:
            # Extract and validate query
            query = kwargs.get("query")
            if not query:
                return ToolResult(error="Query parameter is required")
                
            num_results = kwargs.get("num_results", 5)
            open_result = kwargs.get("open_result", 1)  # 1 means open the first result
            
            # Get search results
            results = list(search(query, num_results=num_results))
            
            # Store the results for future reference
            self.last_query = query
            self.last_results = results
            
            # Create HTML content
            html_content = self._create_html_content(query, results)
            
            # Save to temporary file with a more unique name
            filename = f'search_results_{abs(hash(query))}.html'
            temp_file = os.path.join(self.temp_dir, filename)
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            # Get an instance of BrowserUseTool and use it to open the file
            browser_tool = BrowserUseTool()
            
            # If we have an event handler, pass it to the browser tool
            if hasattr(self, 'event_handler') and self.event_handler:
                browser_tool.event_handler = self.event_handler
            
            # Show the search results
            await browser_tool.execute(action="navigate", url=f"file://{temp_file}")
            
            # If open_result is specified and valid, navigate to that result
            if open_result > 0 and open_result <= len(results):
                # Get the URL of the selected result
                result_url = results[open_result - 1]
                
                # Log the URL we're navigating to
                print(f"Agent is opening result #{open_result}: {result_url}")
                
                # Add a longer delay before navigating to give time to view results
                print(f"Waiting 5 seconds before navigating to allow viewing search results...")
                await asyncio.sleep(5.0)
                
                # Always use the content extraction approach first
                print(f"Extracting and displaying content from: {result_url}")
                extracted_url = await self._fetch_and_display_content(result_url)
                
                if extracted_url:
                    # Use extracted content
                    await browser_tool.execute(action="navigate", url=extracted_url)
                    
                    # Add a longer delay to ensure the agent sees the content
                    await asyncio.sleep(3.0)
                    
                    return ToolResult(
                        output=f"Found {len(results)} results for '{query}' and displayed extracted content from result #{open_result}: {result_url}\n\n"
                        f"IMPORTANT: The browser is now showing the content from the selected result. "
                        f"Take time to examine this content before continuing. "
                        f"To return to search results, search for '{query}' again."
                    )
                else:
                    # Fall back to direct navigation if extraction fails
                    print(f"Content extraction failed, attempting direct navigation to: {result_url}")
                    await browser_tool.execute(action="navigate", url=result_url)
                    return ToolResult(
                        output=f"Found {len(results)} results for '{query}' and attempted to open result #{open_result}: {result_url}\n\n"
                        f"Note: Some websites may block being displayed in this view due to security restrictions. "
                        f"To return to search results, the agent can search for '{query}' again."
                    )
            
            return ToolResult(output=f"Found {len(results)} results for '{query}'")
            
        except Exception as e:
            print(f"GoogleSearch error: {str(e)}")
            import traceback
            traceback.print_exc()
            return ToolResult(error=f"Search failed: {str(e)}")

    def _create_html_content(self, query: str, results: List[str]) -> str:
        """Create HTML content for search results"""
        html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Search Results: {query}</title>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        padding: 20px;
                        max-width: 800px;
                        margin: 0 auto;
                        background-color: #f9f9f9;
                    }}
                    .result {{
                        margin-bottom: 20px;
                        padding: 15px;
                        border-radius: 8px;
                        border: 1px solid #eee;
                        background-color: white;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
                        transition: all 0.2s;
                    }}
                    .result:hover {{
                        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                        transform: translateY(-2px);
                    }}
                    .title {{
                        color: #1a0dab;
                        font-size: 18px;
                        text-decoration: none;
                        display: block;
                        margin-bottom: 5px;
                        font-weight: 500;
                    }}
                    .url {{
                        color: #006621;
                        font-size: 13px;
                        margin-bottom: 8px;
                        word-break: break-all;
                    }}
                    .snippet {{
                        color: #545454;
                        font-size: 14px;
                        line-height: 1.5;
                    }}
                    .search-header {{
                        margin-bottom: 20px;
                        padding-bottom: 10px;
                        border-bottom: 2px solid #eee;
                    }}
                    .search-info {{
                        color: #666;
                        font-size: 14px;
                    }}
                    .visit-btn {{
                        display: inline-block;
                        margin-top: 10px;
                        padding: 6px 12px;
                        background-color: #f0f7ff;
                        color: #1a73e8;
                        border-radius: 4px;
                        font-size: 13px;
                        text-decoration: none;
                        border: 1px solid #d2e3fc;
                    }}
                    .visit-btn:hover {{
                        background-color: #e8f1fe;
                    }}
                </style>
            </head>
            <body>
                <div class="search-header">
                    <h2>Search Results: {query}</h2>
                    <p class="search-info">Found {len(results)} results</p>
                </div>
                <div class="results">
                    {self._generate_result_html(results)}
                </div>
            </body>
            </html>
            """
        return html

    def _generate_result_html(self, results: List[str]) -> str:
        """Generate HTML for individual search results"""
        result_html = ""
        for url in results:
            title = self._get_title_from_url(url)
            snippet = self._generate_snippet(url, title)
            result_html += f"""
                    <div class="result">
                        <a href="{url}" class="title" target="_blank">{title}</a>
                        <div class="url">{url}</div>
                        <div class="snippet">{snippet}</div>
                        <a href="{url}" class="visit-btn" target="_blank">Visit Site</a>
                    </div>
                    """
        return result_html

    def _get_title_from_url(self, url: str) -> str:
        """Extract a readable title from URL"""
        try:
            # Remove protocol, www and trailing slashes
            clean_url = url.replace('https://', '').replace('http://', '').replace('www.', '')
            # Remove query params and fragments
            if '?' in clean_url:
                clean_url = clean_url.split('?')[0]
            if '#' in clean_url:
                clean_url = clean_url.split('#')[0]
                
            # Remove trailing slash
            if clean_url.endswith('/'):
                clean_url = clean_url[:-1]
                
            # Get the last part of the path
            parts = clean_url.split('/')
            if len(parts) > 1 and parts[-1]:
                # Replace dashes and underscores with spaces
                title = parts[-1].replace('-', ' ').replace('_', ' ')
                # Capitalize first letter of each word
                return ' '.join(word.capitalize() for word in title.split())
            else:
                # Use domain name if no path
                domain = parts[0].split('.')[0].capitalize()
                return f"{domain} - Home Page"
        except:
            return url
            
    def _generate_snippet(self, url: str, query: str) -> str:
        """Generate a snippet description for the result"""
        # In a real implementation, you would fetch and parse the page content
        # For now, generate a synthetic snippet based on the URL and query
        keywords = query.lower().split()
        domain = url.replace('https://', '').replace('http://', '').split('/')[0]
        
        snippets = [
            f"Find information about {' and '.join(keywords)} on this site.",
            f"Explore {' '.join(keywords)} with detailed guides and resources.",
            f"Learn about {', '.join(keywords)} from {domain}'s comprehensive collection.",
            f"Discover {query} information with expert advice and tips.",
            f"Get the latest updates and information on {query} from this trusted source."
        ]
        import random
        return random.choice(snippets)

    def __del__(self):
        """Cleanup temporary files on deletion"""
        try:
            for file in Path(self.temp_dir).glob('search_results_*.html'):
                file.unlink()
        except:
            pass

    # Add a new method to fetch and display external content
    async def _fetch_and_display_content(self, url: str) -> str:
        """Fetch external content and prepare it for display"""
        try:
            # First show a loading page to make navigation visible
            loading_page_url = self._create_loading_page(url)
            if loading_page_url:
                # Get an instance of BrowserUseTool and use it to open the loading page
                browser_tool = BrowserUseTool()
                if hasattr(self, 'event_handler') and self.event_handler:
                    browser_tool.event_handler = self.event_handler
                
                # Show loading page first
                await browser_tool.execute(action="navigate", url=loading_page_url)
            
            # Now try to fetch the actual content
            import aiohttp
            
            # Create a session with appropriate headers
            async with aiohttp.ClientSession(headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36'
            }) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        # Get the content
                        html_content = await response.text()
                        
                        # Basic content extraction (you could use a library like readability for better results)
                        from bs4 import BeautifulSoup
                        soup = BeautifulSoup(html_content, 'html.parser')
                        
                        # Extract title
                        title = soup.title.string if soup.title else url
                        
                        # Extract main content - this is a simple approach
                        # For better results, use a dedicated content extraction library
                        main_content = ""
                        
                        # Try to find main content containers
                        for tag in ['article', 'main', 'div.content', 'div.main', 'div#content', 'div#main']:
                            content_element = soup.select_one(tag)
                            if content_element:
                                main_content = content_element.get_text()
                                break
                        
                        # If couldn't find main content, use body
                        if not main_content and soup.body:
                            main_content = soup.body.get_text()
                        
                        # Create a simplified HTML version
                        simplified_html = f"""
                        <!DOCTYPE html>
                        <html>
                        <head>
                            <title>{title}</title>
                            <style>
                                body {{
                                    font-family: Arial, sans-serif;
                                    line-height: 1.6;
                                    margin: 0;
                                    padding: 20px;
                                    max-width: 800px;
                                    margin: 0 auto;
                                }}
                                .header {{
                                    margin-bottom: 20px;
                                    padding-bottom: 10px;
                                    border-bottom: 1px solid #eee;
                                }}
                                .content {{
                                    white-space: pre-line;
                                }}
                                .source {{
                                    margin-top: 20px;
                                    padding-top: 10px;
                                    border-top: 1px solid #eee;
                                    font-size: 14px;
                                    color: #666;
                                }}
                            </style>
                        </head>
                        <body>
                            <div class="header">
                                <h1>{title}</h1>
                            </div>
                            <div class="content">{main_content}</div>
                            <div class="source">
                                Source: <a href="{url}" target="_blank">{url}</a>
                            </div>
                        </body>
                        </html>
                        """
                        
                        # Save to temporary file
                        import uuid
                        temp_file = os.path.join(self.temp_dir, f'extracted_{uuid.uuid4().hex}.html')
                        with open(temp_file, 'w', encoding='utf-8') as f:
                            f.write(simplified_html)
                        
                        return f"file://{temp_file}"
                    else:
                        return None
        except Exception as e:
            print(f"Error fetching content: {str(e)}")
            return None

    # Create a loading/error page that shows the URL being loaded
    def _create_loading_page(self, url: str) -> str:
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Loading {url}</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    text-align: center;
                    margin-top: 100px;
                }}
                .loading {{
                    display: block;
                    margin: 20px auto;
                    width: 50px;
                    height: 50px;
                    border: 5px solid #f3f3f3;
                    border-top: 5px solid #3498db;
                    border-radius: 50%;
                    animation: spin 2s linear infinite;
                }}
                @keyframes spin {{
                    0% {{ transform: rotate(0deg); }}
                    100% {{ transform: rotate(360deg); }}
                }}
                .url {{
                    margin: 20px;
                    padding: 10px;
                    background-color: #f9f9f9;
                    border: 1px solid #ddd;
                    display: inline-block;
                    word-break: break-all;
                }}
                .error {{
                    color: #e74c3c;
                    margin-top: 20px;
                    display: none;
                }}
                .back {{
                    margin-top: 20px;
                    padding: 10px 20px;
                    background-color: #3498db;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    cursor: pointer;
                }}
            </style>
            <script>
                // Show error message after timeout
                setTimeout(function() {{
                    document.querySelector('.error').style.display = 'block';
                    document.querySelector('.loading').style.display = 'none';
                }}, 8000);
            </script>
        </head>
        <body>
            <h2>Loading External Content</h2>
            <div class="url">{url}</div>
            <div class="loading"></div>
            <div class="error">
                <p>The content could not be displayed due to security restrictions.</p>
                <p>Many websites prevent being displayed in embedded frames.</p>
                <p>You can try viewing the extracted content instead.</p>
            </div>
        </body>
        </html>
        """
        
        # Save to temp file
        import uuid
        temp_file = os.path.join(self.temp_dir, f'loading_{uuid.uuid4().hex}.html')
        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write(html)
        
        return f"file://{temp_file}"
