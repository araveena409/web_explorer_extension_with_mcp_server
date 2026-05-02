import os
import asyncio
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

app = Flask(__name__)
CORS(app)

# Configuration - USER SHOULD SET THIS
GEMINI_API_KEY = "<YOUR_API_KEY>"
genai.configure(api_key=GEMINI_API_KEY)

# Define the server parameters
server_params = StdioServerParameters(
    command="python",
    args=[r"c:\AI\MCP Task\mcp_server.py"],
)

async def run_agent(prompt):
    print(f"[*] Connecting to MCP server at {server_params.command} {server_params.args}...")
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("[+] Connected to MCP server successfully.")
            
            # List available tools from the MCP server
            tools_resp = await session.list_tools()
            available_tools = tools_resp.tools
            print(f"[*] Found {len(available_tools)} tools from MCP server.")
            
            # Create a dictionary of tool functions for Gemini
            # In a real scenario, we'd map Gemini's tool calls to these session.call_tool calls
            
            model = genai.GenerativeModel('gemini-3.1-flash-lite-preview')
            
            def clean_schema(schema):
                if not isinstance(schema, dict):
                    return schema
                
                # 1. Remove problematic keywords from THIS schema object
                cleaned = {k: v for k, v in schema.items() if k not in ["title", "default", "examples"]}
                
                # 2. Handle 'properties' (dictionary of sub-schemas)
                if "properties" in cleaned and isinstance(cleaned["properties"], dict):
                    cleaned["properties"] = {
                        prop_name: clean_schema(prop_schema) 
                        for prop_name, prop_schema in cleaned["properties"].items()
                    }
                    
                    # 3. Fix 'required' list (only keep properties that actually exist)
                    if "required" in cleaned and isinstance(cleaned["required"], list):
                        cleaned["required"] = [r for r in cleaned["required"] if r in cleaned["properties"]]
                
                # 4. Handle 'items' (for array types)
                if "items" in cleaned:
                    cleaned["items"] = clean_schema(cleaned["items"])
                
                # 5. Handle 'allOf', 'anyOf', 'oneOf' (lists of sub-schemas)
                for composite in ["allOf", "anyOf", "oneOf"]:
                    if composite in cleaned and isinstance(cleaned[composite], list):
                        cleaned[composite] = [clean_schema(s) for s in cleaned[composite]]

                return cleaned

            # Simplified tool definitions for Gemini
            gemini_tools = []
            for tool in available_tools:
                print(f"[*] Processing schema for tool: {tool.name}")
                schema = clean_schema(tool.inputSchema)
                
                gemini_tools.append({
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": schema
                })

            system_instruction = (
                "You are an AI assistant in a Chrome extension. "
                "When answering the user, you MUST ALWAYS use the 'write_to_file' tool to save the resulting data "
                "AND ALWAYS use the 'render_prefab_ui' tool to generate a visual component. "
                "Then provide a short text response summarizing."
            )
            messages = [{"role": "user", "parts": [f"SYSTEM INSTRUCTION: {system_instruction}\n\nUSER REQUEST: {prompt}"]}]
            text_content = ""
            ui_data = None
            last_filename = "nobel_winners.txt" # Default
            
            print(f"[*] Sending prompt to Gemini: {prompt[:50]}...")
            for i in range(10):
                print(f"--- Iteration {i+1}/10 ---")
                # Call Gemini
                response = model.generate_content(
                    messages,
                    tools=[{"function_declarations": gemini_tools}]
                )
                
                print(f"response: {response}")
                # Check for candidates
                if not response.candidates:
                    print("[!] No candidates in response. It might be blocked or empty.")
                    break
                    
                # Add response to messages
                messages.append(response.candidates[0].content)
                
                # Check for tool calls and grouping them
                has_tool_call = False
                tool_responses_parts = []
                
                for part in response.candidates[0].content.parts:
                    if part.text:
                        text_content += part.text + "\n"
                    
                    if part.function_call:
                        has_tool_call = True
                        tool_name = part.function_call.name
                        def to_plain_python(obj):
                            if isinstance(obj, (dict, list, str, int, float, bool, type(None))):
                                if isinstance(obj, dict):
                                    return {k: to_plain_python(v) for k, v in obj.items()}
                                if isinstance(obj, list):
                                    return [to_plain_python(v) for v in obj]
                                return obj
                            # Handle Google SDK internal types (proto.marshal)
                            if hasattr(obj, "items"): # dict-like
                                return {k: to_plain_python(v) for k, v in obj.items()}
                            if hasattr(obj, "__iter__") and not isinstance(obj, str): # list-like
                                return [to_plain_python(v) for v in obj]
                            return obj

                        tool_args = to_plain_python(part.function_call.args)
                        print(f"[!] Gemini requested tool: {tool_name} with cleaned args: {tool_args}")
                        
                        # Call the MCP tool
                        print(f"[*] Executing tool {tool_name}...")
                        try:
                            tool_result = await session.call_tool(tool_name, tool_args)
                            result_text = tool_result.content[0].text
                            print(f"[+] Tool {tool_name} returned {len(result_text)} characters.")
                            
                            # Capture filename if writing
                            if tool_name == "write_to_file":
                                last_filename = tool_args.get("filename", last_filename)
                            
                            # Capture UI data if rendered
                            if tool_name == "render_prefab_ui":
                                try:
                                    ui_data = json.loads(result_text)
                                except:
                                    pass
                            
                            tool_responses_parts.append({
                                "function_response": {
                                    "name": tool_name,
                                    "response": {"result": result_text}
                                }
                            })
                        except Exception as te:
                            print(f"[X] Tool execution failed: {str(te)}")
                            tool_responses_parts.append({
                                "function_response": {
                                    "name": tool_name,
                                    "response": {"error": str(te)}
                                }
                            })

                if tool_responses_parts:
                    messages.append({
                        "role": "function",
                        "parts": tool_responses_parts
                    })
                
                if not has_tool_call:
                    print("[*] Gemini finished thinking (no more tool calls).")
                    break

            # If the model exhausted all iterations without providing text, force a text generation
            if not text_content:
                print("[*] Iteration limit reached without text output. Forcing text generation...")
                try:
                    # Append a final instruction to the conversation history to force a conclusion
                    messages.append({
                        "role": "user", 
                        "parts": ["Based on the search results you gathered, please provide a comprehensive final answer to the user request now. Do not use tools."]
                    })
                    
                    final_response = model.generate_content(
                        messages,
                        tools=[] 
                    )
                    if final_response.candidates:
                        for part in final_response.candidates[0].content.parts:
                            if part.text:
                                text_content += part.text + "\n"
                except Exception as e:
                    print(f"[X] Failed to force final text generation: {e}")
                    text_content = "Agent exhausted search attempts but could not finalize a response."

            # Final check for data in file to read and show
            file_data = await session.call_tool("read_file", {"filename": last_filename})
            raw_file_text = file_data.content[0].text if not "Error" in file_data.content[0].text else ""

            return {
                "text": text_content,
                "ui": ui_data,
                "file_content": raw_file_text
            }

