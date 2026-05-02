# 🚀 Agentic MCP Explorer

A complete agentic ecosystem integrating a **Chrome Extension Side Panel**, a **Flask AI Agent**, and an **MCP Data Server**. This system allows you to search the internet, scrape deep website content, save findings to local files, and render custom UI components—all powered by Gemini.

---

# YOU TUBE Demo link
https://youtu.be/jEee6HWjSpk

## 🏗️ Architecture
1.  **Chrome Extension (Side Panel)**: The user interface that stays open persistently. It sends prompts to the Flask Agent.
2.  **Flask Agent (`agent.py`)**: The brain. It manages the conversation, calls the Gemini API, and orchestrates tool execution via the MCP Server.
3.  **MCP Server (`mcp_server.py`)**: The hands. It provides tools for searching, scraping, and local file I/O.

---

## ✨ Key Features
*   **Persistent Side Panel**: The UI stays open even as you browse different tabs.
*   **Deep Web Scraping**: The search tool doesn't just return snippets; it automatically visits the top search result and scrapes up to 5,000 characters of full-page text for Gemini to analyze.
*   **Dual-Layer Search**: Uses DuckDuckGo with an automatic **Wikipedia API Fallback** to ensure search results are never blocked.
*   **Iterative Reasoning**: The agent performs up to 10 iterations per request to ensure it gathers enough data before finalizing an answer.
*   **Auto-Conclusion**: If the agent reaches its iteration limit, it automatically triggers a "Final Wrap-up" phase to ensure the user always receives a response.
*   **PreFab UI Rendering**: Supports rendering custom JSON-based UI components directly in the extension.

---

## 🛠️ Setup & Installation

### 1. Requirements
*   Python 3.10+
*   Chrome Browser
*   Gemini API Key

### 2. Install Dependencies
```bash
pip install flask flask-cors google-generativeai mcp duckduckgo-search
```

### 3. Configure API Key
Open `agent.py` and set your Gemini API key at line 14:
```python
GEMINI_API_KEY = "YOUR_KEY_HERE"
```

---

## 🚀 How to Run

### Step 1: Start the MCP Server
Run this in your first terminal. It provides the tools to the AI.
```bash
mcp dev "c:\AI\MCP Task\mcp_server.py" --with duckduckgo-search
```

### Step 2: Start the Flask Agent
Run this in your second terminal. This bridges the extension and the AI.
```bash
python "c:\AI\MCP Task\agent.py"
```

### Step 3: Install the Extension
1.  Open Chrome and go to `chrome://extensions`.
2.  Enable **Developer mode** (top right).
3.  Click **Load unpacked** and select the `extension` folder in this directory.
4.  Pin the extension. Click the icon to open the **Side Panel**.

---

## 🛠️ MCP Tools Provided
| Tool | Description |
| :--- | :--- |
| `search_internet` | Searches DuckDuckGo/Wikipedia and scrapes the first result's content. |
| `write_to_file` | Saves search results or data to a local `.txt` file. |
| `read_file` | Reads any file from the local workspace. |
| `render_prefab_ui` | Generates a structured UI list for the Chrome Extension. |

---

## 📝 Troubleshooting
*   **Port in use (6274)**: This is the MCP Inspector. Kill the process using port 6274 or restart your terminal.
*   **Rate Limits (429)**: The system uses `gemini-3.1-flash-lite-preview`. If you hit rate limits, wait 60 seconds for the quota to reset.
*   **Blank Response**: The agent is now configured to force a conclusion if it takes too many steps. Try a broader search query.
