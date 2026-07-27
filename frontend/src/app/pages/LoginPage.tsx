import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../useAuth";


export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState("planner@spip.local");
  const [password, setPassword] = useState("Pass123!");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await login(email, password);
      navigate("/");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Authentication failed.";
      setError(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const setDemoUser = (demoEmail: string) => {
    setEmail(demoEmail);
    setPassword("Pass123!");
  };

  return (
    <div className="login-container">
      <div className="login-card">
        <div className="brand-container" style={{ justifyContent: "center", marginBottom: "1.5rem" }}>
          <div className="brand-logo">S</div>
          <div>
            <h1 className="brand-title">SPIP V1</h1>
            <div className="brand-subtitle">Smart Procurement & Inventory Planning</div>
          </div>
        </div>

        {error && <div className="alert alert-error">{error}</div>}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label" htmlFor="email">
              Email Address
            </label>
            <input
              id="email"
              type="email"
              className="form-input"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="password">
              Password
            </label>
            <input
              id="password"
              type="password"
              className="form-input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            style={{ width: "100%", marginTop: "0.5rem" }}
            disabled={isSubmitting}
          >
            {isSubmitting ? "Signing in..." : "Sign In to SPIP"}
          </button>
        </form>

        <div style={{ marginTop: "1.5rem", borderTop: "1px solid var(--border)", paddingTop: "1rem" }}>
          <div className="eyebrow" style={{ textAlign: "center", marginBottom: "0.5rem" }}>
            DEMO QUICK LOGIN PRESETS
          </div>
          <div style={{ display: "flex", gap: "0.5rem", justifyContent: "center" }}>
            <button
              type="button"
              className="btn btn-secondary"
              style={{ fontSize: "0.75rem", padding: "0.25rem 0.5rem" }}
              onClick={() => setDemoUser("planner@spip.local")}
            >
              Planner
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              style={{ fontSize: "0.75rem", padding: "0.25rem 0.5rem" }}
              onClick={() => setDemoUser("manager@spip.local")}
            >
              Manager
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              style={{ fontSize: "0.75rem", padding: "0.25rem 0.5rem" }}
              onClick={() => setDemoUser("admin@spip.local")}
            >
              Admin
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
