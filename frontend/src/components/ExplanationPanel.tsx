"use client";

interface Props {
  summary: string;
  positives: string[];
  negatives: string[];
  conflicts: string[];
}

export function ExplanationPanel({ summary, positives, negatives, conflicts }: Props) {
  return (
    <div className="rounded-xl border border-surface-border bg-surface-card p-5 space-y-4">
      <h2 className="text-sm font-semibold text-slate-200">Analysis Explanation</h2>

      {/* Summary */}
      <div className="rounded-lg bg-surface p-3">
        <p className="text-sm leading-relaxed text-slate-300">{summary}</p>
      </div>

      {/* Three-column factors */}
      <div className="grid grid-cols-1 gap-3">
        {positives.length > 0 && (
          <FactorList
            title="Supporting"
            items={positives}
            dotClass="bg-suitable"
            textClass="text-suitable/80"
          />
        )}
        {negatives.length > 0 && (
          <FactorList
            title="Risk Factors"
            items={negatives}
            dotClass="bg-danger"
            textClass="text-danger/80"
          />
        )}
        {conflicts.length > 0 && (
          <FactorList
            title="Conflicting"
            items={conflicts}
            dotClass="bg-cautious"
            textClass="text-cautious/80"
          />
        )}
      </div>
    </div>
  );
}

function FactorList({
  title,
  items,
  dotClass,
  textClass,
}: {
  title: string;
  items: string[];
  dotClass: string;
  textClass: string;
}) {
  return (
    <div>
      <p className={`mb-1.5 text-xs font-semibold uppercase tracking-wider ${textClass}`}>
        {title}
      </p>
      <ul className="space-y-1.5">
        {items.map((item, i) => (
          <li key={i} className="flex gap-2 text-xs text-slate-400">
            <span className={`mt-1.5 h-1.5 w-1.5 flex-shrink-0 rounded-full ${dotClass}`} />
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}
