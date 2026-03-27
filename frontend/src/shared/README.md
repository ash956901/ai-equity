# Shared Module Scaffold

Target shared locations during frontend refactor:

- `shared/api/` (split from `lib/api.ts`)
- `shared/types/` (cross-feature type definitions)
- `shared/ui/` (reusable components)
- `shared/utils/` (pure helpers)

This is a scaffold-only change to support incremental extraction from `App.tsx`.
