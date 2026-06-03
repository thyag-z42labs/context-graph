---
sidebar_position: 4
---

# Framework Comparison

`create-context-graph` supports 8 agent frameworks. Each generates a different `agent.py` implementation with the same tool interface. This guide helps you choose the right one.

:::tip New to Create Context Graph?
Start with **PydanticAI** -- it offers the best combination of type safety, full streaming, and documentation. If you prefer working directly with the Anthropic API, **Claude Agent SDK** is the lightest-weight option.
:::

## Comparison Table

| Framework | LLM Provider | Streaming | Async | Performance Notes |
|---|---|---|---|---|
| **PydanticAI** | OpenRouter first; Anthropic fallback | Full (text + tools) | Native async | Fast startup, type-safe tool definitions. Low overhead. |
| **Claude Agent SDK** | OpenRouter first; Anthropic fallback | Full (text + tools) | Native async | Direct Anthropic loop retained as fallback. |
| **OpenAI Agents SDK** | OpenRouter first; OpenAI fallback | Full (text + tools) | Native async | Uses OpenAI-compatible chat completions for OpenRouter. |
| **LangGraph** | OpenRouter first; Anthropic fallback | Full (text + tools) | Native async | Slightly higher startup (graph compilation). Rich observability hooks. |
| **Anthropic Tools** | OpenRouter first; Anthropic fallback | Full (text + tools) | Native async | Direct OpenRouter tool loop with Anthropic SDK fallback. |
| **Strands** | OpenRouter first; Anthropic fallback | Full (text + tools) | Thread-bridged | Sync framework in worker thread; text streams via `agent.stream_async()`. |
| **CrewAI** | OpenRouter first; Anthropic fallback | Full (text + tools) | Thread-bridged | Higher startup (multi-agent init); text streams via `LLMStreamChunkEvent`. |
| **Google ADK** | Google Gemini | Full (text + tools) | Native async | Requires `GOOGLE_API_KEY`. Uses `nest_asyncio` for reentrant async. |

## Choosing a Framework

### Best for most users: **PydanticAI** or **Claude Agent SDK**

Both offer full streaming, excellent tool execution, and native async support. PydanticAI adds type-safe tool definitions with `RunContext`; Claude Agent SDK provides the most direct Anthropic integration.

### Best for OpenAI users: **OpenAI Agents SDK**

If you're already using OpenAI's API and models, this framework integrates naturally. Note that broad semantic queries (e.g., "who are the top players?") may return empty results because the text-matching tools require specific search terms.

### Best for LangChain ecosystem: **LangGraph**

If you're building within the LangChain ecosystem and want access to LangChain's tool ecosystem, agent memory, and observability integrations.

### Best for multi-agent workflows: **CrewAI**

CrewAI's agent/task/crew paradigm is designed for multi-agent collaboration. The generated template uses a single agent, but you can extend it to multi-agent crews for complex workflows.

### Best for modular agentic loops: **Anthropic Tools**

A lightweight, no-framework approach that uses the Anthropic API directly with a custom `@register_tool` registry and bounded agentic loop. Good for understanding how agentic loops work under the hood.

### Best for Google Cloud: **Google ADK**

Uses Google's Gemini models via the Agent Development Kit. Requires a separate Google API key (`GOOGLE_API_KEY`). Best if you're building within the Google Cloud ecosystem.

## Streaming Behavior

**Full streaming (all 8 frameworks):** text tokens stream to the frontend as they're generated, and tool calls appear in real-time in the tool call timeline. CrewAI and Strands run synchronously in a worker thread; their text streams via framework-specific hooks (`LLMStreamChunkEvent` and `agent.stream_async()` respectively) and tool events stream via the thread-safe `CypherResultCollector`. The other six frameworks stream via native async APIs.

## Thread Safety

Most frameworks use native `async/await`. CrewAI and Strands are synchronous and run in worker threads via `asyncio.to_thread()`. Their tools use `asyncio.run_coroutine_threadsafe()` to bridge back to the async event loop for Neo4j queries. This is handled automatically in the generated code.

## Framework-Specific Dependencies

| Framework | Key Dependencies |
|---|---|
| PydanticAI | `pydantic-ai>=0.1` |
| Claude Agent SDK | `claude-agent-sdk>=0.1`, `anthropic>=0.30` |
| OpenAI Agents SDK | `openai-agents>=0.1` |
| LangGraph | `langgraph>=0.1`, `langchain-anthropic>=0.3`, `langchain-openrouter>=0.2`, `langchain-openai>=0.3` |
| CrewAI | `crewai[anthropic,litellm]>=0.1` |
| Strands | `strands-agents[anthropic,openai]>=0.1` |
| Google ADK | `google-adk>=0.1`, `nest-asyncio>=1.5` |
| Anthropic Tools | `anthropic>=0.30` |
