document.addEventListener("DOMContentLoaded", () => {
  initTheme();
  initSearch();
  markActiveNav();
  initOrderFormDynamic();
  if (Array.isArray(window.__msgs)) {
    window.__msgs.forEach((m) =>
      showPopup(
        m.level?.includes("error") ? "error" : "success",
        typeof m.text === "string" ? m.text : String(m.text),
      ),
    );
  }
});

function showPopup(type, text) {
  try {
    const root = document.getElementById("popup-root");
    if (!root) return;
    const overlay = document.createElement("div");
    overlay.className = "popup-overlay";
    const card = document.createElement("div");
    card.className = "popup-card";
    card.innerHTML = `
      <div class="popup-head">
        <div class="popup-icon ${type === "success" ? "success" : "error"}">${type === "success" ? "✓" : "✕"}</div>
        <div>
          <div class="fw-bold">${type === "success" ? "Success" : "Action failed"}</div>
          <div class="text-muted small">${text || ""}</div>
        </div>
      </div>
      <div class="popup-actions">
        <button class="btn btn-outline-secondary btn-sm">Close</button>
      </div>`;
    overlay.appendChild(card);
    root.appendChild(overlay);
    const close = () => {
      overlay.remove();
    };
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) close();
    });
    card.querySelector("button")?.addEventListener("click", close);
    setTimeout(close, 3200);
  } catch {}
}

function initTheme() {
  const body = document.body;
  const btn = document.getElementById("theme-toggle");
  const stored = localStorage.getItem("theme") || "light";
  body.classList.remove("light", "dark");
  body.classList.add(stored);
  if (btn) {
    btn.innerHTML =
      stored === "dark"
        ? '<i class="bi bi-sun"></i>'
        : '<i class="bi bi-moon"></i>';
    btn.onclick = () => {
      const next = body.classList.contains("dark") ? "light" : "dark";
      body.classList.remove("light", "dark");
      body.classList.add(next);
      localStorage.setItem("theme", next);
      btn.innerHTML =
        next === "dark"
          ? '<i class="bi bi-sun"></i>'
          : '<i class="bi bi-moon"></i>';
    };
  }
}

function markActiveNav() {
  const path = location.pathname;
  document.querySelectorAll("#sidebar .nav-link").forEach((a) => {
    if (a.getAttribute("href") === path) a.classList.add("active");
  });
}

async function refreshRecentOrders() {
  const el = document.getElementById("recent-orders");
  if (!el) return;
  el.innerHTML = `<div class="skeleton h-6 mb-2"></div><div class="skeleton h-6 mb-2"></div>`;
  try {
    const res = await fetch("/api/orders/recent/");
    const data = await res.json();
    const rows = (data.orders || [])
      .map(
        (o) => `
      <tr>
        <td>${o.order_number}</td>
        <td><span class="pill pill-${o.status}">${o.status.replace("_", " ").toUpperCase()}</span></td>
        <td>${o.type.toUpperCase()}</td>
        <td><span class="pill pill-priority-${o.priority}">${o.priority.toUpperCase()}</span></td>
        <td>${o.customer}</td>
        <td>${o.vehicle || "-"}</td>
        <td>${new Date(o.created_at).toLocaleString()}</td>
      </tr>`,
      )
      .join("");
    el.innerHTML = `<table class="table align-middle"><thead><tr><th>Order</th><th>Status</th><th>Type</th><th>Priority</th><th>Customer</th><th>Vehicle</th><th>Created</th></tr></thead><tbody>${rows}</tbody></table>`;
  } catch (e) {
    el.innerHTML =
      '<div class="text-danger">Failed to load recent orders.</div>';
  }
}

function initSearch() {
  const input = document.getElementById("global-search");
  const panel = document.getElementById("global-search-panel");
  if (!input || !panel) return;
  let idx = -1;
  let items = [];
  const hide = () => {
    panel.classList.add("d-none");
    idx = -1;
  };
  const show = () => {
    panel.classList.remove("d-none");
  };
  const render = (results) => {
    if (!results.length) {
      panel.innerHTML = '<div class="p-3 text-muted small">No results</div>';
      return;
    }
    panel.innerHTML = results
      .map(
        (r, i) =>
          `<div class="search-item ${i === idx ? "active" : ""}" data-i="${i}" data-id="${r.id}">
        <div><strong>${r.name}</strong><div class="search-secondary">${r.code} · ${r.phone}</div></div>
        <span class="pill pill-${r.type || "personal"}">${(r.type || "personal").toUpperCase()}</span>
      </div>`,
      )
      .join("");
    panel.querySelectorAll(".search-item").forEach((el) => {
      el.onclick = () => {
        location.href = `/customers/${el.dataset.id}/`;
      };
    });
  };
  const fetcher = async (q) => {
    const res = await fetch(`/customers/search/?q=${encodeURIComponent(q)}`);
    const data = await res.json();
    items = data.results || [];
    render(items);
    if (items.length) show();
    else hide();
  };
  let t;
  input.addEventListener("input", (e) => {
    const q = input.value.trim();
    clearTimeout(t);
    if (!q) {
      hide();
      return;
    }
    t = setTimeout(() => fetcher(q), 200);
  });
  input.addEventListener("keydown", (e) => {
    if (panel.classList.contains("d-none")) return;
    if (e.key === "ArrowDown") {
      idx = Math.min(idx + 1, items.length - 1);
      render(items);
      e.preventDefault();
    } else if (e.key === "ArrowUp") {
      idx = Math.max(idx - 1, 0);
      render(items);
      e.preventDefault();
    } else if (e.key === "Enter") {
      if (items[idx]) location.href = `/customers/${items[idx].id}/`;
      else performGlobalSearch();
    } else if (e.key === "Escape") {
      hide();
    }
  });
  document.addEventListener("click", (e) => {
    if (!panel.contains(e.target) && e.target !== input) hide();
  });
}

