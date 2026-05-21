<script>
  import { onMount } from 'svelte';
  import './Landing.css';

  onMount(() => {


      // ─── CONFIGURAÇÃO SUPABASE ─────────────────────────────
      // Valores por omissão do Supabase Sandbox do projeto
      const SUPABASE_URL = "https://zcfrbhrqvneomseqmqam.supabase.co";
      const SUPABASE_ANON_KEY = "sb_publishable_mF0UgfLvgZN5OupdpsSa0A_ibOcfzq4";
      const supabaseClient = supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

      function showLoading(btn) {
        if (!btn) return;
        btn.disabled = true;
        const spinner = btn.querySelector('.spinner');
        if (spinner) spinner.style.display = 'inline-block';
        const text = btn.querySelector('.btn-text');
        if (text) text.style.opacity = '0';
      }
      function hideLoading(btn) {
        if (!btn) return;
        btn.disabled = false;
        const spinner = btn.querySelector('.spinner');
        if (spinner) spinner.style.display = 'none';
        const text = btn.querySelector('.btn-text');
        if (text) text.style.opacity = '1';
      }

      // Função de Login com Provedor Social
      async function loginWith(provider) {
        const btn = document.querySelector(`.${provider}-btn`);
        showLoading(btn);
        const { error } = await supabaseClient.auth.signInWithOAuth({
          provider,
          options: {
            redirectTo: window.location.origin
          }
        });
        if (error) {
          hideLoading(btn);
          alert("Erro no login: " + error.message);
        }
      }

      // Função de Login com Email/Senha
      async function loginWithEmail(e) {
        e.preventDefault();
        const btn = e.target.querySelector('.auth-submit');
        showLoading(btn);
        const email = document.getElementById("loginEmail").value;
        const password = document.getElementById("loginPassword").value;
        
        const { error } = await supabaseClient.auth.signInWithPassword({
          email,
          password
        });
        if (error) {
          hideLoading(btn);
          if (error.message.includes("Invalid login credentials") || error.message.includes("not found")) {
            const { error: signUpError } = await supabaseClient.auth.signUp({
              email,
              password
            });
            if (signUpError) {
               alert("Erro no registo/login: " + signUpError.message);
            } else {
               alert("Registo efetuado! Verifique o seu email para confirmar a conta (caso exigido), ou tente fazer login novamente.");
            }
          } else {
            alert("Erro no login: " + error.message);
          }
        } else {
          closeLoginModal();
          if (localStorage.getItem("pending_pro")) {
            localStorage.removeItem("pending_pro");
            setTimeout(showPayPalModal, 300);
          } else {
            window.history.pushState({}, '', '?page=dashboard'); window.dispatchEvent(new PopStateEvent('popstate'));
          }
        }
      }

      // Verifica se existe sessão ativa
      function restoreSession() {
        const token = localStorage.getItem("supabase_token");
        if (token) {
          // Utilizador já autenticado -> Ajusta botões
          const dbBtn = document.getElementById("dashboardBtn");
          if (dbBtn) {
            dbBtn.textContent = "Ir para Dashboard";
            dbBtn.onclick = (e) => { 
              e.preventDefault();
              window.history.pushState({}, '', '?page=dashboard'); window.dispatchEvent(new PopStateEvent('popstate')); 
            };
          }
          const createBtn = document.getElementById("createServerBtn");
          if (createBtn) {
            createBtn.textContent = "Ir para Dashboard";
            createBtn.href = "?page=dashboard";
          }
        }
      }

      // Intercepta e escuta alterações de autenticação
      supabaseClient.auth.onAuthStateChange((event, session) => {
        if (session?.access_token) {
          localStorage.setItem("supabase_token", session.access_token);
          if (session.user) localStorage.setItem("supabase_user_id", session.user.id);
          if (event === "SIGNED_IN" || event === "INITIAL_SESSION") {
            if (localStorage.getItem("pending_pro")) {
              localStorage.removeItem("pending_pro");
              restoreSession();
              closeLoginModal();
              setTimeout(showPayPalModal, 300);
            } else {
              restoreSession();
            }
          } else {
            restoreSession();
          }
        }
      });

      // Inicializa sessão
      restoreSession();

      // Modal de login dinâmico
      function openLoginModal() {
        if (localStorage.getItem("supabase_token")) {
          window.history.pushState({}, '', '?page=dashboard'); window.dispatchEvent(new PopStateEvent('popstate'));
          return;
        }
        document.getElementById("loginModal").classList.add("open");
      }

      function closeLoginModal() {
        document.getElementById("loginModal").classList.remove("open");
      }

      let paypalRendered = false;
      function showPayPalModal() {
        document.getElementById("paypalModal").classList.add("open");
        const ppc = document.getElementById("paypal-button-container-landing");
        if (!ppc) return;
        ppc.style.display = "block";
        if (typeof paypal !== "undefined" && !paypalRendered) {
          paypalRendered = true;
          paypal.Buttons({
            createSubscription: function(data, actions) {
              return actions.subscription.create({
                plan_id: "P-26B313696D799031LNIFNUDQ",
                custom_id: localStorage.getItem("supabase_user_id") || ""
              });
            },
            onApprove: function(data) {
              alert("Subscrição ativada!");
              document.getElementById("paypalModal").classList.remove("open");
            },
            onError: function(err) {
              console.error("PayPal error:", err);
              alert("Erro ao processar pagamento.");
            }
          }).render("#paypal-button-container-landing");
        }
      }
      function closePayPalModal() {
        document.getElementById("paypalModal").classList.remove("open");
      }

      function handleFreePlan() {
        if (localStorage.getItem("supabase_token")) {
          window.history.pushState({}, '', '?page=dashboard'); window.dispatchEvent(new PopStateEvent('popstate'));
        } else {
          openLoginModal();
        }
      }
      function handleProPlan() {
        if (localStorage.getItem("supabase_token")) {
          showPayPalModal();
        } else {
          localStorage.setItem("pending_pro", "true");
          openLoginModal();
        }
      }

      // Configura os botões da UI para abrirem o modal
      document.getElementById('dashboardBtn')?.addEventListener('click', function(e) {
        if (!localStorage.getItem("supabase_token")) {
          e.preventDefault();
          openLoginModal();
        } else {
          window.history.pushState({}, '', '?page=dashboard'); window.dispatchEvent(new PopStateEvent('popstate'));
        }
      });
      
      document.getElementById('createServerBtn')?.addEventListener('click', function(e) {
        if (!localStorage.getItem("supabase_token")) {
          e.preventDefault();
          openLoginModal();
        } else {
          e.preventDefault();
          window.history.pushState({}, '', '?page=dashboard'); window.dispatchEvent(new PopStateEvent('popstate'));
        }
      });
      
      // Expose to window for inline HTML onclick handlers
      window.loginWith = loginWith;
      window.openLoginModal = openLoginModal;
      window.closeLoginModal = closeLoginModal;
      window.loginWithEmail = loginWithEmail;
      window.showPayPalModal = showPayPalModal;
      window.closePayPalModal = closePayPalModal;
      window.handleFreePlan = handleFreePlan;
      window.handleProPlan = handleProPlan;
      window.scrollTo = (id) => document.getElementById(id).scrollIntoView({ behavior: 'smooth' });
    
  });
