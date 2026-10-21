import { App, Modal, Editor, Notice } from "obsidian";
import type NomadPlugin from "../main";

export class InlinePromptModal extends Modal {
  private plugin: NomadPlugin;
  private editor: Editor;
  private selectedText: string;
  private instructionInput: HTMLTextAreaElement | null = null;

  constructor(app: App, plugin: NomadPlugin, editor: Editor, selectedText: string) {
    super(app);
    this.plugin = plugin;
    this.editor = editor;
    this.selectedText = selectedText;
  }

  onOpen() {
    const { contentEl } = this;
    contentEl.empty();
    contentEl.addClass("nomad-modal");

    contentEl.createEl("h3", { text: "Ask Nomad AI (Inline Action)" });

    // Show excerpt of target text
    const previewContainer = contentEl.createDiv({ cls: "nomad-preview-container" });
    previewContainer.createEl("div", {
      text: `Target text (${this.selectedText.length} chars):`,
      cls: "nomad-preview-label",
    });
    const previewText = previewContainer.createEl("div", { cls: "nomad-preview-snippet" });
    previewText.setText(
      this.selectedText.length > 250
        ? this.selectedText.slice(0, 250) + "..."
        : this.selectedText
    );

    // Prompt input
    const inputContainer = contentEl.createDiv({ cls: "nomad-input-container" });
    inputContainer.createEl("label", { text: "Instruction for AI:" });
    this.instructionInput = inputContainer.createEl("textarea", {
      cls: "nomad-instruction-textarea",
      placeholder: "e.g., Turn into a 3-column table, Extract checklist of action items, Rephrase concisely...",
    });
    this.instructionInput.rows = 3;

    // Quick suggestion chips
    const chipsContainer = contentEl.createDiv({ cls: "nomad-chips-container" });
    const suggestions = [
      "Convert to Markdown table",
      "Extract action checklist",
      "Add Pros & Cons callouts",
      "Reorganize into clear sections",
      "Turn into Q&A FAQ format",
    ];

    suggestions.forEach((sugg) => {
      const chip = chipsContainer.createEl("button", {
        text: sugg,
        cls: "nomad-chip",
      });
      chip.onclick = () => {
        if (this.instructionInput) {
          this.instructionInput.value = sugg;
          this.instructionInput.focus();
        }
      };
    });

    // Action buttons
    const btnContainer = contentEl.createDiv({ cls: "nomad-modal-buttons" });

    const replaceBtn = btnContainer.createEl("button", {
      text: "Replace Selection",
      cls: "mod-cta",
    });
    replaceBtn.onclick = async () => {
      await this.executePrompt("replace", replaceBtn);
    };

    const insertBelowBtn = btnContainer.createEl("button", {
      text: "Insert Below",
      cls: "nomad-secondary-btn",
    });
    insertBelowBtn.onclick = async () => {
      await this.executePrompt("insert", insertBelowBtn);
    };

    const cancelBtn = btnContainer.createEl("button", {
      text: "Cancel",
    });
    cancelBtn.onclick = () => this.close();

    // Auto-focus input
    setTimeout(() => this.instructionInput?.focus(), 50);
  }

  private async executePrompt(mode: "replace" | "insert", triggerBtn: HTMLButtonElement) {
    const instruction = this.instructionInput?.value.trim();
    if (!instruction) {
      new Notice("Please enter an instruction.");
      return;
    }

    triggerBtn.setDisabled(true);
    triggerBtn.setText("Working...");
    const notice = new Notice("Nomad AI is thinking...", 0);

    try {
      const activeFile = this.app.workspace.getActiveFile();
      const client = this.plugin.getClient();
      const response = await client.transformText({
        action: "custom",
        text: this.selectedText,
        instruction: instruction,
        context_note_path: activeFile ? activeFile.path : undefined,
      });

      notice.hide();

      if (mode === "replace") {
        this.editor.replaceSelection(response.result);
        new Notice("Selection replaced by Nomad AI.");
      } else {
        const cursor = this.editor.getCursor("to");
        this.editor.replaceRange(`\n\n${response.result}\n`, cursor);
        new Notice("Inserted below selection.");
      }
      this.close();
    } catch (err: any) {
      notice.hide();
      triggerBtn.setDisabled(false);
      triggerBtn.setText(mode === "replace" ? "Replace Selection" : "Insert Below");
      new Notice(`Nomad Error: ${err.message}`, 8000);
    }
  }

  onClose() {
    const { contentEl } = this;
    contentEl.empty();
  }
}
