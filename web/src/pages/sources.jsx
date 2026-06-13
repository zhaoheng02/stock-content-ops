import {
  Activity,
  AlertCircle,
  Clock3,
  Loader2,
  Play,
  UserRound,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { PageHeader } from "@/components/app/page-header";
import { StatusBadge } from "@/components/app/status-badge";
import { BrandIcon } from "@/components/app/brand-icon";
import { cn } from "@/lib/utils";
import { sourceRows } from "@/data/mock";
import { API_BASE, api } from "@/lib/api";

const CADENCE_OPTIONS = [
  [30, "每 30 分钟"],
  [60, "每 1 小时"],
  [120, "每 2 小时"],
  [180, "每 3 小时"],
  [360, "每 6 小时"],
  [720, "每 12 小时"],
  [1440, "每 24 小时"],
];

function cadenceLabel(minutes) {
  const found = CADENCE_OPTIONS.find(([m]) => m === Number(minutes));
  if (found) return found[1];
  if (minutes % 60 === 0) return `每 ${minutes / 60} 小时`;
  return `每 ${minutes} 分钟`;
}

export function SourcesPage({ selectedSource, setSelectedSource }) {
  const [remoteSources, setRemoteSources] = useState([]);
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [apiError, setApiError] = useState("");
  const [logRun, setLogRun] = useState(null);
  const [logPosts, setLogPosts] = useState([]);
  const [logLoading, setLogLoading] = useState(false);
  const [configOpen, setConfigOpen] = useState(false);
  const [accountsOpen, setAccountsOpen] = useState(false);

  const sources = useMemo(() => {
    const remoteRows = remoteSources.map(sourceToRow);
    const remotePlatforms = new Set(remoteSources.map((s) => s.platform));
    const placeholders = sourceRows
      .filter((row) => !remotePlatforms.has(row.slug))
      .map((row) => ({ ...row, placeholder: true }));
    return [...remoteRows, ...placeholders];
  }, [remoteSources]);

  const current = sources.find((s) => s.id === selectedSource) || sources[0];
  const isPlaceholder = Boolean(current?.placeholder);
  const currentRemote = remoteSources.find((s) => s.id === current?.id);

  const lastRunText = runs.length
    ? `${new Date(runs[0].started_at).toLocaleString("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" })}`
    : (isPlaceholder ? "未接入" : "等待运行");

  const config = [
    ["采集频率", current ? cadenceLabel(currentRemote?.cadence_minutes ?? 30) : "—", Clock3, () => !isPlaceholder && setConfigOpen(true)],
    ["监控账号", `${current?.accounts ?? 0} 个`, UserRound, () => !isPlaceholder && setAccountsOpen(true)],
    ["上次运行", lastRunText, Activity, null],
  ];

  const loadSources = async () => {
    setLoading(true);
    try {
      const payload = await api.get("/api/sources");
      const remote = payload.sources || [];
      setRemoteSources(remote);
      setApiError("");
      const validIds = new Set([...remote.map((i) => i.id), ...sourceRows.map((r) => r.id)]);
      if (!validIds.has(selectedSource)) setSelectedSource(remote[0]?.id || sourceRows[0]?.id);
    } catch {
      setRemoteSources([]);
      setApiError("本地服务未连接，正在显示示例数据");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSources();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!remoteSources.length || !current?.id || isPlaceholder) {
      setRuns([]);
      return;
    }
    let active = true;
    fetch(`${API_BASE}/api/source-runs?source_id=${encodeURIComponent(current.id)}&limit=8`)
      .then((r) => r.json())
      .then((p) => active && setRuns(p.runs || []))
      .catch(() => active && setRuns([]));
    return () => { active = false; };
  }, [current?.id, remoteSources.length, isPlaceholder]);

  const runNow = async () => {
    if (!currentRemote) return;
    setRunning(true);
    setApiError("");
    try {
      const payload = await api.post("/api/source-runs", { source_id: current.id, out: "/tmp/inbox" });
      setRuns((items) => [payload.run, ...items]);
    } catch (error) {
      setApiError(error.message);
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
      const payload = await api.get(`/api/source-posts?run_id=${encodeURIComponent(run.id)}`);
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
          <Button onClick={() => !isPlaceholder && setConfigOpen(true)} disabled={isPlaceholder}>
            数据源配置
          </Button>
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
                selectedSource === s.id ? "border-primary shadow-sm ring-1 ring-primary/30" : "hover:border-primary/40 hover:shadow-sm"
              )}
            >
              <span className="grid size-11 shrink-0 place-items-center rounded-xl border bg-background">
                <BrandIcon slug={s.slug} className="size-5" />
              </span>
              <span className="min-w-0 flex-1">
                <span className="flex items-center justify-between gap-2">
                  <span className="truncate text-[15px] font-semibold text-foreground">{s.name}</span>
                  {s.placeholder ? (
                    <span className="shrink-0 rounded-full border border-dashed px-2 py-0.5 text-[11px] text-muted-foreground">未接入</span>
                  ) : (
                    <StatusBadge state={s.status} className="shrink-0" />
                  )}
                </span>
                <span className="mt-1 block truncate text-[13px] leading-relaxed text-muted-foreground">{s.ingest}</span>
              </span>
            </button>
          ))}
        </div>

        <Card className="min-w-0">
          <CardHeader className="flex-row items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-3">
              <span className="grid size-10 shrink-0 place-items-center rounded-xl border bg-background">
                <BrandIcon slug={current?.slug} className="size-5" />
              </span>
              <div className="min-w-0">
                <CardTitle className="truncate text-lg">{current?.name} 采集配置</CardTitle>
                <p className="mt-0.5 text-sm text-muted-foreground">实时运行状态与采集调度</p>
              </div>
            </div>
            <Button variant="outline" className="w-28 shrink-0 gap-1.5" onClick={runNow} disabled={isPlaceholder || !currentRemote || running}>
              {running ? <Loader2 className="size-4 animate-spin" /> : <Play className="size-4" />}
              {running ? "运行中" : "立即运行"}
            </Button>
          </CardHeader>
          <CardContent className="space-y-6">
            {isPlaceholder && (
              <div className="flex items-center gap-2 rounded-lg border border-dashed bg-muted/30 px-3.5 py-2.5 text-sm text-muted-foreground">
                <AlertCircle className="size-4 shrink-0" />
                <span>{current?.name} 采集尚未接入后端，目前为示例展示，暂不可运行。</span>
              </div>
            )}
            <div className="grid gap-3 sm:grid-cols-3">
              {config.map(([label, value, Icon, onClick]) => (
                <button
                  key={label}
                  type="button"
                  onClick={onClick || undefined}
                  disabled={!onClick}
                  className={cn(
                    "rounded-xl border bg-muted/30 p-4 text-left transition-colors",
                    onClick ? "hover:border-primary/40 hover:bg-muted/50 cursor-pointer" : "cursor-default"
                  )}
                >
                  <span className="grid size-9 place-items-center rounded-lg bg-primary/10 text-primary">
                    <Icon className="size-[18px]" />
                  </span>
                  <p className="mt-3 text-[13px] text-muted-foreground">{label}{onClick ? " · 点击调整" : ""}</p>
                  <p className="mt-1 text-base font-semibold text-foreground">{value}</p>
                </button>
              ))}
            </div>

            <div className="space-y-3">
              <h3 className="text-[15px] font-semibold text-foreground">运行记录</h3>
              {(!currentRemote || isPlaceholder) ? (
                <p className="rounded-lg bg-muted/40 px-3.5 py-2.5 text-sm text-muted-foreground">该数据源尚未接入，暂无运行记录。</p>
              ) : runs.length === 0 ? (
                <p className="rounded-lg bg-muted/40 px-3.5 py-2.5 text-sm text-muted-foreground">还没有运行记录，点击右上角“立即运行”触发一次采集。</p>
              ) : (
                <div className="overflow-hidden rounded-xl border">
                  {runs.map(runToRow).map((r, i) => (
                    <div key={r.id} className={cn("flex items-center gap-4 px-4 py-3.5 text-sm transition-colors hover:bg-muted/40", i > 0 && "border-t")}>
                      <span className={cn("size-2 shrink-0 rounded-full", r.ok ? "bg-success" : "bg-muted-foreground/50")} />
                      <span className="w-12 shrink-0 font-medium text-foreground tnum">{r.time}</span>
                      <span className="flex-1 text-foreground/90">{r.text}</span>
                      <span className="shrink-0 text-muted-foreground tnum">耗时 {r.cost}</span>
                      <Button variant="ghost" size="sm" className="shrink-0 text-primary" disabled={!r.run} onClick={() => r.run && openLog(r.run)}>
                        查看日志
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {currentRemote && (
        <SourceConfigDialog
          open={configOpen}
          onClose={() => setConfigOpen(false)}
          source={currentRemote}
          onSaved={(saved) => { setConfigOpen(false); loadSources().then(() => setSelectedSource(saved.id)); }}
        />
      )}

      <AccountsDialog
        open={accountsOpen}
        onClose={() => setAccountsOpen(false)}
        source={currentRemote}
      />

      <LogDialog logRun={logRun} setLogRun={setLogRun} logPosts={logPosts} logLoading={logLoading} />
    </div>
  );
}

function SourceConfigDialog({ open, onClose, source, onSaved }) {
  const [targets, setTargets] = useState("");
  const [cadence, setCadence] = useState(30);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (open && source) {
      setTargets((source.targets || []).join(", "));
      setCadence(source.cadence_minutes || 30);
      setError("");
    }
  }, [open, source]);

  const save = async () => {
    setSaving(true);
    setError("");
    try {
      const payload = await api.post("/api/sources", {
        id: source.id,
        name: source.name,
        platform: source.platform,
        cadence_minutes: Number(cadence),
        targets,
      });
      window.dispatchEvent(new CustomEvent("sources:changed", { detail: payload.source }));
      onSaved(payload.source);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>数据源配置 · {source?.name}</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-1.5">
            <Label className="text-xs text-muted-foreground">监控账号（逗号或换行分隔，可加 @）</Label>
            <Textarea
              value={targets}
              onChange={(e) => setTargets(e.target.value)}
              className="min-h-28"
              placeholder="@ArtofSpecuycky, @hanking66, @xiaomustock"
            />
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs text-muted-foreground">采集频率（最小 30 分钟，最大 24 小时）</Label>
            <Select value={String(cadence)} onValueChange={(v) => setCadence(Number(v))}>
              <SelectTrigger className="w-full"><SelectValue /></SelectTrigger>
              <SelectContent>
                {CADENCE_OPTIONS.map(([m, label]) => (
                  <SelectItem key={m} value={String(m)}>{label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex items-start gap-2 rounded-lg bg-muted/50 px-3 py-2.5 text-xs text-muted-foreground">
            <AlertCircle className="mt-0.5 size-3.5 shrink-0" />
            <span>采集默认全量保存图片和视频。保存后定时任务会按此频率自动调度 Airtap 采集，也可随时点“立即运行”手动触发。</span>
          </div>
          {error && <p className="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</p>}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>取消</Button>
          <Button onClick={save} disabled={saving || !targets.trim()}>
            {saving && <Loader2 className="mr-1.5 size-4 animate-spin" />}保存配置
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function AccountsDialog({ open, onClose, source }) {
  const [profiles, setProfiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const handles = source?.targets || [];

  useEffect(() => {
    if (!open || !source?.id) return;
    setLoading(true);
    api.get(`/api/source-posts?source_id=${encodeURIComponent(source.id)}&limit=200`)
      .then((p) => {
        const byHandle = {};
        for (const post of p.posts || []) {
          const h = (post.author_handle || "").toLowerCase();
          if (h && !byHandle[h]) {
            byHandle[h] = {
              handle: post.author_handle,
              name: post.author_name,
              avatar: post.author_avatar_url,
            };
          }
        }
        setProfiles(byHandle);
      })
      .catch(() => setProfiles({}))
      .finally(() => setLoading(false));
  }, [open, source?.id]);

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>监控账号 · {handles.length} 个</DialogTitle>
        </DialogHeader>
        <div className="max-h-[60vh] space-y-2 overflow-y-auto">
          {loading && <p className="text-sm text-muted-foreground">正在加载账号信息...</p>}
          {handles.map((handle) => {
            const key = String(handle).toLowerCase().replace(/^@/, "");
            const prof = (profiles || {})[key] || (profiles || {})[`@${key}`] || {};
            return (
              <div key={handle} className="flex items-center gap-3 rounded-xl border bg-card p-3">
                {prof.avatar ? (
                  <img src={prof.avatar} alt={handle} className="size-10 shrink-0 rounded-full object-cover" />
                ) : (
                  <span className="grid size-10 shrink-0 place-items-center rounded-full bg-muted text-sm">
                    {String(handle).replace(/^@/, "").slice(0, 2)}
                  </span>
                )}
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold text-foreground">{prof.name || String(handle).replace(/^@/, "")}</p>
                  <p className="truncate text-xs text-muted-foreground">@{String(handle).replace(/^@/, "")}</p>
                </div>
              </div>
            );
          })}
          {!handles.length && <p className="text-sm text-muted-foreground">尚未配置监控账号。</p>}
        </div>
      </DialogContent>
    </Dialog>
  );
}

function LogDialog({ logRun, setLogRun, logPosts, logLoading }) {
  return (
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
          {logRun?.status === "failed" && (
            <p className="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">{logRun.message}</p>
          )}
          {logLoading && <p className="text-sm text-muted-foreground">正在加载采集内容...</p>}
          {!logLoading && logPosts.length === 0 && logRun?.status !== "failed" && (
            <p className="text-sm text-muted-foreground">这次运行没有可展示的帖子内容（可能是旧记录或采集为空）。</p>
          )}
          {logPosts.map((post) => (
            <div key={post.content_hash} className="flex gap-3 rounded-xl border bg-card p-3.5">
              {post.author_avatar_url ? (
                <img src={post.author_avatar_url} alt={post.author_handle} className="size-9 shrink-0 rounded-full object-cover" />
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
                  {post.url && <a href={post.url} target="_blank" rel="noreferrer" className="text-primary hover:underline">原帖链接</a>}
                  {post.metrics?.likes != null && <span>♥ {post.metrics.likes}</span>}
                  {post.metrics?.reposts != null && <span>↺ {post.metrics.reposts}</span>}
                  {post.metrics?.replies != null && <span>💬 {post.metrics.replies}</span>}
                </div>
              </div>
            </div>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  );
}

function sourceToRow(source) {
  return {
    id: source.id,
    name: source.name,
    slug: source.platform === "x" ? "x" : source.platform,
    status: source.enabled ? "运行中" : "已停用",
    cadence: `每 ${source.cadence_minutes} 分钟`,
    accounts: source.account_count,
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
