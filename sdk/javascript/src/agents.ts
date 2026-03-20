import type {
  ChatMessage,
  ChatResponse,
  AgentInfo,
  AgentCreateRequest,
  MemoryEntry,
  RequestOptions,
} from './types';

type RequestFn = (
  method: string,
  path: string,
  options?: { body?: unknown; formData?: FormData; options?: RequestOptions },
) => Promise<unknown>;

/**
 * Client for AI copilot / agent endpoints.
 */
export class AgentClient {
  constructor(private readonly _request: RequestFn) {}

  /** Send a message to the AI copilot. */
  async chat(message: ChatMessage, options?: RequestOptions): Promise<ChatResponse> {
    return this._request('POST', '/api/agents/chat', { body: message, options }) as Promise<ChatResponse>;
  }

  /** List all agents. */
  async listAgents(options?: RequestOptions): Promise<AgentInfo[]> {
    return this._request('GET', '/api/agents', { options }) as Promise<AgentInfo[]>;
  }

  /** Create a new agent. */
  async create(request: AgentCreateRequest, options?: RequestOptions): Promise<AgentInfo> {
    return this._request('POST', '/api/agents', { body: request, options }) as Promise<AgentInfo>;
  }

  /** Get agent memory entries. */
  async getMemory(agentId: string, options?: RequestOptions): Promise<MemoryEntry[]> {
    return this._request('GET', `/api/agents/${agentId}/memory`, { options }) as Promise<MemoryEntry[]>;
  }

  /** Trigger memory decay for an agent. */
  async decayMemory(agentId: string, options?: RequestOptions): Promise<{ decayed: number }> {
    return this._request('POST', `/api/agents/${agentId}/memory/decay`, { options }) as Promise<{ decayed: number }>;
  }

  /** Delete a specific memory entry. */
  async deleteMemory(agentId: string, memoryId: string, options?: RequestOptions): Promise<void> {
    await this._request('DELETE', `/api/agents/${agentId}/memory/${memoryId}`, { options });
  }
}
