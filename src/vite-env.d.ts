/// <reference types="svelte" />
/// <reference types="vite/client" />

declare global {
  interface Window {
    showAppAlert?: (msg: string) => void;
  }
}

export {};
