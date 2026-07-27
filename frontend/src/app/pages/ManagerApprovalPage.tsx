import { useCallback, useEffect, useState } from "react";
import { allocationsApi } from "../../api/services";
import type { Allocation } from "../../api/types";
import { useAuth } from "../useAuth";

export function ManagerApprovalPage() {
  const { hasRole } = useAuth();
  const isManagerOrAdmin = hasRole(["Manager/Approver", "Admin"]);

  const [queue, setQueue] = useState<Allocation[]>([]);
  const [filterStatus, setFilterStatus] = useState<string>("PENDING_APPROVAL");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Rejection modal
  const [rejectingAlloc, setRejectingAlloc] = useState<Allocation | null>(null);
  const [rejectionReason, setRejectionReason] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [modalError, setModalError] = useState<string | null>(null);

  const loadQueue = useCallback(() => {
    setIsLoading(true);
    setError(null);
    allocationsApi
      .listAllocations({ status: filterStatus || undefined })
      .then((res) => setQueue(res))
      .catch((err) =>
        setError(err instanceof Error ? err.message : "Failed to load approval queue.")
      )
      .finally(() => setIsLoading(false));
  }, [filterStatus]);

  useEffect(() => {
    loadQueue();
  }, [loadQueue]);


  const handleApprove = async (id: number) => {
    setIsSubmitting(true);
    try {
      await allocationsApi.approveAllocation(id);
      loadQueue();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to approve allocation.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRejectSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!rejectingAlloc) return;
    setModalError(null);
    setIsSubmitting(true);
    try {
      await allocationsApi.rejectAllocation(rejectingAlloc.id, rejectionReason);
      setRejectingAlloc(null);
      setRejectionReason("");
      loadQueue();
    } catch (err: unknown) {
      setModalError(err instanceof Error ? err.message : "Failed to reject allocation.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Manager Approval Queue</h1>
          <div className="eyebrow" style={{ marginTop: "0.25rem" }}>
            GOVERNANCE, SAP WRITE-BACK & VENDOR ALLOCATION AUTHORIZATION
          </div>
        </div>

        <div>
          <select
            className="form-select"
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            style={{ width: "auto" }}
          >
            <option value="PENDING_APPROVAL">Pending Approval Only</option>
            <option value="APPROVED">Approved History</option>
            <option value="REJECTED">Rejected History</option>
            <option value="">All Statuses</option>
          </select>
        </div>
      </div>

      {!isManagerOrAdmin && (
        <div className="alert alert-error" style={{ marginBottom: "1rem" }}>
          <strong>RBAC Privilege Restriction:</strong> Your current role does not have Manager/Approver authorization. You can view the queue, but approval and rejection buttons require Manager/Approver or Admin role.
        </div>
      )}

      <div className="card">
        {isLoading ? (
          <div style={{ padding: "2rem", textAlign: "center", color: "var(--text-muted)" }}>
            Loading manager approval queue...
          </div>
        ) : error ? (
          <div className="alert alert-error">{error}</div>
        ) : queue.length === 0 ? (
          <div style={{ padding: "2rem", textAlign: "center", color: "var(--text-muted)" }}>
            No allocations currently in queue for selected status filter.
          </div>
        ) : (
          <div className="spip-table-container">
            <table className="spip-table">
              <thead>
                <tr>
                  <th>Allocation #</th>
                  <th>Plant</th>
                  <th>Material</th>
                  <th>Vendor</th>
                  <th>Quantity</th>
                  <th>Submitted By</th>
                  <th>Status</th>
                  <th>SAP Ref</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {queue.map((alloc) => (
                  <tr key={alloc.id}>
                    <td>
                      <strong>{alloc.allocation_number}</strong>
                    </td>
                    <td>{alloc.plant_code}</td>
                    <td>{alloc.material_code}</td>
                    <td>{alloc.vendor_code || "—"}</td>
                    <td>
                      <strong>
                        {alloc.allocated_quantity.toLocaleString()} {alloc.uom}
                      </strong>
                    </td>
                    <td>
                      <small>{alloc.created_by_email}</small>
                    </td>
                    <td>
                      <span className={`badge-status ${alloc.status}`}>{alloc.status}</span>
                    </td>
                    <td>
                      <code>{alloc.sap_reference_id || "—"}</code>
                    </td>
                    <td>
                      <div style={{ display: "flex", gap: "0.35rem" }}>
                        {alloc.status === "PENDING_APPROVAL" && (
                          <>
                            <button
                              type="button"
                              className="btn btn-success"
                              style={{ padding: "0.25rem 0.5rem", fontSize: "0.75rem" }}
                              disabled={!isManagerOrAdmin || isSubmitting}
                              onClick={() => handleApprove(alloc.id)}
                            >
                              Approve
                            </button>
                            <button
                              type="button"
                              className="btn btn-danger"
                              style={{ padding: "0.25rem 0.5rem", fontSize: "0.75rem" }}
                              disabled={!isManagerOrAdmin || isSubmitting}
                              onClick={() => {
                                setRejectingAlloc(alloc);
                                setRejectionReason("");
                                setModalError(null);
                              }}
                            >
                              Reject
                            </button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Reject Reason Modal */}
      {rejectingAlloc && (
        <div className="modal-backdrop">
          <div className="modal-content">
            <h3 style={{ marginTop: 0 }}>Reject Allocation {rejectingAlloc.allocation_number}</h3>

            {modalError && <div className="alert alert-error">{modalError}</div>}

            <form onSubmit={handleRejectSubmit}>
              <div className="form-group">
                <label className="form-label">Rejection Reason (Mandatory)</label>
                <textarea
                  className="form-textarea"
                  rows={4}
                  value={rejectionReason}
                  onChange={(e) => setRejectionReason(e.target.value)}
                  placeholder="Enter explicit reason for rejecting this allocation..."
                  required
                />
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.5rem", marginTop: "1.5rem" }}>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setRejectingAlloc(null)}
                >
                  Cancel
                </button>
                <button type="submit" className="btn btn-danger" disabled={isSubmitting || !rejectionReason.trim()}>
                  {isSubmitting ? "Rejecting..." : "Confirm Rejection"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