</script>


    <!-- NAV -->
    <nav>
      <div class="nav-inner">
        <div class="logo"><span class="logo-dot"></span>rest2mcp</div>
        <ul class="nav-links">
          <li><button class="nav-link-btn" onclick="scrollTo('about')">Sobre</button></li>
          <li><button class="nav-link-btn" onclick="scrollTo('features')">Recursos</button></li>
          <li><button class="nav-link-btn" onclick="scrollTo('examples')">Exemplos</button></li>

        </ul>
        <div class="nav-actions">
          <button class="nav-btn" id="dashboardBtn">Entrar com Google</button>
        </div>
      </div>
    </nav>

    <!-- HERO -->
    <section class="hero">
      <div class="hero-bg"></div>
      <div class="hero-grid"></div>
      <div class="hero-inner">
        <div class="hero-tag"><span></span>v1.0.0 · Matias Fernando</div>
        <h1>Converte <em>qualquer</em><br />API em MCP</h1>
<p class="hero-sub">
           Conecte suas APIs REST ao Claude ou GPT em segundos. Sem servidor local, sem complexidade, 100% Stateless.
         </p>
        <div class="hero-ctas">
<a href="?page=dashboard" class="btn-primary" id="createServerBtn">Criar Servidor Grátis</a>

        </div>
        <div class="hero-badges">
          <div class="badge">
            <span class="svg-icon"><svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M9 1L3 9h6l-2 6 8-8H9l2-8z" fill="currentColor" stroke="none"/></svg></span> <b>Segundos</b> de configuração
          </div>
          <div class="badge"><span class="svg-icon"><svg width="11" height="11" viewBox="0 0 12 12" fill="currentColor"><path d="M6 0l1.2 4.8L12 6l-4.8 1.2L6 12 4.8 7.2 0 6l4.8-1.2z"/></svg></span> <b>Zero</b> código necessário</div>
          <div class="badge">
            <span class="svg-icon"><svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"><path d="M13 8A5 5 0 112 5.5"/><path d="M2 2v4h4"/></svg></span> <b>Swagger 2.0</b> → OpenAPI 3.0
          </div>
        </div>
      </div>
    </section>

    <!-- ABOUT -->
    <section class="section" id="about">
      <div class="section-label">// 01 — Sobre o projeto</div>
      <h2>Por que este<br />projecto existe?</h2>
      <div class="about-layout">
        <div>
          <p style="color: var(--muted); margin-bottom: 1rem; font-weight: 300">
            LLMs modernos têm capacidades incríveis, mas não conseguem interagir
            diretamente com APIs REST existentes. O Protocolo MCP resolve isso,
            mas exige que cada API tenha um servidor dedicado.
          </p>
          <p
            style="color: var(--muted); margin-bottom: 1.5rem; font-weight: 300"
          >
            O
            <strong style="color: var(--ink)">rest2mcp</strong>
            elimina essa barreira: forneces a URL da spec OpenAPI/Swagger, e o
            servidor gera automaticamente as ferramentas MCP correspondentes.
          </p>

          <div class="callout problem">
            <strong><span style="display:inline-flex;align-items:center;gap:5px;"><svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="#ff5c35" stroke-width="2.2" stroke-linecap="round"><line x1="3" y1="3" x2="13" y2="13"/><line x1="13" y1="3" x2="3" y2="13"/></svg> Problema</span></strong>
            LLMs não conseguem chamar endpoints REST diretamente, e cada API
            precisaria de um servidor MCP dedicado.
          </div>
          <div class="callout solution">
            <strong><span style="display:inline-flex;align-items:center;gap:5px;"><svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="#00d4aa" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 8l4 4 8-8"/></svg> Solução</span></strong>
            Conversão automática de specs OpenAPI/Swagger para ferramentas MCP —
            sem código adicional.
          </div>

          <div class="highlights-box">
            <h4><span style="display:inline-flex;align-items:center;gap:6px;"><svg width="13" height="13" viewBox="0 0 16 16" fill="#1a56ff"><path d="M8 1l1.5 4.5L14 7l-4.5 1.5L8 13l-1.5-4.5L2 7l4.5-1.5z"/></svg> Destaques fundamentais</span></h4>
            <div class="hl-item">
              <span class="hl-num">01</span>
              <p>
                <strong>Zero código</strong> — Apenas configure a URL da spec no
                cliente MCP.
              </p>
            </div>
            <div class="hl-item">
              <span class="hl-num">02</span>
              <p>
                <strong>Múltiplas APIs</strong> — Configure várias APIs no mesmo
                cliente simultaneamente.
              </p>
            </div>
            <div class="hl-item">
              <span class="hl-num">03</span>
              <p>
                <strong>Conversão automática</strong> — Swagger 2.0 é convertido
                para OpenAPI 3.0 automaticamente.
              </p>
            </div>
          </div>
        </div>

        <div class="how-it-works">
          <h3>Como funciona?</h3>
            O rest2mcp corre na nossa infraestrutura na nuvem. Forneces a URL da
            spec OpenAPI/Swagger e o servidor gera automaticamente as ferramentas
            MCP correspondentes — sem instalar nada localmente.
        </div>
      </div>
    </section>

    <!-- ARCHITECTURE & SECURITY -->
    <section class="section" id="security">
      <div class="section-label">// Segurança</div>
      <h2>Sua privacidade é<br />nossa prioridade.</h2>
      <div style="margin-bottom: 2rem;">
        <span class="zk-badge"><span style="display:inline-flex;align-items:center;gap:5px;"><svg width="10" height="10" viewBox="0 0 12 12" fill="currentColor"><path d="M6 0l1.2 4.8L12 6l-4.8 1.2L6 12 4.8 7.2 0 6l4.8-1.2z"/></svg> Arquitetura Zero-Knowledge</span></span>
      </div>
      <div class="sec-grid" style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 1.5rem;">
        <div class="callout solution" style="margin: 0;">
          <strong>Stateless</strong>
          Não possuímos banco de dados de credenciais. Os tokens vivem apenas na memória efêmera durante a sessão.
        </div>
        <div class="callout solution" style="margin: 0;">
          <strong>End-to-End</strong>
          A conexão é feita diretamente entre o LLM e a sua infraestrutura através da nossa ponte.
        </div>
        <div class="callout solution" style="margin: 0;">
          <strong>Auditável</strong>
          Logs transparentes para você monitorar exatamente o que a IA está acessando.
        </div>
      </div>
    </section>

    <!-- FEATURES -->
    <div class="features-bg">
      <div class="features-section" id="features">
        <div class="section-label">// 03 — Recursos</div>
        <h2 style="color: white">Tudo o que precisas,<br />pronto a usar.</h2>
        <p class="section-desc">
          Seis recursos que tornam o rest2mcp a escolha mais rápida para
          conectar LLMs às tuas APIs.
        </p>

        <div class="features-grid">
          <div class="feat-card">
            <div class="feat-icon"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.7)" stroke-width="1.6" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><path d="M2 12h20M12 2a15.3 15.3 0 010 20M12 2a15.3 15.3 0 000 20"/></svg></div>
            <h3>Qualquer API, Zero Código</h3>
            <p>
              Apenas configura a URL da spec. Sem desenvolver servidores MCP
              individuais para cada API.
            </p>
          </div>
          <div class="feat-card">
            <div class="feat-icon"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.7)" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0110 0v4"/></svg></div>
            <h3>Gestão de Sessão</h3>
            <p>
              O servidor detecta automaticamente endpoints de login na
              especificação. O LLM faz autenticação uma vez, e o token é
              injetado em todas as chamadas seguintes — sem intervenção manual.
            </p>
          </div>
          <div class="feat-card">
            <div class="feat-icon"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.7)" stroke-width="1.6" stroke-linecap="round"><path d="M21 2v6h-6"/><path d="M3 12a9 9 0 0115-6.7L21 8"/><path d="M3 22v-6h6"/><path d="M21 12a9 9 0 01-15 6.7L3 16"/></svg></div>
            <h3>Múltiplas APIs Simultâneas</h3>
            <p>
              Configura várias APIs no mesmo cliente MCP, cada uma com o seu
              próprio servidor.
            </p>
          </div>
          <div class="feat-card">
            <div class="feat-icon"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.7)" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4"/></svg></div>
            <h3>Conversão Automática</h3>
            <p>
              Swagger 2.0 desatualizado? Convertido automaticamente para OpenAPI
              3.0 via swagger2openapi.
            </p>
          </div>
          <div class="feat-card">
            <div class="feat-icon"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.7)" stroke-width="1.6" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="M16.5 16.5L21 21"/></svg></div>
            <h3>Modo Inspector</h3>
            <p>
              Testa e depura as ferramentas geradas com o MCP Inspector
              integrado no próprio servidor.
            </p>
          </div>
        </div>
      </div>
    </div>

    <!-- PRICING -->
    <div class="features-bg">
      <div class="features-section" id="pricing">
        <div class="section-label">// Planos</div>
        <h2 style="color: white">Escolha o<br />melhor plano.</h2>
        <p class="section-desc">
          Do hobby ao enterprise — o rest2mcp se adapta às suas necessidades.
        </p>
        <div class="pricing-grid">
          <div class="feat-card pricing-card">
            <div class="pricing-name">Hobby</div>
            <div class="pricing-price">R$ 0</div>
            <div class="pricing-desc">Para testes e experimentação</div>
            <ul class="pricing-features">
              <li><span class="check-icon"><svg width="12" height="12" viewBox="0 0 14 14" fill="none" stroke="#00d4aa" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1.5 7l4 4 7-7"/></svg></span> 1 Servidor Ativo</li>
              <li><span class="check-icon"><svg width="12" height="12" viewBox="0 0 14 14" fill="none" stroke="#00d4aa" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1.5 7l4 4 7-7"/></svg></span> Logs das últimas 24h</li>
              <li><span class="check-icon"><svg width="12" height="12" viewBox="0 0 14 14" fill="none" stroke="#00d4aa" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1.5 7l4 4 7-7"/></svg></span> Rate limiting padrão</li>
            </ul>
            <button class="btn-ghost" style="display: block; text-align: center; color: white; border-color: rgba(255,255,255,0.2); width: 100%; cursor: pointer;" onclick="handleFreePlan()">Começar Grátis</button>
          </div>
          <div class="feat-card pricing-card popular">
            <span class="pricing-popular-badge">POPULAR</span>
            <div class="pricing-name">Pro</div>
            <div class="pricing-price">$ <span style="font-size: 1.5rem;">/mês</span></div>
            <div class="pricing-desc">Para uso profissional</div>
            <ul class="pricing-features">
              <li><span class="check-icon"><svg width="12" height="12" viewBox="0 0 14 14" fill="none" stroke="#00d4aa" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1.5 7l4 4 7-7"/></svg></span> Servidores Ilimitados</li>
              <li><span class="check-icon"><svg width="12" height="12" viewBox="0 0 14 14" fill="none" stroke="#00d4aa" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1.5 7l4 4 7-7"/></svg></span> Logs completos</li>
              <li><span class="check-icon"><svg width="12" height="12" viewBox="0 0 14 14" fill="none" stroke="#00d4aa" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1.5 7l4 4 7-7"/></svg></span> Alta prioridade (sem cold-start)</li>
              <li><span class="check-icon"><svg width="12" height="12" viewBox="0 0 14 14" fill="none" stroke="#00d4aa" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1.5 7l4 4 7-7"/></svg></span> Suporte a APIs privadas via Tunneling</li>
            </ul>
            <button class="btn-primary" style="display: block; text-align: center; width: 100%; cursor: pointer;" onclick="handleProPlan()">Assinar Pro</button>
          </div>
          <div class="feat-card pricing-card">
            <div class="pricing-name">Enterprise</div>
            <div class="pricing-price" style="font-size: 1.8rem;">Sob Consulta</div>
            <div class="pricing-desc">Para organizações</div>
            <ul class="pricing-features">
              <li><span class="check-icon"><svg width="12" height="12" viewBox="0 0 14 14" fill="none" stroke="#00d4aa" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1.5 7l4 4 7-7"/></svg></span> Suporte dedicado</li>
              <li><span class="check-icon"><svg width="12" height="12" viewBox="0 0 14 14" fill="none" stroke="#00d4aa" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1.5 7l4 4 7-7"/></svg></span> SLAs de disponibilidade</li>
            </ul>
            <button class="btn-ghost" style="display: block; width: 100%; text-align: center; color: white; border-color: rgba(255,255,255,0.2); cursor: pointer;" onclick="top.location.href='mailto:sales@rest2mcp.com'">Falar com Vendas</button>
          </div>
        </div>
      </div>
    </div>

    <!-- DASHBOARD PREVIEW -->
    <section class="section" id="dashboard-preview">
      <div class="section-label">// Dashboard</div>
      <h2>Gerencie seus<br />servidores em tempo real.</h2>
      <p class="section-desc">
        Interface simples e direta para monitorar e gerenciar suas pontes MCP.
      </p>
      <div style="background: var(--ink); border-radius: 16px; padding: 2rem; border: 1px solid rgba(255,255,255,0.08);">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 1.5rem;">
          <div style="font-family: var(--display); font-size: 1.1rem; font-weight: 700; color: white;">Meus Servidores</div>
          <div style="display: flex; gap: 8px;">
            <span style="font-family: var(--mono); font-size: 0.65rem; color: var(--accent2); background: rgba(0,212,170,0.1); padding: 4px 10px; border-radius: 100px;">2 online</span>
            <span style="font-family: var(--mono); font-size: 0.65rem; color: var(--muted); background: rgba(255,255,255,0.05); padding: 4px 10px; border-radius: 100px;">1 offline</span>
          </div>
        </div>
        <div style="display: flex; flex-direction: column; gap: 8px; margin-bottom: 1.5rem;">
          <div class="dash-card">
            <div style="display: flex; align-items: center; gap: 12px;">
              <span class="dash-status-dot online"></span>
              <span style="font-family: var(--display); font-weight: 600; color: white; font-size: 0.9rem;">Minha API Principal</span>
            </div>
            <div style="display: flex; align-items: center; gap: 12px;">
              <span style="font-family: var(--mono); font-size: 0.7rem; color: var(--accent2);">Online</span>
              <button class="dash-copy-btn">Copy Connection URL</button>
            </div>
          </div>
          <div class="dash-card">
            <div style="display: flex; align-items: center; gap: 12px;">
              <span class="dash-status-dot online"></span>
              <span style="font-family: var(--display); font-weight: 600; color: white; font-size: 0.9rem;">Loja API (Teste)</span>
            </div>
            <div style="display: flex; align-items: center; gap: 12px;">
              <span style="font-family: var(--mono); font-size: 0.7rem; color: var(--accent2);">Online</span>
              <button class="dash-copy-btn">Copy Connection URL</button>
            </div>
          </div>
          <div class="dash-card">
            <div style="display: flex; align-items: center; gap: 12px;">
              <span class="dash-status-dot offline"></span>
              <span style="font-family: var(--display); font-weight: 600; color: white; font-size: 0.9rem;">API Legada (Swagger 2.0)</span>
            </div>
            <div style="display: flex; align-items: center; gap: 12px;">
              <span style="font-family: var(--mono); font-size: 0.7rem; color: var(--warn);">Offline</span>
              <button class="dash-copy-btn" disabled>Copy Connection URL</button>
            </div>
          </div>
        </div>
        <div class="dash-logs">
          <div class="dash-logs-header">
            <span class="log-dot"></span>
            <span style="font-family: var(--mono); font-size: 0.7rem; color: rgba(255,255,255,0.4);">Live Logs</span>
          </div>
          <div class="dash-logs-body">
            <div class="info-line">[INFO] IA chamou tool: 'get_user_by_id'</div>
            <div>[200 OK] Resposta enviada em 145ms</div>
            <div class="info-line" style="margin-top: 4px;">[INFO] IA chamou tool: 'list_products'</div>
            <div>[200 OK] Resposta enviada em 89ms</div>
          </div>
        </div>
      </div>
    </section>

    <!-- FAQ -->
    <section class="section" id="faq">
      <div class="section-label">// FAQ</div>
      <h2>Perguntas<br />frequentes.</h2>
      <p class="section-desc">
        Dúvidas comuns de desenvolvedores sobre o rest2mcp.
      </p>
      <div class="faq-grid">
        <div class="qs-step">
          <div class="qs-step-head">
            <h3>Quais especificações são aceitas?</h3>
          </div>
          <div class="qs-step-body">
            <p>Suporte total a OpenAPI 3.0 e conversão automática de Swagger 2.0.</p>
          </div>
        </div>
      </div>
    </section>

    <!-- EXAMPLES -->
    <section class="section" id="examples">
      <div class="section-label">// 04 — Exemplo prático</div>
      <h2>Uma API,<br />um servidor.</h2>
      <p class="section-desc">
        Configura a tua API no servidor MCP cloud. Basta definir a URL da spec.
      </p>

      <div class="apis-grid">
        <div class="api-card">
          <div class="api-card-head">
            <span class="api-head-icon"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><path d="M2 12h20M12 2a15.3 15.3 0 010 20M12 2a15.3 15.3 0 000 20"/></svg></span>
            <h3>PetStore API (Externa)</h3>
            <span class="api-badge warn">Swagger 2.0</span>
          </div>
          <div class="api-card-body">
            <div class="code-block">
              <pre><span class="hl">MCP_SPEC_URL</span>=https://petstore.swagger.io/v2/swagger.json
