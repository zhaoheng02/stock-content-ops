import { useState } from "react";
import { Activity, BarChart3, Download, MessageSquareText, Send } from "lucide-react";
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
import { FilterBar } from "@/components/app/filter-bar";
import { Metric } from "@/components/app/metric";
import { StatusBadge } from "@/components/app/status-badge";
import { BrandIcon } from "@/components/app/brand-icon";
import { cn } from "@/lib/utils";
import {
  accounts,
  assets,
  platformCards,
  platformPalette,
  publishRows,
  teamRows,
} from "@/data/mock";

function TabsRow({ tabs }) {
  return (
    <Tabs defaultValue={tabs[0]}>
      <TabsList>
        {tabs.map((t) => (
          <TabsTrigger key={t} value={t}>{t}</TabsTrigger>
        ))}
      </TabsList>
    </Tabs>
  );
}

export function PublishPage({ openModal }) {
  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="发布"
        title="发布记录与草稿箱"
        description="统一管理小红书、公众号、视频号、抖音等平台的发布任务。"
        actions={
          <>
            <Button variant="outline" className="gap-1.5"><Download className="size-4" />导出</Button>
            <Button onClick={() => openModal("newPublish")}>新增发布</Button>
          </>
        }
      />
      <TabsRow tabs={["发布记录", "草稿箱", "定时队列", "失败重试"]} />
      <FilterBar labels={["全部发布人", "全部类型", "全部状态", "全部模式"]} placeholder="搜索作品描述或任务标题..." />
      <Card className="py-0">
        <CardContent className="px-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>作品</TableHead><TableHead>类型</TableHead><TableHead>平台</TableHead>
                <TableHead>负责人</TableHead><TableHead>状态</TableHead><TableHead>时间</TableHead>
                <TableHead className="text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {publishRows.map((row) => (
                <TableRow key={row.title}>
                  <TableCell className="font-semibold text-foreground">{row.title}</TableCell>
                  <TableCell className="text-muted-foreground">{row.type}</TableCell>
                  <TableCell className="text-muted-foreground">{row.platforms}</TableCell>
                  <TableCell className="text-muted-foreground">{row.owner}</TableCell>
                  <TableCell><StatusBadge state={row.state} /></TableCell>
                  <TableCell className="text-muted-foreground">{row.time}</TableCell>
                  <TableCell className="text-right">
                    <Button variant="ghost" size="sm" className="text-primary">编辑</Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}

export function AccountsPage({ openModal }) {
  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="账号"
        title="发布账号授权"
        description="管理国内发布账号，也保留海外来源账号的登录状态和网络环境。"
        actions={<Button onClick={() => openModal("accountAuth")}>添加账号</Button>}
      />
      <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-3 lg:grid-cols-5">
        {platformPalette.map((p) => (
          <button
            key={p.name}
            className={cn(
              "flex flex-col items-center gap-2.5 rounded-xl border p-4 transition-all",
              p.active ? "border-primary bg-primary/5 shadow-sm" : "bg-card hover:border-primary/40 hover:shadow-sm"
            )}
          >
            <span className="grid size-10 place-items-center rounded-xl border bg-background">
              <BrandIcon slug={p.slug} className="size-5" />
            </span>
            <strong className="text-sm font-medium text-foreground">{p.name}</strong>
          </button>
        ))}
      </div>
      <Card className="py-0">
        <CardContent className="px-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>平台</TableHead><TableHead>账号</TableHead><TableHead>状态</TableHead>
                <TableHead>发布模式</TableHead><TableHead>代理</TableHead>
                <TableHead className="text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {accounts.map((a) => (
                <TableRow key={a.platform}>
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
                    <Button variant="ghost" size="sm" className="text-primary">检查登录</Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}

