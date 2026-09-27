import type { ButtonRef } from "@/types/sections";

type Variant = "primary" | "accent" | "secondary" | "inverse" | "ghost";

const base =
  "inline-flex h-12 items-center justify-center rounded-[var(--sec-btn-radius)] px-6 text-base font-medium transition-colors";

const variants: Record<Variant, string> = {
  primary: "bg-primary text-primary-foreground hover:opacity-90",
  accent: "bg-accent text-accent-foreground hover:opacity-90",
  secondary: "border border-border text-foreground hover:bg-muted",
  inverse: "bg-background text-foreground hover:opacity-90",
  ghost: "border border-white/40 text-white hover:bg-white/10",
};

function Label({ children, path }: { children: string; path?: string }) {
  return path ? (
    <span data-path={`${path}.label`} data-raw={children}>
      {children}
    </span>
  ) : (
    <span data-role="button">{children}</span>
  );
}

export function Button({
  button,
  variant = "primary",
  path,
}: {
  button: ButtonRef;
  variant?: Variant;
  path?: string;
}) {
  const className = `${base} ${variants[variant]}`;

  if (button.href) {
    return (
      <a href={button.href} className={className}>
        <Label path={path}>{button.label}</Label>
      </a>
    );
  }

  return (
    <button type="button" className={className}>
      <Label path={path}>{button.label}</Label>
    </button>
  );
}
