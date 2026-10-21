import { ItemView, WorkspaceLeaf, MarkdownRenderer, Notice } from "obsidian";
import type NomadPlugin from "../main";
import type { ChatStreamEvent } from "../api/nomadClient";

export const NOMAD_CHAT_VIEW_TYPE = "nomad-chat-view";

interface Message {
  role: "user" | "assistant";
  content: string;
  tools?: string[];
}

export class NomadChatView extends ItemView {
  private plugin: NomadPlugin;
  private messages: Message[] = [];
  private threadId: string = "thread_" + Date.now();
  private messagesContainer: HTMLElement | null = null;
  private inputEl: HTMLTextAreaElement | null = null;
  private attachNoteCheckbox: HTMLInputElement | null = null;
  private sendBtn: HTMLButtonElement | null = null;
  private isGenerating: boolean = false;

  constructor(leaf: WorkspaceLeaf, plugin: NomadPlugin) {
    super(leaf);
    this.plugin = plugin;
  }

  getViewType(): string {
    return NOMAD_CHAT_VIEW_TYPE;
  }

  getDisplayText(): string {
    return "Nomad Agent Chat";
  }

  getIcon(): string {
    return "compass";
  }

  async onOpen() {
    const container = this.containerEl.children[1] as HTMLElement;
    container.empty();
    container.addClass("nomad-chat-view");

    // Header bar
    const header = container.createDiv({ cls: "nomad-chat-header" });
    const titleSection = header.createDiv({ cls: "nomad-header-title-section" });
    titleSection.createEl("span", { text: "🧭 Nomad Agent", cls: "nomad-title" });
    const statusDot = titleSection.createEl("span", { cls: "nomad-status-dot online" });

    const headerActions = header.createDiv({ cls: "nomad-header-actions" });
    const newChatBtn = headerActions.createEl("button", {
      text: "New Chat",
      cls: "nomad-icon-btn",
    });
    newChatBtn.onclick = () => {
      this.messages = [];
      this.threadId = "thread_" + Date.now();
      this.renderMessages();
      new Notice("Started new chat session.");
    };

    // Messages container
    this.messagesContainer = container.createDiv({ cls: "nomad-messages-container" });

    // Active Note Attachment Bar
    const contextBar = container.createDiv({ cls: "nomad-context-bar" });
    const label = contextBar.createEl("label", { cls: "nomad-context-label" });
    this.attachNoteCheckbox = label.createEl("input", { type: "checkbox" });
    this.attachNoteCheckbox.checked = this.plugin.settings.autoAttachActiveNote;
    label.createSpan({ text: " Include active note context" });

    // Input area
    const inputArea = container.createDiv({ cls: "nomad-input-area" });
    this.inputEl = inputArea.createEl("textarea", {
      cls: "nomad-chat-input",
      placeholder: "Ask about your notes, research a topic, or request formatting...",
    });
    this.inputEl.rows = 2;

    this.inputEl.addEventListener("keydown", (e: KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        this.handleSend();
      }
    });

    const controls = inputArea.createDiv({ cls: "nomad-input-controls" });
    this.sendBtn = controls.createEl("button", {
      text: "Send",
      cls: "mod-cta nomad-send-btn",
    });
    this.sendBtn.onclick = () => this.handleSend();

