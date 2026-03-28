import type { ReactNode } from "react";

interface PageHeaderProps {
  title: string;
  subtitle: string;
  dataMode?: "live" | "demo";
  right?: ReactNode;
}

export function PageHeader(props: PageHeaderProps) {
  return (
    <header className="page-header">
      <div>
        <h1>{props.title}</h1>
        <p>{props.subtitle}</p>
        <div className="page-header-meta">
          <span className={`chip data-mode-chip ${props.dataMode === "demo" ? "demo" : "live"}`}>
            {props.dataMode === "demo" ? "Demo Data" : "Live API"}
          </span>
        </div>
      </div>
      {props.right ? <div>{props.right}</div> : null}
    </header>
  );
}
