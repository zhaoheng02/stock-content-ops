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
  const [runPage, setRunPage] = useState(0);
  const [runTotal, setRunTotal] = useState(0);
  const runPageSize = 5;

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
    ? `${new Date(runs[0].started_at).toLocaleString("zh-CN", { year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" })}`
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
      setRunTotal(0);
      return;
    }
    let active = true;
    fetch(`${API_BASE}/api/source-runs?source_id=${encodeURIComponent(current.id)}&limit=${runPageSize}&offset=${runPage * runPageSize}`)
      .then((r) => r.json())
      .then((p) => {
        if (!active) return;
        setRuns(p.runs || []);
        setRunTotal(Number(p.total || 0));
      })
      .catch(() => {
        if (!active) return;
        setRuns([]);
        setRunTotal(0);
      });
    return () => { active = false; };
  }, [current?.id, remoteSources.length, isPlaceholder, runPage]);

  useEffect(() => {
    setRunPage(0);
  }, [current?.id]);

  const runNow = async () => {
    if (!currentRemote) return;
    setRunning(true);
    setApiError("");
    try {
      const payload = await api.post("/api/source-runs", { source_id: current.id });
      setRunPage(0);
      setRuns((items) => [payload.run, ...items]);
      setRunTotal((total) => total + 1);
    } catch (error) {
      setApiError(error.message);
    } finally {
      setRunning(false);
    }
  };

  // Auto-reconcile pending Airtap runs: while any run is pending, poll the
  // reconcile endpoint and refresh the run list until it resolves.
  const hasPending = runs.some((r) => r.status === "pending");
  useEffect(() => {
    if (!hasPending || !current?.id || isPlaceholder) return;
    let active = true;
    const tick = async () => {
      try {
        await api.get("/api/cron");
        const payload = await api.get(`/api/source-runs?source_id=${encodeURIComponent(current.id)}&limit=${runPageSize}&offset=${runPage * runPageSize}`);
        if (active) {
          setRuns(payload.runs || []);
          setRunTotal(Number(payload.total || 0));
        }
      } catch {
        /* keep polling */
      }
    };
    const timer = setInterval(tick, 12000);
    tick();
    return () => { active = false; clearInterval(timer); };
  }, [hasPending, current?.id, isPlaceholder, runPage]);

  const pageCount = Math.max(1, Math.ceil(runTotal / runPageSize));

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
        description="统一管理海外内容源的采集频率、账号资料和运行记录。"
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
            <Button variant="outline" className="w-28 shrink-0 gap-1.5" onClick={runNow} disabled={isPlaceholder || !currentRemote || running || hasPending}>
              {running || hasPending ? <Loader2 className="size-4 animate-spin" /> : <Play className="size-4" />}
              {hasPending ? "采集中" : running ? "运行中" : "立即运行"}
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
                    <div
                      key={r.id}
                      className={cn(
                        "grid grid-cols-[12px_150px_minmax(0,1fr)_88px_84px] items-center gap-3 px-4 py-3.5 text-sm transition-colors hover:bg-muted/40",
                        i > 0 && "border-t"
                      )}
                    >
                      <span className={cn("size-2 rounded-full", r.pending ? "bg-warning animate-pulse" : r.ok ? "bg-success" : "bg-muted-foreground/50")} />
                      <span className="font-medium text-foreground tnum">{r.time}</span>
                      <span className="min-w-0 truncate text-foreground/90" title={r.text}>{r.text}</span>
                      <span className="text-muted-foreground tnum">耗时 {r.cost}</span>
                      <Button variant="ghost" size="sm" className="text-primary" disabled={!r.run || r.pending} onClick={() => r.run && openLog(r.run)}>
                        查看日志
                      </Button>
                    </div>
                  ))}
                </div>
              )}
              {currentRemote && !isPlaceholder && runTotal > runPageSize && (
                <div className="flex items-center justify-between gap-3 text-sm text-muted-foreground">
                  <span className="tnum">第 {runPage + 1} / {pageCount} 页，共 {runTotal} 条</span>
                  <div className="flex items-center gap-2">
                    <Button variant="outline" size="sm" onClick={() => setRunPage((p) => Math.max(0, p - 1))} disabled={runPage === 0}>
                      上一页
                    </Button>
                    <Button variant="outline" size="sm" onClick={() => setRunPage((p) => Math.min(pageCount - 1, p + 1))} disabled={runPage >= pageCount - 1}>
                      下一页
                    </Button>
                  </div>
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
  const [cadence, setCadence] = useState(30);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (open && source) {
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
        targets: (source.targets || []).join(", "),
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
        <div className="space-y-4 py-1">
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
          <Button onClick={save} disabled={saving}>
            {saving && <Loader2 className="mr-1.5 size-4 animate-spin" />}保存配置
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function AccountsDialog({ open, onClose, source }) {
  const [profiles, setProfiles] = useState({});
  const [targets, setTargets] = useState("");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const handles = source?.targets || [];

  const loadAccounts = () => {
    if (!source?.id) return Promise.resolve();
    setLoading(true);
    setError("");
    return api.get(`/api/source-accounts?source_id=${encodeURIComponent(source.id)}`)
      .then((p) => {
        const byHandle = {};
        for (const account of p.accounts || []) {
          const h = (account.handle || "").toLowerCase();
          if (h && !byHandle[h]) {
            byHandle[h] = {
              handle: account.handle,
              name: account.author_name,
              avatar: account.avatar_url,
              lastPostAt: account.last_post_at,
              onboardedAt: account.onboarded_at,
              bio: account.bio,
            };
          }
        }
        setProfiles(byHandle);
      })
      .catch((err) => {
        setProfiles({});
        setError(err.message || "账号资料加载失败");
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    if (!open || !source?.id) return;
    setTargets((source.targets || []).join(", "));
    loadAccounts();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, source?.id]);

  const save = async () => {
    if (!source?.id) return;
    setSaving(true);
    setError("");
    try {
      const payload = await api.post("/api/source-accounts", {
        source_id: source.id,
        targets,
      });
      window.dispatchEvent(new CustomEvent("sources:changed", { detail: payload.source }));
      setTargets((payload.source?.targets || []).join(", "));
      await loadAccounts();
    } catch (err) {
      setError(err.message || "账号保存失败");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>监控账号 · {handles.length} 个</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-1.5">
            <Label className="text-xs text-muted-foreground">监控账号（逗号或换行分隔，可加 @）</Label>
            <Textarea
              value={targets}
              onChange={(e) => setTargets(e.target.value)}
              className="min-h-24"
              placeholder="@ArtofSpecuycky, @hanking66, @xiaomustock"
            />
          </div>
          {error && <p className="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</p>}
          <div className="overflow-hidden rounded-lg border">
            <div className="grid grid-cols-[minmax(180px,1.2fr)_minmax(120px,0.8fr)_minmax(160px,1fr)] gap-3 border-b bg-muted/40 px-3 py-2 text-xs font-medium text-muted-foreground">
              <span>账号</span>
              <span>头像状态</span>
              <span>最近采集</span>
            </div>
            <div className="max-h-[42vh] overflow-y-auto">
              {loading && <p className="px-3 py-3 text-sm text-muted-foreground">正在加载账号信息...</p>}
              {!loading && handles.map((handle) => {
                const key = String(handle).toLowerCase().replace(/^@/, "");
                const prof = (profiles || {})[key] || (profiles || {})[`@${key}`] || {};
                return (
                  <div key={handle} className="grid grid-cols-[minmax(180px,1.2fr)_minmax(120px,0.8fr)_minmax(160px,1fr)] items-center gap-3 border-b px-3 py-3 last:border-b-0">
                    <div className="flex min-w-0 items-center gap-3">
                      {prof.avatar ? (
                        <img src={prof.avatar} alt={handle} className="size-10 shrink-0 rounded-full object-cover" />
                      ) : (
                        <span className="grid size-10 shrink-0 place-items-center rounded-full bg-muted text-sm font-medium text-muted-foreground">
                          {String(handle).replace(/^@/, "").slice(0, 2)}
                        </span>
                      )}
                      <div className="min-w-0">
                        <p className="truncate text-sm font-semibold text-foreground">{prof.name || String(handle).replace(/^@/, "")}</p>
                        <p className="truncate text-xs text-muted-foreground">@{String(handle).replace(/^@/, "")}</p>
                      </div>
                    </div>
                    <span className={cn("text-sm", prof.avatar ? "text-success" : "text-warning-foreground")}>
                      {prof.avatar ? "已保存" : "待获取"}
                    </span>
                    <span className="text-sm text-muted-foreground">
                      {prof.lastPostAt ? new Date(prof.lastPostAt).toLocaleString("zh-CN") : "—"}
                    </span>
                  </div>
                );
              })}
              {!loading && !handles.length && (
                <p className="px-3 py-3 text-sm text-muted-foreground">尚未配置监控账号。</p>
              )}
            </div>
          </div>
          <div className="flex items-start gap-2 rounded-lg bg-muted/50 px-3 py-2.5 text-xs text-muted-foreground">
            <AlertCircle className="mt-0.5 size-3.5 shrink-0" />
            <span>
              新增账号会创建一次 Airtap 头像获取任务，完成后头像会永久保存；后续帖子采集只复用已保存头像。
            </span>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>关闭</Button>
          <Button onClick={save} disabled={saving || !targets.trim()}>
            {saving && <Loader2 className="mr-1.5 size-4 animate-spin" />}保存账号
          </Button>
        </DialogFooter>
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
  const pending = run.status === "pending";
  const profile = run.kind === "profile";
  const newMatch = /new=(\d+)/.exec(run.message || "");
  const profileMatch = /profiles=(\d+)/.exec(run.message || "");
  const newPart = ok && newMatch ? `（新增 ${newMatch[1]} 条）` : "";
  let text;
  if (pending && profile) text = "获取头像中… Airtap 云手机正在读取账号资料";
  else if (pending) text = "采集中… Airtap 云手机正在抓取";
  else if (ok && profile) text = `头像资料已保存 ${profileMatch ? profileMatch[1] : run.items_collected} 个`;
  else if (ok) text = `成功采集 ${run.items_collected} 条${newPart}`;
  else text = run.message || "运行失败";
  return {
    id: run.id,
    run,
    pending,
    time: new Date(run.started_at).toLocaleString("zh-CN", { year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" }),
    text,
    cost: pending ? "—" : elapsed(run.started_at, run.finished_at),
    ok,
  };
}

function elapsed(startedAt, finishedAt) {
  const seconds = Math.max(0, Math.round((new Date(finishedAt) - new Date(startedAt)) / 1000));
  const minutes = String(Math.floor(seconds / 60)).padStart(2, "0");
  const rest = String(seconds % 60).padStart(2, "0");
  return `${minutes}:${rest}`;
}
