"use client";

import type { Brief } from "@/data/build-mock";
import { inputClass } from "./Panel";

const ROWS: { key: keyof Brief; label: string }[] = [
  { key: "business", label: "Business" },
  { key: "audience", label: "Audience" },
  { key: "goal", label: "Goal" },
];

export function UnderstoodPanel({
  brief,
  isWorking,
  onChange,
}: {
  brief: Brief;
  isWorking: boolean;
  onChange: (brief: Brief) => void;
}) {
  return (
    <div className="flex flex-col gap-2.5">
      {ROWS.map(({ key, label }) => (
        <label key={key} className="block">
          <span className="mb-1 block text-[11px] font-medium uppercase tracking-[0.06em] text-ui-faint">
            {label}
          </span>
          <input
            value={(brief[key] as string) ?? ""}
            onChange={(e) => onChange({ ...brief, [key]: e.target.value })}
            disabled={isWorking}
            className={inputClass}
          />
        </label>
      ))}
    </div>
  );
}
