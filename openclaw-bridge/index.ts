import { definePluginEntry } from "openclaw/plugin-sdk/plugin-entry";

const DEFAULT_URL = "http://127.0.0.1:8787";
const OPENCLAW_COMMANDS = new Set(["new", "reset", "stop", "help", "status"]);

type PluginConfig = {
  jarvisUrl?: string;
  channels?: string[];
};

function resolveConfig(raw: unknown): { jarvisUrl: string; channels: Set<string> | null } {
  const cfg = (raw && typeof raw === "object" ? raw : {}) as PluginConfig;
  const jarvisUrl = (cfg.jarvisUrl ?? process.env.JARVIS_CORE_URL ?? DEFAULT_URL).replace(/\/$/, "");
  const channels = Array.isArray(cfg.channels) && cfg.channels.length > 0
    ? new Set(cfg.channels.map((c) => c.toLowerCase()))
    : null;
  return { jarvisUrl, channels };
}

function isSlashCommand(text: string): boolean {
  const trimmed = text.trim();
  if (!trimmed.startsWith("/")) return false;
  const cmd = trimmed.slice(1).split(/\s+/)[0]?.toLowerCase() ?? "";
  return OPENCLAW_COMMANDS.has(cmd);
}

export default definePluginEntry({
  id: "jarvis-bridge",
  name: "Jarvis Bridge",
  description: "Forward inbound messages to JarvisCore (William Agent)",
  register(api) {
    const resolveState = () => resolveConfig(api.pluginConfig);

    api.on(
      "inbound_claim",
      async (event, ctx) => {
        const { jarvisUrl, channels } = resolveState();
        const channel = (ctx.channelId ?? event.channel ?? "").toLowerCase();
        if (channels && !channels.has(channel)) return;

        const text = (event.bodyForAgent ?? event.content ?? "").trim();
        if (!text || isSlashCommand(text)) return;

        const source = channel ? `${channel}:${event.senderId ?? "unknown"}` : "openclaw";

        try {
          const resp = await fetch(`${jarvisUrl}/api/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: text, source }),
            signal: AbortSignal.timeout(120_000),
          });
          if (!resp.ok) {
            api.logger.warn?.(`jarvis-bridge: JarvisCore returned ${resp.status}`);
            return {
              handled: true,
              reply: { text: `JarvisCore error (${resp.status}). Check http://127.0.0.1:8787` },
            };
          }
          const data = (await resp.json()) as { reply?: string; error?: string };
          return {
            handled: true,
            reply: { text: data.reply ?? data.error ?? "No response from William Agent." },
          };
        } catch (err) {
          api.logger.warn?.(`jarvis-bridge: ${String(err)}`);
          return {
            handled: true,
            reply: { text: "William Agent is offline. Is JarvisCore running on port 8787?" },
          };
        }
      },
      { priority: 200 },
    );
  },
});
