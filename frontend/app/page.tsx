"use client";

import { useState } from "react";
import {
  askStream,
  generateMemo,
  type ChatMessage,
  type Source,
} from "../lib/api";

const TICKERS = ["AAPL", "MSFT", "NVDA"];

export default function Home() {
  const [ticker, setTicker] = useState("AAPL");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [activeSources, setActiveSources] = useState<Source[]>([]);

  async function send() {
    const question = input.trim();
    if (!question || loading) return;
    setInput("");
    setLoading(true);
    setMessages((m) => [...m, { role: "user", content: question }]);
    let answer = "";
    setMessages((m) => [...m, { role: "assistant", content: "" }]);
    try {
      await askStream(
        question,
        ticker,
        (token) => {
          answer += token;
          setMessages((m) => {
            const copy = [...m];
            copy[copy.length - 1] = { role: "assistant", content: answer };
            return copy;
          });
        },
        (meta) => {
          setActiveSources(meta.sources);
          setMessages((m) => {
            const copy = [...m];
            copy[copy.length - 1] = {
              role: "assistant",
              content: answer,
              sources: meta.sources,
              latency_ms: meta.latency_ms,
              cost: meta.cost,
            };
            return copy;
          });
        }
      );
    } catch {
      setMessages((m) => {
        const copy = [...m];
        copy[copy.length - 1] = {
          role: "assistant",
          content: "Something went wrong talking to the API. Is it running?",
        };
        return copy;
      });
    } finally {
      setLoading(false);
    }
  }

  async function downloadMemo() {
    const lastUser = [...messages].reverse().find((m) => m.role === "user");
    const blob = await generateMemo(
      ticker,
      lastUser?.content || "Summarize this company's latest 10-K."
    );
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${ticker}-memo.pdf`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="flex h-screen">
      {/* Left: ticker selector */}
      <aside className="w-48 border-r p-4">
        <h1 className="font-bold text-lg mb-4">FinStack AI</h1>
        <p className="text-xs text-gray-500 mb-2">Ticker</p>
        {TICKERS.map((t) => (
          <button
            key={t}
            onClick={() => setTicker(t)}
            className={`block w-full text-left px-3 py-2 rounded mb-1 ${
              ticker === t ? "bg-blue-600 text-white" : "bg-gray-100"
            }`}
          >
            {t}
          </button>
        ))}
        <button
          onClick={downloadMemo}
          className="mt-6 w-full bg-green-600 text-white px-3 py-2 rounded"
        >
          Generate Investment Memo
        </button>
        <p className="text-xs text-gray-500 mt-4">
          Factual summaries from SEC filings. Not financial advice.
        </p>
      </aside>

      {/* Middle: chat */}
      <main className="flex-1 flex flex-col p-4">
        <div className="flex-1 overflow-y-auto space-y-4">
          {messages.map((m, i) => (
            <div
              key={i}
              onClick={() => m.sources && setActiveSources(m.sources)}
              className={`p-3 rounded max-w-2xl cursor-pointer ${
                m.role === "user"
                  ? "bg-blue-100 ml-auto"
                  : "bg-gray-100"
              }`}
            >
              <p className="whitespace-pre-wrap">{m.content}</p>
              {m.sources && (
                <p className="text-xs text-gray-500 mt-2">
                  {m.sources.map((s) => s.citation).join(" ")}
                  {m.latency_ms !== undefined &&
                    ` · ${m.latency_ms} ms · est. cost $${m.cost?.toFixed(6)}`}
                </p>
              )}
            </div>
          ))}
        </div>
        <div className="flex gap-2 mt-4">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && send()}
            placeholder={`Ask about ${ticker}…`}
            className="flex-1 border rounded px-3 py-2"
          />
          <button
            onClick={send}
            disabled={loading}
            className="bg-blue-600 text-white px-4 py-2 rounded disabled:opacity-50"
          >
            Send
          </button>
        </div>
      </main>

      {/* Right: source preview */}
      <aside className="w-80 border-l p-4 overflow-y-auto">
        <h2 className="font-bold mb-2">Sources</h2>
        <p className="text-xs text-gray-500 mb-4">
          In production these previews come from S3 raw filings; in demo
          mode they are the indexed excerpts.
        </p>
        {activeSources.length === 0 && (
          <p className="text-sm text-gray-500">
            Click an assistant message to inspect its sources.
          </p>
        )}
        {activeSources.map((s, i) => (
          <div key={i} className="mb-4 border rounded p-3">
            <p className="font-mono text-xs mb-1">{s.citation}</p>
            <p className="text-sm">{s.text}</p>
            <p className="text-xs text-gray-500 mt-1">{s.filing}</p>
          </div>
        ))}
      </aside>
    </div>
  );
}
