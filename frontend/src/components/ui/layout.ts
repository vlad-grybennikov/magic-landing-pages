export const PAD = "py-[var(--sec-pad)]";
export const PAD_TIGHT = "py-[calc(var(--sec-pad)*0.62)]";

export const WIDE = "mx-auto w-full max-w-7xl px-6 sm:px-8";
export const CONTENT = "mx-auto w-full max-w-6xl px-6 sm:px-8";
export const TEXT = "mx-auto w-full max-w-3xl px-6";

export function gridCols(n: number): string {
  if (n <= 1) return "";
  if (n === 2) return "sm:grid-cols-2";
  if (n === 4) return "sm:grid-cols-2 lg:grid-cols-4";
  if (n % 3 === 0) return "sm:grid-cols-2 lg:grid-cols-3";
  return "sm:grid-cols-2 lg:grid-cols-3";
}
