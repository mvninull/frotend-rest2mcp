<script>
  import { onMount } from 'svelte';
  import './Landing.css';

  onMount(() => {

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

      async function loginWith(provider) {
        const btn = document.querySelector(`.${provider}-btn`);
        showLoading(btn);
        const { error } = await supabaseClient.auth.signInWithOAuth({
          provider,
          options: { redirectTo: window.location.origin }
        });
        if (error) {
          hideLoading(btn);
          alert("Erro no login: " + error.message);
        }
      }

      async function loginWithEmail(e) {
        e.preventDefault();
        const btn = e.target.querySelector('.auth-submit');
        showLoading(btn);
        const email = document.getElementById("loginEmail").value;
        const password = document.getElementById("loginPassword").value;

        const { error } = await supabaseClient.auth.signInWithPassword({ email, password });
        if (error) {
          if (error.message.includes("Invalid login credentials") || error.message.includes("not found")) {
            const { error: signUpError } = await supabaseClient.auth.signUp({ email, password });
            if (signUpError) {
              hideLoading(btn);
              alert("Erro no registo/login: " + signUpError.message);
            } else {
              hideLoading(btn);
              alert("Registo efetuado! Verifique o seu email para confirmar a conta (caso exigido), ou tente fazer login novamente.");
            }
          } else {
            hideLoading(btn);
            alert("Erro no login: " + error.message);
          }
        } else {
          closeLoginModal();
          window.location.hash = "#/dashboard";
        }
      }

      function restoreSession() {
        const token = localStorage.getItem("supabase_token");
        if (token) {
          const dbBtn = document.getElementById("dashboardBtn");
          if (dbBtn) {
            dbBtn.textContent = "Ir para Dashboard";
            dbBtn.onclick = (e) => { e.preventDefault(); window.location.hash = "#/dashboard"; };
          }
          const createBtn = document.getElementById("createServerBtn");
          if (createBtn) {
            createBtn.textContent = "Ir para Dashboard";
            createBtn.href = "dashboard.html";
          }
        }
      }

      supabaseClient.auth.onAuthStateChange((event, session) => {
        if (session?.access_token) {
          localStorage.setItem("supabase_token", session.access_token);
          restoreSession();
          if (event === "SIGNED_IN" || event === "INITIAL_SESSION") {
            window.location.hash = "#/dashboard";
          }
        }
      });

      restoreSession();

      function openLoginModal() {
        if (localStorage.getItem("supabase_token")) {
          window.location.hash = "#/dashboard";
          return;
        }
        document.getElementById("loginModal").classList.add("open");
      }

      function closeLoginModal() {
        const modal = document.getElementById("loginModal");
        if (modal) modal.classList.remove("open");
      }

      document.getElementById('dashboardBtn')?.addEventListener('click', function(e) {
        if (!localStorage.getItem("supabase_token")) {
          e.preventDefault();
          openLoginModal();
        } else {
          window.location.hash = '#/dashboard';
        }
      });

      document.getElementById('createServerBtn')?.addEventListener('click', function(e) {
        if (!localStorage.getItem("supabase_token")) {
          e.preventDefault();
          openLoginModal();
        } else {
          window.location.hash = '#/dashboard';
        }
      });

      function sendContactEmail(e) {
        e.preventDefault();
        const name = document.getElementById("contactName").value;
        const email = document.getElementById("contactEmail").value;
        const msg = document.getElementById("contactMessage").value;
        const subject = encodeURIComponent("Contacto via rest2mcp");
        const body = encodeURIComponent(`Nome: ${name}\nEmail: ${email}\n\nMensagem:\n${msg}`);
        window.open(`mailto:m4codexp@gmail.com?subject=${subject}&body=${body}`, '_blank');
      }

      window.loginWith = loginWith;
      window.openLoginModal = openLoginModal;
      window.closeLoginModal = closeLoginModal;
      window.loginWithEmail = loginWithEmail;
      window.sendContactEmail = sendContactEmail;

  });
</script>


    <!-- NAV -->
    <nav>
      <div class="nav-inner">
        <div class="logo"><span class="logo-dot"></span>rest2mcp</div>
        <ul class="nav-links">
          <li><a href="#about">Sobre</a></li>
          <li><a href="#features">Recursos</a></li>
          <li><a href="#examples">Exemplos</a></li>
          <li><a href="#contact">Contacto</a></li>
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
        <div class="hero-social">
          <a href="https://matiasdev30.github.io/#/" target="_blank" class="social-badge">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 013 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>
            Portfolio
          </a>
          <a href="https://www.linkedin.com/in/mvni-null/" target="_blank" class="social-badge">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/></svg>
            LinkedIn
          </a>
          <a href="https://github.com/mvninull" target="_blank" class="social-badge">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M12 0C5.37 0 0 5.37 0 12c0 5.3 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61-.546-1.385-1.335-1.755-1.335-1.755-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 21.795 24 17.295 24 12 24 5.37 18.63 0 12 0z"/></svg>
            GitHub
          </a>
        </div>
        <h1>Converte <em>qualquer</em><br />API em MCP</h1>
