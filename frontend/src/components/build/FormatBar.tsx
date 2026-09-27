"use client";

import { useEffect, useState } from "react";
import type { Marker } from "@/lib/richtext";

interface Spot {
  top: number;
  left: number;
}

const BUTTONS: Array<{ marker: Marker; label: string; className: string }> = [
  { marker: "bold", label: "B", className: "font-bold" },
  { marker: "italic", label: "I", className: "italic" },
  { marker: "underline", label: "U", className: "underline" },
];

export function FormatBar({ enabled }: { enabled: boolean }) {
  const [spot, setSpot] = useState<Spot | null>(null);

  useEffect(() => {
    if (!enabled) return;

    const onSelectionChange = () => {
      const selection = document.getSelection();
      if (!selection || selection.isCollapsed || selection.rangeCount === 0) {
        setSpot(null);
        return;
      }
      const range = selection.getRangeAt(0);
      const host =
        range.commonAncestorContainer.parentElement?.closest("[data-editable]");
      if (!host) {
        setSpot(null);
        return;
      }
      const box = range.getBoundingClientRect();
      setSpot({
        top: box.top + window.scrollY - 44,
        left: box.left + box.width / 2,
      });
    };

    document.addEventListener("selectionchange", onSelectionChange);
    return () =>
      document.removeEventListener("selectionchange", onSelectionChange);
  }, [enabled]);

  if (!enabled || !spot) return null;

  const apply = (marker: Marker) => {
    document.execCommand("styleWithCSS", false, "false");
    document.execCommand(marker, false);

    const host = document
      .getSelection()
      ?.anchorNode?.parentElement?.closest("[data-editable]");
    host?.dispatchEvent(new Event("input", { bubbles: true }));
  };

  return (
    <div
      style={{ top: spot.top, left: spot.left }}
      className="absolute z-50 flex -translate-x-1/2 gap-0.5 rounded-lg border border-black/10 bg-white p-1 shadow-lg"
    >
      {BUTTONS.map(({ marker, label, className }) => (
        <button
          key={marker}
          type="button"
          onMouseDown={(event) => {
            event.preventDefault();
            apply(marker);
          }}
          title={`${marker[0].toUpperCase()}${marker.slice(1)}`}
          className={`h-7 w-7 rounded text-sm text-zinc-800 hover:bg-zinc-100 ${className}`}
        >
          {label}
        </button>
      ))}
    </div>
  );
}
