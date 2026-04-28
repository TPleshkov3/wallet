const { createApp } = Vue;

createApp({
  data() {
    const now = new Date();
    return {
      api: "http://127.0.0.1:8000",
      theme: localStorage.getItem("theme") || "light",
      token: localStorage.getItem("token") || "",
      authTab: "login",
      loginForm: { email: "", password: "" },
      registerForm: { name: "", email: "", password: "" },
      familyName: "",
      joinCode: "",
      membership: null,
      selectedAccount: "main",
      accounts: [],
      transactions: [],
      familyMembers: [],
      newAccountName: "",
      recurringPayments: [],
      auditLogs: [],
      ownerInviteCode: "",
      goal: null,
      goalForm: { title: "", target_amount: null, deadline_year: now.getFullYear(), deadline_month: now.getMonth() + 1, account_type: "main" },
      report: { total_income: 0, total_expense: 0, balance: 0, by_category: {}, by_user: {} },
      reportFilters: { year: now.getFullYear(), month: now.getMonth() + 1, dateFrom: "", dateTo: "", category: "", type: "" },
      historyFilters: { dateFrom: "", dateTo: "", category: "", type: "" },
      categories: ["Продукты", "Транспорт", "Зарплата", "Развлечения", "Коммунальные услуги", "Другое"],
      monthOptions: [
        { value: 1, label: "Январь" }, { value: 2, label: "Февраль" }, { value: 3, label: "Март" }, { value: 4, label: "Апрель" },
        { value: 5, label: "Май" }, { value: 6, label: "Июнь" }, { value: 7, label: "Июль" }, { value: 8, label: "Август" },
        { value: 9, label: "Сентябрь" }, { value: 10, label: "Октябрь" }, { value: 11, label: "Ноябрь" }, { value: 12, label: "Декабрь" },
      ],
      years: [now.getFullYear() - 1, now.getFullYear(), now.getFullYear() + 1],
      view: "budget",
      menuOpen: false,
      addModal: false,
      modalType: "income",
      txForm: { amount: null, category: "Зарплата", description: "", recurring_monthly: false, recurring_day: 1 },
      deleteModal: false,
      txToDelete: null,
      goalModal: false,
      recurringEditModal: false,
      recurringEditId: null,
      recurringForm: { amount: null, category: "Продукты", description: "", account_type: "main", day_of_month: 1 },
      toasts: [],
    };
  },
  computed: {
    balance() { return this.transactions.reduce((s, t) => s + (t.type === "income" ? t.amount : -t.amount), 0); },
    filteredTransactions() {
      return this.transactions.filter((t) => {
        if (this.historyFilters.type && t.type !== this.historyFilters.type) return false;
        if (this.historyFilters.category && t.category !== this.historyFilters.category) return false;
        if (this.historyFilters.dateFrom && t.date < this.historyFilters.dateFrom) return false;
        if (this.historyFilters.dateTo && t.date > this.historyFilters.dateTo) return false;
        return true;
      });
    },
    categoryRows() { return this.toRows(this.report.by_category); },
    userRows() { return this.toRows(this.report.by_user); },
    canManageAccounts() {
      if (!this.membership) return false;
      if (this.membership.role === "owner") return true;
      const me = this.familyMembers.find((m) => m.user_id === this.membership.user_id);
      return Boolean(me && me.can_manage_accounts);
    },
    editableMembers() {
      return this.familyMembers.filter((m) => m.role !== "owner");
    },
  },
  async mounted() {
    document.body.setAttribute("data-theme", this.theme);
    if (this.token) {
      await this.loadMembership();
      if (this.membership) await this.refreshMainData();
    }
    document.addEventListener("click", this.handleOutsideClick);
  },
  unmounted() { document.removeEventListener("click", this.handleOutsideClick); },
  methods: {
    headers() { return { "Content-Type": "application/json", ...(this.token ? { Authorization: `Bearer ${this.token}` } : {}) }; },
    toast(text, type = "ok") { const id = Date.now() + Math.random(); this.toasts.push({ id, text, type }); setTimeout(() => this.toasts = this.toasts.filter((t) => t.id !== id), 3500); },
    money(v) { return Number(v || 0).toLocaleString("ru-RU"); },
    signedMoney(v) { const n = Number(v || 0); return `${n >= 0 ? "+" : ""}${this.money(n)}`; },
    prettyDate(d) { return new Date(d).toLocaleDateString("ru-RU", { day: "2-digit", month: "long", year: "numeric" }); },
    prettyDateTime(d) { return new Date(d).toLocaleString("ru-RU"); },
    monthLabel(m) { return this.monthOptions.find((x) => x.value === m)?.label || m; },
    toRows(map) { const e = Object.entries(map || {}); const max = Math.max(...e.map(([,v]) => v), 0); return e.map(([name, value]) => ({ name, value, percent: max ? Math.round(value / max * 100) : 0 })); },
    async request(path, options = {}) { const r = await fetch(this.api + path, options); const b = await r.json().catch(() => ({})); if (!r.ok) throw new Error(b.detail || "Ошибка"); return b; },
    async register() { try { await this.request("/auth/register", { method:"POST", headers:this.headers(), body:JSON.stringify(this.registerForm)}); this.authTab="login"; this.toast("Регистрация успешна"); } catch(e){ this.toast(e.message, "error"); } },
    async login() { try { const d = await this.request("/auth/login", { method:"POST", headers:this.headers(), body:JSON.stringify(this.loginForm)}); this.token=d.token; localStorage.setItem("token", d.token); await this.loadMembership(); if (this.membership) await this.refreshMainData(); this.toast("Вход выполнен"); } catch(e){ this.toast(e.message, "error"); } },
    async loadMembership() { try { this.membership = await this.request("/families/me", { headers: this.headers() }); } catch { this.membership = null; } },
    async createFamily() { try { await this.request("/families", { method:"POST", headers:this.headers(), body:JSON.stringify({name:this.familyName}) }); await this.loadMembership(); await this.refreshMainData(); this.toast("Семья создана"); } catch(e){ this.toast(e.message, "error"); } },
    async joinFamily() { try { await this.request("/families/join", { method:"POST", headers:this.headers(), body:JSON.stringify({code:this.joinCode.toUpperCase()}) }); await this.loadMembership(); await this.refreshMainData(); this.toast("Вы вступили в семью"); } catch(e){ this.toast(e.message, "error"); } },
    async refreshMainData() {
      await this.loadAccounts();
      await Promise.all([this.loadTransactions(), this.loadGoal(), this.loadOwnerInviteCode()]);
      if (this.view === "report") await this.loadReport();
      if (this.view === "family") await this.loadFamilyMembers();
      if (this.view === "regular") await this.loadRecurring();
      if (this.view === "journal") await this.loadAuditLogs();
    },
    async loadAccounts() {
      this.accounts = await this.request(`/families/${this.membership.family_id}/accounts`, { headers: this.headers() });
      if (!this.accounts.some((a) => a.name === this.selectedAccount)) {
        this.selectedAccount = this.accounts[0]?.name || "main";
      }
    },
    async loadTransactions() { this.transactions = await this.request(`/transactions?family_id=${this.membership.family_id}&account_type=${this.selectedAccount}`, { headers:this.headers() }); },
    async loadGoal() { this.goal = await this.request(`/goals/current?family_id=${this.membership.family_id}`, { headers:this.headers() }); },
    async loadOwnerInviteCode() { if (this.membership.role !== "owner") { this.ownerInviteCode = ""; return; } const d = await this.request(`/families/${this.membership.family_id}/invite`, { headers:this.headers() }); this.ownerInviteCode = d.invite_code; },
    async loadFamilyMembers() {
      this.familyMembers = await this.request(`/families/${this.membership.family_id}/members`, { headers:this.headers() });
    },
    async loadRecurring() { this.recurringPayments = await this.request(`/transactions/recurring?family_id=${this.membership.family_id}`, { headers:this.headers() }); },
    async loadAuditLogs() { this.auditLogs = await this.request(`/transactions/audit-log?family_id=${this.membership.family_id}`, { headers:this.headers() }); },
    reportQuery() {
      const p = new URLSearchParams({ family_id: String(this.membership.family_id), year: String(this.reportFilters.year), month: String(this.reportFilters.month), account_type: this.selectedAccount });
      if (this.reportFilters.dateFrom) p.set("date_from", this.reportFilters.dateFrom);
      if (this.reportFilters.dateTo) p.set("date_to", this.reportFilters.dateTo);
      if (this.reportFilters.type) p.set("tx_type", this.reportFilters.type);
      if (this.reportFilters.category) p.set("category", this.reportFilters.category);
      return p.toString();
    },
    async loadReport() { this.report = await this.request(`/report?${this.reportQuery()}`, { headers:this.headers() }); },
    setView(v) { this.view=v; this.menuOpen=false; if (v==="history") this.loadTransactions(); if (v==="report") this.loadReport(); if (v==="family") this.loadFamilyMembers(); if (v==="regular") this.loadRecurring(); if (v==="journal") this.loadAuditLogs(); },
    async createAccount() {
      if (!this.newAccountName.trim()) return;
      try {
        await this.request(`/families/${this.membership.family_id}/accounts`, {
          method: "POST",
          headers: this.headers(),
          body: JSON.stringify({ name: this.newAccountName.trim() }),
        });
        this.newAccountName = "";
        await this.loadAccounts();
        this.toast("Счет создан");
      } catch (e) {
        this.toast(e.message, "error");
      }
    },
    async updatePermission(member, key, value) {
      try {
        const payload = {
          user_id: member.user_id,
          can_manage_accounts: key === "can_manage_accounts" ? value : member.can_manage_accounts,
          can_delete_any_transactions: key === "can_delete_any_transactions" ? value : member.can_delete_any_transactions,
        };
        await this.request(`/families/${this.membership.family_id}/permissions`, {
          method: "PUT",
          headers: this.headers(),
          body: JSON.stringify(payload),
        });
        await this.loadFamilyMembers();
        this.toast("Права обновлены");
      } catch (e) {
        this.toast(e.message, "error");
      }
    },
    openAddModal(type) { this.modalType = type; this.txForm.category = type === "income" ? "Зарплата" : "Продукты"; this.txForm.recurring_monthly = false; this.addModal = true; },
    closeAddModal() { this.addModal = false; },
    async submitAdd() {
      try {
        await this.request("/transactions", { method:"POST", headers:this.headers(), body: JSON.stringify({ family_id: this.membership.family_id, type: this.modalType, amount: this.txForm.amount, category: this.txForm.category, description: this.txForm.description, account_type: this.selectedAccount, recurring_monthly: this.txForm.recurring_monthly, recurring_day: this.txForm.recurring_day }) });
        this.closeAddModal(); await this.refreshMainData(); this.toast("Операция добавлена");
      } catch(e){ this.toast(e.message, "error"); }
    },
    openDeleteModal(tx){ this.txToDelete = tx; this.deleteModal = true; },
    async submitDelete(){ try { await this.request(`/transactions/${this.txToDelete.id}?family_id=${this.membership.family_id}`, { method:"DELETE", headers:this.headers() }); this.deleteModal=false; await this.refreshMainData(); this.toast("Удалено"); } catch(e){ this.toast(e.message, "error"); } },
    async deleteRecurring(id){ try { await this.request(`/transactions/recurring/${id}?family_id=${this.membership.family_id}`, { method:"DELETE", headers:this.headers() }); await this.loadRecurring(); this.toast("Регулярный платеж удален"); } catch(e){ this.toast(e.message, "error"); } },
    openEditRecurringModal(recurring) {
      this.recurringEditId = recurring.id;
      this.recurringForm = {
        amount: recurring.amount,
        category: recurring.category,
        description: recurring.description || "",
        account_type: recurring.account_type,
        day_of_month: recurring.day_of_month,
      };
      this.recurringEditModal = true;
    },
    closeEditRecurringModal() {
      this.recurringEditModal = false;
      this.recurringEditId = null;
    },
    async submitEditRecurring() {
      try {
        await this.request(`/transactions/recurring/${this.recurringEditId}?family_id=${this.membership.family_id}`, {
          method: "PUT",
          headers: this.headers(),
          body: JSON.stringify(this.recurringForm),
        });
        this.closeEditRecurringModal();
        await this.loadRecurring();
        this.toast("Регулярный платеж обновлен");
      } catch (e) {
        this.toast(e.message, "error");
      }
    },
    openGoalModal(){ if (this.goal) { this.goalForm = { title:this.goal.title, target_amount:this.goal.target_amount, deadline_year:this.goal.deadline_year, deadline_month:this.goal.deadline_month, account_type:this.goal.account_type }; } this.goalModal=true; },
    openGoalModalFromMenu(){ this.menuOpen = false; this.openGoalModal(); },
    async saveGoal(){ try { await this.request(`/goals?family_id=${this.membership.family_id}`, { method:"POST", headers:this.headers(), body:JSON.stringify(this.goalForm) }); this.goalModal=false; await this.loadGoal(); this.toast("Цель сохранена"); } catch(e){ this.toast(e.message, "error"); } },
    async copyInvite(code){ if(!code) { this.toast("Код недоступен", "error"); return; } await navigator.clipboard.writeText(code); this.toast("Код скопирован"); },
    toggleTheme(){ this.theme = this.theme === "dark" ? "light" : "dark"; localStorage.setItem("theme", this.theme); document.body.setAttribute("data-theme", this.theme); },
    handleOutsideClick(e){ if(!e.target.closest(".menu-wrap")) this.menuOpen=false; },
    logout(){ localStorage.removeItem("token"); this.token=""; this.membership=null; this.transactions=[]; this.accounts=[]; this.menuOpen=false; this.toast("Вы вышли"); },
  },
}).mount("#app");