<p class="hero-sub">
           Conecte suas APIs REST ao Claude ou GPT em segundos. Sem servidor local, sem complexidade, 100% Stateless.
         </p>
        <div class="hero-ctas">
          <a href="dashboard.html" class="btn-primary" id="createServerBtn">Criar Servidor Grátis</a>
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
          <p
            style="
              color: var(--muted);
              font-size: 0.88rem;
              margin-bottom: 1.5rem;
            "
          >
            O processo é simples:
          </p>
          <div class="step-flow">
            <div class="flow-item">
              <div class="flow-num">01</div>
              <div class="flow-text">
                <strong>Configurar <code>MCP_SPEC_URL</code></strong>
                <span>Define a variável no teu cliente MCP favorito.</span>
              </div>
            </div>
            <div class="flow-item">
              <div class="flow-num">02</div>
              <div class="flow-text">
                <strong>Download e conversão</strong>
                <span>O servidor baixa e converte a especificação da API.</span>
              </div>
            </div>
            <div class="flow-item">
              <div class="flow-num">03</div>
              <div class="flow-text">
                <strong>Geração das ferramentas</strong>
                <span
                  >Ferramentas MCP criadas automaticamente a partir dos
                  endpoints.</span
                >
              </div>
            </div>
            <div class="flow-item">
              <div class="flow-num">04</div>
              <div class="flow-text">
                <strong>LLM usa as ferramentas</strong>
                <span
                  >O modelo chama a API como se fossem funções nativas.</span
                >
              </div>
            </div>
            <div class="flow-item">
              <div class="flow-num">05</div>
              <div class="flow-text">
                <strong>Ciclo encerrado</strong>
                <span>O servidor termina quando o cliente desconecta.</span>
              </div>
            </div>
          </div>
          <div class="sse-note">
            <strong>Nota SSE/HTTP:</strong> Para transporte SSE, o servidor pode
            correr de forma independente num host remoto, sem depender do ciclo
            de vida do cliente.
          </div>
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



    <hr class="divider" />

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
            <div class="feat-icon"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.7)" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M9 3h6M8 3l-4 14a2 2 0 001.9 2.5h12.2A2 2 0 0020 17L16 3"/><path d="M6.5 11h11"/></svg></div>
            <h3>API de Teste Incluída</h3>
            <p>
              Inclui
              <code
                style="
                  color: var(--accent2);
                  background: rgba(0, 212, 170, 0.1);
                "
                >loja_api.py</code
              >
              — uma API FastAPI de demonstração para testes locais imediatos.
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
        <div class="pricing-grid">
          <div class="feat-card pricing-card" style="max-width: 360px;">
            <div class="pricing-name">Free</div>
            <div class="pricing-price">$0 <span style="font-size: 1.5rem;">/mês</span></div>
            <div class="pricing-desc">Para começar</div>
            <ul class="pricing-features">
              <li><span class="check-icon"><svg width="12" height="12" viewBox="0 0 14 14" fill="none" stroke="#00d4aa" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1.5 7l4 4 7-7"/></svg></span> 2 servidores MCP</li>
              <li><span class="check-icon"><svg width="12" height="12" viewBox="0 0 14 14" fill="none" stroke="#00d4aa" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1.5 7l4 4 7-7"/></svg></span> Logs básicos</li>
              <li><span class="check-icon"><svg width="12" height="12" viewBox="0 0 14 14" fill="none" stroke="#00d4aa" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1.5 7l4 4 7-7"/></svg></span> APIs públicas</li>
              <li><span class="check-icon"><svg width="12" height="12" viewBox="0 0 14 14" fill="none" stroke="#00d4aa" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1.5 7l4 4 7-7"/></svg></span> Suporte comunitário</li>
            </ul>
            <a href="dashboard.html" class="btn-primary" style="display: block; text-align: center;">Criar Grátis</a>
          </div>
          <div class="feat-card pricing-card popular" style="max-width: 360px;">
            <span class="pricing-popular-badge">POPULAR</span>
            <div class="pricing-name">Pro</div>
            <div class="pricing-price">$ <span style="font-size: 1.5rem;">/mês</span></div>
            <div class="pricing-desc">Para uso profissional</div>
            <ul class="pricing-features">
              <li><span class="check-icon"><svg width="12" height="12" viewBox="0 0 14 14" fill="none" stroke="#00d4aa" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1.5 7l4 4 7-7"/></svg></span> Servidores Ilimitados</li>
              <li><span class="check-icon"><svg width="12" height="12" viewBox="0 0 14 14" fill="none" stroke="#00d4aa" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1.5 7l4 4 7-7"/></svg></span> Logs completos</li>
              <li><span class="check-icon"><svg width="12" height="12" viewBox="0 0 14 14" fill="none" stroke="#00d4aa" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1.5 7l4 4 7-7"/></svg></span> Alta prioridade (sem cold-start)</li>
              <li><span class="check-icon"><svg width="12" height="12" viewBox="0 0 14 14" fill="none" stroke="#00d4aa" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1.5 7l4 4 7-7"/></svg></span> APIs privadas via Tunneling</li>
            </ul>
            <a href="dashboard.html" class="btn-primary" style="display: block; text-align: center;">Assinar Pro</a>
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
            <h3>Posso usar com APIs em localhost?</h3>
          </div>
          <div class="qs-step-body">
            <p>Sim! Através do nosso CLI com suporte a Tunneling, você pode expor sua API local de forma segura para ser consumida pela nossa ponte na nuvem.</p>
          </div>
        </div>
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
      <h2>Duas APIs,<br />um servidor.</h2>
      <p class="section-desc">
        Configura múltiplas APIs no mesmo cliente MCP. Veja a diferença entre
        uma API externa (Swagger 2.0) e uma API local (OpenAPI 3.0).
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

        <div class="api-card">
          <div class="api-card-head">
            <span class="api-head-icon"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12L12 3l9 9"/><path d="M9 21V12h6v9"/><path d="M3 12v9h18v-9"/></svg></span>
            <h3>Loja API (Local)</h3>
            <span class="api-badge ok">OpenAPI 3.0</span>
          </div>
          <div class="api-card-body">
            <div class="code-block">
              <pre><span class="hl">MCP_SPEC_URL</span>=http://localhost:8000/openapi.json
