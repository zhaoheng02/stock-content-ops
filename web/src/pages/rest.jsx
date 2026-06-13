import { useEffect, useState, useCallback } from "react";
import { Activity, BarChart3, Download, Loader2, MessageSquareText, Plus, RefreshCw, Send, Trash2 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { PageHeader } from "@/components/app/page-header";
import { Metric } from "@/components/app/metric";
import { StatusBadge } from "@/components/app/status-badge";
import { BrandIcon } from "@/components/app/brand-icon";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";
import { platformPalette } from "@/data/mock";

const PLATFORM_LABEL = {
  xiaohongshu: "小红书",
  wechat_article: "公众号",
  video_account: "视频号",
  douyin_script: "抖音",
};

const STATUS_LABEL = {
  draft: "草稿",
  needs_review: "待确认",
  approved: "待发布",
  rejected: "待修改",
  scheduled: "定时队列",
  published: "已发布",
  failed: "失败重试",
};

function useResource(loader, deps = []) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const reload = useCallback(() => {
    setLoading(true);
    setError("");
    loader()
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  useEffect(() => {
    reload();
  }, [reload]);
  return { data, loading, error, reload, setData };
}

function Loading() {
  return (
    <div className="flex items-center justify-center gap-2 py-12 text-muted-foreground">
      <Loader2 className="size-4 animate-spin" /> 加载中...
    </div>
  );
}

function EmptyHint({ children }) {
  return <div className="px-4 py-10 text-center text-sm text-muted-foreground">{children}</div>;
}

function ErrorHint({ children }) {
  return <div className="px-4 py-10 text-center text-sm text-destructive">{children}</div>;
}

function TabsRow({ tabs, value, onChange }) {
  return (
    <Tabs value={value} onValueChange={onChange}>
      <TabsList>
        {tabs.map((t) => (
          <TabsTrigger key={t} value={t}>{t}</TabsTrigger>
        ))}
      </TabsList>
    </Tabs>
  );
}

/* ------------------------------ Publish ------------------------------ */

export function PublishPage({ setActive }) {
  const VIEW_TABS = ["发布记录", "草稿箱", "定时队列", "失败重试"];
  const [tab, setTab] = useState("发布记录");
  const { data, loading, error, reload } = useResource(
    () => api.get("/api/drafts?limit=200").then((d) => d.drafts || []),
    []
  );

  const filtered = (data || []).filter((row) => {
    if (tab === "发布记录") return ["published", "approved", "scheduled"].includes(row.status);
    if (tab === "草稿箱") return ["draft", "needs_review", "rejected"].includes(row.status);
    if (tab === "定时队列") return row.status === "scheduled";
    if (tab === "失败重试") return row.status === "failed";
    return true;
  });

  const publish = async (row) => {
    await api.patch("/api/drafts", { id: row.id, status: "published" });
    reload();
  };
  const retry = async (row) => {
    await api.patch("/api/drafts", { id: row.id, status: "approved", publish_error: "" });
    reload();
  };

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="发布"
        title="发布记录与草稿箱"
        description="统一管理小红书、公众号、视频号、抖音等平台的发布任务。数据来自创作页生成并落库的真实草稿。"
        actions={
          <>
            <Button variant="outline" className="gap-1.5" onClick={reload}><RefreshCw className="size-4" />刷新</Button>
            <Button onClick={() => setActive?.("studio")} className="gap-1.5"><Plus className="size-4" />去创作生成</Button>
          </>
        }
      />
      <TabsRow tabs={VIEW_TABS} value={tab} onChange={setTab} />
      <Card className="py-0">
        <CardContent className="px-0">
          {loading ? <Loading /> : error ? <ErrorHint>{error}</ErrorHint> : filtered.length === 0 ? (
            <EmptyHint>暂无内容。去“创作”页选择来源并批量生成，会自动写入这里。</EmptyHint>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>作品</TableHead><TableHead>平台</TableHead>
                  <TableHead>负责人</TableHead><TableHead>状态</TableHead><TableHead>更新时间</TableHead>
                  <TableHead className="text-right">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filtered.map((row) => (
                  <TableRow key={row.id}>
                    <TableCell className="max-w-sm truncate font-semibold text-foreground">{row.title}</TableCell>
                    <TableCell className="text-muted-foreground">{PLATFORM_LABEL[row.platform] || row.platform}</TableCell>
                    <TableCell className="text-muted-foreground">{row.owner}</TableCell>
                    <TableCell><StatusBadge state={STATUS_LABEL[row.status] || row.status} /></TableCell>
                    <TableCell className="text-muted-foreground">{formatTime(row.updated_at)}</TableCell>
                    <TableCell className="space-x-2 text-right">
                      {row.status === "failed" ? (
                        <Button variant="ghost" size="sm" className="text-primary" onClick={() => retry(row)}>重试</Button>
                      ) : row.status !== "published" ? (
                        <Button variant="ghost" size="sm" className="text-primary" onClick={() => publish(row)}>发布</Button>
                      ) : (
                        <span className="text-xs text-muted-foreground">已发布</span>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

/* ------------------------------ Review ------------------------------ */

export function ReviewPage() {
  const { data, loading, error, reload } = useResource(
    () => api.get("/api/drafts?status=needs_review&limit=100").then((d) => d.drafts || []),
    []
  );
  const decide = async (row, status) => {
    await api.patch("/api/drafts", { id: row.id, status });
    reload();
  };

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="审批"
        title="发布前确认队列"
        description="每条内容先给出 AI 分析、来源证据和正文，再由你确认是否发布。"
        actions={<Button variant="outline" className="gap-1.5" onClick={reload}><RefreshCw className="size-4" />刷新</Button>}
      />
      {loading ? <Loading /> : error ? <ErrorHint>{error}</ErrorHint> : (data || []).length === 0 ? (
        <Card><CardContent className="pt-6"><EmptyHint>审批队列为空。去“创作”生成草稿后会进入这里待确认。</EmptyHint></CardContent></Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {data.map((row) => (
            <Card key={row.id}>
              <CardContent className="space-y-3 pt-6">
                <div className="flex items-center gap-2">
                  <span className="grid size-8 place-items-center rounded-lg bg-primary/10 text-xs font-medium text-primary">
                    {(PLATFORM_LABEL[row.platform] || "?").slice(0, 2)}
                  </span>
                  <strong className="text-sm font-semibold text-foreground">{PLATFORM_LABEL[row.platform] || row.platform}</strong>
                  <StatusBadge state="待确认" className="ml-auto" />
                </div>
                <h3 className="line-clamp-2 text-sm font-semibold text-foreground">{row.title}</h3>
                {row.ai_analysis && (
                  <p className="line-clamp-3 text-sm leading-relaxed text-muted-foreground">AI 分析：{row.ai_analysis}</p>
                )}
                {row.source_url && (
                  <a href={row.source_url} target="_blank" rel="noreferrer" className="block text-xs text-muted-foreground hover:text-primary">查看原文</a>
                )}
                <div className="flex gap-2 pt-1">
                  <Button variant="outline" size="sm" className="flex-1" onClick={() => decide(row, "rejected")}>退回修改</Button>
                  <Button size="sm" className="flex-1" onClick={() => decide(row, "approved")}>确认发布</Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

/* ------------------------------ Accounts ------------------------------ */

export function AccountsPage({ openModal }) {
  const { data, loading, error, reload } = useResource(
    () => api.get("/api/accounts").then((d) => d.accounts || []),
    []
  );
  const remove = async (row) => {
    await api.del(`/api/accounts?id=${encodeURIComponent(row.id)}`);
    reload();
  };
  useEffect(() => {
    const handler = () => reload();
    window.addEventListener("accounts:changed", handler);
    return () => window.removeEventListener("accounts:changed", handler);
  }, [reload]);

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="账号"
        title="发布账号授权"
        description="管理国内发布账号，也保留海外来源账号的登录状态和网络环境。"
        actions={<Button onClick={() => openModal("accountAuth")} className="gap-1.5"><Plus className="size-4" />添加账号</Button>}
      />
      <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-3 lg:grid-cols-5">
        {platformPalette.map((p) => (
          <div
            key={p.name}
            className="flex flex-col items-center gap-2.5 rounded-xl border bg-card p-4"
          >
            <span className="grid size-10 place-items-center rounded-xl border bg-background">
              <BrandIcon slug={p.slug} className="size-5" />
            </span>
            <strong className="text-sm font-medium text-foreground">{p.name}</strong>
          </div>
        ))}
      </div>
      <Card className="py-0">
        <CardContent className="px-0">
          {loading ? <Loading /> : error ? <ErrorHint>{error}</ErrorHint> : (data || []).length === 0 ? (
            <EmptyHint>还没有授权账号。点击右上角“添加账号”创建。</EmptyHint>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>平台</TableHead><TableHead>账号</TableHead><TableHead>状态</TableHead>
                  <TableHead>发布模式</TableHead><TableHead>代理</TableHead>
                  <TableHead className="text-right">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.map((a) => (
                  <TableRow key={a.id}>
                    <TableCell>
                      <span className="flex items-center gap-2.5 text-foreground">
                        <span className="grid size-7 shrink-0 place-items-center rounded-lg border bg-background">
                          <BrandIcon slug={a.slug} className="size-3.5" />
                        </span>
                        {a.platform}
                      </span>
                    </TableCell>
                    <TableCell className="font-semibold text-foreground">{a.name}</TableCell>
                    <TableCell><StatusBadge state={a.status} /></TableCell>
                    <TableCell className="text-muted-foreground">{a.mode}</TableCell>
                    <TableCell className="text-muted-foreground">{a.proxy}</TableCell>
                    <TableCell className="text-right">
                      <Button variant="ghost" size="icon" className="text-muted-foreground hover:text-destructive" onClick={() => remove(a)}>
                        <Trash2 className="size-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

/* ------------------------------ Analytics ------------------------------ */

export function AnalyticsPage() {
  const { data, loading, error, reload } = useResource(() => api.get("/api/analytics"), []);
  const t = data?.totals || {};
  const byPlatform = data?.by_platform || {};
  const maxCount = Math.max(1, ...Object.values(byPlatform));

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="数据"
        title="跨平台发布效果"
        description="聚合生成、审批、发布和平台表现，形成选题复盘。"
        actions={<Button variant="outline" className="gap-1.5" onClick={reload}><RefreshCw className="size-4" />刷新</Button>}
      />
      {loading ? <Loading /> : error ? <ErrorHint>{error}</ErrorHint> : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Metric title="已发布" value={String(data.published_count ?? 0)} hint="累计" icon={Send} tone="purple" />
            <Metric title="草稿总数" value={String(data.draft_count ?? 0)} hint="含待审" icon={BarChart3} tone="blue" />
            <Metric title="阅读/播放" value={formatNum(t.views || 0)} hint="累计" icon={Activity} tone="green" />
            <Metric title="互动" value={formatNum(data.interactions ?? 0)} hint="赞评藏转" icon={MessageSquareText} tone="orange" />
          </div>
          <Card>
            <CardContent className="space-y-5 pt-6">
              <h2 className="text-base font-semibold text-foreground">各平台草稿分布</h2>
              {Object.keys(byPlatform).length === 0 ? (
                <EmptyHint>暂无数据，去“创作”生成草稿后这里会出现分布。</EmptyHint>
              ) : (
                <div className="space-y-3">
                  {Object.entries(byPlatform).map(([platform, count]) => (
                    <div key={platform} className="flex items-center gap-3">
                      <span className="w-16 shrink-0 text-sm text-muted-foreground">{PLATFORM_LABEL[platform] || platform}</span>
                      <div className="h-6 flex-1 overflow-hidden rounded-md bg-muted">
                        <div className="h-full rounded-md bg-gradient-to-r from-primary/50 to-primary" style={{ width: `${(count / maxCount) * 100}%` }} />
                      </div>
                      <span className="w-8 text-right text-sm tnum text-foreground">{count}</span>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}

/* ------------------------------ Team ------------------------------ */

export function TeamPage({ openModal }) {
  const TAB = ["成员", "团队代理"];
  const [tab, setTab] = useState("成员");
  const members = useResource(() => api.get("/api/team").then((d) => d.members || []), []);
  const proxies = useResource(() => api.get("/api/proxies").then((d) => d.proxies || []), []);
  useEffect(() => {
    const onMember = () => members.reload();
    const onProxy = () => proxies.reload();
    window.addEventListener("team:changed", onMember);
    window.addEventListener("proxies:changed", onProxy);
    return () => {
      window.removeEventListener("team:changed", onMember);
      window.removeEventListener("proxies:changed", onProxy);
    };
  }, [members, proxies]);

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="团队"
        title="团队、席位与代理"
        description="给采集、编辑、审核、发布配置不同权限，并管理各平台发布环境。"
        actions={
          <>
            <Button variant="outline" onClick={() => openModal("proxy")}>添加代理</Button>
            <Button onClick={() => openModal("member")}>邀请成员</Button>
          </>
        }
      />
      <TabsRow tabs={TAB} value={tab} onChange={setTab} />
      {tab === "成员" ? (
        <Card className="py-0">
          <CardContent className="px-0">
            {members.loading ? <Loading /> : members.error ? <ErrorHint>{members.error}</ErrorHint> : (members.data || []).length === 0 ? (
              <EmptyHint>还没有团队成员，点击“邀请成员”添加。</EmptyHint>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>成员</TableHead><TableHead>角色</TableHead><TableHead>运营账号</TableHead>
                    <TableHead>加入时间</TableHead><TableHead>状态</TableHead>
                    <TableHead className="text-right">操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {members.data.map((r) => (
                    <TableRow key={r.id}>
                      <TableCell className="font-semibold text-foreground">{r.name}</TableCell>
                      <TableCell className="text-muted-foreground">{r.role}</TableCell>
                      <TableCell className="text-muted-foreground tnum">{r.account_count}</TableCell>
                      <TableCell className="text-muted-foreground tnum">{r.joined_at}</TableCell>
                      <TableCell><StatusBadge state={r.status} /></TableCell>
                      <TableCell className="text-right">
                        <Button variant="ghost" size="icon" className="text-muted-foreground hover:text-destructive"
                          onClick={async () => { await api.del(`/api/team?id=${encodeURIComponent(r.id)}`); members.reload(); }}>
                          <Trash2 className="size-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      ) : (
        <Card className="py-0">
          <CardContent className="px-0">
            {proxies.loading ? <Loading /> : proxies.error ? <ErrorHint>{proxies.error}</ErrorHint> : (proxies.data || []).length === 0 ? (
              <EmptyHint>还没有代理，点击“添加代理”创建。</EmptyHint>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>名称</TableHead><TableHead>类型</TableHead><TableHead>地址</TableHead>
                    <TableHead>状态</TableHead><TableHead className="text-right">操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {proxies.data.map((r) => (
                    <TableRow key={r.id}>
                      <TableCell className="font-semibold text-foreground">{r.name}</TableCell>
                      <TableCell className="text-muted-foreground">{r.type}</TableCell>
                      <TableCell className="text-muted-foreground tnum">{r.host}:{r.port}</TableCell>
                      <TableCell><StatusBadge state={r.status} /></TableCell>
                      <TableCell className="text-right">
                        <Button variant="ghost" size="icon" className="text-muted-foreground hover:text-destructive"
                          onClick={async () => { await api.del(`/api/proxies?id=${encodeURIComponent(r.id)}`); proxies.reload(); }}>
                          <Trash2 className="size-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

/* ------------------------------ Assets ------------------------------ */

export function AssetsPage({ openModal }) {
  const [group, setGroup] = useState("全部分组");
  const { data, loading, error, reload } = useResource(
    () => api.get(`/api/assets?group=${encodeURIComponent(group)}`).then((d) => d.assets || []),
    [group]
  );
  useEffect(() => {
    const handler = () => reload();
    window.addEventListener("assets:changed", handler);
    return () => window.removeEventListener("assets:changed", handler);
  }, [reload]);

  const groups = ["全部分组", ...new Set((data || []).map((a) => a.group_name).filter(Boolean))];

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="素材"
        title="跨平台素材库"
        description="保存下载后的视频、截图、封面、字幕、DOCX 和平台草稿。"
        actions={<Button onClick={() => openModal("asset")} className="gap-1.5"><Plus className="size-4" />上传素材</Button>}
      />
      <div className="grid gap-5 lg:grid-cols-[240px_minmax(0,1fr)]">
        <Card className="h-fit">
          <CardContent className="space-y-1 pt-6">
            <h3 className="px-1 pb-1 text-xs font-semibold text-muted-foreground">分组</h3>
            {groups.map((g) => (
              <button
                key={g}
                onClick={() => setGroup(g)}
                className={cn(
                  "block w-full rounded-lg px-3 py-2 text-left text-sm font-medium transition-colors",
                  group === g ? "bg-primary/10 text-primary" : "text-muted-foreground hover:bg-accent/50 hover:text-foreground"
                )}
              >
                {g}
              </button>
            ))}
          </CardContent>
        </Card>

        <Card className="py-0">
          <CardContent className="px-0">
            {loading ? <Loading /> : error ? <ErrorHint>{error}</ErrorHint> : (data || []).length === 0 ? (
              <EmptyHint>该分组暂无素材，点击“上传素材”添加。</EmptyHint>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>素材名</TableHead><TableHead>类型</TableHead><TableHead>大小</TableHead>
                    <TableHead>分组</TableHead><TableHead>关联内容</TableHead>
                    <TableHead className="text-right">操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.map((a) => (
                    <TableRow key={a.id}>
                      <TableCell className="font-semibold text-foreground">{a.name}</TableCell>
                      <TableCell className="text-muted-foreground">{a.type}</TableCell>
                      <TableCell className="text-muted-foreground tnum">{formatSize(a.size_bytes)}</TableCell>
                      <TableCell className="text-muted-foreground">{a.group_name}</TableCell>
                      <TableCell className="text-muted-foreground">{a.used}</TableCell>
                      <TableCell className="text-right">
                        <Button variant="ghost" size="icon" className="text-muted-foreground hover:text-destructive"
                          onClick={async () => { await api.del(`/api/assets?id=${encodeURIComponent(a.id)}`); reload(); }}>
                          <Trash2 className="size-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

/* ------------------------------ helpers ------------------------------ */

function formatTime(iso) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" });
  } catch {
    return iso;
  }
}

function formatNum(n) {
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`;
  return String(n);
}

function formatSize(bytes) {
  if (!bytes) return "—";
  if (bytes >= 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)}MB`;
  if (bytes >= 1024) return `${(bytes / 1024).toFixed(0)}KB`;
  return `${bytes}B`;
}