@app.route('/', methods=['GET'])
def health_check():
    return jsonify({"status": "online", "message": "MCP Agent is reachable"}), 200

@app.route('/process', methods=['POST'])
def process_request():
    print("[*] Received request from extension...")
    data = request.json
    prompt = data.get("prompt")
    if not prompt:
        print("[!] No prompt in request.")
        return jsonify({"error": "No prompt provided"}), 400
    
    print(f"[*] Processing prompt: {prompt}")
    # Run the async agent loop
    try:
        result = asyncio.run(run_agent(prompt))
        print("[+] Request processed successfully.")
        return jsonify(result)
    except Exception as e:
        import traceback
        error_msg = str(e)
        traceback_str = traceback.format_exc()
        print(f"[X] Agent crashed: {error_msg}")
        print(f"[X] Traceback:\n{traceback_str}")
        if "429" in traceback_str or "ResourceExhausted" in traceback_str or "quota" in traceback_str.lower():
            return jsonify({
                "text": "⚠️ **API Rate Limit Exceeded (429 Quota Error)**\nYour Gemini API key has hit its usage limit for this model (likely the free tier RPM or RPD limit). Please wait a minute and try again, or use a 'Flash' model which has higher quotas.",
                "ui": None,
                "file_content": ""
            })
        return jsonify({"error": error_msg, "traceback": traceback_str}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000)
