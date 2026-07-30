import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import { notificationsApi } from "../api/services";
import { ChangePasswordModal } from "../components/ChangePasswordModal";
import { useAuth } from "./useAuth";

export function AppShell() {
  const { user, logout, hasRole } = useAuth();
  const isManagerOrAdmin = hasRole(["Manager/Approver", "Manager", "Admin"]);
  const isAdmin = hasRole(["Admin"]);
  const [unreadCount, setUnreadCount] = useState<number>(0);

  const location = useLocation();
  const path = location.pathname;

  const [openSections, setOpenSections] = useState<Record<string, boolean>>(() => {
    return {
      planning: ["/planning-workspace", "/planning-insights", "/forecasting", "/planning"].some((p) => path.startsWith(p)),
      materials: ["/finished-goods", "/dependencies"].some((p) => path.startsWith(p)),
      operations: ["/allocations", "/approvals", "/notifications", "/ingestion"].some((p) => path.startsWith(p)),
      reports: path.startsWith("/reports"),
      admin: path.startsWith("/users"),
    };
  });

  useEffect(() => {
    if (["/planning-workspace", "/planning-insights", "/forecasting", "/planning"].some((p) => path.startsWith(p))) {
      setOpenSections((prev) => ({ ...prev, planning: true }));
    } else if (["/finished-goods", "/dependencies"].some((p) => path.startsWith(p))) {
      setOpenSections((prev) => ({ ...prev, materials: true }));
    } else if (["/allocations", "/approvals", "/notifications", "/ingestion"].some((p) => path.startsWith(p))) {
      setOpenSections((prev) => ({ ...prev, operations: true }));
    } else if (path.startsWith("/reports")) {
      setOpenSections((prev) => ({ ...prev, reports: true }));
    } else if (path.startsWith("/users")) {
      setOpenSections((prev) => ({ ...prev, admin: true }));
    }
  }, [path]);

  const toggleSection = (section: string) => {
    setOpenSections((prev) => ({ ...prev, [section]: !prev[section] }));
  };

  useEffect(() => {
    if (!user) return;
    notificationsApi
      .getUnreadCount()
      .then((res) => setUnreadCount(res.unread_count))
      .catch(() => {});
  }, [user]);

  const getPrimaryRole = (roles?: string[]): string => {
    if (!roles || roles.length === 0) return "Planner";
    if (roles.includes("Admin")) return "Admin";
    if (roles.includes("Manager") || roles.includes("Manager/Approver")) return "Manager";
    if (roles.includes("Planner")) return "Planner";
    return roles[0];
  };

  return (
    <div className="app-shell">
      <ChangePasswordModal />

      <header className="top-header">
        <div className="brand-container">
          <div className="brand-logo">S</div>
          <div>
            <h1 className="brand-title">SPIP</h1>
            <div className="brand-subtitle">Smart Procurement & Inventory Planning</div>
          </div>
        </div>

        {user && (
          <div className="user-profile" style={{ display: "flex", alignItems: "center", gap: "1.25rem" }}>
            <Link
              to="/notifications"
              className="btn btn-secondary"
              style={{ position: "relative", padding: "0.4rem 0.75rem", fontSize: "0.85rem" }}
              title="Notifications"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
                <path d="M13.73 21a2 2 0 0 1-3.46 0" />
              </svg>
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

            <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
              <div
                style={{
                  width: "2.4rem",
                  height: "2.4rem",
                  borderRadius: "50%",
                  backgroundColor: "var(--spip-red-light, #fef2f2)",
                  border: "1px solid var(--spip-red-border, #fecaca)",
                  display: "grid",
                  placeItems: "center",
                }}
              >
                <svg
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="var(--spip-red)"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                  <circle cx="12" cy="7" r="4" />
                </svg>
              </div>

              <div className="user-info" style={{ textAlign: "left" }}>
                <div className="user-name" style={{ fontSize: "0.9rem", fontWeight: 700, color: "var(--text-main)" }}>
                  {user.full_name}
                </div>
                <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", fontWeight: 500 }}>
                  {getPrimaryRole(user.roles)}
                </div>
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
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: "0.5rem" }}>
              <rect x="3" y="3" width="7" height="7" />
              <rect x="14" y="3" width="7" height="7" />
              <rect x="14" y="14" width="7" height="7" />
              <rect x="3" y="14" width="7" height="7" />
            </svg>
            Dashboard
          </NavLink>

          {/* Section: Planning */}
          <div>
            <button
              type="button"
              className="sidebar-section-toggle"
              onClick={() => toggleSection("planning")}
              style={{
                width: "100%",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "0.65rem 1rem 0.35rem",
                background: "none",
                border: "none",
                fontSize: "0.75rem",
                fontWeight: 700,
                color: "var(--text-muted)",
                textTransform: "uppercase",
                letterSpacing: "0.05em",
                cursor: "pointer",
              }}
            >
              <span>Planning</span>
              <span style={{ fontSize: "0.7rem", opacity: 0.7 }}>{openSections.planning ? "▼" : "►"}</span>
            </button>
            {openSections.planning && (
              <div style={{ paddingLeft: "0.5rem" }}>
                <NavLink
                  to="/planning-workspace"
                  className={({ isActive }) =>
                    `sidebar-nav-item ${isActive ? "active" : ""}`
                  }
                >
                  Planning Overview
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
                  to="/forecasting"
                  className={({ isActive }) =>
                    `sidebar-nav-item ${isActive ? "active" : ""}`
                  }
                >
                  Demand Forecasting
                </NavLink>
              </div>
            )}
          </div>

          {/* Section: Materials */}
          <div>
            <button
              type="button"
              className="sidebar-section-toggle"
              onClick={() => toggleSection("materials")}
              style={{
                width: "100%",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "0.65rem 1rem 0.35rem",
                background: "none",
                border: "none",
                fontSize: "0.75rem",
                fontWeight: 700,
                color: "var(--text-muted)",
                textTransform: "uppercase",
                letterSpacing: "0.05em",
                cursor: "pointer",
              }}
            >
              <span>Materials</span>
              <span style={{ fontSize: "0.7rem", opacity: 0.7 }}>{openSections.materials ? "▼" : "►"}</span>
            </button>
            {openSections.materials && (
              <div style={{ paddingLeft: "0.5rem" }}>
                <NavLink
                  to="/finished-goods"
                  className={({ isActive }) =>
                    `sidebar-nav-item ${isActive ? "active" : ""}`
                  }
                >
                  Finished Goods
                </NavLink>

                <NavLink
                  to="/dependencies"
                  className={({ isActive }) =>
                    `sidebar-nav-item ${isActive ? "active" : ""}`
                  }
                >
                  Where-Used Analysis
                </NavLink>
              </div>
            )}
          </div>

          {/* Section: Operations */}
          <div>
            <button
              type="button"
              className="sidebar-section-toggle"
              onClick={() => toggleSection("operations")}
              style={{
                width: "100%",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "0.65rem 1rem 0.35rem",
                background: "none",
                border: "none",
                fontSize: "0.75rem",
                fontWeight: 700,
                color: "var(--text-muted)",
                textTransform: "uppercase",
                letterSpacing: "0.05em",
                cursor: "pointer",
              }}
            >
              <span>Operations</span>
              <span style={{ fontSize: "0.7rem", opacity: 0.7 }}>{openSections.operations ? "▼" : "►"}</span>
            </button>
            {openSections.operations && (
              <div style={{ paddingLeft: "0.5rem" }}>
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
                  Manager Queue {isManagerOrAdmin && (
                    <svg width="8" height="8" viewBox="0 0 8 8" fill="var(--spip-red)" style={{ marginLeft: "0.25rem", verticalAlign: "middle" }}>
                      <circle cx="4" cy="4" r="4" />
                    </svg>
                  )}
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
                  to="/ingestion"
                  className={({ isActive }) =>
                    `sidebar-nav-item ${isActive ? "active" : ""}`
                  }
                >
                  Data & SAP Sync
                </NavLink>
              </div>
            )}
          </div>

          {/* Section: Reports */}
          <div>
            <button
              type="button"
              className="sidebar-section-toggle"
              onClick={() => toggleSection("reports")}
              style={{
                width: "100%",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "0.65rem 1rem 0.35rem",
                background: "none",
                border: "none",
                fontSize: "0.75rem",
                fontWeight: 700,
                color: "var(--text-muted)",
                textTransform: "uppercase",
                letterSpacing: "0.05em",
                cursor: "pointer",
              }}
            >
              <span>Reports</span>
              <span style={{ fontSize: "0.7rem", opacity: 0.7 }}>{openSections.reports ? "▼" : "►"}</span>
            </button>
            {openSections.reports && (
              <div style={{ paddingLeft: "0.5rem" }}>
                <NavLink
                  to="/reports"
                  className={({ isActive }) =>
                    `sidebar-nav-item ${isActive ? "active" : ""}`
                  }
                >
                  Reports & Exports
                </NavLink>
              </div>
            )}
          </div>

          {/* Section: Administration */}
          {isAdmin && (
            <div>
              <button
                type="button"
                className="sidebar-section-toggle"
                onClick={() => toggleSection("admin")}
                style={{
                  width: "100%",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "0.65rem 1rem 0.35rem",
                  background: "none",
                  border: "none",
                  fontSize: "0.75rem",
                  fontWeight: 700,
                  color: "var(--text-muted)",
                  textTransform: "uppercase",
                  letterSpacing: "0.05em",
                  cursor: "pointer",
                }}
              >
                <span>Administration</span>
                <span style={{ fontSize: "0.7rem", opacity: 0.7 }}>{openSections.admin ? "▼" : "►"}</span>
              </button>
              {openSections.admin && (
                <div style={{ paddingLeft: "0.5rem" }}>
                  <NavLink
                    to="/users"
                    className={({ isActive }) =>
                      `sidebar-nav-item ${isActive ? "active" : ""}`
                    }
                  >
                    User Management
                  </NavLink>
                </div>
              )}
            </div>
          )}
        </aside>

        <main className="main-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
