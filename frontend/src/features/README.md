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
