import { useEffect, useState } from "react";
import { Link, NavLink, Outlet } from "react-router-dom";
import { notificationsApi } from "../api/services";
import { useAuth } from "./useAuth";

export function AppShell() {
  const { user, logout, hasRole } = useAuth();
  const isManagerOrAdmin = hasRole(["Manager/Approver", "Admin"]);
  const [unreadCount, setUnreadCount] = useState<number>(0);

  useEffect(() => {
    if (!user) return;
    notificationsApi
      .getUnreadCount()
      .then((res) => setUnreadCount(res.unread_count))
      .catch(() => {});
  }, [user]);

  return (
    <div className="app-shell">
      <header className="top-header">
        <div className="brand-container">
          <div className="brand-logo">S</div>
          <div>
            <h1 className="brand-title">SPIP</h1>
            <div className="brand-subtitle">Smart Procurement & Inventory Planning</div>
          </div>
        </div>

        {user && (
          <div className="user-profile" style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
            <Link
              to="/notifications"
              className="btn btn-secondary"
              style={{ position: "relative", padding: "0.4rem 0.75rem", fontSize: "0.85rem" }}
              title="Notifications"
            >
              ðŸ””
              {unreadCount > 0 && (
                <span
                  style={{
                    position: "absolute",
                    top: "-6px",
                    right: "-6px",
                    backgroundColor: "var(--spip-red, #e63946)",
                    color: "#fff",
                    borderRadius: "50%",
                    padding: "2px 6px",
                    fontSize: "0.7rem",
                    fontWeight: "bold",
                  }}
                >
                  {unreadCount}
                </span>
              )}
            </Link>
            <div className="user-info">
              <div className="user-name">{user.full_name}</div>
              <div>
                {user.roles?.map((r) => (
                  <span key={r} className="user-role-badge">
                    {r}
                  </span>
                ))}
              </div>
            </div>
            <button type="button" className="btn btn-secondary" onClick={logout}>
              Sign Out
            </button>
          </div>
        )}
      </header>

      <div className="layout-body">
        <aside className="sidebar">
          <NavLink
            to="/"
            end
            className={({ isActive }) =>
              `sidebar-nav-item ${isActive ? "active" : ""}`
            }
          >
            Dashboard
          </NavLink>

          <NavLink
            to="/finished-goods"
            className={({ isActive }) =>
              `sidebar-nav-item ${isActive ? "active" : ""}`
            }
          >
            Finished Goods
          </NavLink>

          <NavLink
            to="/bom-explorer"
            className={({ isActive }) =>
              `sidebar-nav-item ${isActive ? "active" : ""}`
            }
          >
            BOM Explorer
          </NavLink>

          <NavLink
            to="/planning-workspace"
            className={({ isActive }) =>
              `sidebar-nav-item ${isActive ? "active" : ""}`
            }
          >
            Planning Engine
          </NavLink>

          <NavLink
            to="/planning-insights"
            className={({ isActive }) =>
              `sidebar-nav-item ${isActive ? "active" : ""}`
            }
          >
            Shortages & Orders
          </NavLink>

          <NavLink
            to="/dependencies"
            className={({ isActive }) =>
              `sidebar-nav-item ${isActive ? "active" : ""}`
            }
          >
            Where-Used Analysis
          </NavLink>

          <NavLink
            to="/planning"
            className={({ isActive }) =>
              `sidebar-nav-item ${isActive ? "active" : ""}`
            }
          >
            Planning Overview
          </NavLink>

          <NavLink
            to="/forecasting"
            className={({ isActive }) =>
              `sidebar-nav-item ${isActive ? "active" : ""}`
            }
          >
            Demand Forecasting
          </NavLink>

          <NavLink
            to="/allocations"
            className={({ isActive }) =>
              `sidebar-nav-item ${isActive ? "active" : ""}`
            }
          >
            Vendor Allocations
          </NavLink>

          <NavLink
            to="/approvals"
            className={({ isActive }) =>
              `sidebar-nav-item ${isActive ? "active" : ""}`
            }
          >
            Manager Queue {isManagerOrAdmin && <span style={{ color: "var(--spip-red)", fontWeight: "bold" }}>â— </span>}
          </NavLink>

          <NavLink
            to="/notifications"
            className={({ isActive }) =>
              `sidebar-nav-item ${isActive ? "active" : ""}`
            }
          >
            Notifications {unreadCount > 0 && <span className="badge badge-error" style={{ marginLeft: "0.5rem", fontSize: "0.7rem" }}>{unreadCount}</span>}
          </NavLink>

          <NavLink
            to="/reports"
            className={({ isActive }) =>
              `sidebar-nav-item ${isActive ? "active" : ""}`
            }
          >
            Reports & Exports
          </NavLink>

          <NavLink
            to="/ingestion"
            className={({ isActive }) =>
              `sidebar-nav-item ${isActive ? "active" : ""}`
            }
          >
            Data & SAP Sync
          </NavLink>
        </aside>

        <main className="main-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
