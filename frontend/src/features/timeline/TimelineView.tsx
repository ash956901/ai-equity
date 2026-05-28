import { useCallback, useEffect, useMemo, useState } from "react";
import { ExternalLink, Loader2, Search } from "lucide-react";

import { ApiError, fetchTimeline, type TimelineEvent as BackendTimelineEvent } from "../../lib/api";
import { PageHeader } from "../../shared/ui/PageHeader";
import { SourceBadges } from "../../shared/ui/SourceBadges";

interface SearchSelection {
  stamp: number;
  timelineQuery?: string;
  timelineEventId?: string;
}

interface TimelineViewProps {
  dataMode: "live" | "demo";
  searchSelection: SearchSelection | null;
  goToView: (view: "chat") => void;
  setSearchSelection: (selection: { stamp: number; chatPrompt: string }) => void;
}

function getUserId(): string {
  let id = localStorage.getItem("equityai-user-id");
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem("equityai-user-id", id);
  }
  return id;
}

export function TimelineView(props: TimelineViewProps) {
  const [lastSelectionStamp, setLastSelectionStamp] = useState<number>(0);
  const [query, setQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState<"all" | "filing" | "news" | "signal">("all");
  const [events, setEvents] = useState<BackendTimelineEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedEventId, setSelectedEventId] = useState<string>("");

  const userId = useMemo(() => getUserId(), []);

  const loadEvents = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchTimeline(userId, undefined, 40);
      setEvents(data);
      if (data.length > 0 && !selectedEventId) {
        setSelectedEventId(data[0].id);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not load timeline.");
      setEvents([]);
    } finally {
      setLoading(false);
    }
  }, [selectedEventId, userId]);

  useEffect(() => {
    void loadEvents();
  }, [loadEvents]);

  useEffect(() => {
    if (!props.searchSelection) return;
    if (props.searchSelection.stamp === lastSelectionStamp) return;
    if (props.searchSelection.timelineQuery) setQuery(props.searchSelection.timelineQuery);
    if (props.searchSelection.timelineEventId) setSelectedEventId(props.searchSelection.timelineEventId);
    setLastSelectionStamp(props.searchSelection.stamp);
  }, [lastSelectionStamp, props.searchSelection]);

  const filteredEvents = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    return events
      .filter((event) => {
        const matchesQuery = !normalized ||
          `${event.company_name ?? ""} ${event.title} ${event.summary}`.toLowerCase().includes(normalized);
        const matchesType = typeFilter === "all" || event.event_type === typeFilter;
        return matchesQuery && matchesType;
      })
      .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
  }, [events, query, typeFilter]);

  useEffect(() => {
    if (!filteredEvents.length) {
      setSelectedEventId("");
      return;
    }
    const exists = filteredEvents.some((e) => e.id === selectedEventId);
    if (!exists) setSelectedEventId(filteredEvents[0].id);
  }, [filteredEvents, selectedEventId]);

  const selectedEvent = filteredEvents.find((e) => e.id === selectedEventId) ?? null;

  const formatTimestamp = (value: string) => {
    const d = new Date(value);
    return Number.isNaN(d.getTime()) ? value : d.toLocaleString();
  };

  const getTypeClass = (type: string) => {
    if (type === "filing") return "chip type-filing";
    if (type === "signal") return "chip type-signal";
    return "chip type-news";
  };
  const getImpactClass = (impact?: string) => {
    if (impact === "high") return "chip negative";
    if (impact === "medium") return "chip warning";
    return "chip positive";
  };

  return (
    <section className="page-wrap">
      <PageHeader
        title="Research Timeline Feed"
        subtitle="Real-time filings and news events from the database."
        dataMode={props.dataMode}
        right={
          <button type="button" className="primary-btn" onClick={() => void loadEvents()}>
            {loading ? "Loading..." : "Refresh"}
          </button>
        }
      />

      <div className="timeline-toolbar">
        <div className="search-pill timeline-search">
          <Search size={14} />
          <input placeholder="Search events..." value={query} onChange={(e) => setQuery(e.target.value)} />
        </div>
        <div className="chip-row">
          <select className="type-select" value={typeFilter} onChange={(e) => setTypeFilter(e.target.value as typeof typeFilter)}>
            <option value="all">Type: All</option>
            <option value="filing">Type: Filing</option>
            <option value="news">Type: News</option>
            <option value="signal">Type: Signal</option>
          </select>

        </div>
      </div>

      {error ? <div className="notice warning">{error}</div> : null}
      {loading ? <div className="notice"><Loader2 size={16} className="spin" /> Loading timeline...</div> : null}

      {!loading && !filteredEvents.length && !error ? (
        <div className="notice">No timeline events found. Events appear as filings and news are indexed by the backend.</div>
      ) : null}

      <div className="timeline-layout">
        <div className="timeline-list">
          {filteredEvents.map((event) => (
            <button
              key={event.id}
              type="button"
              className={`timeline-item ${selectedEventId === event.id ? "active" : ""}`}
              onClick={() => setSelectedEventId(event.id)}
            >
              <div className="timeline-item-head">
                <p>{event.company_name ?? "Unknown"}</p>
                <span>{formatTimestamp(event.timestamp)}</span>
              </div>
              <h3>{event.title}</h3>
              <p>{event.summary}</p>
              <div className="chip-row timeline-item-chips">
                <span className={getTypeClass(event.event_type)}>{event.event_type}</span>
                {event.metadata?.impact ? (
                  <span className={getImpactClass(String(event.metadata.impact))}>
                    {String(event.metadata.impact)} impact
                  </span>
                ) : null}
              </div>
              <SourceBadges sources={event.data_sources} />
            </button>
          ))}
        </div>

        <aside className="timeline-detail">
          {selectedEvent ? (
            <>
              <div className="timeline-detail-head">
                <div>
                  <p className="discovery-symbol">{selectedEvent.company_name ?? "Unknown"}</p>
                  <h3>{selectedEvent.title}</h3>
                </div>
                <span className="chip">{formatTimestamp(selectedEvent.timestamp)}</span>
              </div>
              <p className="discovery-insight">{selectedEvent.summary}</p>
              <div className="chip-row timeline-item-chips">
                <span className={getTypeClass(selectedEvent.event_type)}>{selectedEvent.event_type}</span>
                {selectedEvent.metadata?.source ? (
                  <span className="chip">{String(selectedEvent.metadata.source)}</span>
                ) : null}
              </div>
              <SourceBadges sources={selectedEvent.data_sources} />
              {selectedEvent.metadata?.source_url ? (
                <a
                  href={String(selectedEvent.metadata.source_url)}
                  target="_blank"
                  rel="noreferrer"
                  className="secondary-btn timeline-link"
                >
                  <ExternalLink size={14} /> Open Source Reference
                </a>
              ) : null}
              <button
                type="button"
                className="primary-btn timeline-chat-btn"
                onClick={() => {
                  props.setSearchSelection({
                    stamp: Date.now(),
                    chatPrompt: `Analyze this timeline event: ${selectedEvent.title} (${selectedEvent.company_name ?? "Unknown"}).`,
                  });
                  props.goToView("chat");
                }}
              >
                Ask Minerva About This Event
              </button>
            </>
          ) : (
            <div className="list-item single-line">
              <p>Select an event to view details.</p>
            </div>
          )}
        </aside>
      </div>
    </section>
  );
}
