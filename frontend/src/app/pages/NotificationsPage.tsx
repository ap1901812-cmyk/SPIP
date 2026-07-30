import { useEffect, useState } from "react";
import { notificationsApi } from "../../api/services";
import type { NotificationItem } from "../../api/types";

export function NotificationsPage() {
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [unreadCount, setUnreadCount] = useState<number>(0);
  const [filterUnread, setFilterUnread] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    setIsLoading(true);
    setError(null);
    Promise.all([
      notificationsApi.getNotifications(filterUnread),
      notificationsApi.getUnreadCount(),
    ])
      .then(([listRes, countRes]) => {
        if (isMounted) {
          setNotifications(listRes.items);
          setUnreadCount(countRes.unread_count);
        }
      })
      .catch((err: unknown) => {
        if (isMounted) {
          setError(err instanceof Error ? err.message : "Failed to load notifications.");
        }
      })
      .finally(() => {
        if (isMounted) {
          setIsLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [filterUnread]);


  const [selectedNotification, setSelectedNotification] = useState<NotificationItem | null>(null);

  const handleMarkAsRead = async (id: number) => {
    try {
      await notificationsApi.markAsRead(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true, read_at: new Date().toISOString() } : n))
      );
      setUnreadCount((prev) => Math.max(0, prev - 1));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to mark as read.");
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await notificationsApi.markAllAsRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
      setUnreadCount(0);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to mark all as read.");
    }
  };

  const handleOpenDetail = (n: NotificationItem) => {
    setSelectedNotification(n);
    if (!n.is_read) {
      handleMarkAsRead(n.id);
    }
  };

  const formatRelativeTime = (dateStr: string): string => {
    try {
      const d = new Date(dateStr);
      const now = new Date();
      const diffMs = now.getTime() - d.getTime();
      const diffMin = Math.floor(diffMs / 60000);
      if (diffMin < 1) return "Just now";
      if (diffMin < 60) return `${diffMin} min ago`;
      const diffHr = Math.floor(diffMin / 60);
      if (diffHr < 24) return `${diffHr} hr ago`;
      const diffDays = Math.floor(diffHr / 24);
      if (diffDays < 7) return `${diffDays}d ago`;
      return d.toLocaleDateString();
    } catch {
      return dateStr;
    }
  };

  const parseDetails = (n: NotificationItem) => {
    const allocMatch = n.message.match(/ALC-[\w-]+/i) || n.title.match(/ALC-[\w-]+/i);
    const allocId = n.resource_id || (allocMatch ? allocMatch[0] : "N/A");
    
    let summary = n.title;
    if (n.message && n.message.length < 50) {
      summary = n.message;
    }
    return { allocId, summary };
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Notification Center</h1>
          <div className="eyebrow" style={{ marginTop: "0.25rem" }}>
            IN-APP ALERTS & SYSTEM EVENT AUDIT
          </div>
        </div>
        <div style={{ display: "flex", gap: "0.75rem" }}>
          {unreadCount > 0 && (
            <button type="button" className="btn btn-secondary" onClick={handleMarkAllRead}>
              Mark All Read ({unreadCount})
            </button>
          )}
        </div>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      <div className="card" style={{ marginBottom: "1.25rem", padding: "0.75rem 1.25rem" }}>
        <div style={{ display: "flex", gap: "1rem", alignItems: "center" }}>
          <label style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "0.875rem", cursor: "pointer" }}>
            <input
              type="checkbox"
              checked={filterUnread}
              onChange={(e) => setFilterUnread(e.target.checked)}
            />
            Show unread only ({unreadCount} unread)
          </label>
        </div>
      </div>

      {isLoading ? (
        <div className="card" style={{ textAlign: "center", padding: "3rem", color: "var(--text-muted)" }}>
          Loading Notification Center...
        </div>
      ) : notifications.length === 0 ? (
        <div className="card" style={{ textAlign: "center", padding: "3rem" }}>
          <h3 style={{ color: "var(--text-muted)", marginBottom: "0.5rem" }}>No Notifications</h3>
          <p className="text-secondary">
            {filterUnread
              ? "You have no unread notifications."
              : "No notifications recorded for your account."}
          </p>
        </div>
      ) : (
        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          <div className="spip-table-container">
            <table className="spip-table">
              <thead>
                <tr>
                  <th style={{ width: "100px" }}>Status</th>
                  <th style={{ width: "140px" }}>Allocation</th>
                  <th>Summary</th>
                  <th style={{ width: "120px" }}>Received</th>
                  <th style={{ textAlign: "right", width: "140px" }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {notifications.map((n) => {
                  const { allocId, summary } = parseDetails(n);
                  return (
                    <tr key={n.id} style={{ background: n.is_read ? "transparent" : "rgba(230,57,70,0.04)" }}>
                      <td>
                        <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
                          {!n.is_read && (
                            <span
                              style={{
                                display: "inline-block",
                                width: "7px",
                                height: "7px",
                                borderRadius: "50%",
                                backgroundColor: "var(--spip-red, #e63946)",
                                flexShrink: 0,
                              }}
                              title="Unread notification"
                            />
                          )}
                          <span
                            className={`badge-status ${
                              n.notification_type.includes("CRITICAL") || n.notification_type.includes("REJECTED")
                                ? "CRITICAL"
                                : n.notification_type.includes("WARNING") || n.notification_type.includes("PENDING")
                                ? "WARNING"
                                : "HEALTHY"
                            }`}
                            style={{ fontSize: "0.7rem" }}
                          >
                            {n.notification_type.replace(/_/g, " ")}
                          </span>
                        </div>
                      </td>
                      <td style={{ fontWeight: "700", fontFamily: "monospace" }}>{allocId}</td>
                      <td style={{ maxWidth: "340px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        <span style={{ fontWeight: n.is_read ? "500" : "700" }}>{summary}</span>
                      </td>
                      <td style={{ fontSize: "0.8rem", color: "var(--text-muted)", whiteSpace: "nowrap" }}>
                        {formatRelativeTime(n.created_at)}
                      </td>
                      <td style={{ textAlign: "right", whiteSpace: "nowrap" }}>
                        <button
                          type="button"
                          className="btn btn-secondary"
                          style={{ padding: "0.2rem 0.55rem", fontSize: "0.75rem", marginRight: "0.4rem" }}
                          onClick={() => handleOpenDetail(n)}
                        >
                          View
                        </button>
                        {!n.is_read && (
                          <button
                            type="button"
                            className="btn btn-secondary"
                            style={{ padding: "0.2rem 0.45rem", fontSize: "0.75rem" }}
                            onClick={() => handleMarkAsRead(n.id)}
                          >
                            Read
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {selectedNotification && (
        <div className="modal-backdrop" onClick={() => setSelectedNotification(null)}>
          <div className="modal-content" style={{ maxWidth: "560px" }} onClick={(e) => e.stopPropagation()}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
              <h3 style={{ margin: 0, fontSize: "1.15rem" }}>
                Notification Audit Details
              </h3>
              <button
                type="button"
                className="btn btn-secondary"
                style={{ padding: "0.25rem 0.5rem" }}
                onClick={() => setSelectedNotification(null)}
              >
                ✕
              </button>
            </div>

            <div style={{ background: "var(--surface-subtle)", padding: "1rem", borderRadius: "0.5rem", marginBottom: "1.25rem" }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.5rem" }}>
                <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>Allocation / Resource ID:</span>
                <strong style={{ fontFamily: "monospace" }}>
                  {selectedNotification.resource_id || parseDetails(selectedNotification).allocId}
                </strong>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.5rem" }}>
                <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>Notification Category:</span>
                <span className="badge-status HEALTHY" style={{ fontSize: "0.75rem" }}>
                  {selectedNotification.notification_type}
                </span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.5rem" }}>
                <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>Timestamp:</span>
                <span style={{ fontSize: "0.85rem" }}>{new Date(selectedNotification.created_at).toLocaleString()}</span>
              </div>
              {selectedNotification.resource_type && (
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>Resource Type:</span>
                  <span style={{ fontSize: "0.85rem" }}>{selectedNotification.resource_type}</span>
                </div>
              )}
            </div>

            <div style={{ marginBottom: "1.25rem" }}>
              <h4 style={{ margin: "0 0 0.4rem 0", fontSize: "0.95rem" }}>{selectedNotification.title}</h4>
              <p style={{ fontSize: "0.9rem", color: "var(--text-secondary)", lineHeight: 1.5, margin: 0 }}>
                {selectedNotification.message}
              </p>
            </div>

            <div style={{ textAlign: "right" }}>
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => setSelectedNotification(null)}
              >
                Close Details
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