<span class="hl">MCP_SERVER_NAME</span>=PetStore API</pre>
            </div>
            <div class="api-note warn">
              <span style="display:inline-flex;align-items:center;gap:5px;vertical-align:middle;"><svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="#a05020" stroke-width="1.8" stroke-linecap="round"><path d="M8 1.5L1 14h14L8 1.5z"/><path d="M8 6v4"/><circle cx="8" cy="12" r=".7" fill="#a05020"/></svg></span> <strong>Swagger 2.0 desatualizado</strong> — O servidor
              converte automaticamente para OpenAPI 3.0 usando swagger2openapi.
            </div>
          </div>
        </div>

      </div>

      <div class="multi-config">
        <div class="multi-config-head">
          <span class="tip-dot"></span>
          <h4>Configuração no VS Code</h4>
        </div>
        <div class="code-block" style="border-radius: 0; margin: 0">
          <pre>&#123;
  <span class="hl">"mcp.servers"</span>: &#123;
    "petstore": &#123;
      "command": ".../venv/Scripts/python.exe",
      "args": ["main.py"],
      "env": &#123;
        "MCP_SPEC_URL": "https://petstore.swagger.io/v2/swagger.json",
        "MCP_SERVER_NAME": "PetStore API"
      &#125;
    &#125;
  &#125;