// Auto-submit status change selects
document.addEventListener("change", (e) => {
  const sel = e.target.closest(".js-status-select");
  if (sel) {
    const form = sel.closest("form");
    if (form) {
      form.submit();
    }
  }
});

function performGlobalSearch() {
  const q = document.getElementById("global-search").value.trim();
  if (!q) return;
  fetch(`/customers/search/?q=${encodeURIComponent(q)}`)
    .then((r) => r.json())
    .then((data) => {
      if (!data.results?.length) {
        alert("No customers found");
        return;
      }
      const c = data.results[0];
      window.location.href = `/customers/${c.id}/`;
    });
}

function setNextStep(n) {
  const inp = document.querySelector('input[name="step"]');
  if (inp) inp.value = n;
}

function saveDraft() {
  const form = document.getElementById("reg-form");
  if (!form) return;
  const data = new FormData(form);
  const obj = {};
  data.forEach((v, k) => {
    obj[k] = v;
  });
  localStorage.setItem("customer_reg_draft", JSON.stringify(obj));
}

function restoreDraft() {
  const s = localStorage.getItem("customer_reg_draft");
  if (!s) return;
  try {
    const data = JSON.parse(s);
    for (const [k, v] of Object.entries(data)) {
      const el = document.querySelector(`[name="${k}"]`);
      if (el && !["csrfmiddlewaretoken", "step"].includes(k)) el.value = v;
    }
  } catch {}
}

function initOrderFormDynamic() {
  const typeSel = document.querySelector('select[name="type"], #id_type');
  const service = document.getElementById("service-group");
  const sales = document.getElementById("sales-group");
  const consult = document.getElementById("consultation-group");
  const vehicle = document.getElementById("vehicle-section");
  const form = typeSel
    ? typeSel.closest("form")
    : document.getElementById("reg-form") || document.querySelector("form");

  const byName = (n) =>
    form
      ? form.querySelector(`[name="${n}"]`)
      : document.querySelector(`[name="${n}"]`);
  const setReq = (names, on) => {
    (names || []).forEach((n) => {
      const el = byName(n);
      if (!el) return;
      if (on) el.setAttribute("required", "required");
      else el.removeAttribute("required");
    });
  };
  const hideAll = () => {
    [service, sales, consult].forEach((x) => x && (x.style.display = "none"));
  };
  const toggle = () => {
    if (!typeSel) return;
    const v = typeSel.value;
    hideAll();
    // Reset requirements
    setReq(
      [
        "description",
        "estimated_duration",
        "item_name",
        "brand",
        "quantity",
        "tire_type",
        "inquiry_type",
        "questions",
        "contact_preference",
      ],
      false,
    );
    if (v === "service") {
      if (service) service.style.display = "block";
      if (vehicle) vehicle.style.display = "block";
      setReq(["description", "estimated_duration"], true);
    } else if (v === "sales") {
      if (sales) sales.style.display = "flex";
      if (vehicle) vehicle.style.display = "none";
      setReq(["item_name", "brand", "quantity", "tire_type"], true);
      const qty = byName("quantity");
      if (
        qty &&
        (!qty.getAttribute("min") || Number(qty.getAttribute("min")) < 1)
      )
        qty.setAttribute("min", "1");
    } else if (v === "consultation") {
      if (consult) consult.style.display = "flex";
      if (vehicle) vehicle.style.display = "none";
      setReq(["inquiry_type", "questions", "contact_preference"], true);
    }
  };
  if (typeSel) {
    typeSel.addEventListener("change", toggle);
    setTimeout(toggle, 0);
  }

  // Submit-time validation for dynamic parts
  if (form) {
    form.addEventListener("submit", (e) => {
      if (!typeSel) return;
      const v = typeSel.value;
      if (v === "service") {
        const any =
          form.querySelectorAll('input[name="service_selection"]:checked')
            .length > 0;
        if (!any) {
          e.preventDefault();
          showPopup(
            "error",
            "Select at least one service in Service Selection",
          );
          return;
        }
      }
      if (v === "sales") {
        const qty = byName("quantity");
        if (qty && Number(qty.value || 0) < 1) {
          e.preventDefault();
          showPopup("error", "Quantity must be at least 1");
          qty.focus();
          return;
        }
      }
    });
  }

  // Customer type dynamic fields
  const custType = document.querySelector(
    'select[name="customer_type"], #id_customer_type',
  );
  const org = document.getElementById("org-fields");
  const personal = document.getElementById("personal-fields");
  const toggleCust = () => {
    if (!custType) return;
    const t = custType.value;
    if (org)
      org.style.display =
        t === "government" || t === "ngo" || t === "company" ? "block" : "none";
    if (personal) personal.style.display = t === "personal" ? "block" : "none";
  };
  if (custType) {
    custType.addEventListener("change", toggleCust);
    setTimeout(toggleCust, 0);
  }
}
