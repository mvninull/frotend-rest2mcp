<script>
  // @ts-nocheck
  import { onMount } from 'svelte';
  import './Dashboard.css';

  onMount(() => {

      const API_BASE = (
        localStorage.getItem("api_base") || "http://localhost:8080"
      ).replace(/\/+$/, "");
      const POLL_LOGS_INTERVAL = 5000;
      let activeServerId = null;

      // ─── Supabase Auth ───────────────────────────────────────
      const SUPABASE_URL = localStorage.getItem("supabase_url") || "https://zcfrbhrqvneomseqmqam.supabase.co";
      const SUPABASE_ANON_KEY = localStorage.getItem("supabase_anon_key") || "sb_publishable_mF0UgfLvgZN5OupdpsSa0A_ibOcfzq4";
      let supabaseClient = null;
      let currentUser = null;
      let currentProfile = null;

      if (SUPABASE_URL && SUPABASE_ANON_KEY) {
        supabaseClient = supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
      }

      function getAuthToken() {
        return localStorage.getItem("supabase_token") || "";
      }

      // ─── Loading Overlay ─────────────────────────────────
      function showLoading(text = "Aguarde...", blur = true) {
        const overlay = document.getElementById("loadingOverlay");
        const textEl = document.getElementById("loadingText");
        if (!overlay) return;
        overlay.classList.toggle("no-blur", !blur);
        if (textEl) textEl.textContent = text;
        overlay.classList.add("open");
      }
      function hideLoading() {
        const overlay = document.getElementById("loadingOverlay");
        if (overlay) overlay.classList.remove("open");
      }

      async function loginWith(provider) {
        if (!supabaseClient) return alert("Supabase não configurado.");
        showLoading("Redirecionando para " + provider + "...");
        const { error } = await supabaseClient.auth.signInWithOAuth({ provider });
        if (error) {
          hideLoading();
          console.error("Login error:", error);
        }
      }

      async function logout() {
        showLoading("Terminando sessão...");
        try {
          if (supabaseClient) await supabaseClient.auth.signOut({ scope: 'global' });
        } catch (e) {
          console.error("Erro ao terminar sessão Supabase:", e);
        }
        localStorage.removeItem("supabase_token");
        localStorage.removeItem("supabase.auth.token");
        sessionStorage.removeItem("supabase.auth.token");
        currentUser = null;
        currentProfile = null;
        window.location.href = window.location.origin;
      }

      async function restoreSession() {
        if (!supabaseClient) return;
        const token = getAuthToken();
        if (!token) return;
        try {
          const { data, error } = await supabaseClient.auth.getUser(token);
          if (error || !data?.user) {
            logout();
            return;
          }
          currentUser = data.user;
          await fetchProfile();
        } catch {
          logout();
        }
      }

      async function fetchProfile() {
        if (!currentUser) return;
        try {
          const resp = await apiFetch("/v1/me");
          currentProfile = resp;
        } catch {
          currentProfile = null;
        }
        renderAuthUI();
        renderProfile();
      }

      function renderAuthUI() {
        const loginEl = document.getElementById("authLogin");
        const userEl = document.getElementById("authUser");
        if (!loginEl || !userEl) return;
        if (currentUser) {
          loginEl.style.display = "none";
          userEl.style.display = "flex";
          const nameEl = document.getElementById("authName");
          const avatarEl = document.getElementById("authAvatar");
          const planEl = document.getElementById("authPlan");
          if (nameEl) nameEl.textContent = currentProfile?.name || currentUser.email?.split("@")[0] || currentUser.email || "";
          if (avatarEl) avatarEl.src = currentProfile?.avatar_url || currentUser.user_metadata?.avatar_url || "";
          if (planEl) {
            const plan = (currentProfile?.plan_tier || "free").toLowerCase();
            planEl.textContent = plan;
            planEl.className = `auth-plan ${plan}`;
          }
        } else {
          loginEl.style.display = "none";
          userEl.style.display = "none";
        }
      }

      function renderProfile() {
        const qrs = document.getElementById("quotaRowServers");
        const qrp = document.getElementById("quotaRowPlan");
        const sub = document.getElementById("subSection");
        if (!currentProfile) {
          if (qrs) qrs.style.display = "none";
          if (qrp) qrp.style.display = "none";
          if (sub) sub.style.display = "none";
          return;
        }
        const profile = currentProfile;
        if (qrs) qrs.style.display = "flex";
        if (qrp) qrp.style.display = "flex";
        const qs = document.getElementById("quotaServers");
        const qp = document.getElementById("quotaPlan");
        if (qs) {
          qs.textContent = `${profile.servers_count} / ${profile.servers_limit}`;
          qs.className = "stat-value" + (profile.servers_count >= profile.servers_limit ? " warn" : "");
        }
        if (qp) qp.textContent = profile.plan_tier;

        if (sub) sub.style.display = "block";
        const ss = document.getElementById("subServers");
        if (ss) {
          ss.textContent = `${profile.servers_count} / ${profile.servers_limit}`;
          ss.className = "val" + (profile.servers_count >= profile.servers_limit ? " warn" : "");
        }

        const isPro = profile.plan_tier === "pro";
        const sRpm = document.getElementById("subRPM");
        if (sRpm) sRpm.textContent = isPro ? "100" : "10";
        const upg = document.getElementById("subUpgrade");
        if (upg) upg.style.display = isPro ? "none" : "block";
      }

      let paypalRendered = false;
      function showPayPal() {
        const ppc = document.getElementById("paypal-button-container");
        if (!ppc) return;
        ppc.style.display = "block";
        if (typeof paypal !== "undefined" && currentUser && !paypalRendered) {
          paypalRendered = true;
          paypal.Buttons({
            createSubscription: function(data, actions) {
              return actions.subscription.create({
                plan_id: "P-26B313696D799031LNIFNUDQ",
                custom_id: currentUser.id,
              });
            },
            onApprove: function(data) {
              alert("Subscrição ativada!");
              setTimeout(fetchProfile, 3000);
            },
            onError: function(err) {
              console.error("PayPal error:", err);
              alert("Erro ao processar pagamento.");
            },
          }).render("#paypal-button-container");
        }
      }

      // ─── API ───────────────────────────────────────────────
      async function apiFetch(path, options = {}) {
        const url = `${API_BASE}${path}`;
        const headers = { "Content-Type": "application/json", ...options.headers };
        const token = getAuthToken();
        if (token) headers["Authorization"] = `Bearer ${token}`;
        const res = await fetch(url, {
          headers,
          ...options,
        });
        if (res.status === 204) return null;
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || `Erro ${res.status}`);
        return data;
      }

      // ─── Render Card ───────────────────────────────────────
      function renderServerCard(s) {
        const isActive = s.status === "active";
        const card = document.createElement("div");
        card.className = `server-card${isActive ? " active-status" : ""}`;
        card.dataset.serverId = s.server_id;
        card.dataset.apikey = s.apikey || "";
        card.dataset.transport = s.transport || "http";

        const emoji = isActive
          ? `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="4" fill="#00d4aa"/><circle cx="8" cy="8" r="7" stroke="#00d4aa" stroke-width="1.5" stroke-opacity="0.3"/></svg>`
          : `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="4" fill="#ff5c35"/><circle cx="8" cy="8" r="7" stroke="#ff5c35" stroke-width="1.5" stroke-opacity="0.3"/></svg>`;

        card.addEventListener("click", () => selectServer(s.server_id));

        card.innerHTML = `
          <div class="server-info">
            <div class="status-icon ${isActive ? "active" : "inactive"}">${emoji}</div>
            <div class="server-meta">
              <div class="server-name">${escapeHtml(s.name)}</div>
              <div class="server-url">${escapeHtml(s.url_sse || s.server_id)}</div>
            </div>
          </div>
          <div class="server-actions">
            <span class="status-chip ${isActive ? "active" : "inactive"}">
              <span class="status-chip-dot"></span>
              ${isActive ? "Online" : "Offline"}
            </span>
            <button class="btn-copy" ${isActive ? "" : "disabled"} onclick="copyUrl(this, '${escapeHtml(s.url_sse || "")}')">
              Copy URL
            </button>
            <div class="menu-wrapper">
              <button class="menu-btn" onclick="toggleMenu(this)" title="Mais opções">
                <svg width="14" height="14" viewBox="0 0 14 14" fill="currentColor">
                  <circle cx="7" cy="2" r="1.3"/><circle cx="7" cy="7" r="1.3"/><circle cx="7" cy="12" r="1.3"/>
                </svg>
              </button>
              <div class="menu-dropdown">
                <button onclick="openInspector('${escapeHtml(s.url_sse || "")}', '${s.transport || "http"}'); closeMenu();">
                  <span class="menu-icon"><svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"><circle cx="6.5" cy="6.5" r="4.2"/><path d="M10.2 10.2L14 14"/></svg></span> Inspecionar
                </button>
                <button onclick="editServer('${s.server_id}', '${escapeHtml(s.name || "")}', '${s.transport || "http"}'); closeMenu();">
                  <span class="menu-icon"><svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linejoin="round"><path d="M11 2l3 3-8 8H3v-3l8-8z"/></svg></span> Editar
                </button>
                <div class="menu-divider"></div>
                <button onclick="toggleServerStatus('${s.server_id}'); closeMenu();">
                  <span class="menu-icon">${isActive ? `<svg width="13" height="13" viewBox="0 0 16 16" fill="currentColor"><rect x="3" y="2" width="4" height="12" rx="1"/><rect x="9" y="2" width="4" height="12" rx="1"/></svg>` : `<svg width="13" height="13" viewBox="0 0 16 16" fill="currentColor"><path d="M4 2l10 6-10 6V2z"/></svg>`}</span>
                  ${isActive ? "Desativar" : "Ativar"}
                </button>
                <div class="menu-divider"></div>
                <button class="menu-danger" onclick="deleteServer('${s.server_id}'); closeMenu();">
                  <span class="menu-icon"><svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"><path d="M2 4h12"/><path d="M5 4V2h6v2"/><path d="M6 7v5M10 7v5"/><path d="M3 4l1 10h8l1-10"/></svg></span> Remover
                </button>
              </div>
            </div>
          </div>
        `;
        return card;
      }

      // ─── Load Servers ──────────────────────────────────────
      async function loadServers() {
        const list = document.getElementById("serverList");
        if (!list) return;
        try {
          const servers = await apiFetch("/v1/servers");
          list.innerHTML = "";

          if (!servers || servers.length === 0) {
            list.innerHTML = `
              <div class="empty-state">
                <div class="empty-icon"><svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"><rect x="7" y="2" width="10" height="14" rx="2"/><path d="M9 16v4M15 16v4M9 20h6"/><path d="M9 6h6M9 10h6"/></svg></div>
                <div>Nenhum servidor ainda.<br/>Clique em <strong>+ Novo Servidor</strong> para começar.</div>
              </div>
            `;
          } else {
            servers.forEach((s) => list.appendChild(renderServerCard(s)));
            _populateLogServerSelect(servers);
            selectServer(servers[0].server_id);
          }

          const sc = document.getElementById("serverCount");
          if (sc) sc.textContent = servers ? servers.length : 0;

        } catch (err) {
          list.innerHTML = `
            <div class="empty-state">
              <div class="empty-icon"><svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="#ff5c35" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg></div>
              <div style="color:var(--warn)">Erro ao carregar servidores:<br/>${escapeHtml(err.message)}</div>
              <button onclick="loadServers()" style="margin-top:1.2rem;padding:8px 18px;border:1px solid var(--border);border-radius:8px;background:white;cursor:pointer;font-family:var(--mono);font-size:0.78rem;transition:all 0.2s;">
                Tentar novamente
              </button>
            </div>
          `;
          const sc = document.getElementById("serverCount");
          if (sc) sc.textContent = "—";
        }
      }

      // ─── Create Server ─────────────────────────────────────
      async function createServer() {
        const name = document.getElementById("inputName")?.value?.trim();
        const specUrl = document.getElementById("inputSpecUrl")?.value?.trim();
        const transport = document.getElementById("inputTransport")?.value;
        const errorEl = document.getElementById("modalError");
        const btn = document.getElementById("btnCreateConfirm");

        if (errorEl) showModalError(errorEl, "");

        if (!name) {
          if (errorEl) showModalError(errorEl, "Informe o nome do servidor.");
          return;
        }
        if (!specUrl) {
          if (errorEl) showModalError(errorEl, "Informe a URL do OpenAPI Spec.");
          return;
        }

        if (btn) {
          btn.disabled = true;
          btn.innerHTML = '<span class="btn-spinner"></span> Criando...';
        }

        try {
          await apiFetch("/v1/servers", {
            method: "POST",
            body: JSON.stringify({ name, spec_url: specUrl, transport }),
          });
          closeCreateModal();
          showLoading("Servidor criado! Carregando...", false);
          await loadServers();
          hideLoading();
          const cards = document.querySelectorAll(".server-card");
          if (cards.length > 0)
            cards[0].scrollIntoView({ behavior: "smooth", block: "center" });
        } catch (err) {
          if (errorEl) showModalError(errorEl, err.message);
        } finally {
          if (btn) {
            btn.disabled = false;
            btn.textContent = "Criar Servidor";
          }
        }
      }

      // ─── Delete Server ─────────────────────────────────────
      async function deleteServer(serverId) {
        if (!confirm("Remover este servidor permanentemente?")) return;
        const card = document.querySelector(
          `.server-card[data-server-id="${serverId}"]`,
        );
        if (!card) return;
        card.style.opacity = "0";
        card.style.transform = "translateX(20px)";
        card.style.transition = "all 0.3s";
        try {
          await apiFetch(`/v1/servers/${serverId}`, { method: "DELETE" });
          setTimeout(() => {
            card.remove();
            const sc = document.getElementById("serverCount");
            if (sc) sc.textContent = document.querySelectorAll(".server-card").length;
            if (activeServerId === serverId) activeServerId = null;
          }, 300);
        } catch (err) {
          card.style.opacity = "1";
          card.style.transform = "";
          alert("Erro ao remover: " + err.message);
        }
      }

      // ─── Toggle Status ──────────────────────────────────────
      async function toggleServerStatus(serverId) {
        const card = document.querySelector(`.server-card[data-server-id="${serverId}"]`);
        if (!card) return;
        const isActive = card.classList.contains("active-status");
        try {
          await apiFetch(`/v1/servers/${serverId}`, {
            method: "PATCH",
            body: JSON.stringify({ status: isActive ? "inactive" : "active" }),
          });
          await loadServers();
        } catch (err) {
          alert("Erro ao alterar status: " + err.message);
        }
      }

      // ─── Menu Portal ───────────────────────────────────────
      const portal = document.getElementById("menuPortal");
      let activeMenu = null;
      let activeMenuOriginWrapper = null;

      function toggleMenu(btn) {
        if (!portal) return;
        const wrapper = btn.closest(".menu-wrapper");
        if (!wrapper) return;
        const menu = wrapper.querySelector(".menu-dropdown");
        if (!menu) return;

        if (activeMenu === menu && portal.classList.contains("open")) {
          closeAllMenus();
          return;
        }
        closeAllMenus();

        portal.appendChild(menu);
        portal.classList.add("open");
        menu.classList.add("open");
        activeMenu = menu;
        activeMenuOriginWrapper = wrapper;

        const rect = btn.getBoundingClientRect();
        const menuW = 200;
        let left = rect.right - menuW;
        let top = rect.bottom + 6;
        if (left < 8) left = 8;
        if (top + 240 > window.innerHeight) top = rect.top - 240;
        menu.style.position = "fixed";
        menu.style.left = left + "px";
        menu.style.top = top + "px";
        menu.style.minWidth = menuW + "px";
      }

      function closeMenu() {
        closeAllMenus();
      }

      function closeAllMenus() {
        if (!portal) return;
        if (activeMenu) {
          activeMenu.classList.remove("open");
          if (activeMenuOriginWrapper)
            activeMenuOriginWrapper.appendChild(activeMenu);
          activeMenu = null;
          activeMenuOriginWrapper = null;
        }
        portal.classList.remove("open");
      }

      document.addEventListener("click", (e) => {
        if (
          !e.target.closest(".menu-wrapper") &&
          !e.target.closest("#menuPortal")
        )
          closeAllMenus();
      });
      window.addEventListener("scroll", closeAllMenus, true);
      window.addEventListener("resize", closeAllMenus);

      // ─── Edit ──────────────────────────────────────────────
      let editingServerId = null;
      function editServer(serverId, name, transportType) {
        editingServerId = serverId;
        const en = document.getElementById("editName");
        const et = document.getElementById("editTransport");
        const es = document.getElementById("editStatus");
        const ee = document.getElementById("editError");
        const em = document.getElementById("editModal");
        if (en) en.value = name;
        if (et) et.value = transportType === "sse" ? "sse" : "http";
        if (es) es.value = "active";
        if (ee) showModalError(ee, "");
        if (em) em.classList.add("open");
      }
      async function saveEdit() {
        const name = document.getElementById("editName")?.value?.trim();
        const transport = document.getElementById("editTransport")?.value;
        const status = document.getElementById("editStatus")?.value;
        const errorEl = document.getElementById("editError");
        const btn = document.getElementById("btnEditConfirm");
        if (errorEl) showModalError(errorEl, "");
        if (!name) {
          if (errorEl) showModalError(errorEl, "Nome não pode ficar vazio.");
          return;
        }
        if (btn) btn.disabled = true;
        if (btn) btn.textContent = "Salvando...";
        try {
          await apiFetch(`/v1/servers/${editingServerId}`, {
            method: "PATCH",
            body: JSON.stringify({ name, status, transport }),
          });
          closeEditModal();
          await loadServers();
        } catch (err) {
          if (errorEl) showModalError(errorEl, err.message);
        } finally {
          if (btn) {
            btn.disabled = false;
            btn.textContent = "Salvar";
          }
        }
      }
      function closeEditModal() {
        const em = document.getElementById("editModal");
        if (em) em.classList.remove("open");
        editingServerId = null;
      }
      const editModal = document.getElementById("editModal");
      if (editModal) editModal.addEventListener("click", (e) => {
        if (e.target === e.currentTarget) closeEditModal();
      });

      // ─── Inspector ─────────────────────────────────────────
      function openInspector(url, transportType) {
        const transport = transportType === "http" ? "streamable-http" : "sse";
        navigator.clipboard.writeText(url).catch(() => {});
        fetch("http://127.0.0.1:6277/connect", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url, transportType: transport }),
        }).catch(() => {});
        window.open(
          `http://localhost:6274/?url=${encodeURIComponent(url)}&transportType=${transport}`,
          "_blank",
        );
      }

      // ─── Copy URL ──────────────────────────────────────────
      function copyUrl(btn, url) {
        if (!url) return;
        navigator.clipboard.writeText(url).then(() => {
          btn.textContent = "Copiado ✓";
          btn.classList.add("copied");
          setTimeout(() => {
            btn.textContent = "Copy URL";
            btn.classList.remove("copied");
          }, 2000);
        });
      }

      // ─── Modals ─────────────────────────────────────────────
      function openCreateModal() {
        const cm = document.getElementById("createModal");
        const inEl = document.getElementById("inputName");
        const isEl = document.getElementById("inputSpecUrl");
        const me = document.getElementById("modalError");
        const bcc = document.getElementById("btnCreateConfirm");
        if (cm) cm.classList.add("open");
        if (inEl) inEl.value = "";
        if (isEl) isEl.value = "";
        if (me) showModalError(me, "");
        if (bcc) {
          bcc.disabled = false;
          bcc.textContent = "Criar Servidor";
        }
        setTimeout(() => {
          const f = document.getElementById("inputName");
          if (f) f.focus();
        }, 120);
      }
      function closeCreateModal() {
        const cm = document.getElementById("createModal");
        if (cm) cm.classList.remove("open");
      }
      const createModal = document.getElementById("createModal");
      if (createModal) createModal.addEventListener("click", (e) => {
        if (e.target === e.currentTarget) closeCreateModal();
      });
      document.addEventListener("keydown", (e) => {
        if (e.key === "Escape") {
          closeCreateModal();
          closeEditModal();
        }
        if (
          e.key === "Enter" &&
          document.getElementById("createModal")?.classList.contains("open")
        )
          createServer();
      });

      // ─── Error helper ──────────────────────────────────────
      function showModalError(el, msg) {
        if (!el) return;
        el.textContent = msg;
        el.classList.toggle("visible", !!msg);
      }

      // ─── Logs ──────────────────────────────────────────────
      let logsInterval = null;
      let logDebounceTimer = null;

      function _populateLogServerSelect(servers) {
        const sel = document.getElementById("logServerSelect");
        if (!sel) return;
        sel.innerHTML = '<option value="">Servidor...</option>';
        servers.forEach((s) => {
          const opt = document.createElement("option");
          opt.value = s.server_id;
          opt.textContent = s.name;
          if (s.server_id === activeServerId) opt.selected = true;
          sel.appendChild(opt);
        });
      }

      function selectServer(serverId) {
        document.querySelectorAll(".server-card").forEach((c) => c.classList.remove("selected"));
        const card = document.querySelector(`.server-card[data-server-id="${serverId}"]`);
        if (card) card.classList.add("selected");
        activeServerId = serverId;
        const sel = document.getElementById("logServerSelect");
        if (sel) sel.value = serverId;
        pollLogs();
      }

      function switchLogServer(serverId) {
        selectServer(serverId || activeServerId);
      }

      function debouncePoll() {
        clearTimeout(logDebounceTimer);
        logDebounceTimer = setTimeout(pollLogs, 300);
      }

      function relativeTime(isoStr) {
        const now = Date.now();
        const t = new Date(isoStr).getTime();
        const diff = now - t;
        const sec = Math.floor(diff / 1000);
        if (sec < 5) return "agora";
        if (sec < 60) return `${sec}s`;
        const min = Math.floor(sec / 60);
        if (min < 60) return `${min}min`;
        const h = Math.floor(min / 60);
        if (h < 24) return `${h}h`;
        return `${Math.floor(h / 24)}d`;
      }

      function methodBadge(method) {
        const colors = {GET:'#00d4aa',POST:'#1a56ff',PUT:'#ff9f1c',PATCH:'#ff9f1c',DELETE:'#ff5c35'};
        const color = colors[method] || '#7a7a8a';
        return `<span style="display:inline-block;font-size:0.58rem;font-weight:700;padding:1px 5px;border-radius:3px;background:${color}22;color:${color};margin-right:4px">${escapeHtml(method || '?')}</span>`;
      }

      async function pollLogs() {
        if (!activeServerId) return;
        try {
          const toolFilter = document.getElementById("logToolFilter")?.value?.trim() || "";
          const statusFilter = document.getElementById("logStatusFilter")?.value || "";
          let params = `limit=20`;
          if (toolFilter) params += `&tool=${encodeURIComponent(toolFilter)}`;
          if (statusFilter) {
            const [smin, smax] = statusFilter.split("-");
            if (smin) params += `&status_min=${smin}`;
            if (smax) params += `&status_max=${smax}`;
          }
          const logs = await apiFetch(`/v1/servers/${activeServerId}/logs?${params}`);
          const container = document.getElementById("liveLogs");
          if (!container) return;
          container.innerHTML = "";

          if (!logs || logs.length === 0) {
            container.innerHTML = '<div style="color:rgba(255,255,255,0.2)">Nenhuma chamada ainda...</div>';
            return;
          }
          logs.forEach((log) => {
            const isSuccess = log.status_code >= 200 && log.status_code < 300;
            const row = document.createElement("div");
            row.className = "log-entry";
            row.style.cursor = "pointer";
            row.onclick = () => openLogDetail(log);

            const line1 = document.createElement("div");
            line1.className = "log-line1";
            line1.innerHTML = `${methodBadge(log.method)}<span class="${isSuccess ? "hl" : "log-err"}">${escapeHtml(log.tool_called)}</span>`;

            const line2 = document.createElement("div");
            line2.className = "log-line2";
            line2.innerHTML = `<span class="${isSuccess ? "" : "log-err"}">[${log.status_code}]</span> ${log.duration_ms.toFixed(0)}ms · <span class="log-time">${relativeTime(log.timestamp)}</span>`;

            row.appendChild(line1);
            row.appendChild(line2);
            container.appendChild(row);
          });
          container.scrollTop = container.scrollHeight;
        } catch {}
      }

      async function openLogDetail(log) {
        try {
          const detail = await apiFetch(`/v1/servers/${activeServerId}/logs/${log.id}`);
          const dt = document.getElementById("detailTool");
          const dm = document.getElementById("detailMethod");
          const stEl = document.getElementById("detailStatus");
          const dd = document.getElementById("detailDuration");
          const dti = document.getElementById("detailTime");
          const reqBody = document.getElementById("detailReqBody");
          const resBody = document.getElementById("detailResBody");
          const ldm = document.getElementById("logDetailModal");
          if (dt) dt.textContent = detail.tool_called || "—";
          if (dm) dm.textContent = detail.method || "—";
          if (stEl) {
            stEl.textContent = detail.status_code;
            stEl.className = detail.status_code >= 200 && detail.status_code < 300 ? "status-badge success" : "status-badge error";
          }
          if (dd) dd.textContent = `${detail.duration_ms.toFixed(1)}ms`;
          if (dti) dti.textContent = new Date(detail.timestamp).toLocaleString();

          if (reqBody) {
            if (detail.request_body) {
              try { reqBody.textContent = JSON.stringify(JSON.parse(detail.request_body), null, 2); }
              catch { reqBody.textContent = detail.request_body; }
            } else {
              reqBody.textContent = "(vazio)";
            }
          }

          if (resBody) {
            if (detail.response_body) {
              try { resBody.textContent = JSON.stringify(JSON.parse(detail.response_body), null, 2); }
              catch { resBody.textContent = detail.response_body; }
            } else {
              resBody.textContent = "(vazio)";
            }
          }

          if (ldm) ldm.classList.add("open");
        } catch (err) {
          console.error("Erro ao carregar detalhe do log:", err);
        }
      }

      function closeLogDetail() {
        const ldm = document.getElementById("logDetailModal");
        if (ldm) ldm.classList.remove("open");
      }
      const logDetailModal = document.getElementById("logDetailModal");
      if (logDetailModal) logDetailModal.addEventListener("click", (e) => {
        if (e.target === e.currentTarget) closeLogDetail();
      });

      async function exportLogs(format) {
        if (!activeServerId) return;
        window.open(`${API_BASE}/v1/servers/${activeServerId}/logs/export?format=${format}`, "_blank");
      }

      async function clearLogs() {
        if (!activeServerId) return;
        if (!confirm("Limpar todos os logs deste servidor?")) return;
        try {
          await apiFetch(`/v1/servers/${activeServerId}/logs`, { method: "DELETE" });
          pollLogs();
        } catch (err) {
          alert("Erro ao limpar logs: " + err.message);
        }
      }

      function startLogsPolling() {
        if (logsInterval) clearInterval(logsInterval);
        pollLogs();
        logsInterval = setInterval(pollLogs, POLL_LOGS_INTERVAL);
      }

      // ─── Gateway ───────────────────────────────────────────
      async function checkGateway() {
        try {
          const h = await apiFetch("/health");
          const el = document.getElementById("gatewayStatus");
          if (!el) return;
          el.textContent = `ok · ${h.active_servers} ativos`;
          el.className = "stat-value ok";
        } catch {
          const el = document.getElementById("gatewayStatus");
          if (!el) return;
          el.textContent = "offline";
          el.className = "stat-value";
          el.style.color = "var(--warn)";
        }
      }

      function escapeHtml(str) {
        const div = document.createElement("div");
        div.textContent = str;
        return div.innerHTML;
      }

      // ─── Init ──────────────────────────────────────────────
      (async function init() {
        await checkGateway();
        await restoreSession();
        await loadServers();
        startLogsPolling();

        if (supabaseClient) {
          const { data: listener } = supabaseClient.auth.onAuthStateChange((event, session) => {
            if (session?.access_token) {
              localStorage.setItem("supabase_token", session.access_token);
              currentUser = session.user;
              fetchProfile();
              loadServers();
            } else if (event === "SIGNED_OUT") {
              localStorage.removeItem("supabase_token");
              localStorage.removeItem("supabase.auth.token");
              sessionStorage.removeItem("supabase.auth.token");
              currentUser = null;
              currentProfile = null;
              window.location.href = window.location.origin;
            }
          });
        }

        // ─── Profile Modal ─────────────────────────────────────
        function openProfileModal() {
          if (!currentUser) return;
          const token = getAuthToken();
          const email = currentUser.email || "";
          const name = currentProfile?.name || currentUser.user_metadata?.full_name || currentUser.user_metadata?.name || email.split("@")[0] || "";
          const avatarUrl = currentProfile?.avatar_url || currentUser.user_metadata?.avatar_url || "";
          const plan = (currentProfile?.plan_tier || "free");
          const userId = currentUser.id || "";
          const createdAt = currentUser.created_at ? new Date(currentUser.created_at).toLocaleDateString("pt-PT", { year: "numeric", month: "long", day: "numeric" }) : "—";
          const provider = (currentUser.app_metadata?.provider || "email").toUpperCase();

          const initials = name ? name.split(" ").map(n => n[0]).join("").toUpperCase().slice(0, 2) : email[0]?.toUpperCase() || "U";

          const avatarHtml = avatarUrl
            ? `<img src="${escapeHtml(avatarUrl)}" alt="" class="profile-modal-avatar-img" onerror="this.style.display='none';this.nextElementSibling.style.display='flex'" /><span class="profile-modal-avatar-initials" style="display:none">${initials}</span>`
            : `<span class="profile-modal-avatar-initials">${initials}</span>`;

          const paw = document.getElementById("profileAvatarWrap");
          const pn = document.getElementById("profileName");
          const pe = document.getElementById("profileEmail");
          const pp = document.getElementById("profilePlan");
          const ppr = document.getElementById("profileProvider");
          const pui = document.getElementById("profileUserId");
          const pca = document.getElementById("profileCreatedAt");
          const tokenInput = document.getElementById("profileToken");
          const psc = document.getElementById("profileServersCount");
          const prpm = document.getElementById("profileRpm");
          const pm = document.getElementById("profileModal");

          if (paw) paw.innerHTML = avatarHtml;
          if (pn) pn.textContent = name || "Utilizador";
          if (pe) pe.textContent = email;
          if (pp) {
            pp.textContent = plan;
            pp.className = `profile-plan-badge ${plan}`;
          }
          if (ppr) ppr.textContent = provider;
          if (pui) pui.textContent = userId;
          if (pca) pca.textContent = createdAt;
          if (tokenInput) tokenInput.value = token || "(não autenticado)";

          if (currentProfile) {
            if (psc) psc.textContent = `${currentProfile.servers_count ?? 0} / ${currentProfile.servers_limit ?? 1}`;
            if (prpm) prpm.textContent = plan === "pro" ? "100" : "10";
          } else {
            if (psc) psc.textContent = "—";
            if (prpm) prpm.textContent = "—";
          }

          if (pm) pm.classList.add("open");
        }

        function closeProfileModal() {
          const pm = document.getElementById("profileModal");
          if (pm) pm.classList.remove("open");
        }

        const profileModal = document.getElementById("profileModal");
        if (profileModal) profileModal.addEventListener("click", (e) => {
          if (e.target === e.currentTarget) closeProfileModal();
        });

        function copyToken() {
          const val = document.getElementById("profileToken")?.value;
          if (!val || val === "(não autenticado)") return;
          navigator.clipboard.writeText(val).then(() => {
            const btn = document.getElementById("copyTokenBtn");
            if (!btn) return;
            btn.textContent = "Copiado ✓";
            btn.classList.add("copied");
            setTimeout(() => {
              btn.textContent = "Copiar";
              btn.classList.remove("copied");
            }, 2000);
          });
        }

        function toggleTokenVisibility() {
          const input = document.getElementById("profileToken");
          const btn = document.getElementById("toggleTokenBtn");
          if (!input || !btn) return;
          if (input.type === "password") {
            input.type = "text";
            btn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>`;
          } else {
            input.type = "password";
            btn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>`;
          }
        }

        async function logoutFromProfile() {
          closeProfileModal();
          await logout();
        }

        // Expose to window for inline HTML onclick handlers
        window.loginWith = loginWith;
        window.logout = logout;
        window.showLoading = showLoading;
        window.hideLoading = hideLoading;
        window.openProfileModal = openProfileModal;
        window.closeProfileModal = closeProfileModal;
        window.copyToken = copyToken;
        window.toggleTokenVisibility = toggleTokenVisibility;
        window.logoutFromProfile = logoutFromProfile;
        window.copyUrl = copyUrl;
        window.toggleMenu = toggleMenu;
        window.openInspector = openInspector;
        window.editServer = editServer;
        window.toggleServerStatus = toggleServerStatus;
        window.deleteServer = deleteServer;
        window.openCreateModal = openCreateModal;
        window.closeCreateModal = closeCreateModal;
        window.createServer = createServer;
        window.saveEdit = saveEdit;
        window.closeEditModal = closeEditModal;
        window.closeLogDetail = closeLogDetail;
        window.exportLogs = exportLogs;
        window.clearLogs = clearLogs;
        window.loadServers = loadServers;
        window.switchLogServer = switchLogServer;
        window.debouncePoll = debouncePoll;
        window.showPayPal = showPayPal;
        window.pollLogs = pollLogs;
      })();
    
  });
