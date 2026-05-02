# Global imports
import os
import json
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("DataHandler")

BASE_DIR = r"c:\AI\MCP Task"

# Ensure the directory exists
if not os.path.exists(BASE_DIR):
    os.makedirs(BASE_DIR)

@mcp.tool()
def search_internet(query: str) -> str:
    """Search the internet for the given query and return the results, including webpage content."""
    from duckduckgo_search import DDGS
    import urllib.request
    import re
    
    try:
        results = []
        # 1. DuckDuckGo Search
        with DDGS() as ddgs:
            try:
                for r in ddgs.text(query, max_results=3):
                    results.append(r)
            except Exception as de:
                print(f"DuckDuckGo failed: {de}")
                
        # 2. Wikipedia API Search Fallback (General Purpose)
        if not results:
            try:
                import urllib.parse
                # Clean query for better wiki search
                clean_q = query.lower().replace("who won", "").replace("list of", "").strip()
                wiki_search_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(clean_q)}&format=json"
                req = urllib.request.Request(wiki_search_url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=5) as response:
                    wiki_data = json.loads(response.read().decode('utf-8'))
                    for r in wiki_data.get('query', {}).get('search', [])[:3]:
                        results.append({
                            "title": r['title'],
                            "href": f"https://en.wikipedia.org/wiki/{r['title'].replace(' ', '_')}",
                            "body": r['snippet']
                        })
            except Exception as e:
                print(f"Wikipedia fallback failed: {e}")
                
        # To give Gemini a "better response", we fetch the actual content of the first link
        if results:
            try:
                # Use the first URL that isn't just a placeholder
                first_url = results[0].get('href')
                if first_url:
                    req = urllib.request.Request(
                        first_url, 
                        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                    )
                    with urllib.request.urlopen(req, timeout=5) as response:
                        html = response.read().decode('utf-8', errors='ignore')
                        text = re.sub(r'<style.*?>.*?</style>', ' ', html, flags=re.DOTALL|re.IGNORECASE)
                        text = re.sub(r'<script.*?>.*?</script>', ' ', text, flags=re.DOTALL|re.IGNORECASE)
                        text = re.sub(r'<[^>]+>', ' ', text)
                        # Remove sequences of non-alphanumeric characters that aren't common punctuation
                        text = re.sub(r'[^a-zA-Z0-9\s.,!?;:\'\"-]', ' ', text)
                        text = re.sub(r'\s+', ' ', text).strip()
                        results[0]['scraped_website_content'] = text[:5000] 
            except Exception as e:
                results[0]['scraped_website_content'] = f"Could not scrape full text: {str(e)}"
        else:
            return "Error: No search results found via DuckDuckGo or Wikipedia fallback. Please try a broader query."
                
        return json.dumps(results, indent=2)
    except Exception as e:
        return f"Error searching internet: {str(e)}"

@mcp.tool()
def write_to_file(filename: str, content: str) -> str:
    """Write content to a file in the MCP Task directory."""
    if not filename.endswith(".txt") and not filename.endswith(".json"):
        filename += ".txt"
    
    file_path = os.path.join(BASE_DIR, os.path.basename(filename))
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully wrote to {file_path}"
    except Exception as e:
        return f"Error writing to file: {str(e)}"

@mcp.tool()
def update_file(filename: str, content: str) -> str:
    """Update (append) content to a file in the MCP Task directory."""
    file_path = os.path.join(BASE_DIR, os.path.basename(filename))
    try:
        if not os.path.exists(file_path):
            return write_to_file(filename, content)
        with open(file_path, "a", encoding="utf-8") as f:
            f.write("\n" + content)
        return f"Successfully updated {file_path}"
    except Exception as e:
        return f"Error updating file: {str(e)}"

@mcp.tool()
def read_file(filename: str) -> str:
    """Read content from a file in the MCP Task directory."""
    file_path = os.path.join(BASE_DIR, os.path.basename(filename))
    try:
        if not os.path.exists(file_path):
            return "File not found."
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"

@mcp.tool()
def render_prefab_ui(title: str, data_list: list) -> str:
    """
    Generates a PreFab UI JSON structure to be rendered in the Chrome Extension.
    data_list should be a list of objects with 'label' and 'value' keys.
    """
    prefab_config = {
        "type": "card",
        "title": title,
        "items": data_list
    }
    return json.dumps(prefab_config)

if __name__ == "__main__":
    mcp.run()
