import {
  Bot,
  CheckCircle2,
  ClipboardCheck,
  Globe2,
  Link as LinkIcon,
  Network,
  Send,
  ShieldCheck,
  Wand2,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { PageHeader } from "@/components/app/page-header";
import { Metric } from "@/components/app/metric";
import { ContentList } from "@/components/app/content-list";

const flow = [
  ["采集", "X/TikTok/Reddit", Globe2],
  ["理解", "转写/翻译/评分", Bot],
  ["重写", "真人口吻/平台适配", Wand2],
  ["审核", "人工确认/事实检查", CheckCircle2],
  ["发布", "小红书/公众号/视频号/抖音", Send],
];

const entries = [
  [Network, "发布代理", "管理 HTTP/SOCKS5 和账号网络环境"],
  [Bot, "AI 工作台", "改写、翻译、去水印、生成封面"],
  [LinkIcon, "Webhook", "接入飞书、企业微信和自定义回调"],
];

const quota = [
  ["数据源账号", "370 / 500"],
  ["AI 生成次数", "128 / 300"],
  ["素材库容量", "21GB / 50GB"],
  ["发布席位", "6 / 10"],
];

export function HomePage({ openModal, setActive }) {
  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="海外采集 · AI 整理 · 国内分发"
        title="今天有 18 条高价值线索等待处理"
        description="X、TikTok、Reddit、YouTube 的内容会先进入线索池，再生成小红书、公众号、视频号和抖音版本。"
        actions={
          <>
            <Button variant="outline" onClick={() => openModal("source")}>新增数据源</Button>
            <Button onClick={() => openModal("newPublish")}>新增发布</Button>
          </>
        }
      />

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_340px]">
        <div className="space-y-5">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Metric title="今日采集" value="426" hint="+18% vs 昨日" icon={Globe2} tone="blue" />
            <Metric title="入选线索" value="18" hint="平均分 84" icon={ClipboardCheck} tone="green" />
            <Metric title="待审批" value="7" hint="2 条含视频" icon={ShieldCheck} tone="orange" />
            <Metric title="已发布" value="11" hint="覆盖 4 平台" icon={Send} tone="purple" />
          </div>

          <Card>
            <CardHeader className="flex-row items-center justify-between">
              <CardTitle>自动化链路</CardTitle>
              <Button variant="ghost" size="sm" className="text-primary">查看全部</Button>
            </CardHeader>
            <CardContent className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
              {flow.map(([title, desc, Icon]) => (
                <div key={title} className="rounded-xl border bg-muted/30 p-3.5">
                  <span className="grid size-9 place-items-center rounded-lg bg-primary/10 text-primary">
                    <Icon className="size-[18px]" />
                  </span>
                  <p className="mt-2.5 text-sm font-semibold text-foreground">{title}</p>
                  <p className="mt-0.5 text-xs text-muted-foreground">{desc}</p>
                </div>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex-row items-center justify-between">
              <CardTitle>本小时线索</CardTitle>
              <Button variant="ghost" size="sm" className="text-primary" onClick={() => setActive("inbox")}>
                进入线索池
              </Button>
            </CardHeader>
            <CardContent>
              <ContentList compact />
            </CardContent>
          </Card>
        </div>

        <div className="space-y-5">
          <Card className="bg-gradient-to-br from-primary/10 to-primary/[0.03]">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>专业版试用</CardTitle>
                <span className="text-xs text-muted-foreground">内容点数</span>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="text-2xl font-bold text-foreground tnum">3,260 / 5,000</div>
              <Progress value={65} />
              <dl className="grid gap-2.5 text-sm">
                {quota.map(([k, v]) => (
                  <div key={k} className="flex items-center justify-between">
                    <dt className="text-muted-foreground">{k}</dt>
                    <dd className="font-medium text-foreground tnum">{v}</dd>
                  </div>
                ))}
              </dl>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>常用入口</CardTitle></CardHeader>
            <CardContent className="grid gap-2">
              {entries.map(([Icon, title, desc]) => (
                <button
                  key={title}
                  className="flex items-start gap-3 rounded-xl border bg-card p-3 text-left transition-colors hover:border-primary/40 hover:bg-accent/40"
                >
                  <span className="grid size-9 shrink-0 place-items-center rounded-lg bg-primary/10 text-primary">
                    <Icon className="size-[18px]" />
                  </span>
                  <span>
                    <span className="block text-sm font-semibold text-foreground">{title}</span>
                    <span className="mt-0.5 block text-xs text-muted-foreground">{desc}</span>
                  </span>
                </button>
              ))}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
