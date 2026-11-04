export type Source = {
  text: string;
  page: number | null;
  filing: string;
  citation: string;
};

export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  latency_ms?: number;
  cost?: number;
};

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function askStream(
  query: string,
  ticker: string,
  onToken: (token: string) => void,
  onDone: (meta: {
    sources: Source[];
    latency_ms: number;
    cost: number;
  }) => void
): Promise<void> {
  const res = await fetch(
    `${API}/ask/stream?query=${encodeURIComponent(query)}&ticker=${ticker}`
  );
  if (!res.ok || !res.body) throw new Error("Stream request failed");
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() || "";
    for (const part of parts) {
      const line = part.trim();
      if (!line.startsWith("data:")) continue;
      const payload = JSON.parse(line.slice(5).trim());
      if (payload.token) onToken(payload.token);
      if (payload.sources) onDone(payload);
    }
  }
}

export async function generateMemo(
  ticker: string,
  query: string
): Promise<Blob> {
  const res = await fetch(`${API}/memo`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ticker, query }),
  });
  if (!res.ok) throw new Error("Memo request failed");
  return res.blob();
}

export async function getEval(): Promise<unknown> {
  const res = await fetch(`${API}/eval`);
  return res.json();
}
