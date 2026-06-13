import { cn } from "@/lib/utils";

const STATUS_MAP = {
  运行中: "success",
  已授权: "success",
  已生成: "success",
  已入选: "success",
  在线: "success",
  待授权: "warning",
  待复核: "warning",
  待校对: "warning",
  待确认: "warning",
  待登录: "warning",
  需素材: "warning",
  排队中: "info",
  转写中: "info",
  素材处理中: "info",
  草稿: "info",
  未授权: "muted",
  待修改: "danger",
};

const VARIANT_CLASS = {
  success: "bg-success-muted text-success border-transparent dark:text-success-foreground",
  warning: "bg-warning-muted text-warning-foreground border-transparent",
  info: "bg-info-muted text-info border-transparent dark:text-info-foreground",
  danger: "bg-destructive/10 text-destructive border-transparent",
  muted: "bg-muted text-muted-foreground border-transparent",
};

const DOT_CLASS = {
  success: "bg-success",
  warning: "bg-warning",
  info: "bg-info",
  danger: "bg-destructive",
  muted: "bg-muted-foreground/60",
};

export function StatusBadge({ state, dot = true, className }) {
  const variant = STATUS_MAP[state] || "muted";
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium whitespace-nowrap",
        VARIANT_CLASS[variant],
        className
      )}
    >
      {dot && <span className={cn("size-1.5 rounded-full", DOT_CLASS[variant])} />}
      {state}
    </span>
  );
}
