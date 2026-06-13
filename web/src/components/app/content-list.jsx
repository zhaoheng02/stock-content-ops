import { useEffect, useState } from "react";
import {
  Avatar,
  AvatarFallback,
  AvatarImage,
} from "@/components/ui/avatar";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { StatusBadge } from "@/components/app/status-badge";
import { collectedItems } from "@/data/mock";
import { API_BASE } from "@/lib/api";

function toItem(post) {
  return {
    key: post.content_hash,
    source: (post.platform || "x").toUpperCase(),
    author: post.author_name || post.author_handle,
    handle: post.author_handle ? `@${post.author_handle}` : "",
    avatar: post.author_avatar_url,
    time: post.published_at_raw || post.published_at || "",
    text: post.text,
    url: post.url,
    images: Array.isArray(post.image_urls) ? post.image_urls : [],
    metrics: post.metrics || {},
    status: "待复核",
  };
}

export function ContentList({ compact = false }) {
  const [posts, setPosts] = useState(null);

  useEffect(() => {
    let active = true;
    fetch(`${API_BASE}/api/source-posts?limit=50`)
      .then((response) => (response.ok ? response.json() : { posts: [] }))
      .then((payload) => active && setPosts(payload.posts || []))
      .catch(() => active && setPosts([]));
    return () => {
      active = false;
    };
  }, []);

  const useReal = Array.isArray(posts) && posts.length > 0;
  const items = useReal
    ? posts.map(toItem)
    : collectedItems.map((item) => ({
        key: `${item.source}-${item.author}`,
        source: item.source,
        author: item.author,
        handle: item.handle,
        avatar: null,
        time: item.time,
        text: item.text,
        url: null,
        images: [],
        metrics: {},
        topic: item.topic,
        score: item.score,
        status: item.status,
      }));

  const shown = compact ? items.slice(0, 2) : items;

  return (
    <div className="grid gap-3">
      {posts === null && (
        <p className="text-sm text-muted-foreground">正在加载线索...</p>
      )}
      {shown.map((item) => (
        <Card
          key={item.key}
          className="flex-row gap-3 p-4 transition-colors hover:border-primary/40"
        >
          <Avatar className="size-10">
            {item.avatar && <AvatarImage src={item.avatar} alt={item.author} />}
            <AvatarFallback className="bg-primary/10 text-xs font-semibold text-primary">
              {(item.author || "?").slice(0, 2).toUpperCase()}
            </AvatarFallback>
          </Avatar>
          <div className="min-w-0 flex-1 space-y-2">
            <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm">
              <span className="font-semibold text-foreground">{item.author}</span>
              <span className="text-muted-foreground">{item.handle}</span>
              {item.time && <span className="text-muted-foreground">·</span>}
              <span className="text-muted-foreground">{item.time}</span>
              <StatusBadge state={item.status} className="ml-auto" />
            </div>
            <p className="text-sm leading-relaxed text-foreground/90 whitespace-pre-wrap">{item.text}</p>
            {item.images.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {item.images.slice(0, 4).map((src) => (
                  <img key={src} src={src} alt="" className="h-24 w-24 rounded-lg object-cover" />
                ))}
              </div>
            )}
            <div className="flex flex-wrap items-center gap-1.5">
              <Badge variant="secondary" className="font-medium">{item.source}</Badge>
              {item.topic && <Badge variant="outline" className="font-medium">{item.topic}</Badge>}
              {item.score != null && (
                <Badge variant="outline" className="font-medium text-primary">评分 {item.score}</Badge>
              )}
              {item.metrics?.likes != null && (
                <Badge variant="outline" className="text-muted-foreground">♥ {item.metrics.likes}</Badge>
              )}
              {item.url && (
                <a
                  href={item.url}
                  target="_blank"
                  rel="noreferrer"
                  className="ml-auto text-xs text-primary hover:underline"
                >
                  原帖
                </a>
              )}
            </div>
          </div>
        </Card>
      ))}
    </div>
  );
}