export function AnalyticsPage({ openModal }) {
  const bars = [36, 52, 44, 68, 58, 82, 74];
  const [range, setRange] = useState("近7日");
  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="数据"
        title="跨平台发布效果"
        description="聚合采集、生成、审批、发布和平台表现，形成选题复盘。"
        actions={<Button onClick={() => openModal("dataPush")}>数据推送</Button>}
      />
      <TabsRow tabs={["数据总览", "增量数据", "账号数据", "作品数据", "负责人数据"]} />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Metric title="发布数" value="42" hint="本周" icon={Send} tone="purple" />
        <Metric title="阅读/播放" value="128k" hint="+22%" icon={Activity} tone="blue" />
        <Metric title="互动" value="4,821" hint="赞评藏" icon={MessageSquareText} tone="green" />
        <Metric title="转化线索" value="36" hint="内容回流" icon={BarChart3} tone="orange" />
      </div>
      <Card>
        <CardContent className="space-y-5 pt-6">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold text-foreground">平台新增趋势</h2>
            <div className="flex gap-1 rounded-lg border bg-card p-1">
              {["近7日", "近30日", "自定义"].map((r) => (
                <button
                  key={r}
                  onClick={() => setRange(r)}
                  className={cn(
                    "rounded-md px-3 py-1 text-xs font-medium transition-colors",
                    range === r ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground"
                  )}
                >
                  {r}
                </button>
              ))}
            </div>
          </div>
          <div className="flex h-56 items-end gap-3">
            {bars.map((h, i) => (
              <div key={i} className="flex flex-1 flex-col items-center gap-2">
                <div
                  className="w-full rounded-t-md bg-gradient-to-t from-primary/40 to-primary transition-all"
                  style={{ height: `${h}%` }}
                />
                <span className="text-xs text-muted-foreground">D{i + 1}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

export function ReviewPage({ openModal }) {
  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="审批"
        title="发布前确认队列"
        description="每条内容先给出 AI 分析、来源证据、引用和素材清单，再由你确认是否发布。"
        actions={<Button onClick={() => openModal("approval")}>查看确认卡</Button>}
      />
      <div className="grid gap-4 sm:grid-cols-2">
        {platformCards.map((p, i) => {
          const Icon = p.icon;
          return (
            <Card key={p.id}>
              <CardContent className="space-y-3 pt-6">
                <div className="flex items-center gap-2">
                  <span className="grid size-8 place-items-center rounded-lg bg-primary/10 text-primary">
                    <Icon className="size-4" />
                  </span>
                  <strong className="text-sm font-semibold text-foreground">{p.name}</strong>
                  <StatusBadge state={i % 2 ? "待修改" : "待确认"} className="ml-auto" />
                </div>
                <h3 className="text-sm font-semibold text-foreground">{p.title}</h3>
                <p className="text-sm leading-relaxed text-muted-foreground">
                  AI 分析：这条内容不是单点新闻，而是“端侧 AI 能力重新定价”的早期信号，适合用观点型包装。
                </p>
                <div className="flex gap-2 pt-1">
                  <Button variant="outline" size="sm" className="flex-1" onClick={() => openModal("approval")}>退回修改</Button>
                  <Button size="sm" className="flex-1" onClick={() => openModal("approval")}>确认发布</Button>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}

export function TeamPage({ openModal }) {
  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="团队"
        title="团队、席位与代理"
        description="给采集、编辑、审核、发布配置不同权限，并管理各平台发布环境。"
        actions={
          <>
            <Button variant="outline" onClick={() => openModal("proxy")}>添加代理</Button>
            <Button>邀请成员</Button>
          </>
        }
      />
      <TabsRow tabs={["成员", "团队代理", "Webhook", "团队订单"]} />
      <Card className="py-0">
        <CardContent className="px-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>成员</TableHead><TableHead>角色</TableHead><TableHead>运营账号</TableHead>
                <TableHead>加入时间</TableHead><TableHead>状态</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {teamRows.map((r) => (
                <TableRow key={r.name}>
                  <TableCell className="font-semibold text-foreground">{r.name}</TableCell>
                  <TableCell className="text-muted-foreground">{r.role}</TableCell>
                  <TableCell className="text-muted-foreground tnum">{r.accounts}</TableCell>
                  <TableCell className="text-muted-foreground tnum">{r.joined}</TableCell>
                  <TableCell><StatusBadge state={r.status} /></TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}

export function AssetsPage({ openModal }) {
  const [group, setGroup] = useState("全部分组");
  const groups = ["全部分组", "AI PC", "短视频素材", "公众号", "系统内容"];
  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="素材"
        title="跨平台素材库"
        description="保存下载后的视频、截图、封面、字幕、DOCX 和平台草稿。"
        actions={
          <>
            <Button variant="outline">批量操作</Button>
            <Button onClick={() => openModal("asset")}>上传素材</Button>
          </>
        }
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
            <div className="space-y-2 pt-3">
              <span className="text-xs text-muted-foreground tnum">21GB / 50GB</span>
              <Progress value={42} />
            </div>
          </CardContent>
        </Card>

        <Card className="py-0">
          <CardContent className="space-y-4 px-0 pt-4">
            <div className="px-4">
              <TabsRow tabs={["全部类型", "图片", "视频", "文章"]} />
            </div>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>素材名</TableHead><TableHead>类型</TableHead><TableHead>大小</TableHead>
                  <TableHead>分组</TableHead><TableHead>关联内容</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {assets.map((a) => (
                  <TableRow key={a.name}>
                    <TableCell className="font-semibold text-foreground">{a.name}</TableCell>
                    <TableCell className="text-muted-foreground">{a.type}</TableCell>
                    <TableCell className="text-muted-foreground tnum">{a.size}</TableCell>
                    <TableCell className="text-muted-foreground">{a.group}</TableCell>
                    <TableCell className="text-muted-foreground">{a.used}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
