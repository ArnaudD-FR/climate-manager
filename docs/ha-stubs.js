// SPDX-License-Identifier: MIT
/**
 * Stubs of the lazy-loaded HA elements the panel renders, for the docs
 * screenshot harness (test-harness.html). Each renders a native
 * equivalent and fires the events the panel listens to, like HA.
 *
 * Loaded before panel.js, so the panel's loader (ha-elements.ts) finds
 * every tag defined and returns at once.
 */

/* global customElements, HTMLElement, CustomEvent, Event, document */

const fire = (el, type, detail) =>
  el.dispatchEvent(
    new CustomEvent(type, { detail, bubbles: true, composed: true }),
  );

/** Base: shadow root re-rendered whenever a stub property is set. */
class Stub extends HTMLElement {
  static props = [];
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    for (const prop of this.constructor.props) {
      let value = this[prop];
      Object.defineProperty(this, prop, {
        get: () => value,
        set: (v) => {
          value = v;
          if (this.isConnected) this.render();
        },
      });
    }
  }
  connectedCallback() {
    this.render();
  }
  render() {}
}

const CONTROL_CSS = `font:inherit;font-size:14px;color:var(--primary-text-color);
  background:var(--card-background-color);border:1px solid
  var(--divider-color);border-radius:4px;padding:6px 8px;`;

customElements.define(
  "ha-alert",
  class extends Stub {
    render() {
      const type = this.getAttribute("alert-type") || "info";
      const color =
        {
          error: "var(--error-color)",
          warning: "#f57c00",
          success: "var(--success-color)",
        }[type] || "var(--primary-color)";
      this.shadowRoot.innerHTML = `<div style="border-left:4px solid
        ${color};padding:8px 12px;margin:4px 0;font-size:14px;
        background:rgba(0,0,0,0.03)"><slot></slot></div>`;
    }
  },
);

customElements.define(
  "ha-button",
  class extends Stub {
    static observedAttributes = ["disabled"];
    attributeChangedCallback() {
      if (this.isConnected) this.render();
    }
    render() {
      const disabled = this.hasAttribute("disabled");
      const accent = this.getAttribute("appearance") === "accent";
      const danger = this.getAttribute("variant") === "danger";
      const color = danger ? "var(--error-color)" : "var(--primary-color)";
      this.shadowRoot.innerHTML = `<button ${disabled ? "disabled" : ""}
        style="font:inherit;font-size:14px;font-weight:500;cursor:pointer;
        border:none;border-radius:18px;padding:6px 14px;
        background:${accent ? color : "transparent"};
        color:${accent ? "#fff" : color};
        opacity:${disabled ? 0.5 : 1}">
        <slot name="start"></slot><slot></slot></button>`;
    }
  },
);

customElements.define(
  "ha-chip-set",
  class extends Stub {
    render() {
      this.shadowRoot.innerHTML = `<div style="display:flex;flex-wrap:wrap;
        gap:8px"><slot></slot></div>`;
    }
  },
);

/** Chips: outlined pill, icon slot, label; input chips get a ×. */
class Chip extends Stub {
  static props = ["label", "selected", "removable"];
  render() {
    const removable = this.removable ?? this.localName === "ha-input-chip";
    const selected = this.selected;
    this.shadowRoot.innerHTML = `<span style="display:inline-flex;
      align-items:center;gap:4px;height:32px;padding:0 12px;
      border-radius:16px;font-size:14px;cursor:pointer;
      border:1px solid var(--divider-color);
      background:${selected ? "rgba(3,169,244,0.18)" : "transparent"};
      color:var(--primary-text-color)"><slot name="icon"></slot>
      ${selected && this.localName === "ha-filter-chip" ? "✓ " : ""}
      ${this.label ?? ""}<slot></slot><slot name="trailing-icon"></slot>
      ${
        removable ? '<span class="remove" style="margin-left:4px">×</span>' : ""
      }
      </span>`;
    this.shadowRoot.querySelector(".remove")?.addEventListener("click", (e) => {
      e.stopPropagation();
      fire(this, "remove");
    });
  }
}
customElements.define("ha-input-chip", class extends Chip {});
customElements.define("ha-assist-chip", class extends Chip {});
customElements.define(
  "ha-filter-chip",
  class extends Chip {
    connectedCallback() {
      super.connectedCallback();
      this.addEventListener(
        "click",
        () => {
          this.selected = !this.selected;
        },
        { capture: true },
      );
    }
  },
);

/** A native input firing value-changed, for date / time / text. */
class NativeInput extends Stub {
  static props = ["value", "label"];
  static type = "text";
  render() {
    this.shadowRoot.innerHTML = `<input type="${this.constructor.type}"
      style="${CONTROL_CSS}" />`;
    const input = this.shadowRoot.querySelector("input");
    const value = (this.value ?? "").toString();
    input.value = this.constructor.type === "time" ? value.slice(0, 5) : value;
    input.addEventListener("change", () => {
      this.value = input.value;
      fire(this, "value-changed", { value: input.value });
      this.dispatchEvent(new Event("change", { bubbles: true }));
    });
  }
}
customElements.define(
  "ha-date-input",
  class extends NativeInput {
    static type = "date";
  },
);
customElements.define(
  "ha-time-input",
  class extends NativeInput {
    static type = "time";
  },
);
customElements.define("ha-input", class extends NativeInput {});

