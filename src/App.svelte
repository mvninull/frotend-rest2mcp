<script>
  import { onMount } from 'svelte';
  import Landing from './Landing.svelte';
  import Dashboard from './Dashboard.svelte';

  let currentRoute = 'landing';

  function handleRoute() {
    const hash = window.location.hash;
    if (hash.includes('#/dashboard')) {
      currentRoute = 'dashboard';
    } else {
      currentRoute = 'landing';
    }
  }

  onMount(() => {
    // Escuta alterações de rota
    window.addEventListener('hashchange', handleRoute);
    handleRoute(); // Verificação inicial

    // Interceta cliques em links para navegação SPA fluida
    const handleLinkClick = (e) => {
      const anchor = e.target.closest('a');
      if (anchor && anchor.href) {
        const href = anchor.getAttribute('href') || '';
        if (href.endsWith('dashboard.html') || href === 'dashboard.html') {
          e.preventDefault();
          window.location.hash = '#/dashboard';
        } else if (href.endsWith('index.html') || href === 'index.html' || href === '/') {
          e.preventDefault();
          window.location.hash = '#/';
        }
      }
    };

    document.addEventListener('click', handleLinkClick);

    return () => {
      window.removeEventListener('hashchange', handleRoute);
      document.removeEventListener('click', handleLinkClick);
    };
  });
</script>

{#if currentRoute === 'dashboard'}
  <Dashboard />
{:else}
  <Landing />
{/if}
