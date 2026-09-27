export function at(path: string, raw?: string) {
  return { "data-path": path, "data-raw": raw };
}

export function el(path: string, label: string) {
  return { "data-el": path, "data-el-label": label };
}
