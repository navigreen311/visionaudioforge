# Copilot Agent

Agentic Media Copilot powered by Claude API with streaming chat, persistent memory, skill-based personas, and integrated tool use.

## Architecture

```
Frontend (Next.js)          Backend (FastAPI)
--------------------        --------------------------------
AgentsPage                  POST /api/agents/chat (REST)
  CopilotChat  <--WS-->    WS /ws/agents/stream
  SkillPackSwitcher         CopilotService
  MemoryPanel               AgentMemoryService
                            tools.py (6 tools)
                            skill_packs.py (7 personas)
```

### Components

| Layer | File | Purpose |
|-------|------|---------|
| Service | `backend/app/services/agents/copilot.py` | Claude API streaming, system prompt, tool execution |
| Service | `backend/app/services/agents/memory.py` | Store, recall, decay, promote memories |
| Service | `backend/app/services/agents/tools.py` | Tool definitions + mock executors |
| Service | `backend/app/services/agents/skill_packs.py` | 7 persona system prompts |
| API | `backend/app/api/routes/agents.py` | REST endpoints for chat, CRUD, memory |
| WS | `backend/app/ws/copilot.py` | WebSocket streaming handler |
| Frontend | `frontend/src/app/(dashboard)/agents/page.tsx` | Main page layout |
| Frontend | `frontend/src/components/agents/CopilotChat.tsx` | Chat UI with WebSocket streaming |
| Frontend | `frontend/src/components/agents/MessageBubble.tsx` | User/assistant message display |
| Frontend | `frontend/src/components/agents/MemoryPanel.tsx` | Memory list with importance badges |
| Frontend | `frontend/src/components/agents/SkillPackSwitcher.tsx` | Skill pack selector |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/agents/chat` | Non-streaming chat fallback |
| GET | `/api/agents` | List agents |
| POST | `/api/agents` | Create agent |
| GET | `/api/agents/{id}/memory` | List agent memories |
| POST | `/api/agents/{id}/memory/decay` | Trigger memory decay |
| DELETE | `/api/agents/{id}/memory/{mem_id}` | Delete specific memory |
| WS | `/ws/agents/stream` | Streaming chat via WebSocket |

## WebSocket Protocol

**Send:**
```json
{"message": "analyze my latest upload", "agent_id": "...", "skill_pack": "general"}
```

**Receive (sequence):**
```json
{"type": "token", "content": "I'll "}
{"type": "token", "content": "analyze "}
{"type": "tool_use", "tool": "analyze_image", "input": {...}}
{"type": "token", "content": "The image contains..."}
{"type": "done"}
```

## Skill Packs

| Pack | Persona |
|------|---------|
| `general` | General-purpose media assistant |
| `investigator` | Security investigator — evidence, timelines, anomalies |
| `qa_analyst` | QA analyst — quality metrics, defect patterns |
| `compliance` | Compliance officer — policy, audit trails |
| `media_editor` | Media editor — content quality, transformations |
| `operations` | Operations controller — health, alerts, performance |
| `executive` | Executive summarizer — KPIs, trends, strategic insights |

## Memory System

Memories are scored by `importance_score * freshness_score`:
- **importance_score** (0-1): Set at creation, promotable via API
- **freshness_score** (0-1): Starts at 1.0, decays by configurable factor (default 0.95)
- **Expiration**: Low-importance memories (<0.8) expire after 30 days; high-importance memories never expire

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | `""` | Claude API key. If empty, copilot runs in mock mode |

## Running Tests

```bash
cd backend
python -m pytest tests/test_copilot.py -v
```

## Local Demo

1. Set `ANTHROPIC_API_KEY` in `.env` (optional — mock mode works without it)
2. Start services: `docker compose up`
3. Open http://localhost:3000/agents
4. Select a skill pack, type a message, and see streaming responses