</script>


    <!-- ── NAVBAR ───────────────────────────────────────────── -->
    <nav>
      <div class="nav-inner">
        <a href="index.html" class="logo">
          <span class="logo-mark">
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <rect x="1" y="1" width="5" height="5" rx="1.5" fill="white" opacity="0.9" />
              <rect x="8" y="1" width="5" height="5" rx="1.5" fill="white" opacity="0.6" />
              <rect x="1" y="8" width="5" height="5" rx="1.5" fill="white" opacity="0.6" />
              <rect x="8" y="8" width="5" height="5" rx="1.5" fill="white" opacity="0.35" />
            </svg>
          </span>
          rest2mcp
        </a>

        <div class="nav-right" id="navAuth">
          <div class="auth-user" id="authUser" style="display:none">
            <button class="user-profile-btn" id="userProfileBtn" onclick="openProfileModal()" title="Ver perfil">
              <img class="auth-avatar" id="authAvatar" src="" alt="" onerror="this.style.display='none';this.nextElementSibling.style.display='flex'" />
              <span class="auth-avatar-fallback" id="authAvatarFallback" style="display:none"></span>
              <span class="auth-name" id="authName"></span>
              <span class="auth-plan" id="authPlan"></span>
            </button>
            <button class="auth-btn logout-btn-nav" onclick="logout()" title="Sair da conta">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
              Sair
            </button>
          </div>
          <div class="auth-login-buttons" id="authLogin" style="display:none"></div>
        </div>
      </div>
    </nav>

    <!-- ── MAIN LAYOUT ──────────────────────────────────────── -->
    <div class="dash-layout">
      <!-- LEFT: Servers -->
      <div class="dash-main">
        <div class="page-header">
          <div class="page-header-text">
            <h2>Meus Servidores</h2>
            <p class="sub">Gerencie suas pontes MCP na nuvem</p>
          </div>
          <button class="btn-add-server" onclick="openCreateModal()">
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <path d="M7 1v12M1 7h12" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
            </svg>
            Novo Servidor
          </button>
        </div>

        <div class="server-list" id="serverList">
          <div class="empty-state" id="loadingState">
            <div class="empty-icon">
              <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round">
                <path d="M5 3h14M5 21h14M7 3v4l5 5-5 5v4M17 3v4l-5 5 5 5v4" />
              </svg>
            </div>
            <div>Carregando servidores<span class="loading-dots"></span></div>
          </div>
        </div>
      </div>

      <!-- RIGHT: Sidebar -->
      <div class="dash-sidebar">
        <!-- Plan Card -->
        <div class="sidebar-card">
          <div class="sidebar-card-header">
            <span class="sidebar-label">Plano Atual</span>
            <span class="plan-badge">✦ Hobby</span>
          </div>
          <div class="stat-grid">
            <div class="stat-row">
              <span class="stat-label">Servidores ativos</span>
              <span class="stat-value num" id="serverCount">—</span>
            </div>
            <div class="stat-row">
              <span class="stat-label">Retenção de logs</span>
              <span class="stat-value num">24h</span>
            </div>
            <div class="stat-row">
              <span class="stat-label">Gateway</span>
              <span class="stat-value ok" id="gatewayStatus">---</span>
            </div>
            <div class="stat-row" id="quotaRowServers" style="display:none">
              <span class="stat-label">Servidores</span>
              <span class="stat-value" id="quotaServers">0/1</span>
            </div>
            <div class="stat-row" id="quotaRowPlan" style="display:none">
              <span class="stat-label">Plano</span>
              <span class="stat-value" id="quotaPlan">Free</span>
            </div>
          </div>
          <div class="sub-section" id="subSection" style="display:none">
            <div class="sub-title">Subscrição</div>
            <div class="sub-quota"><span>Servidores</span><span class="val" id="subServers">0 / 1</span></div>
            <div class="sub-quota"><span>RPM</span><span class="val" id="subRPM">10</span></div>
            <div class="sub-upgrade" id="subUpgrade">
              <button class="sub-upgrade-btn" onclick="showPayPal()">Assinar Pro — $9.90/mês</button>
            </div>
            <div id="paypal-button-container" style="display:none"></div>
          </div>
        </div>

        <!-- Live Logs -->
        <div class="sidebar-logs">
          <div class="sidebar-logs-header">
            <div class="logs-header-left">
              <span class="pulse-dot"></span>
              <span class="log-title">Logs</span>
              <select class="log-server-select" id="logServerSelect" onchange="switchLogServer(this.value)">
                <option value="">Servidor...</option>
              </select>
            </div>
            <div class="logs-header-actions">
              <button class="log-action-btn" title="Exportar JSON" onclick="exportLogs('json')">↓</button>
              <button class="log-action-btn" title="Exportar CSV" onclick="exportLogs('csv')">⇩</button>
              <button class="log-action-btn log-action-danger" title="Limpar logs" onclick="clearLogs()">✕</button>
              <button class="log-refresh-btn" title="Atualizar" onclick="pollLogs()">↻</button>
            </div>
          </div>
          <div class="log-filter-bar">
            <input type="text" class="log-filter-input" id="logToolFilter" placeholder="Filtrar tool..." oninput="debouncePoll()">
            <select class="log-filter-select" id="logStatusFilter" onchange="pollLogs()">
              <option value="">Todos</option>
              <option value="200-299">2xx Sucesso</option>
              <option value="400-499">4xx Erro</option>
              <option value="500-599">5xx Erro</option>
            </select>
          </div>
          <div class="sidebar-logs-body" id="liveLogs">
            <div style="color: rgba(255, 255, 255, 0.2)">
              Aguardando atividade...
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ── EDIT MODAL ────────────────────────────────────────── -->
    <div class="modal-overlay" id="editModal">
      <div class="modal-box">
        <div class="modal-header">
          <h3>Editar Servidor</h3>
          <p class="modal-sub">Altere as configurações do servidor MCP</p>
        </div>
        <div class="form-group">
          <label for="editName">Nome do Servidor</label>
          <input type="text" id="editName" placeholder="Ex: Minha API" />
        </div>
        <div class="form-group">
          <label for="editTransport">Transporte</label>
          <select id="editTransport">
            <option value="http">Streamable HTTP (recomendado)</option>
            <option value="sse">SSE (legado)</option>
          </select>
        </div>
        <div class="form-group">
          <label for="editStatus">Status</label>
          <select id="editStatus">
            <option value="active">Online</option>
            <option value="inactive">Offline</option>
          </select>
        </div>
        <div class="modal-error" id="editError"></div>
        <div class="modal-actions">
          <button class="btn-cancel" onclick="closeEditModal()">Cancelar</button>
          <button class="btn-confirm" id="btnEditConfirm" onclick="saveEdit()">Salvar</button>
        </div>
      </div>
    </div>

    <!-- ── CREATE MODAL ──────────────────────────────────────── -->
    <div class="modal-overlay" id="createModal">
      <div class="modal-box">
        <div class="modal-header">
          <h3>Novo Servidor</h3>
          <p class="modal-sub">Registre uma nova API para ser convertida em MCP</p>
        </div>
        <div class="form-group">
          <label for="inputName">Nome do Servidor</label>
          <input type="text" id="inputName" placeholder="Ex: Minha API Principal" />
        </div>
        <div class="form-group">
          <label for="inputSpecUrl">URL do OpenAPI Spec</label>
          <input type="url" id="inputSpecUrl" placeholder="https://api.exemplo.com/openapi.json" />
        </div>
        <div class="form-group">
          <label for="inputTransport">Transporte</label>
          <select id="inputTransport">
            <option value="http">Streamable HTTP (recomendado)</option>
            <option value="sse">SSE (legado)</option>
          </select>
        </div>
        <div class="modal-error" id="modalError"></div>
        <div class="modal-actions">
          <button class="btn-cancel" onclick="closeCreateModal()">Cancelar</button>
          <button class="btn-confirm" id="btnCreateConfirm" onclick="createServer()">Criar Servidor</button>
        </div>
      </div>
    </div>

    <!-- ── LOG DETAIL MODAL ──────────────────────────────────── -->
    <div class="modal-overlay" id="logDetailModal">
      <div class="modal-box log-detail-box">
        <div class="modal-header">
          <h3>Detalhe do Log</h3>
          <p class="modal-sub">Requisição e resposta completas</p>
        </div>
        <div class="log-detail-meta">
          <span class="log-detail-meta-item"><span class="label">Tool</span> <span id="detailTool">—</span></span>
          <span class="log-detail-meta-item"><span class="label">Method</span> <span id="detailMethod">—</span></span>
          <span class="log-detail-meta-item"><span class="label">Status</span> <span id="detailStatus" class="status-badge">—</span></span>
          <span class="log-detail-meta-item"><span class="label">Duração</span> <span id="detailDuration">—</span></span>
          <span class="log-detail-meta-item"><span class="label">Data</span> <span id="detailTime">—</span></span>
        </div>
        <div class="log-detail-scroll">
          <div class="log-detail-section">
            <h4>Request Body</h4>
            <div class="log-detail-body" id="detailReqBody">(vazio)</div>
          </div>
          <div class="log-detail-section">
            <h4>Response Body</h4>
            <div class="log-detail-body" id="detailResBody">(vazio)</div>
          </div>
        </div>
        <div class="modal-actions">
          <button class="btn-cancel" onclick="closeLogDetail()">Fechar</button>
        </div>
      </div>
    </div>

    <!-- ── PROFILE MODAL ────────────────────────────────────────── -->
    <div class="modal-overlay" id="profileModal">
      <div class="modal-box profile-modal-box">
        <!-- Header -->
        <div class="profile-modal-header">
          <div class="profile-avatar-section">
            <div class="profile-modal-avatar" id="profileAvatarWrap">
              <span class="profile-modal-avatar-initials">U</span>
            </div>
            <div class="profile-header-info">
              <h3 id="profileName">—</h3>
              <span id="profileEmail" class="profile-email">—</span>
              <div class="profile-badges">
                <span id="profilePlan" class="profile-plan-badge free">free</span>
                <span class="profile-provider-badge" id="profileProvider">EMAIL</span>
              </div>
            </div>
          </div>
          <button class="profile-close-btn" onclick="closeProfileModal()" title="Fechar">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
          </button>
        </div>

        <!-- Stats row -->
        <div class="profile-stats-row">
          <div class="profile-stat">
            <span class="profile-stat-label">Servidores</span>
            <span class="profile-stat-value" id="profileServersCount">—</span>
          </div>
          <div class="profile-stat-divider"></div>
          <div class="profile-stat">
            <span class="profile-stat-label">RPM</span>
            <span class="profile-stat-value" id="profileRpm">—</span>
          </div>
          <div class="profile-stat-divider"></div>
          <div class="profile-stat">
            <span class="profile-stat-label">Membro desde</span>
            <span class="profile-stat-value profile-stat-date" id="profileCreatedAt">—</span>
          </div>
        </div>

        <!-- Token section -->
        <div class="profile-section">
          <div class="profile-section-title">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"/></svg>
            Token de Acesso (Bearer)
          </div>
          <div class="profile-token-field">
            <input type="password" id="profileToken" class="profile-token-input" readonly />
            <button class="profile-token-btn" id="toggleTokenBtn" onclick="toggleTokenVisibility()" title="Mostrar/ocultar token">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
            </button>
            <button class="profile-token-btn profile-copy-btn" id="copyTokenBtn" onclick="copyToken()" title="Copiar token">Copiar</button>
          </div>
          <p class="profile-token-hint">Use este token no cabeçalho <code>Authorization: Bearer <token></code> para autenticar pedidos à API.</p>
        </div>

        <!-- Account details -->
        <div class="profile-section">
          <div class="profile-section-title">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="3"/><path d="M19.07 4.93l-1.41 1.41M12 2v2M4.93 4.93l1.41 1.41M2 12h2M4.93 19.07l1.41-1.41M12 20v2M19.07 19.07l-1.41-1.41M20 12h2"/></svg>
            Detalhes da Conta
          </div>
          <div class="profile-details-grid">
            <div class="profile-detail-row">
              <span class="profile-detail-label">User ID</span>
              <span class="profile-detail-value profile-detail-mono" id="profileUserId">—</span>
            </div>
            <div class="profile-detail-row">
              <span class="profile-detail-label">Email</span>
              <span class="profile-detail-value" id="profileEmailDetail">—</span>
            </div>
            <div class="profile-detail-row">
              <span class="profile-detail-label">Fornecedor</span>
              <span class="profile-detail-value" id="profileProviderDetail">—</span>
            </div>
          </div>
        </div>

        <!-- Actions -->
        <div class="profile-modal-actions">
          <button class="btn-cancel" onclick="closeProfileModal()">Fechar</button>
          <button class="profile-logout-btn" onclick="logoutFromProfile()">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
            Terminar Sessão
          </button>
        </div>
      </div>
    </div>

    <!-- Portal para dropdowns (evita overflow:hidden dos cards) -->
    <div id="menuPortal"></div>

    <!-- Loading Overlay -->
    <div class="loading-overlay" id="loadingOverlay">
      <div class="loading-spinner"></div>
      <div class="loading-text" id="loadingText">Aguarde...</div>
    </div>