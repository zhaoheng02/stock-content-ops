import { Plus, Send } from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { navItems } from "@/data/mock";

export function SidebarContent({ active, onNavigate, onQuickCreate }) {
  return (
    <div className="flex h-full flex-col gap-5 bg-sidebar px-3 py-5">
      <div className="flex items-center justify-between px-1">
        <div className="flex items-center gap-2.5">
          <div className="grid size-9 place-items-center rounded-lg bg-foreground font-extrabold text-background">
            OR
          </div>
          <div className="leading-tight">
            <p className="text-sm font-bold text-foreground">Overseas Relay</p>
            <p className="text-xs text-muted-foreground">跨境内容中台</p>
          </div>
        </div>
        <Button
          variant="outline"
          size="icon"
          className="size-8 shrink-0 bg-card text-primary"
          onClick={onQuickCreate}
        >
          <Plus className="size-4" />
        </Button>
      </div>

      <ScrollArea className="-mx-1 flex-1 px-1">
        <nav className="grid gap-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = active === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onNavigate(item.id)}
                className={cn(
                  "flex items-center gap-2.5 rounded-lg px-3 py-2.5 text-sm font-semibold transition-colors",
                  isActive
                    ? "bg-sidebar-accent text-primary shadow-sm"
                    : "text-sidebar-foreground hover:bg-sidebar-accent/60 hover:text-foreground"
                )}
              >
                <Icon className="size-[18px]" />
                <span>{item.label}</span>
                {item.badge && (
                  <span className="ml-auto rounded-full bg-warning-muted px-1.5 py-0.5 text-[10px] font-semibold text-warning-foreground">
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </ScrollArea>

      <Button className="w-full gap-2" onClick={() => onNavigate("publish")}>
        <Send className="size-4" />
        一键发布
      </Button>
    </div>
  );
}
