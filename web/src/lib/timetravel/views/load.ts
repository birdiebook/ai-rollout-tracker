// Run-time documents for the time-travel views, only through the typed loaders of $lib/data (clientBundle). The
// views pass what they load straight to gate.ts; nothing from these documents is drawn uncut.
import { resolve } from '$app/paths';
import { clientBundle, type Bundle } from '$lib/data';

let cached: Bundle | null = null;
export function bundle(): Bundle {
  cached ??= clientBundle(fetch, resolve('/').replace(/\/$/, ''));
  return cached;
}