&#125;</pre>
        </div>
      </div>
    </section>

    <hr class="divider" />

    <!-- CONFIG -->
    <section class="section" id="config">
      <div class="section-label">// 07 — Configuração</div>
      <h2>Clientes MCP<br />suportados.</h2>
      <p class="section-desc">
        O rest2mcp funciona com qualquer cliente MCP. Basta apontar para a nossa ponte na nuvem.
      </p>
    </section>

    <!-- FOOTER -->
    <footer>
      <div class="footer-inner">
        <div class="footer-logo">rest2mcp</div>
        <p style="color: rgba(255, 255, 255, 0.35); font-size: 0.85rem">
          Versão 1.0.0 · Autor: Matias Fernando
        </p>
        <ul class="footer-links">
          <li>
            <a href="https://gofastmcp.com" target="_blank">FastMCP Docs</a>
          </li>
          <li>
            <a href="https://modelcontextprotocol.io" target="_blank"
              >MCP Protocol</a
            >
          </li>
          <li>
            <a href="https://swagger.io/specification/" target="_blank"
              >OpenAPI Spec</a
            >
          </li>
          <li><a href="https://rest2mcp.com/privacy" target="_blank">Termos de Privacidade</a></li>
        </ul>
        <p class="footer-copy">
          © 2026 rest2mcp. Todos os direitos reservados. Nenhum dado é retido em nossos servidores.
        </p>
      </div>
    </footer>

    <!-- MODAL DE LOGIN SOCIAL -->
    <div class="modal-overlay" id="loginModal">
      <div class="modal-box">
        <div class="modal-header">
          <h3>Entrar na sua Conta</h3>
          <p class="modal-sub">Selecione o seu provedor favorito para continuar</p>
        </div>
        <div class="social-login-container">
          <button class="social-btn google-btn" onclick="loginWith('google')">
            <svg viewBox="0 0 24 24" class="social-icon" fill="currentColor"><path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"/><path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/><path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/></svg>
            <span class="btn-text">Entrar com o Google</span>
            <span class="spinner" style="display:none;"><svg class="spinner-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/></svg></span>
          </button>
          <button class="social-btn github-btn" onclick="loginWith('github')">
            <svg viewBox="0 0 24 24" class="social-icon" fill="currentColor"><path d="M12 0C5.37 0 0 5.37 0 12c0 5.3 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61-.546-1.385-1.335-1.755-1.335-1.755-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 21.795 24 17.295 24 12 24 5.37 18.63 0 12 0z"/></svg>
            <span class="btn-text">Entrar com o GitHub</span>
            <span class="spinner" style="display:none;"><svg class="spinner-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/></svg></span>
          </button>
          <!--
          <button class="social-btn apple-btn" onclick="loginWith('apple')">
            <svg viewBox="0 0 24 24" class="social-icon" fill="currentColor"><path d="M17.05 20.28c-.98.95-2.05.8-3.08.35-1.09-.46-2.09-.48-3.24 0-1.44.62-2.2.44-3.06-.35C2.79 15.25 3.51 7.59 9.05 7.31c1.35.07 2.29.74 3.08.8 1.18-.24 2.31-.93 3.57-.84 1.51.12 2.65.72 3.4 1.8-3.12 1.87-2.38 5.98.48 7.13-.57 1.5-1.31 2.99-2.54 4.09zM12.03 7.25c-.15-2.23 1.66-4.07 3.74-4.25.29 2.58-2.34 4.5-3.74 4.25z"/></svg>
            Entrar com a Apple
          </button>
          -->
          <div class="email-login-divider"><span>ou use o seu email</span></div>
          <form class="email-login-form" onsubmit="loginWithEmail(event)">
            <input type="email" id="loginEmail" placeholder="O seu email" required class="auth-input" />
            <input type="password" id="loginPassword" placeholder="Palavra-passe" required class="auth-input" />
            <button type="submit" class="btn-primary auth-submit"><span class="btn-text">Entrar / Registar</span><span class="spinner" style="display:none;"><svg class="spinner-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/></svg></span></button>
          </form>
        </div>
        <div class="modal-actions" style="margin-top: 1.5rem; display: flex; justify-content: center;">
          <button class="btn-cancel" onclick="closeLoginModal()">Cancelar</button>
        </div>
      </div>
    </div>

    <!-- PAYPAL SUBSCRIPTION MODAL -->
    <div class="modal-overlay" id="paypalModal">
      <div class="modal-box">
        <div class="modal-header">
          <h3>Assinar Pro</h3>
          <p class="modal-sub">Finalize a sua subscrição mensal</p>
        </div>
        <div class="social-login-container">
          <div id="paypal-button-container-landing" style="display:block; min-height:200px;"></div>
        </div>
        <div class="modal-actions" style="margin-top: 1.5rem; display: flex; justify-content: center;">
          <button class="btn-cancel" onclick="closePayPalModal()">Cancelar</button>
        </div>
      </div>
    </div>

    <!-- Supabase SDK e Código de Autenticação -->
    
    
    <a href='https://ko-fi.com/F1F81ZH0QM' target='_blank' class="kofi-btn">
      <img height='36' style='border:0px;height:36px;' src='https://storage.ko-fi.com/cdn/kofi5.png?v=6' border='0' alt='Buy Me a Coffee at ko-fi.com' />
    </a>
  
