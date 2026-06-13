import {
  Activity,
  AlertCircle,
  CheckCircle2,
  Clock3,
  Loader2,
  Play,
  SlidersHorizontal,
  UserRound,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { PageHeader } from "@/components/app/page-header";
import { StatusBadge } from "@/components/app/status-badge";
import { BrandIcon } from "@/components/app/brand-icon";
import { cn } from "@/lib/utils";
import { sourceRows } from "@/data/mock";
import { API_BASE } from "@/lib/api";

export function SourcesPage({ openModal, selectedSource, setSelectedSource }) {
  const [remoteSources, setRemoteSources] = useState([]);
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [apiError, setApiError] = useState("");
  const [logRun, setLogRun] = useState(null);
  const [logPosts, setLogPosts] = useState([]);
  const [logLoading, setLogLoading] = useState(false);
  const sources = useMemo(() => {
    const remoteRows = remoteSources.map(sourceToRow);
    const remotePlatforms = new Set(remoteSources.map((source) => source.platform));
    const placeholders = sourceRows
      .filter((row) => !remotePlatforms.has(row.slug))
      .map((row) => ({ ...row, placeholder: true }));
    return [...remoteRows, ...placeholders];
  }, [remoteSources]);
  const current = sources.find((s) => s.id === selectedSource) || sources[0];
  const isPlaceholder = Boolean(current?.placeholder);
  const config = [
    ["采集频率", current.cadence, Clock3],
    ["监控账号", `${current.accounts} 个`, UserRound],
    ["上次运行", current.lastRun, Activity],
    ["入库策略", "评分 ≥ 70 自动入池", SlidersHorizontal],
  ];

  const loadSources = async ({ active = true } = {}) => {
    setLoading(true);
    return fetch(`${API_BASE}/api/sources`)
      .then((response) => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.json();
      })
      .then((payload) => {
        if (!active) return;
        const remote = payload.sources || [];
        setRemoteSources(remote);
        setApiError("");
        const validIds = new Set([
          ...remote.map((item) => item.id),
          ...sourceRows.map((row) => row.id),
        ]);
        if (!validIds.has(selectedSource)) {
          setSelectedSource(remote[0]?.id || sourceRows[0]?.id);
        }
      })
      .catch(() => {
        if (!active) return;
        setRemoteSources([]);
        setApiError("本地服务未连接，正在显示示例数据");
      })
      .finally(() => active && setLoading(false));
  };

  useEffect(() => {
    let active = true;
    loadSources({ active });
    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const listener = (event) => {
      loadSources().then(() => {
        if (event.detail?.id) setSelectedSource(event.detail.id);
      });
    };
    window.addEventListener("sources:changed", listener);
    return () => window.removeEventListener("sources:changed", listener);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [setSelectedSource]);

  useEffect(() => {
    if (!remoteSources.length || !current?.id || isPlaceholder) {
      setRuns([]);
      return;
    }
    let active = true;
    fetch(`${API_BASE}/api/source-runs?source_id=${encodeURIComponent(current.id)}&limit=5`)
      .then((response) => response.json())
      .then((payload) => active && setRuns(payload.runs || []))
      .catch(() => active && setRuns([]));
    return () => {
      active = false;
    };
  }, [current?.id, remoteSources.length, isPlaceholder]);

  const runNow = async () => {
    if (!remoteSources.length || !current?.id || isPlaceholder) return;
    setRunning(true);
    try {
      const response = await fetch(`${API_BASE}/api/source-runs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ source_id: current.id, out: "data/inbox" }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || "运行失败");
      setRuns((items) => [payload.run, ...items]);
      setApiError("");
    } catch (error) {
      setApiError(error.message);
      const response = await fetch(`${API_BASE}/api/source-runs?source_id=${encodeURIComponent(current.id)}&limit=5`);
      const payload = await response.json();
      setRuns(payload.runs || []);
    } finally {
      setRunning(false);
    }
  };

  const openLog = async (run) => {
    if (!run?.id) return;
    setLogRun(run);
    setLogPosts([]);
    setLogLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/source-posts?run_id=${encodeURIComponent(run.id)}`);
      const payload = await response.json();
      setLogPosts(payload.posts || []);
    } catch {
      setLogPosts([]);
    } finally {
      setLogLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="数据源"
        title="海外内容采集中心"
        description="把 X、TikTok、Reddit、YouTube 等内容源统一管理，进入同一个线索评分和素材处理流程。"
        actions={
          <>
            <Button variant="outline" onClick={() => openModal("proxy")}>网络代理</Button>
            <Button onClick={() => openModal("source")}>新增数据源</Button>
          </>
        }
      />
      {(apiError || loading) && (
        <div className="flex items-center gap-2 rounded-lg border bg-muted/30 px-3.5 py-2.5 text-sm text-muted-foreground">
          {loading ? <Loader2 className="size-4 animate-spin" /> : <AlertCircle className="size-4 text-warning-foreground" />}
          <span>{loading ? "正在连接本地数据源服务" : apiError}</span>
        </div>
      )}
      <div className="grid items-start gap-6 lg:grid-cols-[320px_minmax(0,1fr)]">
        <div className="grid min-w-0 gap-3">
          {sources.map((s) => (
            <button
              key={s.id}
              onClick={() => setSelectedSource(s.id)}
              className={cn(
                "flex w-full min-w-0 items-start gap-3.5 rounded-xl border bg-card p-4 text-left transition-all",
                selectedSource === s.id
                  ? "border-primary shadow-sm ring-1 ring-primary/30"
                  : "hover:border-primary/40 hover:shadow-sm"
              )}
            >
              <span className="grid size-11 shrink-0 place-items-center rounded-xl border bg-background">
                <BrandIcon slug={s.slug} className="size-5" />
              </span>
              <span className="min-w-0 flex-1">
                <span className="flex items-center justify-between gap-2">
                  <span className="truncate text-[15px] font-semibold text-foreground">{s.name}</span>
                  {s.placeholder ? (
                    <span className="shrink-0 rounded-full border border-dashed px-2 py-0.5 text-[11px] text-muted-foreground">
                      未接入
                    </span>
                  ) : (
                    <StatusBadge state={s.status} className="shrink-0" />
                  )}
                </span>
                <span className="mt-1 block truncate text-[13px] leading-relaxed text-muted-foreground">
                  {s.ingest}
                </span>
              </span>
            </button>
          ))}
        </div>

        <Card className="min-w-0">
          <CardHeader className="flex-row items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-3">
              <span className="grid size-10 shrink-0 place-items-center rounded-xl border bg-background">
                <BrandIcon slug={current.slug} className="size-5" />
              </span>
              <div className="min-w-0">
                <CardTitle className="truncate text-lg">{current.name} 采集配置</CardTitle>
                <p className="mt-0.5 text-sm text-muted-foreground">实时运行状态与采集规则</p>
              </div>
            </div>
            <div className="flex shrink-0 items-center gap-2">
              <Button variant="outline" className="w-28 shrink-0 gap-1.5" onClick={runNow} disabled={isPlaceholder || !remoteSources.length || running}>
                {running ? <Loader2 className="size-4 animate-spin" /> : <Play className="size-4" />}
                {running ? "运行中" : "立即运行"}
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-6">
            {isPlaceholder && (
              <div className="flex items-center gap-2 rounded-lg border border-dashed bg-muted/30 px-3.5 py-2.5 text-sm text-muted-foreground">
                <AlertCircle className="size-4 shrink-0" />
                <span>{current.name} 采集尚未接入后端，目前为示例展示，暂不可运行。</span>
              </div>
            )}
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {config.map(([label, value, Icon]) => (
                <div key={label} className="rounded-xl border bg-muted/30 p-4">
                  <span className="grid size-9 place-items-center rounded-lg bg-primary/10 text-primary">
                    <Icon className="size-[18px]" />
                  </span>
                  <p className="mt-3 text-[13px] text-muted-foreground">{label}</p>
                  <p className="mt-1 text-base font-semibold text-foreground">{value}</p>
                </div>
              ))}
            </div>

            <div className="space-y-3">
              <h3 className="text-[15px] font-semibold text-foreground">采集规则</h3>
              <div className="grid gap-2">
                {[
                  "保存正文、引用链、图片、视频链接和作者头像",
                  "YouTube / TikTok 视频进入下载和转写队列",
                  "重复链接 72 小时内自动合并，保留最高评分版本",
                ].map((rule) => (
                  <div
                    key={rule}
                    className="flex items-center gap-2.5 rounded-lg bg-muted/40 px-3.5 py-2.5 text-sm text-foreground/90"
                  >
                    <CheckCircle2 className="size-[18px] shrink-0 text-success" />
                    {rule}
                  </div>
                ))}
              </div>
            </div>

            <div className="space-y-3">
              <h3 className="text-[15px] font-semibold text-foreground">运行记录</h3>
              <div className="overflow-hidden rounded-xl border">
                {(remoteSources.length && !isPlaceholder ? runs.map(runToRow) : demoRuns).map((r, i) => (
                  <div
                    key={r.id || r.time}
                    className={cn(
                      "flex items-center gap-4 px-4 py-3.5 text-sm transition-colors hover:bg-muted/40",
                      i > 0 && "border-t"
                    )}
                  >
                    <span className={cn("size-2 shrink-0 rounded-full", r.ok ? "bg-success" : "bg-muted-foreground/50")} />
                    <span className="w-12 shrink-0 font-medium text-foreground tnum">{r.time}</span>
                    <span className="flex-1 text-foreground/90">{r.text}</span>
                    <span className="shrink-0 text-muted-foreground tnum">耗时 {r.cost}</span>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="shrink-0 text-primary"
                      disabled={!r.run}
                      onClick={() => r.run && openLog(r.run)}
                    >
                      查看日志
                    </Button>
                  </div>
                ))}
              </div>
              {remoteSources.length > 0 && !isPlaceholder && runs.length === 0 && (
                <p className="rounded-lg bg-muted/40 px-3.5 py-2.5 text-sm text-muted-foreground">
                  还没有运行记录
                </p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      <Dialog open={Boolean(logRun)} onOpenChange={(open) => !open && setLogRun(null)}>
        <DialogContent className="sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>
              运行日志
              {logRun && (
                <span className="ml-2 text-sm font-normal text-muted-foreground">
                  {new Date(logRun.started_at).toLocaleString("zh-CN")} · 采集 {logRun.items_collected} 条
                </span>
              )}
            </DialogTitle>
          </DialogHeader>
          <div className="max-h-[60vh] space-y-3 overflow-y-auto">
            {logLoading && <p className="text-sm text-muted-foreground">正在加载采集内容...</p>}
            {!logLoading && logPosts.length === 0 && (
              <p className="text-sm text-muted-foreground">
                这次运行没有可展示的帖子内容（可能是旧记录或采集为空）。
              </p>
            )}
            {logPosts.map((post) => (
              <div key={post.content_hash} className="flex gap-3 rounded-xl border bg-card p-3.5">
                {post.author_avatar_url ? (
                  <img
                    src={post.author_avatar_url}
                    alt={post.author_handle}
                    className="size-9 shrink-0 rounded-full object-cover"
                  />
                ) : (
                  <span className="grid size-9 shrink-0 place-items-center rounded-full bg-muted text-xs">
                    {(post.author_handle || "?").slice(0, 2)}
                  </span>
                )}
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 text-sm">
                    <span className="font-semibold text-foreground">{post.author_name || post.author_handle}</span>
                    <span className="text-muted-foreground">@{post.author_handle}</span>
                    <span className="text-muted-foreground">·</span>
                    <span className="text-muted-foreground">{post.published_at_raw || post.published_at || ""}</span>
                  </div>
                  <p className="mt-1 whitespace-pre-wrap text-sm text-foreground/90">{post.text}</p>
                  {Array.isArray(post.image_urls) && post.image_urls.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-2">
                      {post.image_urls.map((src) => (
                        <img key={src} src={src} alt="" className="h-20 w-20 rounded-lg object-cover" />
                      ))}
                    </div>
                  )}
                  <div className="mt-2 flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
                    {post.url && (
                      <a href={post.url} target="_blank" rel="noreferrer" className="text-primary hover:underline">
                        原帖链接
                      </a>
                    )}
                    {post.metrics?.likes != null && <span>♥ {post.metrics.likes}</span>}
                    {post.metrics?.reposts != null && <span>↺ {post.metrics.reposts}</span>}
                    {post.metrics?.replies != null && <span>💬 {post.metrics.replies}</span>}
                    <span className="truncate">hash {String(post.content_hash).slice(0, 10)}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

const demoRuns = [
  { time: "20:30", text: "成功采集 84 条", cost: "02:18", ok: true },
  { time: "20:00", text: "成功采集 69 条", cost: "02:18", ok: true },
  { time: "19:30", text: "跳过重复 14 条", cost: "00:42", ok: false },
];

function sourceToRow(source) {
  return {
    id: source.id,
    name: source.name,
    slug: source.platform === "x" ? "x" : source.platform,
    status: source.enabled ? "运行中" : "已停用",
    cadence: `每 ${source.cadence_minutes} 分钟`,
    accounts: source.account_count,
    lastRun: "等待运行",
    ingest: source.targets?.join(" / ") || "未配置账号",
  };
}

function runToRow(run) {
  const ok = run.status === "success";
  const newMatch = /new=(\d+)/.exec(run.message || "");
  const newPart = ok && newMatch ? `（新增 ${newMatch[1]} 条）` : "";
  return {
    id: run.id,
    run,
    time: new Date(run.started_at).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" }),
    text: ok ? `成功采集 ${run.items_collected} 条${newPart}` : run.message || "运行失败",
    cost: elapsed(run.started_at, run.finished_at),
    ok,
  };
}

function elapsed(startedAt, finishedAt) {
  const seconds = Math.max(0, Math.round((new Date(finishedAt) - new Date(startedAt)) / 1000));
  const minutes = String(Math.floor(seconds / 60)).padStart(2, "0");
  const rest = String(seconds % 60).padStart(2, "0");
  return `${minutes}:${rest}`;
}
