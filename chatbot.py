import os
from dotenv import load_dotenv
import asyncio
import json

import gradio as gr
from openai import OpenAI

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


load_dotenv()
#MODEL = "gpt-5-mini"
MODEL = "gpt-4.1"

MCP_SERVER_URL = "http://localhost:8000/mcp"

client = OpenAI()


async def ask_mcp(user_message: str) -> str:

    # Connect to the remote MCP server over HTTP
    async with streamable_http_client(MCP_SERVER_URL) as (
        read_stream,
        write_stream,
    ):

        async with ClientSession(
            read_stream,
            write_stream,
        ) as session:

            # Initialize MCP connection
            await session.initialize()

            # Discover tools from MCP server
            tools_result = await session.list_tools()

            tools = []

            for tool in tools_result.tools:
                tools.append(
                    {
                        "type": "function",
                        "name": tool.name,
                        "description": tool.description or "",
                        "parameters": tool.input_schema,
                    }
                )

            # Ask the LLM
            response = client.responses.create(
                model=MODEL,
                instructions="""
                You are an ERP business assistant.

                Use the available tools to retrieve business information.

                When a tool returns JSON data, never return the raw JSON
                directly to the user.

                Instead, analyze the data and provide a clear,
                natural-language business response.

                Be concise but include important information such as:
                - Order number
                - Customer
                - Order status
                - Total amount
                - Important order items

                If the user asks about inventory, explain stock
                availability and whether a reorder is required.

                If the user asks about vendors, summarize relevant
                vendor information such as status, rating, and payment terms.
                """,
                input=user_message,
                tools=tools,
            )

            # Check whether the model wants to call an MCP tool
            for item in response.output:

                if item.type != "function_call":
                    continue

                # OpenAI may return arguments as a JSON string
                arguments = item.arguments

                if isinstance(arguments, str):
                    arguments = json.loads(arguments)

                # Call the tool on the remote MCP server
                result = await session.call_tool(
                    item.name,
                    arguments=arguments,
                )

                # Extract the MCP tool response
                tool_result = "\n".join(
                    content.text
                    for content in result.content
                    if hasattr(content, "text")
                )

                # Send MCP result back to the LLM
                final_response = client.responses.create(
                    model=MODEL,
                    previous_response_id=response.id,
                    input=[
                        {
                            "type": "function_call_output",
                            "call_id": item.call_id,
                            "output": tool_result,
                        }
                    ],
                )

                return final_response.output_text

            # No MCP tool was required
            return response.output_text


def chat(message, history):
    return asyncio.run(ask_mcp(message))


demo = gr.ChatInterface(
    fn=chat,
    title="ERP MCP Chatbot",
    description="Ask questions about orders, inventory, and vendors.",
)

demo.launch()