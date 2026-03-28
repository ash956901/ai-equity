import { Database, ExternalLink } from "lucide-react";

import type { DataSourceInfo } from "../types/api";

interface SourceBadgesProps {
  sources?: DataSourceInfo[];
}

export function SourceBadges({ sources }: SourceBadgesProps) {
  if (!sources?.length) return null;
  return (
    <div className="source-badges">
      {sources.map((src, i) => (
        <a
          key={`${src.name}-${i}`}
          href={src.url.startsWith("/") ? undefined : src.url}
          target={src.url.startsWith("/") ? undefined : "_blank"}
          rel="noopener noreferrer"
          className="source-badge"
        >
          <Database size={10} />
          <span>{src.name}</span>
          {!src.url.startsWith("/") && <ExternalLink size={10} />}
        </a>
      ))}
    </div>
  );
}
