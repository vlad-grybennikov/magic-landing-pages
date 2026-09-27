"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import {
  searchIcons,
  searchImages,
  type ImageCandidate,
} from "@/lib/orchestrator";

const SHELF = 80;

export function MediaPicker({
  kind,
  title,
  suggestion,
  onClose,
  onChoose,
}: {
  kind: "image" | "icon";
  title: string;
  suggestion: string;
  onClose: () => void;
  onChoose: (value: string) => void;
}) {
  const [query, setQuery] = useState(suggestion);
  const [results, setResults] = useState<ImageCandidate[]>([]);
  const [loading, setLoading] = useState(false);
  const [limit, setLimit] = useState(SHELF);

  useEffect(() => {
    let cancelled = false;
    const timer = setTimeout(async () => {
      if (cancelled) return;
      setLoading(true);
      const found =
        kind === "icon"
          ? await searchIcons(query, limit)
          : await searchImages(query);
      if (!cancelled) {
        setResults(found);
        setLoading(false);
      }
    }, 250);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [kind, query, limit]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={title}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-3 sm:p-6"
      onClick={onClose}
    >
      <div
        onClick={(event) => event.stopPropagation()}
        className="flex max-h-[88vh] w-full max-w-4xl flex-col overflow-hidden rounded-2xl border border-ui-border bg-ui-surface shadow-2xl sm:max-h-[80vh]"
      >
        <div className="flex flex-wrap items-center gap-x-3 gap-y-2 border-b border-ui-border p-3 sm:p-4">
          <div className="min-w-0 flex-1">
            <h2 className="truncate text-sm font-medium text-ui-text">
              {title}
            </h2>
            <p className="text-xs text-ui-muted">
              {kind === "icon"
                ? "Describe what it should show"
                : "Describe the photo you want"}
            </p>
          </div>
          <input
            autoFocus
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setLimit(SHELF);
            }}
            placeholder={
              kind === "icon" ? "clock, leaf, shield" : "bakery counter"
            }
            className="order-last w-full rounded-lg border border-ui-border bg-ui-surface px-3 py-1.5 text-sm text-ui-text sm:order-none sm:ml-auto sm:w-64"
          />
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="shrink-0 rounded-md px-2 py-1 text-ui-muted hover:bg-ui-inset"
          >
            ×
          </button>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto p-3 sm:p-4">
          {loading && <p className="text-sm text-ui-muted">Searching…</p>}
          {!loading && results.length === 0 && (
            <p className="text-sm text-ui-muted">
              Nothing matched. Try naming the trade or the setting.
            </p>
          )}

          <div
            className={
              kind === "icon"
                ? "grid grid-cols-[repeat(auto-fill,minmax(4.5rem,1fr))] gap-2 sm:grid-cols-[repeat(auto-fill,minmax(5rem,1fr))]"
                : "grid grid-cols-[repeat(auto-fill,minmax(8.5rem,1fr))] gap-3 sm:grid-cols-[repeat(auto-fill,minmax(13rem,1fr))]"
            }
          >
            {results.map((item) => (
              <button
                key={item.id ?? item.src}
                type="button"
                onClick={() => {
                  onChoose(
                    kind === "icon" ? (item.id ?? "") : item.alt || query,
                  );
                  onClose();
                }}
                title={kind === "icon" ? (item.id ?? undefined) : item.alt}
                className={`group relative overflow-hidden rounded-xl border border-ui-border hover:border-ui-accent ${
                  kind === "icon"
                    ? "flex aspect-square flex-col items-center justify-center gap-1 p-2"
                    : "aspect-[4/3]"
                }`}
              >
                {kind === "icon" ? (
                  <>
                    <span
                      role="img"
                      aria-label={item.id ?? undefined}
                      className="h-7 w-7 bg-ui-text"
                      style={{
                        maskImage: `url(${item.src})`,
                        WebkitMaskImage: `url(${item.src})`,
                        maskRepeat: "no-repeat",
                        WebkitMaskRepeat: "no-repeat",
                        maskPosition: "center",
                        WebkitMaskPosition: "center",
                        maskSize: "contain",
                        WebkitMaskSize: "contain",
                      }}
                    />
                    <span className="w-full truncate text-[10px] text-ui-faint">
                      {item.id}
                    </span>
                  </>
                ) : (
                  <>
                    <Image
                      src={item.src}
                      alt={item.alt}
                      fill
                      sizes="240px"
                      className="object-cover"
                    />
                    {item.alt && (
                      <span className="absolute inset-x-0 bottom-0 truncate bg-black/60 px-2 py-1 text-left text-[11px] text-white opacity-0 transition-opacity group-hover:opacity-100">
                        {item.alt}
                      </span>
                    )}
                  </>
                )}
              </button>
            ))}
          </div>

          {kind === "icon" && !loading && results.length >= limit && (
            <button
              type="button"
              onClick={() => setLimit(limit + SHELF)}
              className="mt-4 w-full rounded-lg border border-ui-border py-2 text-sm text-ui-text hover:bg-ui-inset"
            >
              Show more
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
