# 🥗 Smart Recipe Concierge

> **The AI-Powered Culinary Assistant & Digital Household Pantry**  
> *Built with Google Agent Development Kit (ADK), Gemini 2.5 Flash, Vertex AI Agent Runtime, Firestore, Cloud Storage, Vertex AI Memory Bank, RAG Engine, and A2UI.*

---

## 🎬 Product Launch Demo

![Smart Recipe Concierge Live Demo](demo.gif)

*Watch the Smart Recipe Concierge in action: searching the digital household pantry in Firestore, retrieving grounded historical remedy wisdom via Vertex AI RAG Engine, and rendering rich A2UI recipe cards with AI-generated dish photography.*

---

## 🚀 Product Overview

**Smart Recipe Concierge** is an agentic application designed to transform home cooking, meal planning, and digital kitchen inventory management. Built on Google Cloud's Agent Development Kit (ADK) and deployed to **Vertex AI Agent Runtime**, the agent goes beyond standard conversational AI by combining persistent database management, cross-session memory, grounded document retrieval, generative dish visualization, server-side code execution, and structured A2UI card rendering.

---

## ✨ Verified Capabilities & Feature Matrix

Every capability listed below is fully implemented, wired, and verified in the codebase:

| Capability | Google Cloud Service / Tech Stack | Implementation Detail in Codebase |
| :--- | :--- | :--- |
| **🧠 Cross-Session Memory** | **Vertex AI Memory Bank** | `PreloadMemoryTool` & `add_session_to_memory` callback in `app/agent.py` automatically store and retrieve user dietary preferences across sessions. |
| **🗄️ Digital Pantry Management** | **Google Cloud Firestore** | `search_pantry` tool queries the `pantry_inventory` NoSQL collection to list active ingredients, quantities, and expiration dates. |
| **☁️ Persistent Media Storage** | **Google Cloud Storage (GCS)** | Dedicated public GCS bucket (`smart-recipe-assets-...`) hosts uploaded recipe photography and generated dish assets with public HTTPS URLs. |
| **📚 Grounded Knowledge RAG** | **Vertex AI RAG Engine** | `search_medical_guide` function tool performs semantic vector search over an indexed historical culinary and herbal reference manual. |
| **🎨 Generative Dish Imagery** | **`gemini-3.1-flash-lite-image`** | `generate_dish_image` function tool generates 1024x1024 dish photos, saves them as Playground artifacts, and uploads JPEG bytes to GCS. |
| **⚡ Server-Side Code Execution** | **Agent Engine Code Sandbox** | `AgentEngineSandboxCodeExecutor` enables safe Python code execution in an isolated container sandbox for recipe nutrition math. |
| **📱 Rich Component Cards** | **A2UI Agent SDK (v0.8)** | `a2ui-agent-sdk` integration with `BasicCatalog` emits declarative JSON components (`Card`, `Column`, `Row`, `Text`, `Image`, `Icon`). |
| **💻 Custom Web Frontend** | **FastAPI + A2A Protocol** | Same-origin FastAPI proxy (`frontend/main.py`) forwards chat turns via `a2a-sdk` to Agent Runtime, serving a glassmorphic dark-mode UI. |

---

## 🏗️ Technical Architecture & Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          Glassmorphic Web Frontend                              │
│                    (Plus Jakarta Sans + A2UI Mini-Renderer)                     │
└────────────────────────────────────────┬────────────────────────────────────────┘
                                         │  HTTP /chat JSON
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                               FastAPI Proxy                                     │
│                     (A2A Protocol Client with ADC Auth)                         │
└────────────────────────────────────────┬────────────────────────────────────────┘
                                         │  A2A Protocol / gRPC
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      Vertex AI Agent Runtime Deployment                         │
│                    (Root Agent powered by Gemini 2.5 Flash)                     │
└─────┬──────────────────┬─────────────────┬─────────────────┬──────────────┬─────┘
      │                  │                 │                 │              │
      ▼                  ▼                 ▼                 ▼              ▼
┌───────────┐      ┌───────────┐     ┌───────────┐     ┌───────────┐  ┌───────────┐
│  Memory   │      │ Firestore │     │    GCS    │     │   RAG     │  │ Image Gen │
│   Bank    │      │ Database  │     │  Bucket   │     │  Engine   │  │  Global   │
└───────────┘      └───────────┘     └───────────┘     └───────────┘  └───────────┘
```

1. **User Interaction**: The user submits queries through the custom web interface or suggestion pills.
2. **A2A Translation**: The FastAPI proxy retrieves the agent's A2A card and sends messages via `a2a-sdk`.
3. **Agent Reasoning**: The root agent evaluates context, retrieves long-term preferences from Vertex AI Memory Bank, and selects tools.
4. **Tool Execution**:
   - `search_pantry`: Connects to Firestore to pull real-time kitchen inventory.
   - `search_medical_guide`: Performs semantic search on the Vertex AI RAG Engine vector corpus.
   - `generate_dish_image`: Invokes `gemini-3.1-flash-lite-image` in the `global` region and saves image bytes to GCS.
5. **A2UI Output Generation**: The `a2ui_callback` converts structured model responses into declarative A2UI card schemas for rich UI rendering.

---

## 💻 Local Setup & Running Instructions

### Prerequisites
- Python 3.10+
- Google Cloud SDK (`gcloud`) authenticated with a project
- Node.js 18+ (for recording tools or dev frontend)

### 1. Environment Setup

Clone the repository and install dependencies using `uv`:

```bash
cd smart-recipe-concierge
uv sync
```

Set required environment variables:

```bash
export GOOGLE_CLOUD_PROJECT="<your-gcp-project-id>"
export GOOGLE_CLOUD_LOCATION="us-east1"
```

### 2. Run Agent Locally in ADK Playground

Start the local Agent Development Kit playground:

```bash
agents-cli playground
```

Access the playground UI in your browser at the local port printed by `agents-cli`.

### 3. Run Custom FastAPI Web Frontend

Navigate to the `frontend` directory, set the deployed agent resource name, and launch the proxy:

```bash
cd frontend
export AGENT_ENGINE_RESOURCE_NAME="projects/<project-number>/locations/us-east1/reasoningEngines/<agent-id>"
export AGENT_DIRECTORY="app"
uv run python main.py
```

Open your browser to the local server port (default `8080`) to interact with the full A2A interface.

---

## 📸 Recording Demos

To record an automated Playwright screen recording of the agent in action:

```bash
NODE_PATH=./node_modules node .agents/skills/record-demo/record-agent.js \
  -q "Search my digital pantry and list ingredients" \
  -q "Consult the medical guide for a natural herbal cough remedy" \
  -q "Generate a vibrant dish photo of an authentic Italian pasta recipe" \
  --wait 30000 \
  -o agent_demo.webm
```

---

## 📜 Project Structure

```
smart-recipe-concierge/
├── app/
│   ├── agent.py               # Root ADK agent, tools, callbacks, and sandbox executor
│   ├── a2ui_utils.py          # A2UI response rewrapping callback utilities
│   └── __init__.py
├── frontend/
│   ├── main.py                # FastAPI proxy server using a2a-sdk
│   ├── requirements.txt       # Frontend dependencies
│   └── static/
│       └── index.html         # Custom glassmorphic web UI with A2UI renderer
├── agents-cli-manifest.yaml   # Agents CLI deployment configuration
├── pyproject.toml             # Python package definition and dependencies
├── agent_demo.webm            # Full HD screen recording video
├── demo.gif                   # Looping inline demo animation
└── README.md                  # Project documentation & launch guide
```

---

*Developed for the Google Cloud Gemini World Tour Workshop.*
