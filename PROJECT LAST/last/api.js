/**
 * ArtCraft API Client
 * Drop this <script> into all 4 HTML pages (login, artist, brand, customer)
 * Replaces all localStorage calls with real API calls
 *
 * Usage:
 *   <script src="api.js"></script>
 *   Then use: await API.login(email, password, role)
 */

const API_BASE = "http://localhost:8000";   // Change to your server URL

// ── Token Storage ─────────────────────────────────────────────
const API = {
  _token: localStorage.getItem("artcraft_api_token") || null,

  _headers() {
    const h = { "Accept": "application/json" };
    if (this._token) h["Authorization"] = `Bearer ${this._token}`;
    return h;
  },

  _setToken(token) {
    this._token = token;
    localStorage.setItem("artcraft_api_token", token);
  },

  _clearToken() {
    this._token = null;
    localStorage.removeItem("artcraft_api_token");
  },

  // ── Helper: build FormData from object ─────────────────────
  _form(data) {
    const fd = new FormData();
    for (const [k, v] of Object.entries(data)) {
      if (v !== null && v !== undefined) fd.append(k, v);
    }
    return fd;
  },

  // ── Core fetch wrapper ──────────────────────────────────────
  async _fetch(method, path, body = null, isForm = false) {
    const opts = { method, headers: this._headers() };
    if (body) {
      if (isForm) {
        opts.body = body instanceof FormData ? body : this._form(body);
        // Don't set Content-Type — browser sets it with boundary for FormData
      } else {
        opts.headers["Content-Type"] = "application/json";
        opts.body = JSON.stringify(body);
      }
    }
    const res = await fetch(`${API_BASE}${path}`, opts);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
    return data;
  },

  // ═══════════════════════════════════════════════════════════
  // AUTH
  // ═══════════════════════════════════════════════════════════

  async signup(firstName, lastName, email, password, role) {
    const data = await this._fetch("POST", "/auth/signup", {
      first_name: firstName, last_name: lastName,
      email, password, role
    }, true);
    this._setToken(data.token);
    localStorage.setItem("artcraft_session_v1", JSON.stringify({
      userId: data.user_id, role: data.role,
      name: data.name, email: data.email
    }));
    return data;
  },

  async login(email, password, role) {
    const data = await this._fetch("POST", "/auth/login", { email, password, role }, true);
    this._setToken(data.token);
    localStorage.setItem("artcraft_session_v1", JSON.stringify({
      userId: data.user_id, role: data.role,
      name: data.name, email: data.email
    }));
    return data;
  },

  async logout() {
    try { await this._fetch("POST", "/auth/logout"); } catch (e) {}
    this._clearToken();
    localStorage.removeItem("artcraft_session_v1");
  },

  async getMe() {
    return this._fetch("GET", "/auth/me");
  },

  // ═══════════════════════════════════════════════════════════
  // PROFILE
  // ═══════════════════════════════════════════════════════════

  async updateProfile(fields) {
    // fields can include File objects for 'avatar' and 'cover'
    const fd = new FormData();
    for (const [k, v] of Object.entries(fields)) {
      if (v !== null && v !== undefined) fd.append(k, v);
    }
    const res = await fetch(`${API_BASE}/profile`, {
      method: "PUT", headers: this._headers(), body: fd
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || "Update failed");
    return data;
  },

  async addSkill(skill) {
    return this._fetch("POST", "/profile/skills", { skill }, true);
  },

  async removeSkill(skill) {
    return this._fetch("DELETE", `/profile/skills/${encodeURIComponent(skill)}`);
  },

  // ═══════════════════════════════════════════════════════════
  // ARTWORKS
  // ═══════════════════════════════════════════════════════════

  async uploadArtwork(fields) {
    // fields: { title, price, medium, dims, desc, status, image?: File }
    const fd = new FormData();
    for (const [k, v] of Object.entries(fields)) {
      if (v !== null && v !== undefined) fd.append(k, v);
    }
    const res = await fetch(`${API_BASE}/artworks`, {
      method: "POST", headers: this._headers(), body: fd
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || "Upload failed");
    return data;
  },

  async getArtworks(params = {}) {
    const q = new URLSearchParams(params).toString();
    return this._fetch("GET", `/artworks${q ? "?" + q : ""}`);
  },

  async getMyArtworks() {
    return this._fetch("GET", "/artworks/mine");
  },

  async updateArtwork(id, fields) {
    const fd = new FormData();
    for (const [k, v] of Object.entries(fields)) {
      if (v !== null && v !== undefined) fd.append(k, v);
    }
    const res = await fetch(`${API_BASE}/artworks/${id}`, {
      method: "PUT", headers: this._headers(), body: fd
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || "Update failed");
    return data;
  },

  async deleteArtwork(id) {
    return this._fetch("DELETE", `/artworks/${id}`);
  },

  // ═══════════════════════════════════════════════════════════
  // TUTORIALS
  // ═══════════════════════════════════════════════════════════

  async uploadTutorial(fields) {
    // fields: { title, price, duration, level, lang, desc, video?: File, thumb?: File }
    const fd = new FormData();
    for (const [k, v] of Object.entries(fields)) {
      if (v !== null && v !== undefined) fd.append(k, v);
    }
    const res = await fetch(`${API_BASE}/tutorials`, {
      method: "POST", headers: this._headers(), body: fd
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || "Upload failed");
    return data;
  },

  async getTutorials(params = {}) {
    const q = new URLSearchParams(params).toString();
    return this._fetch("GET", `/tutorials${q ? "?" + q : ""}`);
  },

  async getTutorial(id) {
    return this._fetch("GET", `/tutorials/${id}`);
  },

  async getPurchasedTutorials() {
    return this._fetch("GET", "/tutorials/mine/purchased");
  },

  async deleteTutorial(id) {
    return this._fetch("DELETE", `/tutorials/${id}`);
  },

  // ═══════════════════════════════════════════════════════════
  // PAYMENTS
  // ═══════════════════════════════════════════════════════════

  async buyTutorial(tutorialId) {
    // Returns { checkout_url } — redirect browser to it
    return this._fetch("POST", "/payments/tutorial/checkout", { tutorial_id: tutorialId }, true);
  },

  async verifyTutorialPayment(sessionId) {
    return this._fetch("POST", "/payments/tutorial/verify", { session_id: sessionId }, true);
  },

  async buyArtwork(artworkId, address, phone, note = "", paymentType = "online") {
    // Online returns { checkout_url }; COD returns { order_id }
    return this._fetch("POST", "/payments/artwork/checkout", {
      artwork_id: artworkId, address, phone, note, payment_type: paymentType
    }, true);
  },

  async verifyArtworkPayment(sessionId) {
    return this._fetch("POST", "/payments/artwork/verify", { session_id: sessionId }, true);
  },

  async brandPayArtist(artistName, amount, purpose, note = "") {
    // Returns { client_secret } — confirm with Stripe.js
    return this._fetch("POST", "/payments/brand/pay-artist", {
      artist_name: artistName, amount, purpose, note
    }, true);
  },

  async confirmBrandPayment(paymentIntentId) {
    return this._fetch("POST", "/payments/brand/confirm", {
      payment_intent_id: paymentIntentId
    }, true);
  },

  async getBrandPaymentHistory() {
    return this._fetch("GET", "/payments/brand/history");
  },

  // ═══════════════════════════════════════════════════════════
  // ORDERS
  // ═══════════════════════════════════════════════════════════

  async getMyOrders() {
    return this._fetch("GET", "/orders/mine");
  },

  async getArtistOrders() {
    return this._fetch("GET", "/orders/artist");
  },

  async updateOrderStatus(orderId, status) {
    return this._fetch("PUT", `/orders/${orderId}/status`, { status }, true);
  },

  // ═══════════════════════════════════════════════════════════
  // JOBS
  // ═══════════════════════════════════════════════════════════

  async createJob(fields) {
    return this._fetch("POST", "/jobs", fields, true);
  },

  async getJobs(params = {}) {
    const q = new URLSearchParams(params).toString();
    return this._fetch("GET", `/jobs${q ? "?" + q : ""}`);
  },

  async applyToJob(jobId, message = "") {
    return this._fetch("POST", `/jobs/${jobId}/apply`, { message }, true);
  },

  async getApplications() {
    return this._fetch("GET", "/jobs/applications");
  },

  async updateApplicationStatus(appId, status) {
    return this._fetch("PUT", `/jobs/applications/${appId}/status`, { status }, true);
  },

  // ═══════════════════════════════════════════════════════════
  // COMPETITIONS
  // ═══════════════════════════════════════════════════════════

  async createCompetition(fields) {
    return this._fetch("POST", "/competitions", fields, true);
  },

  async getCompetitions(params = {}) {
    const q = new URLSearchParams(params).toString();
    return this._fetch("GET", `/competitions${q ? "?" + q : ""}`);
  },

  async registerForCompetition(compId) {
    return this._fetch("POST", `/competitions/${compId}/register`);
  },

  // ═══════════════════════════════════════════════════════════
  // MESSAGES
  // ═══════════════════════════════════════════════════════════

  async sendMessage(recipientId, body) {
    return this._fetch("POST", "/messages/send", { recipient_id: recipientId, body }, true);
  },

  async getThreads() {
    return this._fetch("GET", "/messages/threads");
  },

  async getThread(threadId) {
    return this._fetch("GET", `/messages/thread/${threadId}`);
  },

  // ═══════════════════════════════════════════════════════════
  // NOTIFICATIONS
  // ═══════════════════════════════════════════════════════════

  async getNotifications() {
    return this._fetch("GET", "/notifications");
  },

  async markAllNotificationsRead() {
    return this._fetch("PUT", "/notifications/read-all");
  },

  // ═══════════════════════════════════════════════════════════
  // ARTIST DIRECTORY
  // ═══════════════════════════════════════════════════════════

  async searchArtists(params = {}) {
    const q = new URLSearchParams(params).toString();
    return this._fetch("GET", `/artists${q ? "?" + q : ""}`);
  },

  async getArtistProfile(artistId) {
    return this._fetch("GET", `/artists/${artistId}`);
  },

  // ═══════════════════════════════════════════════════════════
  // UTILITY: Full image URL
  // ═══════════════════════════════════════════════════════════
  imgUrl(path) {
    if (!path) return null;
    if (path.startsWith("http")) return path;
    return `${API_BASE}${path}`;
  },

  isLoggedIn() {
    return !!this._token;
  }
};

// Auto-check token on load
(async () => {
  if (API._token) {
    try {
      await API.getMe();
    } catch (e) {
      API._clearToken();
    }
  }
})();