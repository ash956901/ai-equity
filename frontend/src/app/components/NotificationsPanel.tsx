import { CheckCheck, X } from "lucide-react";

type NotificationCategory = "filing" | "risk" | "theme" | "system";

interface NotificationItem {
  id: string;
  title: string;
  message: string;
  category: NotificationCategory;
  severity: "high" | "medium" | "low";
  timestamp: string;
  read: boolean;
}

interface NotificationsPanelProps {
  open: boolean;
  filter: "all" | NotificationCategory;
  notifications: NotificationItem[];
  onClose: () => void;
  onFilterChange: (value: "all" | NotificationCategory) => void;
  onMarkAllRead: () => void;
  onMarkRead: (id: string) => void;
  onDismiss: (id: string) => void;
}

export function NotificationsPanel(props: NotificationsPanelProps) {
  if (!props.open) return null;

  return (
    <div className="notification-overlay" role="dialog" aria-modal="true" aria-label="Notifications panel">
      <button
        type="button"
        className="notification-backdrop"
        onClick={props.onClose}
      />

      <aside className="notification-panel">
        <div className="notification-panel-head">
          <div>
            <p className="results-title">Alerts Center</p>
            <h3>Notifications</h3>
          </div>
          <button
            type="button"
            className="notification-close"
            onClick={props.onClose}
            aria-label="Close notifications panel"
          >
            <X size={16} />
          </button>
        </div>

        <div className="notification-panel-actions">
          <select
            className="type-select"
            value={props.filter}
            onChange={(event) =>
              props.onFilterChange(event.target.value as "all" | NotificationCategory)
            }
          >
            <option value="all">All categories</option>
            <option value="filing">Filing</option>
            <option value="risk">Risk</option>
            <option value="theme">Theme</option>
            <option value="system">System</option>
          </select>

          <button type="button" className="secondary-btn mini-btn" onClick={props.onMarkAllRead}>
            <CheckCheck size={14} />
            Mark all read
          </button>
        </div>

        <div className="notification-list">
          {props.notifications.length ? (
            props.notifications.map((notification) => (
              <article
                key={notification.id}
                className={`notification-item ${notification.read ? "read" : "unread"}`}
              >
                <div className="notification-item-head">
                  <span className={`chip notif-${notification.category}`}>{notification.category}</span>
                  <span className={`chip notif-severity-${notification.severity}`}>
                    {notification.severity}
                  </span>
                </div>

                <h4>{notification.title}</h4>
                <p>{notification.message}</p>
                <small>{new Date(notification.timestamp).toLocaleString()}</small>

                <div className="notification-item-actions">
                  {!notification.read ? (
                    <button
                      type="button"
                      className="secondary-btn mini-btn"
                      onClick={() => props.onMarkRead(notification.id)}
                    >
                      Mark read
                    </button>
                  ) : null}
                  <button
                    type="button"
                    className="secondary-btn mini-btn"
                    onClick={() => props.onDismiss(notification.id)}
                  >
                    Dismiss
                  </button>
                </div>
              </article>
            ))
          ) : (
            <div className="list-item single-line">
              <p>No notifications in this category.</p>
            </div>
          )}
        </div>
      </aside>
    </div>
  );
}
