import { CheckCircle2, XCircle, Hourglass } from "lucide-react";

import { cn } from "@/lib/utils";
import type { Verdict } from "@/lib/audits";

type Props = {
  verdict: Verdict | null;
  pending?: boolean;
  size?: "sm" | "lg";
};

export function VerdictBadge({ verdict, pending = false, size = "sm" }: Props) {
  if (pending && !verdict) {
    return (
      <Pill className="bg-muted text-muted-foreground" size={size}>
        <Hourglass className="h-3.5 w-3.5" /> Pending
      </Pill>
    );
  }
  if (verdict === "go") {
    return (
      <Pill className="bg-emerald-500/15 text-emerald-700 dark:text-emerald-400" size={size}>
        <CheckCircle2 className="h-3.5 w-3.5" /> Go
      </Pill>
    );
  }
  if (verdict === "no_go") {
    return (
      <Pill className="bg-destructive/15 text-destructive" size={size}>
        <XCircle className="h-3.5 w-3.5" /> No-Go
      </Pill>
    );
  }
  return (
    <Pill className="bg-muted text-muted-foreground" size={size}>
      —
    </Pill>
  );
}

function Pill({
  children,
  className,
  size,
}: {
  children: React.ReactNode;
  className: string;
  size: "sm" | "lg";
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full font-medium",
        size === "lg" ? "px-3 py-1 text-sm" : "px-2 py-0.5 text-xs",
        className,
      )}
    >
      {children}
    </span>
  );
}
