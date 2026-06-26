export async function checkN8n(baseUrl: string, apiKey: string): Promise<{ ok: boolean; workflowCount?: number; error?: string }> {
  try {
    const url = `${baseUrl.replace(/\/$/, "")}/api/v1/workflows?limit=1`;
    const res = await fetch(url, { headers: { "X-N8N-API-KEY": apiKey } });
    if (!res.ok) return { ok: false, error: `HTTP ${res.status}` };
    const data = (await res.json()) as { data?: unknown[] };
    return { ok: true, workflowCount: data.data?.length ?? 0 };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : "unknown" };
  }
}
