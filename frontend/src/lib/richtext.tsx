import type { ReactNode } from "react";

const TOKEN = /(\*\*[^*\n]+\*\*|_[^_\n]+_|\*[^*\n]+\*)/g;

export const MARKERS = {
  bold: "**",
  italic: "*",
  underline: "_",
} as const;

export type Marker = keyof typeof MARKERS;

export function hasFormatting(text: string): boolean {
  TOKEN.lastIndex = 0;
  return TOKEN.test(text);
}

export function rich(text: string): ReactNode {
  if (!text) return text;

  const parts: ReactNode[] = [];
  let last = 0;
  let key = 0;

  TOKEN.lastIndex = 0;
  for (let match = TOKEN.exec(text); match; match = TOKEN.exec(text)) {
    if (match.index > last) parts.push(text.slice(last, match.index));
    const token = match[0];

    if (token.startsWith("**")) {
      parts.push(<strong key={key++}>{token.slice(2, -2)}</strong>);
    } else if (token.startsWith("_")) {
      parts.push(<u key={key++}>{token.slice(1, -1)}</u>);
    } else {
      parts.push(<em key={key++}>{token.slice(1, -1)}</em>);
    }
    last = match.index + token.length;
  }

  if (last === 0) return text;
  if (last < text.length) parts.push(text.slice(last));
  return parts;
}

export function Rich({
  text,
  ...rest
}: { text: string } & Record<string, unknown>) {
  return (
    <span data-raw={text} {...rest}>
      {rich(text)}
    </span>
  );
}

export function toMarkdown(node: Node): string {
  if (node.nodeType === Node.TEXT_NODE) return node.textContent ?? "";
  if (!(node instanceof HTMLElement)) return "";

  const inner = Array.from(node.childNodes).map(toMarkdown).join("");
  if (node.tagName === "BR") return " ";
  if (!inner.trim()) return inner;

  switch (node.tagName) {
    case "STRONG":
    case "B":
      return `**${inner}**`;
    case "EM":
    case "I":
      return `*${inner}*`;
    case "U":
      return `_${inner}_`;
    default:
      return inner;
  }
}

export function toggleMarker(text: string, marker: Marker): string {
  const mark = MARKERS[marker];
  const wrapped =
    text.startsWith(mark) && text.endsWith(mark) && text.length > mark.length * 2;
  return wrapped ? text.slice(mark.length, -mark.length) : `${mark}${text}${mark}`;
}
