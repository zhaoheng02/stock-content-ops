import {
  Activity,
  BarChart3,
  Bot,
  ClipboardCheck,
  FileText,
  Folder,
  Globe2,
  Home,
  Image,
  PlayCircle,
  Send,
  ShieldCheck,
  Sparkles,
  UserRound,
  Users,
  Video,
} from "lucide-react";

export const navItems = [
  { id: "home", label: "主页", icon: Home },
  { id: "sources", label: "数据源", icon: Globe2, badge: "新" },
  { id: "inbox", label: "线索池", icon: ClipboardCheck },
  { id: "studio", label: "创作", icon: Sparkles },
  { id: "publish", label: "发布", icon: Send },
  { id: "accounts", label: "账号", icon: UserRound },
  { id: "analytics", label: "数据", icon: BarChart3 },
  { id: "review", label: "审批", icon: ShieldCheck },
  { id: "team", label: "团队", icon: Users },
  { id: "assets", label: "素材", icon: Folder },
];

export const sourceRows = [
  {
    id: "x",
    name: "X / Twitter",
    slug: "x",
    status: "运行中",
    cadence: "每 30 分钟",
    accounts: 218,
    lastRun: "10 分钟前",
    ingest: "帖子 / 引用 / 图片 / 视频 / YouTube 链接",
  },
  {
    id: "tiktok",
    name: "TikTok",
    slug: "tiktok",
    status: "待授权",
    cadence: "每 2 小时",
    accounts: 36,
    lastRun: "未开始",
    ingest: "热视频 / 评论 / 作者信息 / 音频",
  },
  {
    id: "reddit",
    name: "Reddit",
    slug: "reddit",
    status: "运行中",
    cadence: "每 1 小时",
    accounts: 74,
    lastRun: "26 分钟前",
    ingest: "帖子 / 评论 / subreddit 趋势",
  },
  {
    id: "youtube",
    name: "YouTube",
    slug: "youtube",
    status: "排队中",
    cadence: "每天 3 次",
    accounts: 42,
    lastRun: "昨天 21:00",
    ingest: "视频 / 描述 / 字幕 / 缩略图",
  },
];

export const collectedItems = [
  {
    source: "X",
    author: "RamenPanda",
    handle: "@IamRamenPanda",
    time: "18:42",
    score: 92,
    topic: "AI PC",
    text: "Windows as a local AI runtime is getting interesting again. The winner may be the OS that makes small models feel invisible.",
    quote: "NPU workloads are moving from demos into default system features.",
    media: ["image", "youtube"],
    status: "已入选",
  },
  {
    source: "Reddit",
    author: "r/LocalLLaMA",
    handle: "u/modelbench",
    time: "17:11",
    score: 88,
    topic: "模型部署",
    text: "A 7B local model with tool calling and memory is good enough for small team operations if the workflow is narrow.",
    quote: "",
    media: ["thread"],
    status: "待复核",
  },
  {
    source: "TikTok",
    author: "AI Product Lab",
    handle: "@aiprodlab",
    time: "16:05",
    score: 84,
    topic: "产品演示",
    text: "A side-by-side prompt-to-video workflow is going viral because the before/after is instantly understandable.",
    quote: "",
    media: ["video", "audio"],
    status: "转写中",
  },
];

export const platformCards = [
  {
    id: "xhs",
    name: "小红书图文",
    icon: Image,
    status: "已生成",
    title: "AI PC 真要回来了？这次不是换壳",
    desc: "8 张图文卡片 + 口语化正文 + 话题标签",
  },
  {
    id: "wechat",
    name: "公众号长文",
    icon: FileText,
    status: "待校对",
    title: "从本地模型到操作系统：AI PC 的第二条路",
    desc: "结构化长文、引用来源、延伸阅读",
  },
  {
    id: "video",
    name: "视频号口播",
    icon: Video,
    status: "已生成",
    title: "60 秒讲清 AI PC 的机会",
    desc: "口播脚本、分镜、封面标题",
  },
  {
    id: "douyin",
    name: "抖音短视频",
    icon: PlayCircle,
    status: "需素材",
    title: "本地 AI 不是噱头，它开始有用了",
    desc: "3 段式脚本、字幕、贴纸提示",
  },
];

export const accounts = [
  { platform: "小红书", slug: "xiaohongshu", name: "科技观察员", status: "已授权", mode: "浏览器发布", proxy: "上海-1" },
  { platform: "公众号", slug: "wechat", name: "出海技术札记", status: "已授权", mode: "API / 草稿", proxy: "默认" },
  { platform: "视频号", slug: "wechat", name: "产品增长笔记", status: "待登录", mode: "浏览器发布", proxy: "默认" },
  { platform: "抖音", slug: "tiktok", name: "AI商业拆解", status: "未授权", mode: "应用发布", proxy: "北京-2" },
];

export const publishRows = [
  { title: "AI PC 的第二波机会", type: "图文", platforms: "小红书 / 公众号", owner: "内容组", state: "待确认", time: "今天 20:30" },
  { title: "TikTok 上爆的 prompt-to-video 流程", type: "视频", platforms: "视频号 / 抖音", owner: "视频组", state: "素材处理中", time: "明天 10:00" },
  { title: "Reddit 热帖：小模型工具调用", type: "文章", platforms: "公众号", owner: "编辑组", state: "草稿", time: "未定时" },
];

export const assets = [
  { name: "ai-pc-cover-grid.png", type: "图片", size: "2.4MB", group: "AI PC", used: "小红书图文" },
  { name: "prompt-video-demo.mp4", type: "视频", size: "18.7MB", group: "短视频素材", used: "抖音脚本" },
  { name: "local-model-notes.docx", type: "文章", size: "820KB", group: "公众号", used: "长文草稿" },
];

export const teamRows = [
  { name: "内容编辑", role: "编辑", accounts: "8", joined: "2026-06-12", status: "在线" },
  { name: "审核负责人", role: "审核", accounts: "4", joined: "2026-06-10", status: "在线" },
  { name: "发布机器人", role: "自动化", accounts: "12", joined: "2026-06-08", status: "运行中" },
];

export const platformPalette = [
  { name: "小红书", slug: "xiaohongshu", active: true },
  { name: "公众号", slug: "wechat", active: true },
  { name: "视频号", slug: "wechat", active: true },
  { name: "抖音", slug: "tiktok", active: true },
  { name: "快手", slug: "kuaishou" },
  { name: "哔哩哔哩", slug: "bilibili" },
  { name: "微博", slug: "sinaweibo" },
  { name: "知乎", slug: "zhihu" },
  { name: "TikTok", slug: "tiktok" },
  { name: "YouTube", slug: "youtube" },
];
