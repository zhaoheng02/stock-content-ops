import { KeyRound, Loader2, Upload } from "lucide-react";
import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { platformCards } from "@/data/mock";
import { API_BASE } from "@/lib/api";

function Field({ label, children, full }) {
  return (
    <div className={full ? "space-y-1.5 sm:col-span-2" : "space-y-1.5"}>
      <Label className="text-xs text-muted-foreground">{label}</Label>
      {children}
    </div>
  );
}

function Picker({ placeholder, options, value, onValueChange }) {
  return (
    <Select value={value} onValueChange={onValueChange}>
      <SelectTrigger className="w-full">
        <SelectValue placeholder={placeholder} />
      </SelectTrigger>
      <SelectContent>
        {options.map((o) => (
          <SelectItem key={Array.isArray(o) ? o[0] : o} value={Array.isArray(o) ? o[0] : o}>
            {Array.isArray(o) ? o[1] : o}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

const TITLES = {
  source: "新增海外数据源",
  newPublish: "选择发布类型",
  draftPreview: "平台草稿预览",
  accountAuth: "添加发布账号",
  asset: "上传素材",
  proxy: "添加代理",
  dataPush: "数据推送",
  approval: "发布确认",
};

const WIDE = new Set(["newPublish", "draftPreview"]);

export function ModalRouter({ modal, onClose, onToast }) {
  const open = Boolean(modal);
  const confirm = (msg) => {
    onClose();
    onToast?.(msg);
  };
  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className={WIDE.has(modal) ? "sm:max-w-3xl" : "sm:max-w-lg"}>
        <DialogHeader>
          <DialogTitle>{TITLES[modal]}</DialogTitle>
        </DialogHeader>
        {modal === "source" && <SourceBody onConfirm={confirm} onClose={onClose} />}
        {modal === "newPublish" && <NewPublishBody onConfirm={confirm} />}
        {modal === "draftPreview" && <DraftPreviewBody onConfirm={confirm} onClose={onClose} />}
        {modal === "accountAuth" && <AccountAuthBody onConfirm={confirm} onClose={onClose} />}
        {modal === "asset" && <AssetBody onConfirm={confirm} onClose={onClose} />}
        {modal === "proxy" && <ProxyBody onConfirm={confirm} onClose={onClose} />}
        {modal === "dataPush" && <DataPushBody onConfirm={confirm} onClose={onClose} />}
        {modal === "approval" && <ApprovalBody onConfirm={confirm} onClose={onClose} />}
      </DialogContent>
    </Dialog>
  );
}

function SourceBody({ onConfirm, onClose }) {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState({
    platform: "x",
    cadence_minutes: 30,
    targets: "@openai, @levelsio",
    min_score: 70,
    material_strategy: "download_media",
  });
  const saveSource = async () => {
    setSaving(true);
    setError("");
    try {
      const payload = {
        id: sourceId(form.platform, form.targets),
        name: sourceName(form.platform),
        platform: form.platform,
        cadence_minutes: Number(form.cadence_minutes),
        targets: form.targets,
        min_score: Number(form.min_score),
        material_strategy: form.material_strategy,
      };
      const response = await fetch(`${API_BASE}/api/sources`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "保存失败");
      window.dispatchEvent(new CustomEvent("sources:changed", { detail: data.source }));
      onConfirm("数据源已保存");
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };
  return (
    <>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="来源平台">
          <Picker
            value={form.platform}
            onValueChange={(platform) => setForm((item) => ({ ...item, platform }))}
            placeholder="X"
            options={[
              ["x", "X"],
              ["tiktok", "TikTok"],
              ["reddit", "Reddit"],
              ["youtube", "YouTube"],
            ]}
          />
        </Field>
        <Field label="采集频率">
          <Picker
            value={String(form.cadence_minutes)}
            onValueChange={(cadence) => setForm((item) => ({ ...item, cadence_minutes: Number(cadence) }))}
            placeholder="每 30 分钟"
            options={[
              ["30", "每 30 分钟"],
              ["60", "每 1 小时"],
              ["480", "每天 3 次"],
            ]}
          />
        </Field>
        <Field label="账号 / 关键词" full>
          <Textarea
            value={form.targets}
            onChange={(event) => setForm((item) => ({ ...item, targets: event.target.value }))}
            placeholder="@openai, @levelsio, subreddit:LocalLLaMA, #aivideo"
          />
        </Field>
        <Field label="最小评分">
          <Input
            value={form.min_score}
            onChange={(event) => setForm((item) => ({ ...item, min_score: event.target.value }))}
          />
        </Field>
        <Field label="素材策略">
          <Picker
            value={form.material_strategy}
            onValueChange={(strategy) => setForm((item) => ({ ...item, material_strategy: strategy }))}
            placeholder="下载图片和视频"
            options={[
              ["download_media", "下载图片和视频"],
              ["links_only", "只保存链接"],
              ["text_only", "仅正文"],
            ]}
          />
        </Field>
      </div>
      {error && <p className="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</p>}
      <DialogFooter>
        <Button variant="outline" onClick={onClose}>取消</Button>
        <Button onClick={saveSource} disabled={saving || !form.targets.trim()}>
          {saving && <Loader2 className="mr-1.5 size-4 animate-spin" />}
          保存数据源
        </Button>
      </DialogFooter>
    </>
  );
}

function sourceName(platform) {
  return {
    x: "X Custom Sources",
    tiktok: "TikTok Custom Sources",
    reddit: "Reddit Custom Sources",
    youtube: "YouTube Custom Sources",
  }[platform] || "Custom Sources";
}

function sourceId(platform, targets) {
  const firstTarget = (targets.split(/[\s,]+/).find(Boolean) || "custom")
    .replace(/^@/, "")
    .replace(/[^a-zA-Z0-9_-]/g, "")
    .toLowerCase();
  return `${platform}-${firstTarget}`;
}

function NewPublishBody({ onConfirm }) {
  const types = [
    ["视频发布", "支持平台 12", "抖音 / 视频号 / 小红书 / B站"],
    ["图文发布", "支持平台 8", "小红书 / 抖音 / 视频号 / 微博"],
    ["文章发布", "支持平台 6", "公众号 / 头条号 / 知乎"],
    ["全平台组合", "智能拆分", "一份素材生成多平台版本"],
  ];
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {types.map(([title, count, desc]) => (
        <button
          key={title}
          onClick={() => onConfirm(`已创建：${title}`)}
          className="group rounded-xl border bg-card p-4 text-left transition-colors hover:border-primary hover:bg-accent/40"
        >
          <div className="flex items-center justify-between">
            <span className="font-semibold text-foreground">{title}</span>
            <Badge variant="secondary">{count}</Badge>
          </div>
          <p className="mt-2 text-sm text-muted-foreground">{desc}</p>
        </button>
      ))}
    </div>
  );
}

function DraftPreviewBody({ onConfirm, onClose }) {
  return (
    <>
      <div className="grid gap-3 sm:grid-cols-2">
        {platformCards.map((p) => (
          <div key={p.id} className="rounded-xl border bg-card p-4">
            <span className="text-xs font-medium text-primary">{p.name}</span>
            <h3 className="mt-1.5 text-sm font-semibold text-foreground">{p.title}</h3>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
              先抛判断，再补证据。不逐条搬运原帖，整理成国内用户能直接理解的一个观点。
            </p>
            <div className="mt-3 flex flex-wrap gap-1.5">
              {["#AI", "#出海", "#产品观察"].map((t) => (
                <Badge key={t} variant="outline">{t}</Badge>
              ))}
            </div>
          </div>
        ))}
      </div>
      <DialogFooter>
        <Button variant="outline" onClick={onClose}>继续编辑</Button>
        <Button onClick={() => onConfirm("已送审")}>送审</Button>
      </DialogFooter>
    </>
  );
}

function AccountAuthBody({ onConfirm, onClose }) {
  return (
    <>
      <div className="grid grid-cols-3 gap-2">
        {["小红书", "公众号", "视频号", "抖音", "快手", "B站"].map((p) => (
          <button
            key={p}
            className="rounded-lg border bg-card py-2.5 text-sm font-medium transition-colors hover:border-primary hover:text-primary"
          >
            {p}
          </button>
        ))}
      </div>
      <div className="flex items-center gap-2 rounded-lg bg-muted px-3 py-2.5 text-sm text-muted-foreground">
        <KeyRound className="size-4 shrink-0" />
        <span>选择平台后会打开对应授权页，登录完成后保存账号会话。</span>
      </div>
      <DialogFooter>
        <Button variant="outline" onClick={onClose}>取消</Button>
        <Button onClick={() => onConfirm("正在打开授权页")}>打开授权</Button>
      </DialogFooter>
    </>
  );
}

function AssetBody({ onConfirm, onClose }) {
  return (
    <>
      <Field label="分组">
        <Picker placeholder="全部分组" options={["全部分组", "AI PC", "短视频素材"]} />
      </Field>
      <div className="flex flex-col items-center justify-center gap-2 rounded-xl border border-dashed bg-muted/40 py-10 text-center text-muted-foreground">
        <Upload className="size-6" />
        <span className="text-sm">点击上传图片、视频、DOCX 或字幕文件</span>
      </div>
      <DialogFooter>
        <Button variant="outline" onClick={onClose}>取消</Button>
        <Button onClick={() => onConfirm("素材已上传")}>上传</Button>
      </DialogFooter>
    </>
  );
}

function ProxyBody({ onConfirm, onClose }) {
  return (
    <>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="名称"><Input placeholder="美国-内容发布-1" /></Field>
        <Field label="类型"><Picker placeholder="HTTP" options={["HTTP", "SOCKS5"]} /></Field>
        <Field label="代理地址"><Input placeholder="proxy.example.com" /></Field>
        <Field label="端口"><Input placeholder="8080" /></Field>
        <Field label="账号"><Input /></Field>
        <Field label="密码"><Input type="password" /></Field>
      </div>
      <DialogFooter>
        <Button variant="outline" onClick={onClose}>取消</Button>
        <Button onClick={() => onConfirm("代理已添加")}>添加</Button>
      </DialogFooter>
    </>
  );
}

function DataPushBody({ onConfirm, onClose }) {
  return (
    <>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="发送渠道">
          <Picker placeholder="飞书" options={["飞书", "企业微信", "钉钉"]} />
        </Field>
        <Field label="推送频次">
          <Picker placeholder="日报" options={["日报", "周报", "月报"]} />
        </Field>
        <Field label="Webhook 地址" full>
          <Input placeholder="https://open.feishu.cn/open-apis/bot/..." />
        </Field>
      </div>
      <DialogFooter>
        <Button variant="outline" onClick={() => onConfirm("测试消息已发送")}>测试发送</Button>
        <Button onClick={() => onConfirm("推送配置已保存")}>保存</Button>
      </DialogFooter>
    </>
  );
}

function ApprovalBody({ onConfirm, onClose }) {
  return (
    <>
      <DialogDescription asChild>
        <div className="space-y-3">
          <h3 className="text-base font-semibold text-foreground">
            AI PC 真要回来了？这次不是换壳
          </h3>
          <p className="text-sm leading-relaxed text-muted-foreground">
            AI 分析：这组海外讨论的重点不是某个产品发布，而是本地模型、系统权限和端侧硬件被重新组合，适合拆成“为什么现在值得看”的观点型内容。
          </p>
          <blockquote className="rounded-lg border-l-2 border-primary/40 bg-muted/50 px-3 py-2 text-sm text-muted-foreground">
            来源含 X 原帖 2 条、Reddit 讨论 1 条、YouTube 视频 1 条，素材已进入下载队列。
          </blockquote>
        </div>
      </DialogDescription>
      <DialogFooter>
        <Button variant="outline" onClick={onClose}>退回修改</Button>
        <Button onClick={() => onConfirm("内容已确认发布")}>确认发布</Button>
      </DialogFooter>
    </>
  );
}
