import { useCallback, useEffect, useState } from "react";
import { createProfile, listProfiles } from "../../shared/api/platform";
import type { AppProfile } from "../../shared/types/api";

interface ProfilePickerScreenProps {
  onProfileSelected: (profile: AppProfile) => void;
}

const AVATAR_COLORS_HEX = [
  "#0f86ba",
  "#1f9d72",
  "#cf4f4f",
  "#7C3AED",
  "#D97706",
  "#0891B2",
  "#BE185D",
];

function getInitials(name: string): string {
  return name
    .split(" ")
    .map((w) => w[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);
}

export function ProfilePickerScreen({ onProfileSelected }: ProfilePickerScreenProps) {
  const [profiles, setProfiles] = useState<AppProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [newName, setNewName] = useState("");
  const [selectedColorIdx, setSelectedColorIdx] = useState(0);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadProfiles = useCallback(async () => {
    try {
      const data = await listProfiles();
      setProfiles(data);
    } catch {
      setError("Could not load profiles. Make sure the backend is running.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadProfiles();
  }, [loadProfiles]);

  const handleCreate = useCallback(async () => {
    if (!newName.trim()) return;
    setCreating(true);
    setError(null);
    try {
      const profile = await createProfile(newName.trim(), AVATAR_COLORS_HEX[selectedColorIdx]);
      setProfiles((prev) => [...prev, profile]);
      setShowAdd(false);
      setNewName("");
      onProfileSelected(profile);
    } catch {
      setError("Failed to create profile. Try again.");
    } finally {
      setCreating(false);
    }
  }, [newName, selectedColorIdx, onProfileSelected]);

  return (
    <div className="picker-overlay">
      <div className="picker-container">
        {/* Brand header — matches sidebar brand block */}
        <div className="picker-brand">
          <div className="brand-mark" style={{ width: 44, height: 44, borderRadius: 13 }}>
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
            </svg>
          </div>
          <div>
            <p className="brand-title" style={{ fontSize: "1.1rem" }}>AI Equity</p>
            <p className="brand-subtitle">Research Platform</p>
          </div>
        </div>

        <div className="picker-heading-wrap">
          <h1 className="picker-heading">Who's investing?</h1>
          <p style={{ color: "var(--muted)", margin: 0, fontSize: "0.88rem" }}>
            Select your profile to continue
          </p>
        </div>

        {error && <div className="notice warning">{error}</div>}

        {loading ? (
          <p style={{ color: "var(--muted)", textAlign: "center" }}>Loading profiles...</p>
        ) : (
          <div className="picker-grid">
            {profiles.map((profile) => (
              <button
                key={profile.id}
                type="button"
                className="picker-card"
                onClick={() => onProfileSelected(profile)}
              >
                <div
                  className="picker-avatar"
                  style={{ background: profile.avatar_color ?? "var(--brand)" }}
                >
                  {getInitials(profile.name)}
                </div>
                <span className="picker-name">{profile.name}</span>
              </button>
            ))}

            {!showAdd && (
              <button
                type="button"
                className="picker-card"
                onClick={() => setShowAdd(true)}
              >
                <div className="picker-avatar picker-add-avatar">+</div>
                <span className="picker-name">Add Profile</span>
              </button>
            )}
          </div>
        )}

        {showAdd && (
          <div className="list-card picker-add-form">
            <p style={{ margin: "0 0 12px", fontWeight: 600, color: "var(--ink)" }}>
              New Profile
            </p>
            <input
              className="search-input"
              placeholder="Enter name (e.g. Shamanth)"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") void handleCreate();
                if (e.key === "Escape") setShowAdd(false);
              }}
              autoFocus
              style={{ marginBottom: 12 }}
            />
            <div className="chip-row" style={{ marginBottom: 14, justifyContent: "flex-start" }}>
              {AVATAR_COLORS_HEX.map((hex, idx) => (
                <button
                  key={hex}
                  type="button"
                  style={{
                    width: 28,
                    height: 28,
                    borderRadius: "50%",
                    background: hex,
                    border: selectedColorIdx === idx
                      ? "3px solid var(--ink)"
                      : "2px solid transparent",
                    cursor: "pointer",
                    padding: 0,
                    flexShrink: 0,
                  }}
                  onClick={() => setSelectedColorIdx(idx)}
                />
              ))}
            </div>
            <div className="chip-row">
              <button
                type="button"
                className="primary-btn"
                disabled={!newName.trim() || creating}
                onClick={() => void handleCreate()}
              >
                {creating ? "Creating..." : "Create Profile"}
              </button>
              <button
                type="button"
                className="secondary-btn"
                onClick={() => {
                  setShowAdd(false);
                  setNewName("");
                }}
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
