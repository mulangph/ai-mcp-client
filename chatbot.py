"""
ERP MCP Client

A Gradio chatbot that connects to the ERP MCP Server, discovers its tools at
runtime, and lets an OpenAI model call them to answer business questions.

Run (with the server already running):
    uv run chatbot.py
"""

import asyncio
import json
import os

import gradio as gr
from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from openai import OpenAI

load_dotenv()

MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1")
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8000/mcp")
MAX_TOOL_ROUNDS = 5

INSTRUCTIONS = """
You are an ERP business assistant.

Use the available tools to retrieve business information. You may call
several tools, or the same tool several times, to answer one question.

When a tool returns JSON data, never return the raw JSON to the user.
Analyze it and give a clear, natural-language business answer.

Be concise but include the important details:
- Orders: order number, customer, status, total amount, key items
- Inventory: available stock and whether a reorder is required
- Vendors: status, rating and payment terms

If a tool reports that a record was not found, say so plainly.
"""

client = OpenAI()


def to_openai_tool(tool) -> dict:
    """Convert an MCP tool definition into an OpenAI function tool."""
    return {
        "type": "function",
        "name": tool.name,
        "description": tool.description or "",
        "parameters": tool.input_schema,
    }


async def run_tool(session: ClientSession, call) -> dict:
    """Execute one model-requested tool call on the MCP server."""
    arguments = call.arguments
    if isinstance(arguments, str):
        arguments = json.loads(arguments or "{}")

    result = await session.call_tool(call.name, arguments=arguments)
    output = "\n".join(c.text for c in result.content if hasattr(c, "text"))

    return {"type": "function_call_output", "call_id": call.call_id, "output": output}


async def ask_mcp(user_message: str) -> str:
    async with streamable_http_client(MCP_SERVER_URL) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            # Discover tools from the MCP server
            tools_result = await session.list_tools()
            tools = [to_openai_tool(t) for t in tools_result.tools]

            response = client.responses.create(
                model=MODEL,
                instructions=INSTRUCTIONS,
                input=user_message,
                tools=tools,
            )

            # Keep calling tools until the model has everything it needs
            for _ in range(MAX_TOOL_ROUNDS):
                calls = [item for item in response.output if item.type == "function_call"]
                if not calls:
                    break

                outputs = [await run_tool(session, call) for call in calls]

                response = client.responses.create(
                    model=MODEL,
                    instructions=INSTRUCTIONS,
                    previous_response_id=response.id,
                    input=outputs,
                    tools=tools,
                )

            return response.output_text


def chat(message, history):
    try:
        return asyncio.run(ask_mcp(message))
    except Exception as exc:  # show a readable message instead of a stack trace
        if "connect" in str(exc).lower() or "ConnectError" in repr(exc):
            return (
                f"⚠️ Could not reach the MCP server at {MCP_SERVER_URL}. "
                "Start it with `uv run server.py` in the AI_MCP_Server folder."
            )
        return f"⚠️ Something went wrong: {exc}"


demo = gr.ChatInterface(
    fn=chat,
    title="ERP MCP Chatbot",
    description="Ask about sales orders, inventory and vendors.",
    examples=[
        "What is the status of order 12345?",
        "Do we need to reorder product 501?",
        "Compare vendors 2001 and 2002",
    ],
)

if __name__ == "__main__":
    demo.launch()
