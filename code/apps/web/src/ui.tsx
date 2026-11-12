import * as Dialog from "@radix-ui/react-dialog";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { clsx, type ClassValue } from "clsx";
import { AlertCircle, FileText, Search, X } from "lucide-react";
import { twMerge } from "tailwind-merge";
import { useRef, type ComponentProps, type ReactNode, type RefObject } from "react";
import type { Job } from "./api";

const cn = (...inputs: ClassValue[]) => twMerge(clsx(inputs));
const buttonVariants = cva(
  "inline-flex min-h-[var(--control-height)] shrink-0 items-center justify-center gap-2 rounded-lg px-3.5 text-sm font-semibold",
  {
    variants: {
      variant: {
        primary: "bg-primary text-primary-foreground hover:bg-brand-hover",
        secondary: "bg-secondary text-secondary-foreground hover:bg-accent",
        outline: "border border-border bg-card text-foreground hover:bg-muted",
        ghost: "text-muted-foreground hover:bg-muted hover:text-foreground",
        destructive: "bg-destructive text-primary-foreground",
      },
    },
    defaultVariants: { variant: "primary" },
  },
);

export function Button({ className, variant, asChild, type = "button", ...props }:
  ComponentProps<"button"> & VariantProps<typeof buttonVariants> & { asChild?: boolean }) {
  const Component = asChild ? Slot : "button";
  return <Component {...props} type={asChild ? undefined : type}
    className={cn(buttonVariants({ variant }), "disabled:cursor-not-allowed disabled:opacity-50", className)} />;
}

export function Sheet({ title, description, open, onOpenChange, children, side = "right", returnFocus, initialFocus }:
  { title: string; description: string; open: boolean; onOpenChange: (open: boolean) => void;
    children: ReactNode; side?: "left" | "right" | "bottom" | "center"; returnFocus?: RefObject<HTMLElement | null>; initialFocus?: RefObject<HTMLElement | null> }) {
  const fallbackFocus = useRef<HTMLElement | null>(null);
  return <Dialog.Root open={open} onOpenChange={onOpenChange}>
    <Dialog.Portal>
      <Dialog.Overlay className="sheet-overlay" />
      <Dialog.Content className={"sheet sheet-" + side} onOpenAutoFocus={(event) => { fallbackFocus.current = document.activeElement instanceof HTMLElement ? document.activeElement : null; if (initialFocus?.current) { event.preventDefault(); initialFocus.current.focus(); } }} onCloseAutoFocus={(event) => {
        const target = returnFocus?.current?.isConnected ? returnFocus.current : fallbackFocus.current;
        if (target?.isConnected) {
          event.preventDefault();
          target.focus();
        }
      }}>
        <div className="sheet-heading">
          <div>
            <Dialog.Title className="sheet-title">{title}</Dialog.Title>
            <Dialog.Description className="sheet-description">{description}</Dialog.Description>
          </div>
          <Dialog.Close asChild><Button variant="ghost" className="icon-button" aria-label={"Close " + title.toLowerCase()}><X size={18} /></Button></Dialog.Close>
        </div>
        {children}
      </Dialog.Content>
    </Dialog.Portal>
  </Dialog.Root>;
}

export function PageHeading({ title, description, action }: { title: string; description: string; action?: ReactNode }) {
  return <div className="page-heading">
    <div><h1>{title}</h1><p>{description}</p></div>
    {action}
  </div>;
}

export const jobLabels: Record<Job["status"], string> = {
  queued: "Queued",
  processing: "Processing",
  cancelled: "Cancelled",
  ready: "Ready",
  extraction_unavailable: "Extraction unavailable",
  failed: "Failed",
};

export function StatusBadge({ status }: { status: Job["status"] }) {
  return <span className={"status-pill " + status}>{jobLabels[status]}</span>;
}

export function SearchField({ className, ...props }: ComponentProps<"input">) {
  return <div className={cn("search-field", className)}>
    <Search size={17} aria-hidden="true" /><input type="search" {...props} />
  </div>;
}

export function sourceLocation(locator?: Record<string, unknown>, line?: number) {
  return locator ? Object.entries(locator).filter(([key]) => ["page", "line", "paragraph", "table", "row"].includes(key)).map(([key,value]) => key + " " + String(value)).join(" · ") || "Source passage" : line ? "Line " + line : "Source passage";
}

export function SourceCitation({ filename, line, locator, onOpen }: {
  filename: string; line: number; locator?: Record<string, unknown>; onOpen: () => void;
}) {
  return <button className="source-citation" onClick={onOpen} aria-label={"Source " + sourceLocation(locator, line) + " in " + filename}>
    <FileText size={14} /> {filename} · {sourceLocation(locator, line)}
  </button>;
}

export function EvidenceCard({ filename, quote, line, locator }: { filename: string; quote: string; line: number; locator?: Record<string, unknown> }) {
  return <div className="evidence-card">
    <div><FileText size={15} /><strong>{filename}</strong><span>{sourceLocation(locator, line)}</span></div>
    <blockquote dir="auto">{quote}</blockquote>
  </div>;
}

export function Feedback({ children, error = false }: { children: ReactNode; error?: boolean }) {
  return <div className={error ? "feedback feedback-error" : "feedback"} role={error ? "alert" : "status"}>
    {error && <AlertCircle size={18} className="shrink-0" />}
    {children}
  </div>;
}
