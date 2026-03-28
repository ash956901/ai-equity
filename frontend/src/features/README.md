# Frontend Feature Modules (Refactor Scaffold)

This directory is the target home for feature-sliced UI modules currently
implemented in `src/App.tsx`.

Planned folders:

- `chat/`
- `company/`
- `compare/`
- `portfolio/`
- `timeline/`
- `filings/`
- `news/`
- `profile/`
- `settings/`

Migration policy:

- move presentational view blocks first
- keep props stable while extracting
- then extract state/hooks
- finally move feature-specific API and types

## Current extraction status

- `features/dashboard/DashboardView.tsx` extracted from `App.tsx`
- `features/settings/SettingsView.tsx` extracted from `App.tsx`
- `features/discovery/DiscoveryView.tsx` extracted from `App.tsx`
- `features/timeline/TimelineView.tsx` extracted from `App.tsx`
- chat shared primitives extracted:
  - `features/chat/components/ThinkingDropdown.tsx`
  - `features/chat/components/ThinkingIndicator.tsx`
