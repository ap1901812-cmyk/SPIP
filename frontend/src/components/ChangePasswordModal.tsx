import { useState } from "react";
import { authApi } from "../api/services";
import { useAuth } from "../app/useAuth";

export function ChangePasswordModal() {
  const { user, reloadUser } = useAuth();
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!user || !user.must_change_password) {
    return null;
  }

  // Password policy checks
  const hasMinLength = newPassword.length >= 8;
  const hasUpper = /[A-Z]/.test(newPassword);
  const hasLower = /[a-z]/.test(newPassword);
  const hasDigit = /[0-9]/.test(newPassword);
  const hasSpecial = /[!@#$%^&*(),.?":{}|<>\-_=+\\/]/.test(newPassword);
  const isPolicyValid = hasMinLength && hasUpper && hasLower && hasDigit && hasSpecial;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!isPolicyValid) {
      setError("Please ensure your new password meets all security requirements.");
      return;
    }

    if (newPassword !== confirmPassword) {
      setError("New passwords do not match.");
      return;
    }

    setIsSubmitting(true);
    try {
      await authApi.changePassword({
        current_password: currentPassword,
        new_password: newPassword,
      });
      await reloadUser();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to change password.";
      setError(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="modal-backdrop" style={{ zIndex: 1000 }}>
      <div className="modal-content" style={{ maxWidth: "480px" }}>
        <h2 style={{ marginTop: 0, color: "var(--spip-red)" }}>Password Change Required</h2>
        <p style={{ fontSize: "0.875rem", color: "var(--text-muted)", marginBottom: "1.25rem" }}>
          This account requires a new password before proceeding to the application.
        </p>

        {error && <div className="alert alert-error">{error}</div>}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label" htmlFor="currentPassword">
              Current / Temporary Password
            </label>
            <input
              id="currentPassword"
              type="password"
              className="form-input"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="newPassword">
              New Password
            </label>
            <input
              id="newPassword"
              type="password"
              className="form-input"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="confirmPassword">
              Confirm New Password
            </label>
            <input
              id="confirmPassword"
              type="password"
              className="form-input"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
            />
          </div>

          <div
            style={{
              background: "var(--surface-subtle)",
              padding: "0.75rem 1rem",
              borderRadius: "0.375rem",
              marginBottom: "1.25rem",
              fontSize: "0.8rem",
            }}
          >
            <div style={{ fontWeight: 600, marginBottom: "0.35rem" }}>Password Policy Requirements:</div>
            <ul style={{ margin: 0, paddingLeft: 0, listStyleType: "none", display: "flex", flexDirection: "column", gap: "0.25rem" }}>
              <li style={{ color: hasMinLength ? "var(--status-healthy-text)" : "var(--text-muted)", display: "flex", alignItems: "center", gap: "0.4rem" }}>
                {hasMinLength ? (
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12" /></svg>
                ) : (
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="9" /></svg>
                )}
                Minimum 8 characters
              </li>
              <li style={{ color: hasUpper ? "var(--status-healthy-text)" : "var(--text-muted)", display: "flex", alignItems: "center", gap: "0.4rem" }}>
                {hasUpper ? (
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12" /></svg>
                ) : (
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="9" /></svg>
                )}
                At least 1 uppercase letter (A-Z)
              </li>
              <li style={{ color: hasLower ? "var(--status-healthy-text)" : "var(--text-muted)", display: "flex", alignItems: "center", gap: "0.4rem" }}>
                {hasLower ? (
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12" /></svg>
                ) : (
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="9" /></svg>
                )}
                At least 1 lowercase letter (a-z)
              </li>
              <li style={{ color: hasDigit ? "var(--status-healthy-text)" : "var(--text-muted)", display: "flex", alignItems: "center", gap: "0.4rem" }}>
                {hasDigit ? (
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12" /></svg>
                ) : (
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="9" /></svg>
                )}
                At least 1 number (0-9)
              </li>
              <li style={{ color: hasSpecial ? "var(--status-healthy-text)" : "var(--text-muted)", display: "flex", alignItems: "center", gap: "0.4rem" }}>
                {hasSpecial ? (
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12" /></svg>
                ) : (
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="9" /></svg>
                )}
                At least 1 special character (!@#$%^&*)
              </li>
            </ul>
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            style={{ width: "100%" }}
            disabled={isSubmitting || !isPolicyValid}
          >
            {isSubmitting ? "Updating Password..." : "Update Password & Continue"}
          </button>
        </form>
      </div>
    </div>
  );
}
