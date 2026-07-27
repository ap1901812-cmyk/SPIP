import { useCallback, useEffect, useState } from "react";

import { useSearchParams } from "react-router-dom";
import { allocationsApi, domainApi, planningApi } from "../../api/services";
import type { Allocation, Material, Plant, Vendor } from "../../api/types";
import { useAuth } from "../useAuth";


export function AllocationsPage() {
  const { hasRole } = useAuth();
  const isPlannerOrAdmin = hasRole(["Planner", "Admin"]);

  const [searchParams] = useSearchParams();
  const initialAction = searchParams.get("action");
  const initialMaterial = searchParams.get("material") || "";
  const initialPlant = searchParams.get("plant") || "";

  const [allocations, setAllocations] = useState<Allocation[]>([]);
  const [plants, setPlants] = useState<Plant[]>([]);
  const [materials, setMaterials] = useState<Material[]>([]);
  const [vendors, setVendors] = useState<Vendor[]>([]);

  const [filterPlant, setFilterPlant] = useState(initialPlant);
  const [filterMaterial, setFilterMaterial] = useState(initialMaterial);
  const [filterStatus, setFilterStatus] = useState("");

  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // New allocation form modal state
  const [showCreateModal, setShowCreateModal] = useState(initialAction === "new");
  const [formPlant, setFormPlant] = useState(initialPlant || "PLANT-1000");
  const [formMaterial, setFormMaterial] = useState(initialMaterial || "MAT-1001");
  const [formVendor, setFormVendor] = useState("");
  const [formQuantity, setFormQuantity] = useState<number>(100);
  const [formError, setFormError] = useState<string | null>(null);
  const [availableCap, setAvailableCap] = useState<number | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Edit modal state
  const [editAlloc, setEditAlloc] = useState<Allocation | null>(null);
  const [editQuantity, setEditQuantity] = useState<number>(0);

  const loadAllocations = useCallback(() => {
    setIsLoading(true);
    setError(null);
    allocationsApi
      .listAllocations({
        plant_code: filterPlant || undefined,
        material_code: filterMaterial || undefined,
        status: filterStatus || undefined,
      })
      .then((res) => setAllocations(res))
      .catch((err) =>
        setError(err instanceof Error ? err.message : "Failed to load allocations.")
      )
      .finally(() => setIsLoading(false));
  }, [filterPlant, filterMaterial, filterStatus]);

  useEffect(() => {
    domainApi.getPlants().then((p) => setPlants(p)).catch(() => {});
    domainApi.getMaterials().then((m) => setMaterials(m)).catch(() => {});
    domainApi.getVendors().then((v) => setVendors(v)).catch(() => {});
  }, []);

  useEffect(() => {
    loadAllocations();
  }, [loadAllocations]);


  // Check Planning Availability when form inputs change
  useEffect(() => {
    if (showCreateModal && formPlant && formMaterial) {
      planningApi
        .getMaterialPlanning(formMaterial, formPlant)
        .then((res) => setAvailableCap(res.planning_availability))
        .catch(() => setAvailableCap(null));
    }
  }, [showCreateModal, formPlant, formMaterial]);

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    setIsSubmitting(true);
    try {
      await allocationsApi.createAllocation({
        plant_code: formPlant,
        material_code: formMaterial,
        vendor_code: formVendor || undefined,
        allocated_quantity: Number(formQuantity),
      });
      setShowCreateModal(false);
      loadAllocations();
    } catch (err: unknown) {
      setFormError(err instanceof Error ? err.message : "Failed to create allocation.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleEditSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editAlloc) return;
    setFormError(null);
    setIsSubmitting(true);
    try {
      await allocationsApi.updateAllocation(editAlloc.id, {
        allocated_quantity: Number(editQuantity),
        version: editAlloc.version,
      });
      setEditAlloc(null);
      loadAllocations();
    } catch (err: unknown) {
      setFormError(err instanceof Error ? err.message : "Failed to update allocation.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSubmitForApproval = async (id: number) => {
    try {
      await allocationsApi.submitAllocation(id);
      loadAllocations();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to submit allocation.");
    }
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Vendor Material Allocations</h1>
          <div className="eyebrow" style={{ marginTop: "0.25rem" }}>
            V1 ALLOCATION LIFECYCLE & CAPACITY VALIDATION
          </div>
        </div>

        {isPlannerOrAdmin && (
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => {
              setFormError(null);
              setShowCreateModal(true);
            }}
          >
            + Create New Allocation
          </button>
        )}
      </div>

      <div className="card">
        <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap", marginBottom: "1rem" }}>
          <div>
            <label className="form-label" style={{ fontSize: "0.75rem" }}>
              Filter Plant
            </label>
            <select
              className="form-select"
              value={filterPlant}
              onChange={(e) => setFilterPlant(e.target.value)}
              style={{ width: "auto" }}
            >
              <option value="">All Plants</option>
              {plants.map((p) => (
                <option key={p.code} value={p.code}>
                  {p.code}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="form-label" style={{ fontSize: "0.75rem" }}>
              Filter Material
            </label>
            <select
              className="form-select"
              value={filterMaterial}
              onChange={(e) => setFilterMaterial(e.target.value)}
              style={{ width: "auto" }}
            >
              <option value="">All Materials</option>
              {materials.map((m) => (
                <option key={m.code} value={m.code}>
                  {m.code}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="form-label" style={{ fontSize: "0.75rem" }}>
              Filter Status
            </label>
            <select
              className="form-select"
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              style={{ width: "auto" }}
            >
              <option value="">All Statuses</option>
              <option value="DRAFT">DRAFT</option>
              <option value="PENDING_APPROVAL">PENDING_APPROVAL</option>
              <option value="APPROVED">APPROVED</option>
              <option value="REJECTED">REJECTED</option>
            </select>
          </div>
        </div>

        {isLoading ? (
          <div style={{ padding: "2rem", textAlign: "center", color: "var(--text-muted)" }}>
            Loading allocations...
          </div>
        ) : error ? (
          <div className="alert alert-error">{error}</div>
        ) : allocations.length === 0 ? (
          <div style={{ padding: "2rem", textAlign: "center", color: "var(--text-muted)" }}>
            No allocations found matching filters.
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
                  <th>Status</th>
                  <th>Created By</th>
                  <th>SAP Ref</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {allocations.map((alloc) => (
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
                      <span className={`badge-status ${alloc.status}`}>{alloc.status}</span>
                    </td>
                    <td>
                      <small>{alloc.created_by_email}</small>
                    </td>
                    <td>
                      <code>{alloc.sap_reference_id || "—"}</code>
                    </td>
                    <td>
                      <div style={{ display: "flex", gap: "0.35rem" }}>
                        {isPlannerOrAdmin && alloc.status === "DRAFT" && (
                          <>
                            <button
                              type="button"
                              className="btn btn-secondary"
                              style={{ padding: "0.2rem 0.4rem", fontSize: "0.75rem" }}
                              onClick={() => {
                                setEditAlloc(alloc);
                                setEditQuantity(alloc.allocated_quantity);
                                setFormError(null);
                              }}
                            >
                              Edit
                            </button>
                            <button
                              type="button"
                              className="btn btn-primary"
                              style={{ padding: "0.2rem 0.4rem", fontSize: "0.75rem" }}
                              onClick={() => handleSubmitForApproval(alloc.id)}
                            >
                              Submit
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

      {/* Create Modal */}
      {showCreateModal && (
        <div className="modal-backdrop">
          <div className="modal-content">
            <h3 style={{ marginTop: 0 }}>Create Vendor Allocation</h3>

            {formError && <div className="alert alert-error">{formError}</div>}

            <form onSubmit={handleCreateSubmit}>
              <div className="form-group">
                <label className="form-label">Target Plant</label>
                <select
                  className="form-select"
                  value={formPlant}
                  onChange={(e) => setFormPlant(e.target.value)}
                  required
                >
                  {plants.map((p) => (
                    <option key={p.code} value={p.code}>
                      {p.code} ({p.name})
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Material</label>
                <select
                  className="form-select"
                  value={formMaterial}
                  onChange={(e) => setFormMaterial(e.target.value)}
                  required
                >
                  {materials.map((m) => (
                    <option key={m.code} value={m.code}>
                      {m.code} ({m.description})
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Vendor (Optional)</label>
                <select
                  className="form-select"
                  value={formVendor}
                  onChange={(e) => setFormVendor(e.target.value)}
                >
                  <option value="">Select Primary/Preferred Vendor</option>
                  {vendors.map((v) => (
                    <option key={v.code} value={v.code}>
                      {v.code} ({v.name})
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Allocated Quantity (KG)</label>
                <input
                  type="number"
                  className="form-input"
                  min="0.1"
                  step="any"
                  value={formQuantity}
                  onChange={(e) => setFormQuantity(Number(e.target.value))}
                  required
                />
                {availableCap !== null && (
                  <small style={{ display: "block", marginTop: "0.25rem", color: "var(--text-muted)" }}>
                    Current Effective Planning Availability: <strong>{availableCap} KG</strong>
                  </small>
                )}
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.5rem", marginTop: "1.5rem" }}>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setShowCreateModal(false)}
                >
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={isSubmitting}>
                  {isSubmitting ? "Saving..." : "Create Allocation Draft"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Modal */}
      {editAlloc && (
        <div className="modal-backdrop">
          <div className="modal-content">
            <h3 style={{ marginTop: 0 }}>Edit Allocation {editAlloc.allocation_number}</h3>

            {formError && <div className="alert alert-error">{formError}</div>}

            <form onSubmit={handleEditSubmit}>
              <div className="form-group">
                <label className="form-label">Allocated Quantity ({editAlloc.uom})</label>
                <input
                  type="number"
                  className="form-input"
                  min="0.1"
                  step="any"
                  value={editQuantity}
                  onChange={(e) => setEditQuantity(Number(e.target.value))}
                  required
                />
                <small style={{ display: "block", marginTop: "0.25rem", color: "var(--text-muted)" }}>
                  Current Version: <code>v{editAlloc.version}</code> (Optimistic Concurrency Protected)
                </small>
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.5rem", marginTop: "1.5rem" }}>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setEditAlloc(null)}
                >
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={isSubmitting}>
                  {isSubmitting ? "Updating..." : "Save Changes"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
