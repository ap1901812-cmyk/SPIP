import { NavLink, Outlet } from "react-router-dom";

import { useAuth } from "./useAuth";


export function AppShell() {
  const { user, logout, hasRole } = useAuth();
  const isManagerOrAdmin = hasRole(["Manager/Approver", "Admin"]);

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
          <div className="user-profile">
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
            Manager Queue {isManagerOrAdmin && <span style={{ color: "var(--spip-red)", fontWeight: "bold" }}>●</span>}
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
