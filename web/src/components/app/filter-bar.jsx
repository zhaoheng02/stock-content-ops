import { ChevronDown, Search } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

export function FilterBar({ labels = [], placeholder }) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <div className="relative min-w-[220px] flex-1">
        <Search className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
        <Input className="bg-card pl-9" placeholder={placeholder} />
      </div>
      {labels.map((label) => (
        <Button key={label} variant="outline" className="gap-1.5 bg-card font-medium">
          {label}
          <ChevronDown className="size-4 text-muted-foreground" />
        </Button>
      ))}
    </div>
  );
}
