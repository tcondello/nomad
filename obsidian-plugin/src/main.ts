import { Plugin, Editor, MarkdownView, Notice, Menu, MenuItem } from "obsidian";
import {
  NomadPluginSettings,
  DEFAULT_SETTINGS,
  NomadSettingTab,
} from "./settings";
import { NomadClient } from "./api/nomadClient";
import { InlinePromptModal } from "./modals/promptModal";
import { NomadChatView, NOMAD_CHAT_VIEW_TYPE } from "./views/chatView";

export default class NomadPlugin extends Plugin {
  settings: NomadPluginSettings = DEFAULT_SETTINGS;
  private client: NomadClient | null = null;

  async onload() {
    await this.loadSettings();
    this.client = new NomadClient(this.settings);

    // Register Setting Tab
    this.addSettingTab(new NomadSettingTab(this.app, this));

    // Register Chat View
    this.registerView(
      NOMAD_CHAT_VIEW_TYPE,
      (leaf) => new NomadChatView(leaf, this)
    );

    // Register Ribbon Icon
    this.addRibbonIcon("compass", "Nomad Agent Chat", () => {
      this.activateChatView();
    });

    // 1. Format Command
    this.addCommand({
      id: "nomad-format",
      name: "Nomad: Format & Clean Note / Selection",
      editorCallback: (editor: Editor) => {
        this.runInlineAction(editor, "format", "Formatting note...");
      },
    });

    // 2. Polish Command
    this.addCommand({
      id: "nomad-polish",
      name: "Nomad: Polish Tone & Grammar",
      editorCallback: (editor: Editor) => {
        this.runInlineAction(editor, "polish", "Polishing writing...");
      },
    });

    // 3. Expand Command
    this.addCommand({
      id: "nomad-expand",
      name: "Nomad: Expand Bullets / Continue Writing",
      editorCallback: (editor: Editor) => {
        this.runInlineAction(editor, "expand", "Expanding ideas...");
      },
    });

    // 4. Summarize Command
    this.addCommand({
      id: "nomad-summarize",
      name: "Nomad: Summarize Note / Selection",
      editorCallback: (editor: Editor) => {
        this.runInlineAction(editor, "summarize", "Summarizing content...");
      },
    });

    // 5. Ask AI Modal (Custom Prompt)
    this.addCommand({
      id: "nomad-ask-prompt",
      name: "Nomad: Ask AI (Inline Prompt Modal)",
      editorCallback: (editor: Editor) => {
        const selected = editor.getSelection() || editor.getValue();
        new InlinePromptModal(this.app, this, editor, selected).open();
      },
    });

    // 6. Open Chat View Command
    this.addCommand({
      id: "nomad-open-chat",
      name: "Nomad: Open AI Sidebar Chat",
      callback: () => {
        this.activateChatView();
      },
    });

    // Register Context Menu on Editor
    this.registerEvent(
      this.app.workspace.on("editor-menu", (menu: Menu, editor: Editor) => {
        const selection = editor.getSelection();
        if (!selection) return;

        menu.addSeparator();

        menu.addItem((item: MenuItem) => {
          item
            .setTitle("Nomad: Format Selection")
            .setIcon("check-check")
            .onClick(() => {
              this.runInlineAction(editor, "format", "Formatting selection...");
            });
        });

        menu.addItem((item: MenuItem) => {
          item
            .setTitle("Nomad: Polish Tone & Grammar")
            .setIcon("sparkles")
            .onClick(() => {
              this.runInlineAction(editor, "polish", "Polishing selection...");
            });
        });

        menu.addItem((item: MenuItem) => {
          item
            .setTitle("Nomad: Expand Thoughts")
            .setIcon("maximize-2")
            .onClick(() => {
              this.runInlineAction(editor, "expand", "Expanding thoughts...");
            });
        });

        menu.addItem((item: MenuItem) => {
          item
            .setTitle("Nomad: Summarize Selection")
            .setIcon("file-text")
            .onClick(() => {
              this.runInlineAction(editor, "summarize", "Summarizing...");
            });
        });

        menu.addItem((item: MenuItem) => {
          item
            .setTitle("Nomad: Ask AI...")
            .setIcon("compass")
            .onClick(() => {
              new InlinePromptModal(this.app, this, editor, selection).open();
            });
        });
      })
    );
  }

  getClient(): NomadClient {
    if (!this.client) {
      this.client = new NomadClient(this.settings);
    }
    return this.client;
  }

  async runInlineAction(
    editor: Editor,
    action: "format" | "polish" | "expand" | "summarize",
    progressNotice: string
  ) {
    const selection = editor.getSelection();
    const hasSelection = Boolean(selection && selection.trim().length > 0);
    const targetText = hasSelection ? selection : editor.getValue();

    if (!targetText || !targetText.trim()) {
      new Notice("No text to process.");
      return;
    }

    const activeFile = this.app.workspace.getActiveFile();
    const notice = new Notice(`🧭 ${progressNotice}`, 0);

    try {
      const client = this.getClient();
      const response = await client.transformText({
        action,
        text: targetText,
        context_note_path: activeFile ? activeFile.path : undefined,
      });

      notice.hide();

      if (action === "summarize" || action === "expand") {
        if (hasSelection) {
          // Replace selection or append
          editor.replaceSelection(response.result);
        } else {
          // Append to end of note
          const endPos = editor.offsetToPos(editor.getValue().length);
          editor.replaceRange(`\n\n---\n## AI ${action === "summarize" ? "Summary" : "Expansion"}\n${response.result}\n`, endPos);
        }
      } else {
        // Format / Polish: direct replacement
        if (hasSelection) {
          editor.replaceSelection(response.result);
        } else {
          editor.setValue(response.result);
        }
      }

      new Notice(`✅ Nomad: Completed ${action}.`);
    } catch (err: any) {
      notice.hide();
      new Notice(`❌ Nomad Error: ${err.message}`, 8000);
    }
  }

  async activateChatView() {
    const { workspace } = this.app;
    let leaf = workspace.getLeavesOfType(NOMAD_CHAT_VIEW_TYPE)[0];

    if (!leaf) {
      const rightLeaf = workspace.getRightLeaf(false);
      if (rightLeaf) {
        await rightLeaf.setViewState({
          type: NOMAD_CHAT_VIEW_TYPE,
          active: true,
        });
        leaf = rightLeaf;
      }
    }

    if (leaf) {
      workspace.revealLeaf(leaf);
    }
  }

  async loadSettings() {
    this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
  }

  async saveSettings() {
    await this.saveData(this.settings);
    this.client = new NomadClient(this.settings);
  }

  onunload() {
    this.app.workspace.detachLeavesOfType(NOMAD_CHAT_VIEW_TYPE);
  }
}
