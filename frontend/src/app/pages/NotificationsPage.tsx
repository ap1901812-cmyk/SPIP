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

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Notifications Center</h1>
          <div className="eyebrow" style={{ marginTop: "0.25rem" }}>
            IN-APP ALERTS & SYSTEM EVENT AUDIT
          </div>
        </div>
        <div style={{ display: "flex", gap: "0.75rem" }}>
          {unreadCount > 0 && (
            <button type="button" className="btn btn-secondary" onClick={handleMarkAllRead}>
              Mark All as Read
            </button>
          )}
        </div>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <div style={{ display: "flex", gap: "1rem", alignItems: "center" }}>
          <label style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "0.875rem" }}>
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
        <div className="card" style={{ textAlign: "center", padding: "2rem", color: "var(--text-muted)" }}>
          Loading notifications...
        </div>
      ) : notifications.length === 0 ? (
        <div className="card" style={{ textAlign: "center", padding: "3rem" }}>
          <h3 style={{ color: "var(--text-muted)", marginBottom: "0.5rem" }}>No Notifications</h3>
          <p className="text-secondary">
            {filterUnread
              ? "You have no unread notifications."
              : "No notifications found for your account."}
          </p>
        </div>
      ) : (
        <div className="card" style={{ padding: 0 }}>
          <table className="data-table">
            <thead>
              <tr>
                <th style={{ width: "40px" }}></th>
                <th>Type</th>
                <th>Notification</th>
                <th>Received</th>
                <th style={{ textAlign: "right" }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {notifications.map((n) => (
                <tr key={n.id} style={{ background: n.is_read ? "transparent" : "rgba(230,57,70,0.04)" }}>
                  <td style={{ textAlign: "center" }}>
                    {!n.is_read && (
                      <span
                        style={{
                          display: "inline-block",
                          width: "8px",
                          height: "8px",
                          borderRadius: "50%",
                          backgroundColor: "var(--spip-red, #e63946)",
                        }}
                        title="Unread"
                      />
                    )}
                  </td>
                  <td>
                    <span className="badge badge-neutral" style={{ fontSize: "0.75rem" }}>
                      {n.notification_type}
                    </span>
                  </td>
                  <td>
                    <div style={{ fontWeight: n.is_read ? 500 : 700 }}>{n.title}</div>
                    <div className="text-secondary" style={{ fontSize: "0.85rem", marginTop: "0.25rem" }}>
                      {n.message}
                    </div>
                  </td>
                  <td style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
                    {new Date(n.created_at).toLocaleString()}
                  </td>
                  <td style={{ textAlign: "right" }}>
                    {!n.is_read && (
                      <button
                        type="button"
                        className="btn btn-secondary"
                        style={{ fontSize: "0.75rem", padding: "0.25rem 0.5rem" }}
                        onClick={() => handleMarkAsRead(n.id)}
                      >
                        Mark Read
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
