import { App, PluginSettingTab, Setting, Notice } from "obsidian";
import type NomadPlugin from "./main";
import { NomadClient } from "./api/nomadClient";

export interface NomadPluginSettings {
  serverUrl: string;
  apiKey: string;
  model: string;
  tone: string;
  autoAttachActiveNote: boolean;
}

export const DEFAULT_SETTINGS: NomadPluginSettings = {
  serverUrl: "http://127.0.0.1:8765",
  apiKey: "",
  model: "accounts/fireworks/models/llama-v3p3-70b-instruct",
  tone: "Professional",
  autoAttachActiveNote: true,
};

export class NomadSettingTab extends PluginSettingTab {
  plugin: NomadPlugin;

  constructor(app: App, plugin: NomadPlugin) {
    super(app, plugin);
    this.plugin = plugin;
  }

  display(): void {
    const { containerEl } = this;
    containerEl.empty();

    containerEl.createEl("h2", { text: "Nomad: Obsidian Agentic Harness Settings" });

    // Server URL
    new Setting(containerEl)
      .setName("Nomad Server URL")
      .setDesc("The local or remote address of the Nomad Python backend server.")
      .addText((text) =>
        text
          .setPlaceholder("http://127.0.0.1:8765")
          .setValue(this.plugin.settings.serverUrl)
          .onChange(async (value) => {
            this.plugin.settings.serverUrl = value.trim();
            await this.plugin.saveSettings();
          })
      );

    // Test Connection Button
    new Setting(containerEl)
      .setName("Connection Status")
      .setDesc("Check if the Nomad backend server is running and configured.")
      .addButton((btn) =>
        btn.setButtonText("Test Connection").setCta().onClick(async () => {
          btn.setDisabled(true);
          btn.setButtonText("Testing...");
          const client = new NomadClient(this.plugin.settings);
          const health = await client.checkHealth();
          btn.setDisabled(false);
          btn.setButtonText("Test Connection");

          if (health.ok) {
            const keyInfo = health.data.fireworks_configured ? "Fireworks: Configured" : "Fireworks: Missing Key!";
            const vaultInfo = health.data.vault_configured ? `Vault: ${health.data.vault_path}` : "Vault: Not set in server";
            new Notice(` Nomad Connected!\n• ${keyInfo}\n• Model: ${health.data.default_model}\n• ${vaultInfo}`, 6000);
          } else {
            new Notice(` Nomad Server Unreachable at ${this.plugin.settings.serverUrl}.\nMake sure you ran 'nomad start'.`, 6000);
          }
        })
      );

    // Fireworks API Key
    new Setting(containerEl)
      .setName("Fireworks API Key (Optional Override)")
      .setDesc("If set, overrides the FIREWORKS_API_KEY environment variable on the server.")
      .addText((text) => {
        text
          .setPlaceholder("fw_...")
          .setValue(this.plugin.settings.apiKey)
          .onChange(async (value) => {
            this.plugin.settings.apiKey = value.trim();
            await this.plugin.saveSettings();
          });
        text.inputEl.type = "password";
      });

    // Fireworks Model
    new Setting(containerEl)
      .setName("Fireworks LLM Model")
      .setDesc("Model for inline writing, formatting, and DeepAgent execution.")
      .addDropdown((dropdown) => {
        dropdown
          .addOption(
            "accounts/fireworks/models/llama-v3p3-70b-instruct",
            "Llama 3.3 70B Instruct (Recommended Default)"
          )
          .addOption(
            "accounts/fireworks/models/deepseek-r1",
            "DeepSeek R1 (Deep Reasoning & Thought)"
          )
          .addOption(
            "accounts/fireworks/models/qwen2p5-72b-instruct",
            "Qwen 2.5 72B Instruct (High Precision)"
          )
          .addOption(
            "accounts/fireworks/models/llama-v3p1-8b-instruct",
            "Llama 3.1 8B Instruct (Fast & Lightweight)"
          )
          .setValue(this.plugin.settings.model)
          .onChange(async (value) => {
            this.plugin.settings.model = value;
            await this.plugin.saveSettings();
          });
      });

    // Default Writing Tone
    new Setting(containerEl)
      .setName("Writing Tone")
      .setDesc("Preferred tone for inline polishing, rewriting, and expansions.")
      .addDropdown((dropdown) => {
        dropdown
          .addOption("Professional", "Professional")
          .addOption("Concise", "Concise (Direct, minimal filler)")
          .addOption("Academic", "Academic (Formal, rigorous)")
          .addOption("Casual", "Casual (Conversational, approachable)")
          .addOption("Technical", "Technical (Precise, developer-focused)")
          .setValue(this.plugin.settings.tone)
          .onChange(async (value) => {
            this.plugin.settings.tone = value;
            await this.plugin.saveSettings();
          });
      });

    // Auto-attach active note to chat
    new Setting(containerEl)
      .setName("Auto-Attach Active Note Context")
      .setDesc("Automatically provide the active note's content to the sidebar chat assistant.")
      .addToggle((toggle) =>
        toggle
          .setValue(this.plugin.settings.autoAttachActiveNote)
          .onChange(async (value) => {
            this.plugin.settings.autoAttachActiveNote = value;
            await this.plugin.saveSettings();
          })
      );
  }
}
