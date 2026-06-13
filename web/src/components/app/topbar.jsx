import { BookOpen, Bell, Globe2, Headphones, Menu, Smartphone } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Separator } from "@/components/ui/separator";
import { ThemeToggle } from "@/components/app/theme-toggle";

const iconButtons = [
  { icon: Smartphone, label: "移动端" },
  { icon: Headphones, label: "客服" },
  { icon: BookOpen, label: "操作手册" },
  { icon: Bell, label: "消息通知" },
];

export function Topbar({ onMenu }) {
  return (
    <header className="sticky top-0 z-20 flex h-16 items-center justify-between gap-3 border-b bg-background/80 px-4 backdrop-blur-md sm:px-6">
      <div className="flex items-center gap-2">
        <Button
          variant="ghost"
          size="icon"
          className="lg:hidden"
          onClick={onMenu}
        >
          <Menu className="size-5" />
        </Button>
        <div className="hidden items-center gap-2 rounded-full border bg-card px-4 py-1.5 text-sm text-muted-foreground sm:flex">
          <Globe2 className="size-4" />
          <span className="font-medium">relay.local/workbench</span>
        </div>
      </div>

      <div className="flex items-center gap-1">
        {iconButtons.map(({ icon: Icon, label }) => (
          <Tooltip key={label}>
            <TooltipTrigger asChild>
              <Button variant="ghost" size="icon" className="text-muted-foreground">
                <Icon className="size-[18px]" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>{label}</TooltipContent>
          </Tooltip>
        ))}
        <Separator orientation="vertical" className="mx-1 !h-5" />
        <ThemeToggle />
      </div>
    </header>
  );
}
