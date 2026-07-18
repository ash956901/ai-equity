const USER_KEY = "equityai-user-id";
// Demo user that owns the seeded portfolio/holdings in the backend. Real auth
// would replace this; until then every session maps to the demo account so the
// dashboard shows real data.
const DEMO_USER = "00000000-0000-0000-0000-000000000001";

export function getUserId(): string {
  // Demo mode: always map to the seeded account (overrides any stale random id).
  localStorage.setItem(USER_KEY, DEMO_USER);
  return DEMO_USER;
}

export function getExpertise(): "beginner" | "intermediate" | "advanced" {
  const v = localStorage.getItem("equityai-expertise");
  if (v === "beginner" || v === "advanced") return v;
  return "intermediate";
}
