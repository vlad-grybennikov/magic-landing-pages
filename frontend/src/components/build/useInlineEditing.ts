"use client";

import { useEffect } from "react";
import { toMarkdown } from "@/lib/richtext";

export interface EditTarget {
  role?: string;
  path?: string;
}

export function useInlineEditing({
  root,
  enabled,
  onEdit,
  onFocus,
  deps = [],
}: {
  root: React.RefObject<HTMLElement | null>;
  enabled: boolean;
  onEdit: (index: number, target: EditTarget, value: string) => void;
  onFocus?: (index: number, target: EditTarget) => void;
  deps?: unknown[];
}) {
  useEffect(() => {
    const host = root.current;
    if (!host || !enabled) return;

    const fields = Array.from(
      host.querySelectorAll<HTMLElement>("[data-role],[data-path]"),
    );

    const indexOf = (field: HTMLElement) => {
      const section = field.closest<HTMLElement>("[data-section-index]");
      const index = Number(section?.dataset.sectionIndex);
      return Number.isInteger(index) ? index : -1;
    };

    const cleanups: Array<() => void> = [];

    for (const field of fields) {
      const index = indexOf(field);
      const { role, path } = field.dataset;
      if (index < 0 || (!role && !path)) continue;

      const control = field.closest("a,button,summary");
      const swallowsSpace = !!field.closest("button,summary");

      field.contentEditable = "true";
      field.spellcheck = false;
      field.dataset.editable = "true";
      field.tabIndex = 0;

      let original = field.dataset.raw ?? field.textContent ?? "";

      const onFieldFocus = () => {
        original = field.dataset.raw ?? field.textContent ?? "";
        onFocus?.(index, path ? { path } : { role });
      };

      const commit = () => {
        const value = toMarkdown(field).replace(/\s+/g, " ").trim();
        if (!value) {
          field.textContent = original;
          if (original.trim()) onEdit(index, path ? { path } : { role }, "");
          return;
        }
        if (value === original.trim()) {
          return;
        }
        original = value;
        onEdit(index, path ? { path } : { role }, value);
      };

      const onPaste = (event: ClipboardEvent) => {
        event.preventDefault();
        const text = event.clipboardData?.getData("text/plain") ?? "";
        field.ownerDocument.defaultView
          ?.getSelection()
          ?.getRangeAt(0)
          .insertNode(document.createTextNode(text));
      };

      const onKeyDown = (event: KeyboardEvent) => {
        if (event.key === " " && swallowsSpace) {
          event.preventDefault();
          const selection = field.ownerDocument.defaultView?.getSelection();
          const range = selection?.getRangeAt(0);
          if (range) {
            range.deleteContents();
            const space = document.createTextNode(" ");
            range.insertNode(space);
            range.setStartAfter(space);
            range.collapse(true);
            selection?.removeAllRanges();
            selection?.addRange(range);
          }
          return;
        }
        if (event.key === "Enter") {
          event.preventDefault();
          field.blur();
        }
        if (event.key === "Escape") {
          event.preventDefault();
          field.textContent = original;
          field.blur();
        }
        event.stopPropagation();
      };

      const onPointerDown = (event: Event) => event.stopPropagation();
      const onClick = (event: Event) => {
        if (control) event.preventDefault();
        event.stopPropagation();
      };

      field.addEventListener("paste", onPaste);
      field.addEventListener("focus", onFieldFocus);
      field.addEventListener("blur", commit);
      field.addEventListener("keydown", onKeyDown);
      field.addEventListener("pointerdown", onPointerDown);
      field.addEventListener("click", onClick);

      cleanups.push(() => {
        field.removeEventListener("paste", onPaste);
        field.removeEventListener("focus", onFieldFocus);
        field.removeEventListener("blur", commit);
        field.removeEventListener("keydown", onKeyDown);
        field.removeEventListener("pointerdown", onPointerDown);
        field.removeEventListener("click", onClick);
        field.removeAttribute("contenteditable");
        delete field.dataset.editable;
      });
    }

    return () => cleanups.forEach((off) => off());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [root, enabled, onEdit, onFocus, ...deps]);
}
