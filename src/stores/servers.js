import { writable, derived } from 'svelte/store';

export const servers = writable([]);

export const serversLoading = writable(true);

export const serversError = writable(null);

export const serverHealth = writable({});

export const activeServerId = writable(null);

export const serverCount = derived(servers, $s => $s.length);

export const serversWithHealth = derived(
  [servers, serverHealth],
  ([$servers, $serverHealth]) =>
    $servers.map(s => ({
      ...s,
      _health: $serverHealth[s.server_id] || null,
    }))
);
