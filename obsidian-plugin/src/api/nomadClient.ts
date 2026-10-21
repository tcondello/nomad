import { requestUrl } from "obsidian";
import type { NomadPluginSettings } from "../settings";

export interface InlineTransformRequest {
  action: "format" | "polish" | "expand" | "summarize" | "custom";
  text: string;
  instruction?: string;
  context_note_path?: string;
  context_before?: string;
  context_after?: string;
  tone?: string;
  model?: string;
  api_key?: string;
}

export interface InlineTransformResponse {
  result: string;
  action: string;
  model_used: string;
}

export interface ChatStreamEvent {
  type: "token" | "tool_start" | "tool_end" | "error" | "done";
  content?: string;
  tool?: string;
  input?: any;
  output?: string;
  error?: string;
}

export class NomadClient {
  private settings: NomadPluginSettings;

  constructor(settings: NomadPluginSettings) {
    this.settings = settings;
  }

  private getBaseUrl(): string {
    return this.settings.serverUrl.replace(/\/+$/, "");
  }

  private getHeaders(): Record<string, string> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };
    if (this.settings.apiKey) {
      headers["X-Fireworks-Api-Key"] = this.settings.apiKey;
    }
    return headers;
  }

  async checkHealth(): Promise<{ ok: boolean; data?: any; error?: string }> {
    try {
      const res = await requestUrl({
        url: `${this.getBaseUrl()}/v1/health`,
        method: "GET",
      });
      if (res.status === 200) {
        return { ok: true, data: res.json };
      }
      return { ok: false, error: `Status ${res.status}` };
    } catch (e: any) {
      return { ok: false, error: e?.message || "Failed to reach server" };
    }
  }

  async transformText(req: InlineTransformRequest): Promise<InlineTransformResponse> {
    if (!req.model && this.settings.model) {
      req.model = this.settings.model;
    }
    if (!req.tone && this.settings.tone) {
      req.tone = this.settings.tone;
    }
    if (!req.api_key && this.settings.apiKey) {
      req.api_key = this.settings.apiKey;
    }

    try {
      const res = await requestUrl({
        url: `${this.getBaseUrl()}/v1/inline/transform`,
        method: "POST",
        headers: this.getHeaders(),
        body: JSON.stringify(req),
      });

      if (res.status !== 200) {
        const errorDetail = res.json?.detail || `Error code ${res.status}`;
        throw new Error(errorDetail);
      }
      return res.json as InlineTransformResponse;
    } catch (err: any) {
      throw new Error(err?.message || "Transform request failed");
    }
  }

  async runAgentTask(prompt: string, threadId: string = "default"): Promise<{ response: string; thread_id: string }> {
    try {
      const res = await requestUrl({
        url: `${this.getBaseUrl()}/v1/agent/run`,
        method: "POST",
        headers: this.getHeaders(),
        body: JSON.stringify({
          prompt,
          thread_id: threadId,
          model: this.settings.model,
          api_key: this.settings.apiKey || undefined,
        }),
      });

      if (res.status !== 200) {
        throw new Error(res.json?.detail || `Error code ${res.status}`);
      }
      return res.json;
    } catch (err: any) {
      throw new Error(err?.message || "Agent task failed");
    }
  }

  async streamChat(
    payload: {
      message: string;
      thread_id?: string;
      active_note_title?: string;
      active_note_content?: string;
      active_note_path?: string;
    },
    onEvent: (event: ChatStreamEvent) => void
  ): Promise<void> {
    const url = `${this.getBaseUrl()}/v1/chat`;
    const body = {
      message: payload.message,
      thread_id: payload.thread_id || "default",
      active_note_title: payload.active_note_title,
      active_note_content: payload.active_note_content,
      active_note_path: payload.active_note_path,
      model: this.settings.model,
      api_key: this.settings.apiKey || undefined,
      stream: true,
    };

    const response = await fetch(url, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      let errMsg = `Server error ${response.status}`;
      try {
        const errJson = await response.json();
        if (errJson?.detail) errMsg = errJson.detail;
      } catch (_) {}
      throw new Error(errMsg);
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error("No readable stream in response");
    }

    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed || !trimmed.startsWith("data:")) continue;

        const dataStr = trimmed.slice(5).trim();
        if (dataStr === "[DONE]") {
          onEvent({ type: "done" });
          return;
        }

        try {
          const parsed = JSON.parse(dataStr);
          onEvent(parsed);
        } catch (_) {
          // Ignore parse errors on incomplete chunk
        }
      }
    }
    onEvent({ type: "done" });
  }
}