<span class="hl">MCP_SERVER_NAME</span>=Loja API</pre>
            </div>
            <div class="api-note ok">
              <span style="display:inline-flex;align-items:center;gap:5px;vertical-align:middle;"><svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="#166a57" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 8l4 4 8-8"/></svg></span> <strong>OpenAPI 3.0 nativo</strong> — Usado directamente sem
              conversão, mais rápido e confiável.
            </div>
          </div>
        </div>
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
    &#125;,
    "loja-local": &#123;
      "command": ".../venv/Scripts/python.exe",
      "args": ["main.py"],
      "env": &#123;
        "MCP_SPEC_URL": "http://localhost:8000/openapi.json",
        "MCP_SERVER_NAME": "Loja API"
      &#125;
    &#125;
  &#125;
&#125;</pre>
        </div>
    </section>



    <hr class="divider" />

    <!-- CONFIG -->
    <section class="section" id="config">
      <div class="section-label">// 07 — Clientes Suportados</div>
      <h2>Compatível com os<br />principais clientes MCP.</h2>
      <p class="section-desc">
        O rest2mcp funciona com qualquer cliente MCP. Cada um tem o seu próprio
        formato de configuração — consulte a documentação do teu cliente.
      </p>

      <div class="config-grid" style="display: flex; flex-wrap: wrap; gap: 1rem; justify-content: center; margin-top: 2rem;">
        <div class="feat-card" style="flex: 0 0 auto; width: 140px; text-align: center; padding: 1.5rem 1rem;">
          <div style="font-size: 2rem; margin-bottom: 0.5rem;">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.8)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 002 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z"/></svg>
          </div>
          <div style="font-weight: 600; color: white; font-size: 0.9rem;">Cursor</div>
        </div>
        <div class="feat-card" style="flex: 0 0 auto; width: 140px; text-align: center; padding: 1.5rem 1rem;">
          <div style="font-size: 2rem; margin-bottom: 0.5rem;">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.8)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M8 12l2 2 4-4"/></svg>
          </div>
          <div style="font-weight: 600; color: white; font-size: 0.9rem;">Claude</div>
        </div>
        <div class="feat-card" style="flex: 0 0 auto; width: 140px; text-align: center; padding: 1.5rem 1rem;">
          <div style="font-size: 2rem; margin-bottom: 0.5rem;">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.8)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M18 3a3 3 0 00-3 3v12a3 3 0 003 3 3 3 0 003-3 3 3 0 00-3-3H6a3 3 0 00-3 3 3 3 0 003 3 3 3 0 003-3V6a3 3 0 00-3-3 3 3 0 00-3 3 3 3 0 003 3h12a3 3 0 003-3 3 3 0 00-3-3z"/></svg>
          </div>
          <div style="font-weight: 600; color: white; font-size: 0.9rem;">Windsurf</div>
        </div>
        <div class="feat-card" style="flex: 0 0 auto; width: 140px; text-align: center; padding: 1.5rem 1rem;">
          <div style="font-size: 2rem; margin-bottom: 0.5rem;">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.8)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="16 3 21 3 21 8"/><line x1="4" y1="20" x2="21" y2="3"/><polyline points="21 16 21 21 16 21"/><line x1="15" y1="15" x2="21" y2="21"/><line x1="4" y1="4" x2="9" y2="9"/></svg>
          </div>
          <div style="font-weight: 600; color: white; font-size: 0.9rem;">Cline</div>
        </div>
        <div class="feat-card" style="flex: 0 0 auto; width: 140px; text-align: center; padding: 1.5rem 1rem;">
          <div style="font-size: 2rem; margin-bottom: 0.5rem;">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.8)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>
          </div>
          <div style="font-weight: 600; color: white; font-size: 0.9rem;">VS Code</div>
        </div>
        <div class="feat-card" style="flex: 0 0 auto; width: 140px; text-align: center; padding: 1.5rem 1rem;">
          <div style="font-size: 2rem; margin-bottom: 0.5rem;">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.8)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 013 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>
          </div>
          <div style="font-weight: 600; color: white; font-size: 0.9rem;">Antigravity</div>
        </div>
      </div>
    </section>

    <!-- CONTACT -->
    <section class="section" id="contact">
      <div class="section-label">// 08 — Contacto</div>
      <h2>Vamos conversar?</h2>
      <p class="section-desc">
        Tem uma ideia, dúvida ou quer propor uma parceria? Envie uma mensagem.
      </p>
      <form class="contact-form" onsubmit="sendContactEmail(event)">
        <div class="contact-row">
          <input type="text" id="contactName" placeholder="O seu nome" required class="contact-input" />
          <input type="email" id="contactEmail" placeholder="O seu email" required class="contact-input" />
        </div>
        <textarea id="contactMessage" placeholder="A sua mensagem..." required class="contact-textarea"></textarea>
        <button type="submit" class="btn-primary">Enviar Mensagem</button>
      </form>
    </section>

    <!-- FOOTER -->
    <footer>
      <div class="footer-inner">
        <div class="footer-logo">rest2mcp</div>
        <p style="color: rgba(255, 255, 255, 0.35); font-size: 0.85rem">
          Versão 1.0.0 · Autor: Matias Fernando
        </p>
        <ul class="footer-links">
          <li><a href="https://matiasdev30.github.io/#/" target="_blank">Portfolio</a></li>
          <li><a href="https://www.linkedin.com/in/mvni-null/" target="_blank">LinkedIn</a></li>
          <li><a href="https://github.com/mvninull" target="_blank">GitHub</a></li>
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
            <span class="spinner" style="display:none"><svg class="spinner-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10" stroke-dasharray="31.4 31.4" stroke-linecap="round"/></svg></span>
            <span class="btn-text"><svg viewBox="0 0 24 24" class="social-icon" fill="currentColor"><path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"/><path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/><path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/></svg> Entrar com o Google</span>
          </button>
          <button class="social-btn github-btn" onclick="loginWith('github')">
            <span class="spinner" style="display:none"><svg class="spinner-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10" stroke-dasharray="31.4 31.4" stroke-linecap="round"/></svg></span>
            <span class="btn-text"><svg viewBox="0 0 24 24" class="social-icon" fill="currentColor"><path d="M12 0C5.37 0 0 5.37 0 12c0 5.3 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61-.546-1.385-1.335-1.755-1.335-1.755-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 21.795 24 17.295 24 12 24 5.37 18.63 0 12 0z"/></svg> Entrar com o GitHub</span>
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
            <button type="submit" class="btn-primary auth-submit"><span class="spinner" style="display:none"><svg class="spinner-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10" stroke-dasharray="31.4 31.4" stroke-linecap="round"/></svg></span><span class="btn-text">Entrar / Registar</span></button>
          </form>
        </div>
        <div class="modal-actions" style="margin-top: 1.5rem; display: flex; justify-content: center;">
          <button class="btn-cancel" onclick="closeLoginModal()">Cancelar</button>
        </div>
      </div>
    </div>

    <!-- Supabase SDK e Código de Autenticação -->
    
    
    <a href='https://ko-fi.com/F1F81ZH0QM' target='_blank' class="kofi-btn">
      <img height='36' style='border:0px;height:36px;' src='https://storage.ko-fi.com/cdn/kofi5.png?v=6' border='0' alt='Buy Me a Coffee at ko-fi.com' />
    </a>

    <!-- Loading Overlay -->
    <div class="lo" id="loadingOverlay">
      <div class="lo-spinner"></div>
      <div class="lo-text">Redirecionando...</div>
    </div>