/** ha-selector: native control per selector type. */
customElements.define(
  "ha-selector",
  class extends Stub {
    static props = [
      "hass",
      "selector",
      "value",
      "label",
      "placeholder",
      "disabled",
    ];
    render() {
      const selector = this.selector || {};
      const [type] = Object.keys(selector);
      const config = selector[type] || {};
      const root = this.shadowRoot;
      const emit = (value) => fire(this, "value-changed", { value });
      if (type === "boolean") {
        root.innerHTML = `<input type="checkbox" ${
          this.value ? "checked" : ""
        } />`;
        root.querySelector("input").onchange = (e) => emit(e.target.checked);
        return;
      }
      if (type === "number") {
        const unit = config.unit_of_measurement || "";
        const label = this.label
          ? `<div style="font-size:12px;color:var(--secondary-text-color);
              margin-bottom:2px">${this.label}</div>`
          : "";
        root.innerHTML = `${label}<span style="display:inline-flex;
          align-items:center;gap:4px"><input type="number"
          style="${CONTROL_CSS}width:80px" />${unit}</span>`;
        const input = root.querySelector("input");
        input.value = this.value ?? "";
        input.oninput = () =>
          emit(input.value === "" ? undefined : Number(input.value));
        return;
      }
      let options = [];
      if (type === "select") {
        options = (config.options || []).map((o) =>
          typeof o === "string" ? { value: o, label: o } : o,
        );
      } else if (type === "entity") {
        const ids =
          config.include_entities || Object.keys(this.hass?.states || {});
        options = ids.map((id) => ({
          value: id,
          label: this.hass?.states?.[id]?.attributes?.friendly_name || id,
        }));
        options.unshift({ value: "", label: this.placeholder || "" });
      }
      root.innerHTML = `<select style="${CONTROL_CSS}"></select>`;
      const select = root.querySelector("select");
      for (const o of options) {
        const opt = document.createElement("option");
        opt.value = o.value;
        opt.textContent = o.label;
        opt.selected = o.value === (this.value ?? "");
        select.appendChild(opt);
      }
      select.onchange = () => emit(select.value || undefined);
    }
  },
);
for (const tag of [
  "ha-selector-entity",
  "ha-selector-number",
  "ha-selector-select",
]) {
  customElements.define(tag, class extends HTMLElement {});
}

/** ha-area-picker: an "add" button opening a native select of areas. */
customElements.define(
  "ha-area-picker",
  class extends Stub {
    static props = ["hass", "value", "excludeAreas", "addButtonLabel"];
    render() {
      const label =
        this.addButtonLabel || this.getAttribute("add-button-label") || "Add";
      const exclude = this.excludeAreas || [];
      const areas = Object.values(this.hass?.areas || {}).filter(
        (a) => !exclude.includes(a.area_id),
      );
      this.shadowRoot.innerHTML = `<select style="${CONTROL_CSS}">
        <option value="">+ ${label}</option>
        ${areas
          .map((a) => `<option value="${a.area_id}">${a.name}</option>`)
          .join("")}</select>`;
      const select = this.shadowRoot.querySelector("select");
      select.onchange = () =>
        fire(this, "value-changed", { value: select.value || undefined });
    }
  },
);

/** Tabs: a bar of ha-tab-group-tab; a click fires wa-tab-show. */
customElements.define(
  "ha-tab-group",
  class extends Stub {
    connectedCallback() {
      super.connectedCallback();
      this.addEventListener("click", (e) => {
        const tab = e.target.closest?.("ha-tab-group-tab");
        if (tab && tab.parentElement === this) {
          fire(this, "wa-tab-show", { name: tab.getAttribute("panel") });
        }
      });
    }
    render() {
      this.shadowRoot.innerHTML = `<div style="display:flex;overflow-x:auto;
        border-bottom:1px solid var(--divider-color)">
        <slot name="nav"></slot><slot></slot></div>`;
    }
  },
);
customElements.define(
  "ha-tab-group-tab",
  class extends Stub {
    static props = ["active"];
    render() {
      const active = this.active;
      this.shadowRoot.innerHTML = `<div style="padding:12px 16px;
        cursor:pointer;font-size:14px;font-weight:500;white-space:nowrap;
        display:flex;align-items:center;
        color:${active ? "var(--primary-color)" : "var(--primary-text-color)"};
        border-bottom:2px solid ${
          active ? "var(--primary-color)" : "transparent"
        }"><slot></slot></div>`;
    }
  },
);
