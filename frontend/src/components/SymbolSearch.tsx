"use client";

import { useState, useRef } from "react";

const QUICK_SYMBOLS = [
  "AAPL", "MSFT", "NVDA", "TSLA", "SPY", "QQQ",
  "BTC-USD", "ETH-USD", "GLD", "TLT",
];

interface Props {
  value: string;
  onSelect: (symbol: string) => void;
}

export function SymbolSearch({ value, onSelect }: Props) {
  const [input, setInput] = useState(value);
  const [open, setOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const filtered = QUICK_SYMBOLS.filter((s) =>
    s.toLowerCase().includes(input.toLowerCase())
  );

  const commit = (sym: string) => {
    const upper = sym.toUpperCase().trim();
    if (upper) {
      setInput(upper);
      onSelect(upper);
    }
    setOpen(false);
  };

  return (
    <div className="relative">
      <div className="flex items-center gap-2 rounded-lg border border-surface-border bg-surface px-3 py-1.5">
        <svg className="h-3.5 w-3.5 text-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
        <input
          ref={inputRef}
          value={input}
          onChange={(e) => { setInput(e.target.value); setOpen(true); }}
          onFocus={() => setOpen(true)}
          onBlur={() => setTimeout(() => setOpen(false), 150)}
          onKeyDown={(e) => {
            if (e.key === "Enter") commit(input);
            if (e.key === "Escape") setOpen(false);
          }}
          className="w-24 bg-transparent text-sm font-mono font-medium text-slate-100 placeholder-muted outline-none"
          placeholder="Symbol..."
        />
      </div>

      {open && filtered.length > 0 && (
        <div className="absolute right-0 top-full z-50 mt-1 w-40 rounded-lg border border-surface-border bg-surface-card shadow-xl">
          {filtered.map((sym) => (
            <button
              key={sym}
              onMouseDown={() => commit(sym)}
              className="w-full px-3 py-2 text-left text-xs font-mono text-slate-300 hover:bg-surface-hover hover:text-slate-100"
            >
              {sym}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