    this.renderMessages();
  }

  private renderMessages() {
    if (!this.messagesContainer) return;
    this.messagesContainer.empty();

    if (this.messages.length === 0) {
      const welcome = this.messagesContainer.createDiv({ cls: "nomad-welcome-box" });
      welcome.createEl("h4", { text: "Welcome to Nomad" });
      welcome.createEl("p", {
        text: "Your agentic writing, research, and formatting assistant powered by LangChain DeepAgents and Fireworks AI.",
      });

      const suggestions = [
        "Outline a new note about Agent Architectures",
        "Summarize my active note into 3 key takeaways",
        "Find existing notes in vault related to 'Design'",
      ];

      const suggBox = welcome.createDiv({ cls: "nomad-welcome-suggestions" });
      suggestions.forEach((text) => {
        const item = suggBox.createEl("button", { text, cls: "nomad-suggestion-chip" });
        item.onclick = () => {
          if (this.inputEl) {
            this.inputEl.value = text;
            this.handleSend();
          }
        };
      });
      return;
    }

    for (const msg of this.messages) {
      this.renderMessageBubble(msg);
    }

    this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
  }

  private renderMessageBubble(msg: Message) {
    if (!this.messagesContainer) return;

    const row = this.messagesContainer.createDiv({
      cls: `nomad-message-row ${msg.role}`,
    });

    const bubble = row.createDiv({ cls: `nomad-bubble ${msg.role}` });

    if (msg.role === "assistant" && msg.tools && msg.tools.length > 0) {
      const toolsBox = bubble.createDiv({ cls: "nomad-tool-calls" });
      for (const t of msg.tools) {
        toolsBox.createDiv({ text: `🔧 ${t}`, cls: "nomad-tool-badge" });
      }
    }

    const textContainer = bubble.createDiv({ cls: "nomad-message-text" });
    MarkdownRenderer.render(
      this.app,
      msg.content,
      textContainer,
      "",
      this
    );

    if (msg.role === "assistant" && msg.content) {
      const actionsBar = bubble.createDiv({ cls: "nomad-bubble-actions" });

      const insertBtn = actionsBar.createEl("button", {
        text: "Insert to Note",
        cls: "nomad-mini-btn",
      });
      insertBtn.onclick = () => {
        const view = this.app.workspace.getActiveViewOfType(ItemView);
        const editor = (this.app.workspace as any).activeEditor?.editor;
        if (editor) {
          const cursor = editor.getCursor();
          editor.replaceRange(`\n\n${msg.content}\n`, cursor);
          new Notice("Inserted into note.");
        } else {
          new Notice("No active markdown editor found.");
        }
      };

      const copyBtn = actionsBar.createEl("button", {
        text: "Copy",
        cls: "nomad-mini-btn",
      });
      copyBtn.onclick = () => {
        navigator.clipboard.writeText(msg.content);
        new Notice("Copied to clipboard.");
      };
    }
  }

  private async handleSend() {
    if (this.isGenerating || !this.inputEl) return;
    const text = this.inputEl.value.trim();
    if (!text) return;

    this.inputEl.value = "";
    this.isGenerating = true;
    if (this.sendBtn) {
      this.sendBtn.setDisabled(true);
      this.sendBtn.setText("...");
    }

    // Add user message
    this.messages.push({ role: "user", content: text });

    // Prepare assistant message
    const assistantMsg: Message = { role: "assistant", content: "", tools: [] };
    this.messages.push(assistantMsg);
    this.renderMessages();

    // Check active note
    let activeTitle: string | undefined;
    let activeContent: string | undefined;
    let activePath: string | undefined;

    if (this.attachNoteCheckbox?.checked) {
      const activeFile = this.app.workspace.getActiveFile();
      if (activeFile) {
        activeTitle = activeFile.basename;
        activePath = activeFile.path;
        try {
          activeContent = await this.app.vault.read(activeFile);
        } catch (_) {}
      }
    }

    const client = this.plugin.getClient();

    try {
      await client.streamChat(
        {
          message: text,
          thread_id: this.threadId,
          active_note_title: activeTitle,
          active_note_content: activeContent,
          active_note_path: activePath,
        },
        (event: ChatStreamEvent) => {
          if (event.type === "token" && event.content) {
            assistantMsg.content += event.content;
            this.updateLastMessage(assistantMsg);
          } else if (event.type === "tool_start" && event.tool) {
            if (!assistantMsg.tools) assistantMsg.tools = [];
            assistantMsg.tools.push(`Calling: ${event.tool}`);
            this.updateLastMessage(assistantMsg);
          } else if (event.type === "error") {
            assistantMsg.content += `\n\n**Error:** ${event.error}`;
            this.updateLastMessage(assistantMsg);
          }
        }
      );
    } catch (err: any) {
      assistantMsg.content = `**Error:** ${err.message || "Failed to contact Nomad server."}`;
      this.updateLastMessage(assistantMsg);
    } finally {
      this.isGenerating = false;
      if (this.sendBtn) {
        this.sendBtn.setDisabled(false);
        this.sendBtn.setText("Send");
      }
      this.renderMessages();
    }
  }

  private updateLastMessage(msg: Message) {
    if (!this.messagesContainer) return;
    const bubbles = this.messagesContainer.querySelectorAll(".nomad-message-row.assistant");
    const lastRow = bubbles[bubbles.length - 1];
    if (lastRow) {
      const textContainer = lastRow.querySelector(".nomad-message-text") as HTMLElement;
      if (textContainer) {
        textContainer.empty();
        MarkdownRenderer.render(this.app, msg.content, textContainer, "", this);
      }
    }
    this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
  }

  async onClose() {
    // cleanup
  }
}
