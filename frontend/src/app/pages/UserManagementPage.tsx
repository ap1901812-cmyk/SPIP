import { useEffect, useState } from "react";
import { usersApi } from "../../api/services";
import type { UserProfile } from "../../api/types";

export function UserManagementPage() {
  const [users, setUsers] = useState<UserProfile[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Modal states
  const [showCreateModal, setShowCreateModal] = useState<boolean>(false);
  const [showEditModal, setShowEditModal] = useState<boolean>(false);
  const [showResetModal, setShowResetModal] = useState<boolean>(false);
  const [selectedUser, setSelectedUser] = useState<UserProfile | null>(null);

  // Form states - Create
  const [createUsername, setCreateUsername] = useState("");
  const [createEmail, setCreateEmail] = useState("");
  const [createFullName, setCreateFullName] = useState("");
  const [createRole, setCreateRole] = useState("Planner");
  const [createTempPassword, setCreateTempPassword] = useState("");
  const [isSubmittingCreate, setIsSubmittingCreate] = useState(false);

  // Form states - Edit
  const [editUsername, setEditUsername] = useState("");
  const [editEmail, setEditEmail] = useState("");
  const [editFullName, setEditFullName] = useState("");
  const [editRole, setEditRole] = useState("Planner");
  const [editIsActive, setEditIsActive] = useState(true);
  const [isSubmittingEdit, setIsSubmittingEdit] = useState(false);

  // Form states - Reset Password
  const [resetPasswordVal, setResetPasswordVal] = useState("");
  const [generatedTempPwNotice, setGeneratedTempPwNotice] = useState<string | null>(null);
  const [isSubmittingReset, setIsSubmittingReset] = useState(false);

  const fetchUsersList = async () => {
    setIsLoading(true);
    try {
      const data = await usersApi.getUsers();
      setUsers(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load users.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchUsersList();
  }, []);

  const generateSecurePasswordHelper = (): string => {
    const upper = "ABCDEFGHJKLMNPQRSTUVWXYZ";
    const lower = "abcdefghijkmnopqrstuvwxyz";
    const digits = "23456789";
    const special = "!@#$%^&*";

    let pw = "";
    pw += upper[Math.floor(Math.random() * upper.length)];
    pw += lower[Math.floor(Math.random() * lower.length)];
    pw += digits[Math.floor(Math.random() * digits.length)];
    pw += special[Math.floor(Math.random() * special.length)];

    const all = upper + lower + digits + special;
    for (let i = 0; i < 6; i++) {
      pw += all[Math.floor(Math.random() * all.length)];
    }

    return pw
      .split("")
      .sort(() => 0.5 - Math.random())
      .join("");
  };

  const handleOpenCreateModal = () => {
    setCreateUsername("");
    setCreateEmail("");
    setCreateFullName("");
    setCreateRole("Planner");
    setCreateTempPassword(generateSecurePasswordHelper());
    setError(null);
    setShowCreateModal(true);
  };

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmittingCreate(true);
    try {
      const res = await usersApi.createUser({
        username: createUsername,
        email: createEmail,
        full_name: createFullName,
        password: createTempPassword,
        roles: [createRole],
      });
      setShowCreateModal(false);
      setSuccessMessage(
        `User ${res.username} created successfully! Temporary Password: ${createTempPassword}`
      );
      fetchUsersList();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create user.");
    } finally {
      setIsSubmittingCreate(false);
    }
  };

  const handleOpenEditModal = (u: UserProfile) => {
    setSelectedUser(u);
    setEditUsername(u.username || "");
    setEditEmail(u.email);
    setEditFullName(u.full_name);
    setEditRole(displayRole(u.roles));
    setEditIsActive(u.is_active);
    setError(null);
    setShowEditModal(true);
  };

  const handleEditSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedUser) return;
    setError(null);
    setIsSubmittingEdit(true);
    try {
      await usersApi.updateUser(selectedUser.id, {
        username: editUsername,
        email: editEmail,
        full_name: editFullName,
        roles: [editRole],
        is_active: editIsActive,
      });
      setShowEditModal(false);
      setSuccessMessage(`User ${editUsername} updated successfully.`);
      fetchUsersList();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to update user.");
    } finally {
      setIsSubmittingEdit(false);
    }
  };

  const handleOpenResetModal = (u: UserProfile) => {
    setSelectedUser(u);
    setResetPasswordVal(generateSecurePasswordHelper());
    setGeneratedTempPwNotice(null);
    setError(null);
    setShowResetModal(true);
  };

  const handleResetSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedUser) return;
    setError(null);
    setIsSubmittingReset(true);
    try {
      const res = await usersApi.resetPassword(selectedUser.id, {
        new_password: resetPasswordVal,
      });
      const tempPw = res.temporary_password || resetPasswordVal;
      setGeneratedTempPwNotice(`Temporary Password set to: ${tempPw}`);
      setSuccessMessage(`Password reset for ${selectedUser.username}. Temporary Password: ${tempPw}`);
      fetchUsersList();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to reset password.");
    } finally {
      setIsSubmittingReset(false);
    }
  };

  const handleToggleStatus = async (u: UserProfile) => {
    const newStatus = !u.is_active;
    const actionLabel = newStatus ? "activate" : "deactivate";
    if (!window.confirm(`Are you sure you want to ${actionLabel} user ${u.username}?`)) return;

    try {
      await usersApi.updateStatus(u.id, { is_active: newStatus });
      setSuccessMessage(`User ${u.username} ${newStatus ? "activated" : "deactivated"} successfully.`);
      fetchUsersList();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : `Failed to ${actionLabel} user.`);
    }
  };

  const displayRole = (roles: string[]): string => {
    if (!roles || roles.length === 0) return "Planner";
    if (roles.includes("Admin")) return "Admin";
    if (roles.includes("Manager") || roles.includes("Manager/Approver")) return "Manager";
    if (roles.includes("Planner")) return "Planner";
    return roles[0];
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">User Management</h1>
          <div className="eyebrow" style={{ marginTop: "0.25rem" }}>
            ADMIN CONTROL PANEL & USER ACCOUNT PROVISIONING
          </div>
        </div>
        <button type="button" className="btn btn-primary" onClick={handleOpenCreateModal}>
          + Create New User
        </button>
      </div>

      {successMessage && (
        <div className="alert alert-success" style={{ marginBottom: "1rem" }}>
          {successMessage}
          <button
            type="button"
            onClick={() => setSuccessMessage(null)}
            style={{ float: "right", background: "none", border: "none", cursor: "pointer", color: "inherit", padding: "0 0.25rem" }}
            aria-label="Dismiss alert"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>
      )}

      {error && <div className="alert alert-error">{error}</div>}

      <div className="card">
        {isLoading ? (
          <div style={{ padding: "2rem", textAlign: "center", color: "var(--text-muted)" }}>
            Loading users directory...
          </div>
        ) : (
          <div className="spip-table-container">
            <table className="spip-table">
              <thead>
                <tr>
                  <th>Full Name</th>
                  <th>Username</th>
                  <th>Email</th>
                  <th>Role</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id}>
                    <td>
                      <strong style={{ color: "var(--text-main)" }}>{u.full_name}</strong>
                    </td>
                    <td><code>{u.username || "—"}</code></td>
                    <td>{u.email}</td>
                    <td>
                      <span className="user-role-badge">{displayRole(u.roles)}</span>
                    </td>
                    <td>
                      <span
                        className={`badge-status ${u.is_active ? "HEALTHY" : "CRITICAL"}`}
                        style={{ fontSize: "0.75rem" }}
                      >
                        {u.is_active ? "Active" : "Inactive"}
                      </span>
                    </td>
                    <td>
                      <div style={{ display: "flex", gap: "0.5rem" }}>
                        <button
                          type="button"
                          className="btn btn-secondary"
                          style={{ padding: "0.25rem 0.5rem", fontSize: "0.75rem" }}
                          onClick={() => handleOpenEditModal(u)}
                        >
                          Edit
                        </button>
                        <button
                          type="button"
                          className="btn btn-secondary"
                          style={{ padding: "0.25rem 0.5rem", fontSize: "0.75rem" }}
                          onClick={() => handleOpenResetModal(u)}
                        >
                          Reset Password
                        </button>
                        <button
                          type="button"
                          className={u.is_active ? "btn btn-danger" : "btn btn-success"}
                          style={{ padding: "0.25rem 0.5rem", fontSize: "0.75rem" }}
                          onClick={() => handleToggleStatus(u)}
                        >
                          {u.is_active ? "Deactivate" : "Activate"}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* CREATE USER MODAL */}
      {showCreateModal && (
        <div className="modal-backdrop">
          <div className="modal-content">
            <h2 style={{ marginTop: 0, color: "var(--spip-red)" }}>Create New User</h2>
            <form onSubmit={handleCreateSubmit}>
              <div className="form-group">
                <label className="form-label">Full Name</label>
                <input
                  type="text"
                  className="form-input"
                  value={createFullName}
                  onChange={(e) => setCreateFullName(e.target.value)}
                  placeholder="e.g. Rahul Sharma"
                  required
                />
              </div>

              <div className="form-group">
                <label className="form-label">Username</label>
                <input
                  type="text"
                  className="form-input"
                  value={createUsername}
                  onChange={(e) => setCreateUsername(e.target.value)}
                  placeholder="e.g. rahul_s"
                  required
                />
              </div>

              <div className="form-group">
                <label className="form-label">Email Address</label>
                <input
                  type="email"
                  className="form-input"
                  value={createEmail}
                  onChange={(e) => setCreateEmail(e.target.value)}
                  placeholder="e.g. rahul@spip.local"
                  required
                />
              </div>

              <div className="form-group">
                <label className="form-label">Role</label>
                <select
                  className="form-select"
                  value={createRole}
                  onChange={(e) => setCreateRole(e.target.value)}
                >
                  <option value="Planner">Planner</option>
                  <option value="Manager">Manager</option>
                  <option value="Admin">Admin</option>
                </select>
              </div>

              <div className="form-group">
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.35rem" }}>
                  <label className="form-label" style={{ margin: 0 }}>Temporary Password</label>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    style={{ fontSize: "0.75rem", padding: "0.2rem 0.4rem", display: "inline-flex", alignItems: "center", gap: "0.25rem" }}
                    onClick={() => setCreateTempPassword(generateSecurePasswordHelper())}
                  >
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
                    </svg>
                    Generate Password
                  </button>
                </div>
                <input
                  type="text"
                  className="form-input"
                  value={createTempPassword}
                  onChange={(e) => setCreateTempPassword(e.target.value)}
                  required
                />
                <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                  Must meet policy (min 8 chars, 1 upper, 1 lower, 1 digit, 1 special). User will be prompted to change on first login.
                </span>
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.5rem", marginTop: "1.5rem" }}>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setShowCreateModal(false)}
                >
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={isSubmittingCreate}>
                  {isSubmittingCreate ? "Creating..." : "Create User"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* EDIT USER MODAL */}
      {showEditModal && selectedUser && (
        <div className="modal-backdrop">
          <div className="modal-content">
            <h2 style={{ marginTop: 0, color: "var(--spip-red)" }}>Edit User: {selectedUser.username}</h2>
            <form onSubmit={handleEditSubmit}>
              <div className="form-group">
                <label className="form-label">Full Name</label>
                <input
                  type="text"
                  className="form-input"
                  value={editFullName}
                  onChange={(e) => setEditFullName(e.target.value)}
                  required
                />
              </div>

              <div className="form-group">
                <label className="form-label">Username</label>
                <input
                  type="text"
                  className="form-input"
                  value={editUsername}
                  onChange={(e) => setEditUsername(e.target.value)}
                  required
                />
              </div>

              <div className="form-group">
                <label className="form-label">Email Address</label>
                <input
                  type="email"
                  className="form-input"
                  value={editEmail}
                  onChange={(e) => setEditEmail(e.target.value)}
                  required
                />
              </div>

              <div className="form-group">
                <label className="form-label">Role</label>
                <select
                  className="form-select"
                  value={editRole}
                  onChange={(e) => setEditRole(e.target.value)}
                >
                  <option value="Planner">Planner</option>
                  <option value="Manager">Manager</option>
                  <option value="Admin">Admin</option>
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Status</label>
                <select
                  className="form-select"
                  value={editIsActive ? "active" : "inactive"}
                  onChange={(e) => setEditIsActive(e.target.value === "active")}
                >
                  <option value="active">Active</option>
                  <option value="inactive">Inactive</option>
                </select>
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.5rem", marginTop: "1.5rem" }}>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setShowEditModal(false)}
                >
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={isSubmittingEdit}>
                  {isSubmittingEdit ? "Saving..." : "Save Changes"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* RESET PASSWORD MODAL */}
      {showResetModal && selectedUser && (
        <div className="modal-backdrop">
          <div className="modal-content">
            <h2 style={{ marginTop: 0, color: "var(--spip-red)" }}>Reset Password for {selectedUser.username}</h2>
            <form onSubmit={handleResetSubmit}>
              <div className="form-group">
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.35rem" }}>
                  <label className="form-label" style={{ margin: 0 }}>New Temporary Password</label>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    style={{ fontSize: "0.75rem", padding: "0.2rem 0.4rem", display: "inline-flex", alignItems: "center", gap: "0.25rem" }}
                    onClick={() => setResetPasswordVal(generateSecurePasswordHelper())}
                  >
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
                    </svg>
                    Generate Password
                  </button>
                </div>
                <input
                  type="text"
                  className="form-input"
                  value={resetPasswordVal}
                  onChange={(e) => setResetPasswordVal(e.target.value)}
                  required
                />
              </div>

              {generatedTempPwNotice && (
                <div className="alert alert-success" style={{ fontSize: "0.85rem" }}>
                  {generatedTempPwNotice}
                </div>
              )}

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.5rem", marginTop: "1.5rem" }}>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setShowResetModal(false)}
                >
                  Close
                </button>
                <button type="submit" className="btn btn-primary" disabled={isSubmittingReset}>
                  {isSubmittingReset ? "Resetting..." : "Reset Password"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
