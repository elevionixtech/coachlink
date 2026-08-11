import { QueryClient } from '@tanstack/react-query'

// Shared singleton so it can be cleared on logout (see the auth store) — otherwise one
// org's cached data lingers into the next session on the same browser.
export const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } },
})
