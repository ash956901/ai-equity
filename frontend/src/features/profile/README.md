# Profile Feature

- The **ProfileView** component has been extracted into its own feature module (`features/profile`).
- `App.tsx` now imports `ProfileView` from this module and no longer contains any inline profile logic.
- All props (`dataMode`, `theme`, `onToggleTheme`, `onToggleDataMode`, `pushToast`) are wired through the top‑level `App` component.
- The feature is fully covered by the existing test suite (no new tests needed) and passes lint, unit tests, and production build.

**Status:** ✅ Extraction complete and verified.
