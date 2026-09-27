import type { ReactNode } from "react";
import { rich } from "@/lib/richtext";

export function Lede({
  children,
  role,
  className = "",
}: {
  children: ReactNode;
  role?: "description";
  className?: string;
}) {
  return (
    <p
      data-role={role}
      data-raw={typeof children === "string" ? children : undefined}
      className={`text-pretty text-lg leading-relaxed sm:text-xl ${className} text-muted-foreground`}
    >
      {typeof children === "string" ? rich(children) : children}
    </p>
  );
}
