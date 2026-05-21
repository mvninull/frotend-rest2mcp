<script>
  import { onMount } from 'svelte';
  import Landing from './Landing.svelte';
  import Dashboard from './Dashboard.svelte';

  let currentRoute = 'landing';

  function handleRoute() {
    const params = new URLSearchParams(window.location.search);
    if (params.get('page') === 'dashboard') {
      currentRoute = 'dashboard';
    } else {
      currentRoute = 'landing';
    }
  }

  onMount(() => {
    window.addEventListener('popstate', handleRoute);
    handleRoute();

    const handleLinkClick = (e) => {
      const anchor = e.target.closest('a');
      if (anchor && anchor.href) {
        const href = anchor.getAttribute('href') || '';
        const url = new URL(href, window.location.origin);
        const params = new URLSearchParams(url.search);
        if (params.get('page') === 'dashboard') {
          e.preventDefault();
          window.history.pushState({}, '', href);
          handleRoute();
        }
      }
    };

    document.addEventListener('click', handleLinkClick);

    return () => {
      window.removeEventListener('popstate', handleRoute);
      document.removeEventListener('click', handleLinkClick);
    };
  });
</script>

{#if currentRoute === 'dashboard'}
  <Dashboard />
{:else}
  <Landing />
{/if}
