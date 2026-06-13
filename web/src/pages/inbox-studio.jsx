import { useState } from "react";
import { Check, Image, Languages, Link as LinkIcon, Loader2, Sparkles, Video, Wand2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { PageHeader } from "@/components/app/page-header";
import { FilterBar } from "@/components/app/filter-bar";
import { ContentList } from "@/components/app/content-list";
import { StatusBadge } from "@/components/app/status-badge";
import { cn } from "@/lib/utils";
import { platformCards } from "@/data/mock";
import { API_BASE } from "@/lib/api";

const ASSET_KEY_BY_PLATFORM = {
  xhs: "xiaohongshu",
  wechat: "wechat_article",
  video: "video_account",
  douyin: "douyin_script",
};

export function InboxPage({ openModal }) {
  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="线索池"
        title="海外内容统一收件箱"
        description="所有原始帖子先在这里评分、去重、补齐引用和素材，再进入创作工作台。"
        actions={<Button onClick={() => openModal("draftPreview")}>生成平台版本</Button>}
      />
      <FilterBar
        labels={["全部来源", "全部主题", "全部状态", "分数从高到低"]}
        placeholder="搜索作者、正文、链接..."
      />
      <ContentList />
    </div>
  );
}

const tools = [
  ["翻译润色", Languages],
  ["真人语气", Wand2],
  ["视频转写", Video],
  ["去水印", Image],
  ["封面生成", Sparkles],
  ["引用补全", LinkIcon],
];

export function StudioPage({ openModal, selectedSource, selectedPlatforms, setSelectedPlatforms }) {
  const [prompt, setPrompt] = useState(
    "请把这组海外讨论整理成适合国内用户阅读的观点型内容。不要直译，不要保留英文梗，先讲人话，再给判断。"
  );
  const [limit, setLimit] = useState(3);
  const [drafts, setDrafts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const generate = async () => {
    setLoading(true);
    setError("");
    try {
      const response = await fetch(`${API_BASE}/api/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          source_id: selectedSource || "x",
          persona: prompt,
          limit,
        }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "生成失败");
      setDrafts(data.drafts || []);
      if (!data.drafts?.length) setError("该来源暂无可用线索，先去数据源页采集。");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="创作"
        title="把海外线索改造成国内平台内容"
        description="翻译、去 AI 味、补背景、生成封面和多平台草稿都在这里完成。"
        actions={
          <>
            <Button variant="outline" onClick={() => openModal("draftPreview")}>预览草稿</Button>
            <Button onClick={generate} disabled={loading} className="gap-1.5">
              {loading ? <Loader2 className="size-4 animate-spin" /> : <Sparkles className="size-4" />}
              批量生成
            </Button>
          </>
        }
      />

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
        <div className="space-y-5">
          <Card>
            <CardHeader className="flex-row items-center justify-between">
              <CardTitle>输入内容</CardTitle>
              <span className="text-sm text-muted-foreground">来源：{selectedSource || "x"} · 取 {limit} 条</span>
            </CardHeader>
            <CardContent className="space-y-4">
              <Textarea
                className="min-h-28"
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
              />
              <div className="flex items-center gap-2">
                <span className="text-sm text-muted-foreground">生成条数</span>
                {[1, 3, 5].map((n) => (
                  <button
                    key={n}
                    onClick={() => setLimit(n)}
                    className={cn(
                      "rounded-md border px-3 py-1 text-xs font-medium transition-colors",
                      limit === n ? "border-primary bg-primary/5 text-primary" : "text-muted-foreground hover:border-primary/40"
                    )}
                  >
                    {n}
                  </button>
                ))}
              </div>
              <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-4">
                {platformCards.map((p) => {
                  const Icon = p.icon;
                  const checked = selectedPlatforms.includes(p.id);
                  return (
                    <button
                      key={p.id}
                      onClick={() =>
                        setSelectedPlatforms((prev) =>
                          checked ? prev.filter((id) => id !== p.id) : [...prev, p.id]
                        )
                      }
                      className={cn(
                        "relative flex flex-col items-start gap-2 rounded-xl border p-3 text-left transition-colors",
                        checked ? "border-primary bg-primary/5" : "bg-card hover:border-primary/40"
                      )}
                    >
                      <Icon className={cn("size-[18px]", checked ? "text-primary" : "text-muted-foreground")} />
                      <span className="text-sm font-medium text-foreground">{p.name}</span>
                      {checked && (
                        <span className="absolute top-2 right-2 grid size-4 place-items-center rounded-full bg-primary text-primary-foreground">
                          <Check className="size-3" />
                        </span>
                      )}
                    </button>
                  );
                })}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex-row items-center justify-between">
              <CardTitle>输出草稿</CardTitle>
              <span className="text-sm text-muted-foreground">
                {drafts.length ? `${drafts.length} 条线索 × ${selectedPlatforms.length} 平台` : "点击批量生成"}
              </span>
            </CardHeader>
            <CardContent className="grid gap-3">
              {error && <p className="text-sm text-destructive">{error}</p>}
              {!drafts.length && !error && (
                <p className="text-sm text-muted-foreground">
                  尚未生成草稿。选择平台后点击右上角“批量生成”，会基于该来源已采集的真实线索生成多平台草稿。
                </p>
              )}
              {drafts.map((draft) => (
                <div key={draft.post_id} className="space-y-2 rounded-xl border bg-card p-4">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-primary">@{draft.account || "unknown"}</span>
                    {draft.source_url && (
                      <a href={draft.source_url} target="_blank" rel="noreferrer" className="text-xs text-muted-foreground hover:text-primary">
                        查看原文
                      </a>
                    )}
                  </div>
                  <div className="grid gap-2">
                    {platformCards
                      .filter((p) => selectedPlatforms.includes(p.id))
                      .map((p) => {
                        const Icon = p.icon;
                        const asset = draft.assets[ASSET_KEY_BY_PLATFORM[p.id]];
                        if (!asset) return null;
                        return (
                          <div key={p.id} className="flex items-start gap-3 rounded-lg border bg-background p-3">
                            <span className="grid size-8 shrink-0 place-items-center rounded-lg bg-primary/10 text-primary">
                              <Icon className="size-4" />
                            </span>
                            <div className="min-w-0 flex-1">
                              <span className="text-xs font-medium text-primary">{asset.platform}</span>
                              <h3 className="mt-0.5 text-sm font-semibold text-foreground">{asset.title}</h3>
                              <p className="mt-1 line-clamp-3 whitespace-pre-wrap text-sm text-muted-foreground">{asset.body}</p>
                            </div>
                            <StatusBadge state="待确认" />
                          </div>
                        );
                      })}
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>

        <Card className="h-fit">
          <CardHeader><CardTitle>AI 工具</CardTitle></CardHeader>
          <CardContent className="grid grid-cols-2 gap-2.5">
            {tools.map(([label, Icon]) => (
              <button
                key={label}
                className="flex flex-col items-center gap-2 rounded-xl border bg-card p-4 text-sm font-medium text-foreground transition-colors hover:border-primary/40 hover:text-primary"
              >
                <Icon className="size-5 text-primary" />
                {label}
              </button>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
