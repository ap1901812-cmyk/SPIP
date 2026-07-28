import React from "react";

interface FilterBarProps {
  searchTerm: string;
  onSearchChange: (value: string) => void;
  selectedPlant?: string;
  onPlantChange?: (plantCode: string) => void;
  plants?: Array<{ id: number; code: string; name: string }>;
  selectedType?: string;
  onTypeChange?: (type: string) => void;
  types?: string[];
  placeholder?: string;
}

export const FilterBar: React.FC<FilterBarProps> = ({
  searchTerm,
  onSearchChange,
  selectedPlant,
  onPlantChange,
  plants = [],
  selectedType,
  onTypeChange,
  types = [],
  placeholder = "Search by code or description...",
}) => {
  return (
    <div className="card" style={{ padding: "1rem", marginBottom: "1.5rem" }}>
      <div style={{ display: "flex", flexWrap: "wrap", gap: "1rem", alignItems: "center" }}>
        <div style={{ flex: 1, minWidth: "220px" }}>
          <input
            type="text"
            className="form-input"
            placeholder={placeholder}
            value={searchTerm}
            onChange={(e) => onSearchChange(e.target.value)}
          />
        </div>

        {onPlantChange && (
          <div style={{ width: "200px" }}>
            <select
              className="form-select"
              value={selectedPlant || ""}
              onChange={(e) => onPlantChange(e.target.value)}
            >
              <option value="">All Plants</option>
              {plants.map((p) => (
                <option key={p.code} value={p.code}>
                  {p.code} - {p.name}
                </option>
              ))}
            </select>
          </div>
        )}

        {onTypeChange && types.length > 0 && (
          <div style={{ width: "160px" }}>
            <select
              className="form-select"
              value={selectedType || ""}
              onChange={(e) => onTypeChange(e.target.value)}
            >
              <option value="">All Types</option>
              {types.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>
    </div>
  );
};
