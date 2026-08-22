

# ERP MCP Client

A Python-based client application demonstrating the power of the **Model Context Protocol (MCP)**. This project showcases how an LLM can dynamically discover and execute remote enterprise tools to serve as an intelligent ERP business assistant. 

It features an interactive web interface built with **Gradio** and uses OpenAI to orchestrate agentic tool-calling workflows.

---

## 🚀 Key Features

* **Dynamic Tool Discovery:** Automatically inspects and fetches tools exposed by a remote MCP server at runtime.
* **Agentic Orchestration:** Utilizes OpenAI to analyze user requests, decide if an enterprise tool is required, and process data.
* **Natural Language Processing:** Converts raw JSON data from ERP backends into concise, business-ready executive summaries.
* **Streamable HTTP Communication:** Uses asynchronous HTTP streams for robust and lightweight client-server communication.
* **Interactive UI:** Provides a clean web interface for users to easily query orders, check inventory, and manage vendors.

---

## 🛠️ Tech Stack

* **Project Management:** `uv` (Fast Python package installer and resolver)
* **Core Protocol:** Model Context Protocol (MCP) Python SDK
* **LLM Orchestration:** OpenAI API 
* **User Interface:** Gradio
* **Environment Management:** Python-dotenv

## Installation
uv add "mcp[cli]" openai gradio