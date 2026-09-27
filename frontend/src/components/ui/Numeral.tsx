export function Numeral({
  n,
  tone = "tint",
}: {
  n: number;
  tone?: "tint" | "solid" | "bare";
}) {
  const label = String(n).padStart(2, "0");
  if (tone === "bare") {
    return (
      <span
        aria-hidden
        className="text-4xl font-semibold tabular-nums text-primary/30"
      >
        {label}
      </span>
    );
  }
  const tones = {
    tint: "bg-primary/10 text-primary",
    solid: "bg-primary text-primary-foreground",
  }[tone];
  return (
    <span
      aria-hidden
      className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-full text-sm font-semibold tabular-nums ${tones}`}
    >
      {label}
    </span>
  );
}
