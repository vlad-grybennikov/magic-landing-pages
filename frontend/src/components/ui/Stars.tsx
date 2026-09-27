import { el } from "./marks";

export function Stars({
  rating,
  path,
  size = "md",
}: {
  rating: number;
  path?: string;
  size?: "sm" | "md" | "lg";
}) {
  const filled = Math.max(0, Math.min(5, Math.round(rating)));
  const sizes = { sm: "text-sm", md: "text-base", lg: "text-xl" }[size];
  return (
    <div
      {...(path ? el(path, "Rating") : {})}
      className={`flex gap-0.5 text-amber-500 ${sizes}`}
      role="img"
      aria-label={`${filled} out of 5 stars`}
    >
      {Array.from({ length: 5 }).map((_, i) => (
        <span key={i} aria-hidden className={i < filled ? "" : "text-border"}>
          ★
        </span>
      ))}
    </div>
  );
}
