import { useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";

import { TooltipProvider } from "@/components/ui/tooltip";
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet";
import { Toaster } from "@/components/ui/sonner";
import { toast } from "sonner";
import { ThemeProvider } from "@/components/theme-provider";
import { SidebarContent } from "@/components/app/sidebar";
import { Topbar } from "@/components/app/topbar";
import { ModalRouter } from "@/components/app/modals";

import { HomePage } from "@/pages/home";
import { SourcesPage } from "@/pages/sources";
import { InboxPage, StudioPage } from "@/pages/inbox-studio";
import {
  AccountsPage,
  AnalyticsPage,
  AssetsPage,
  PublishPage,
  ReviewPage,
  TeamPage,
} from "@/pages/rest";

function App() {
  const [active, setActive] = useState("home");
  const [modal, setModal] = useState(null);
  const [mobileNav, setMobileNav] = useState(false);
  const [selectedSource, setSelectedSource] = useState("x");
  const [selectedPlatforms, setSelectedPlatforms] = useState(["xhs", "wechat"]);

  const navigate = (id) => {
    setActive(id);
    setMobileNav(false);
  };

  const page = useMemo(() => {
    const props = {
      openModal: setModal,
      setActive: navigate,
      selectedSource,
      setSelectedSource,
      selectedPlatforms,
      setSelectedPlatforms,
    };
    const pages = {
      home: <HomePage {...props} />,
      sources: <SourcesPage {...props} />,
      inbox: <InboxPage {...props} />,
      studio: <StudioPage {...props} />,
      publish: <PublishPage {...props} />,
      accounts: <AccountsPage {...props} />,
      analytics: <AnalyticsPage {...props} />,
      review: <ReviewPage {...props} />,
      team: <TeamPage {...props} />,
      assets: <AssetsPage {...props} />,
    };
    return pages[active];
  }, [active, selectedSource, selectedPlatforms]);

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="lg:grid lg:grid-cols-[244px_minmax(0,1fr)]">
        <aside className="sticky top-0 hidden h-screen border-r lg:block">
          <SidebarContent
            active={active}
            onNavigate={navigate}
            onQuickCreate={() => setModal("newPublish")}
          />
        </aside>

        <div className="flex min-h-screen min-w-0 flex-col">
          <Topbar onMenu={() => setMobileNav(true)} />
          <main className="flex-1 px-4 py-6 sm:px-6 lg:px-8">{page}</main>
        </div>
      </div>

      <Sheet open={mobileNav} onOpenChange={setMobileNav}>
        <SheetContent side="left" className="w-[260px] p-0">
          <SheetTitle className="sr-only">导航</SheetTitle>
          <SidebarContent
            active={active}
            onNavigate={navigate}
            onQuickCreate={() => {
              setModal("newPublish");
              setMobileNav(false);
            }}
          />
        </SheetContent>
      </Sheet>

      <ModalRouter
        modal={modal}
        onClose={() => setModal(null)}
        onToast={(msg) => toast.success(msg)}
      />
      <Toaster position="top-center" richColors />
    </div>
  );
}

createRoot(document.getElementById("root")).render(
  <ThemeProvider>
    <TooltipProvider delayDuration={200}>
      <App />
    </TooltipProvider>
  </ThemeProvider>
);
