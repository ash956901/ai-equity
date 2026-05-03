import { useQuery } from "@tanstack/react-query";

import {
  fetchHomePersonalized,
  type HomeCompany,
  type HomePersonalized,
} from "../../shared/api/home";

interface HomeViewProps {
  onPickCompany: (ticker: string, companyId?: string) => void;
}

export function HomeView({ onPickCompany }: HomeViewProps) {
  const { data, isLoading, error } = useQuery<HomePersonalized>({
    queryKey: ["home", "personalized"],
    queryFn: fetchHomePersonalized,
    staleTime: 30_000,
  });

  if (isLoading) return <p className="muted">Loading your dashboard…</p>;
  if (error) return <p className="auth-error">Could not load personalised dashboard.</p>;
  if (!data) return null;

  return (
    <div className="home-view">
      <Section title="Your watchlist" empty="Add companies to start tracking them.">
        {data.watchlist_companies.map((c: HomeCompany) => (
          <CompanyCard key={`w-${c.company_id}`} company={c} onPick={onPickCompany} />
        ))}
      </Section>
      <Section title="Your holdings" empty="Connect a broker or add holdings manually.">
        {data.holdings_companies.map((c: HomeCompany) => (
          <CompanyCard key={`h-${c.company_id}`} company={c} onPick={onPickCompany} />
        ))}
      </Section>
      <Section
        title="Hidden / asymmetric exposure"
        subtitle="The Castrol-style insights from Discovery."
      >
        {data.asymmetric_feed.map((c: HomeCompany) => (
          <CompanyCard
            key={`a-${c.company_id}`}
            company={c}
            onPick={onPickCompany}
            badge={c.theme}
          />
        ))}
      </Section>
      <Section title="Recent filings (timeline)">
        {data.timeline_recent.map((t: { filing_id: string; company_id: string; company_name: string; ticker_nse?: string | null; filing_type: string; filing_date?: string | null; summary: string }) => (
          <article
            key={t.filing_id}
            className="timeline-card"
            onClick={() => onPickCompany(t.ticker_nse || "", t.company_id)}
          >
            <header>
              <strong>{t.company_name}</strong>
              <span className="muted"> · {t.filing_date}</span>
            </header>
            <p>{t.summary}</p>
            <span className="timeline-card__type">{t.filing_type}</span>
          </article>
        ))}
      </Section>
      <Section
        title="Suggested for you"
        subtitle="Based on your sectors of interest (or top market-cap if none set)."
      >
        {data.suggestions.map((c: HomeCompany) => (
          <CompanyCard key={`s-${c.company_id}`} company={c} onPick={onPickCompany} />
        ))}
      </Section>
    </div>
  );
}

function Section({
  title,
  subtitle,
  empty,
  children,
}: {
  title: string;
  subtitle?: string;
  empty?: string;
  children: React.ReactNode;
}) {
  const isEmpty = Array.isArray(children) ? children.length === 0 : !children;
  return (
    <section className="home-section">
      <header className="home-section__head">
        <h3>{title}</h3>
        {subtitle ? <p className="muted">{subtitle}</p> : null}
      </header>
      {isEmpty && empty ? (
        <p className="muted">{empty}</p>
      ) : (
        <div className="home-section__grid">{children}</div>
      )}
    </section>
  );
}

function CompanyCard({
  company,
  onPick,
  badge,
}: {
  company: HomeCompany;
  onPick: (ticker: string, companyId?: string) => void;
  badge?: string;
}) {
  const ticker = company.ticker_nse || company.ticker_bse || "";
  return (
    <button
      type="button"
      className="company-card"
      onClick={() => onPick(ticker, company.company_id)}
    >
      <div className="company-card__head">
        <strong>{company.name}</strong>
        {badge ? <span className="company-card__badge">{badge}</span> : null}
      </div>
      <div className="company-card__meta">
        <span>{ticker || "—"}</span>
        <span className="muted">·</span>
        <span className="muted">{company.industry || company.sector || "—"}</span>
      </div>
      {company.reasoning ? (
        <p className="company-card__reason">{company.reasoning}</p>
      ) : null}
      {company.quantity !== undefined && company.quantity !== null ? (
        <p className="company-card__qty">Qty: {company.quantity}</p>
      ) : null}
    </button>
  );
}
