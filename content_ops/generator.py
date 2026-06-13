from typing import Dict

from .models import ContentAsset, SourcePost


def generate_assets(post: SourcePost, persona_policy: str) -> Dict[str, ContentAsset]:
    insight = _extract_insight(post.text)
    return {
        "xiaohongshu": ContentAsset(
            platform="小红书",
            title=f"一个海外案例暴露的增长机会：{insight}",
            body=(
                f"案例来源：{post.account}\n\n"
                f"发生了什么：{post.text}\n\n"
                "商业启发：不要只搬运海外信息，重点是拆出可迁移的机制、适用人群和执行成本。\n"
                "可执行动作：记录原始信号、验证数据口径、改写为中文场景下的产品/运营决策。"
            ),
            persona_policy=persona_policy,
        ),
        "video_account": ContentAsset(
            platform="视频号",
            title=f"海外商业案例拆解：{insight}",
            body=(
                "开场：今天拆一个海外真实案例。\n"
                f"信息点：{post.text}\n"
                "商业启发：有价值的不是热闹，而是背后的机制是否能被中国团队复用。\n"
                "结尾：把它转成你的产品假设，再用一周数据验证。"
            ),
            persona_policy=persona_policy,
        ),
        "wechat_article": ContentAsset(
            platform="公众号",
            title=f"从一条海外动态，看见一个可复用的商业机制：{insight}",
            body=(
                "## 1. 原始信号\n"
                f"{post.text}\n\n"
                "## 2. 关键判断\n"
                "这类案例值得保留，是因为它同时包含趋势、数据或操作细节，并能迁移到中文市场。\n\n"
                "## 3. 商业启发\n"
                "信息差只是入口，真正的壁垒是持续监控、AI筛选、中文重构和稳定分发。\n\n"
                "## 4. 行动清单\n"
                "- 复盘原案例的目标用户\n"
                "- 抽象它解决的商业问题\n"
                "- 设计一个低成本验证动作\n"
                "- 记录结果并沉淀为选题资产"
            ),
            persona_policy=persona_policy,
        ),
        "douyin_script": ContentAsset(
            platform="抖音",
            title=f"30秒讲清一个海外增长案例：{insight}",
            body=(
                "镜头1：海外团队最近做了一个动作。\n"
                f"旁白：{post.text}\n"
                "镜头2：重点不是这个动作本身，而是它背后的商业逻辑。\n"
                "商业启发：能被复用的案例，必须同时有信号、证据和可执行路径。\n"
                "镜头3：如果你做AI工具、出海或SaaS，先把它改写成一个一周实验。"
            ),
            persona_policy=persona_policy,
        ),
    }


def _extract_insight(text: str) -> str:
    compact = " ".join(text.split())
    return compact[:38] + ("..." if len(compact) > 38 else "")

