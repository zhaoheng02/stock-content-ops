import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

const TONE = {
  brand: "text-primary bg-primary/10",
  blue: "text-info bg-info-muted dark:text-info-foreground",
  green: "text-success bg-success-muted dark:text-success-foreground",
  orange: "text-warning-foreground bg-warning-muted",
  purple: "text-primary bg-primary/10",
};

export function Metric({ title, value, hint, icon: Icon, tone = "brand" }) {
  return (
    <Card className="gap-0 p-5">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-muted-foreground">{title}</span>
        <span className={cn("grid size-9 place-items-center rounded-lg", TONE[tone])}>
          <Icon className="size-[18px]" />
        </span>
      </div>
      <div className="mt-4 text-3xl font-bold tracking-tight text-foreground tnum">
        {value}
      </div>
      {hint && <p className="mt-1.5 text-xs text-muted-foreground">{hint}</p>}
    </Card>
  );
}
