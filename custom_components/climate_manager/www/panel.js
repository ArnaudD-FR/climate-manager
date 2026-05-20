/**
 * @license
 * Copyright 2019 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const at = globalThis, xt = at.ShadowRoot && (at.ShadyCSS === void 0 || at.ShadyCSS.nativeShadow) && "adoptedStyleSheets" in Document.prototype && "replace" in CSSStyleSheet.prototype, $t = Symbol(), Ut = /* @__PURE__ */ new WeakMap();
let Jt = class {
  constructor(t, e, o) {
    if (this._$cssResult$ = !0, o !== $t) throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");
    this.cssText = t, this.t = e;
  }
  get styleSheet() {
    let t = this.o;
    const e = this.t;
    if (xt && t === void 0) {
      const o = e !== void 0 && e.length === 1;
      o && (t = Ut.get(e)), t === void 0 && ((this.o = t = new CSSStyleSheet()).replaceSync(this.cssText), o && Ut.set(e, t));
    }
    return t;
  }
  toString() {
    return this.cssText;
  }
};
const se = (n) => new Jt(typeof n == "string" ? n : n + "", void 0, $t), z = (n, ...t) => {
  const e = n.length === 1 ? n[0] : t.reduce((o, s, r) => o + ((i) => {
    if (i._$cssResult$ === !0) return i.cssText;
    if (typeof i == "number") return i;
    throw Error("Value passed to 'css' function must be a 'css' function result: " + i + ". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.");
  })(s) + n[r + 1], n[0]);
  return new Jt(e, n, $t);
}, oe = (n, t) => {
  if (xt) n.adoptedStyleSheets = t.map((e) => e instanceof CSSStyleSheet ? e : e.styleSheet);
  else for (const e of t) {
    const o = document.createElement("style"), s = at.litNonce;
    s !== void 0 && o.setAttribute("nonce", s), o.textContent = e.cssText, n.appendChild(o);
  }
}, It = xt ? (n) => n : (n) => n instanceof CSSStyleSheet ? ((t) => {
  let e = "";
  for (const o of t.cssRules) e += o.cssText;
  return se(e);
})(n) : n;
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const { is: re, defineProperty: ie, getOwnPropertyDescriptor: ne, getOwnPropertyNames: ae, getOwnPropertySymbols: ce, getPrototypeOf: le } = Object, O = globalThis, jt = O.trustedTypes, de = jt ? jt.emptyScript : "", ht = O.reactiveElementPolyfillSupport, Z = (n, t) => n, ct = { toAttribute(n, t) {
  switch (t) {
    case Boolean:
      n = n ? de : null;
      break;
    case Object:
    case Array:
      n = n == null ? n : JSON.stringify(n);
  }
  return n;
}, fromAttribute(n, t) {
  let e = n;
  switch (t) {
    case Boolean:
      e = n !== null;
      break;
    case Number:
      e = n === null ? null : Number(n);
      break;
    case Object:
    case Array:
      try {
        e = JSON.parse(n);
      } catch {
        e = null;
      }
  }
  return e;
} }, wt = (n, t) => !re(n, t), Lt = { attribute: !0, type: String, converter: ct, reflect: !1, useDefault: !1, hasChanged: wt };
Symbol.metadata ?? (Symbol.metadata = Symbol("metadata")), O.litPropertyMetadata ?? (O.litPropertyMetadata = /* @__PURE__ */ new WeakMap());
let Y = class extends HTMLElement {
  static addInitializer(t) {
    this._$Ei(), (this.l ?? (this.l = [])).push(t);
  }
  static get observedAttributes() {
    return this.finalize(), this._$Eh && [...this._$Eh.keys()];
  }
  static createProperty(t, e = Lt) {
    if (e.state && (e.attribute = !1), this._$Ei(), this.prototype.hasOwnProperty(t) && ((e = Object.create(e)).wrapped = !0), this.elementProperties.set(t, e), !e.noAccessor) {
      const o = Symbol(), s = this.getPropertyDescriptor(t, o, e);
      s !== void 0 && ie(this.prototype, t, s);
    }
  }
  static getPropertyDescriptor(t, e, o) {
    const { get: s, set: r } = ne(this.prototype, t) ?? { get() {
      return this[e];
    }, set(i) {
      this[e] = i;
    } };
    return { get: s, set(i) {
      const a = s == null ? void 0 : s.call(this);
      r == null || r.call(this, i), this.requestUpdate(t, a, o);
    }, configurable: !0, enumerable: !0 };
  }
  static getPropertyOptions(t) {
    return this.elementProperties.get(t) ?? Lt;
  }
  static _$Ei() {
    if (this.hasOwnProperty(Z("elementProperties"))) return;
    const t = le(this);
    t.finalize(), t.l !== void 0 && (this.l = [...t.l]), this.elementProperties = new Map(t.elementProperties);
  }
  static finalize() {
    if (this.hasOwnProperty(Z("finalized"))) return;
    if (this.finalized = !0, this._$Ei(), this.hasOwnProperty(Z("properties"))) {
      const e = this.properties, o = [...ae(e), ...ce(e)];
      for (const s of o) this.createProperty(s, e[s]);
    }
    const t = this[Symbol.metadata];
    if (t !== null) {
      const e = litPropertyMetadata.get(t);
      if (e !== void 0) for (const [o, s] of e) this.elementProperties.set(o, s);
    }
    this._$Eh = /* @__PURE__ */ new Map();
    for (const [e, o] of this.elementProperties) {
      const s = this._$Eu(e, o);
      s !== void 0 && this._$Eh.set(s, e);
    }
    this.elementStyles = this.finalizeStyles(this.styles);
  }
  static finalizeStyles(t) {
    const e = [];
    if (Array.isArray(t)) {
      const o = new Set(t.flat(1 / 0).reverse());
      for (const s of o) e.unshift(It(s));
    } else t !== void 0 && e.push(It(t));
    return e;
  }
  static _$Eu(t, e) {
    const o = e.attribute;
    return o === !1 ? void 0 : typeof o == "string" ? o : typeof t == "string" ? t.toLowerCase() : void 0;
  }
  constructor() {
    super(), this._$Ep = void 0, this.isUpdatePending = !1, this.hasUpdated = !1, this._$Em = null, this._$Ev();
  }
  _$Ev() {
    var t;
    this._$ES = new Promise((e) => this.enableUpdating = e), this._$AL = /* @__PURE__ */ new Map(), this._$E_(), this.requestUpdate(), (t = this.constructor.l) == null || t.forEach((e) => e(this));
  }
  addController(t) {
    var e;
    (this._$EO ?? (this._$EO = /* @__PURE__ */ new Set())).add(t), this.renderRoot !== void 0 && this.isConnected && ((e = t.hostConnected) == null || e.call(t));
  }
  removeController(t) {
    var e;
    (e = this._$EO) == null || e.delete(t);
  }
  _$E_() {
    const t = /* @__PURE__ */ new Map(), e = this.constructor.elementProperties;
    for (const o of e.keys()) this.hasOwnProperty(o) && (t.set(o, this[o]), delete this[o]);
    t.size > 0 && (this._$Ep = t);
  }
  createRenderRoot() {
    const t = this.shadowRoot ?? this.attachShadow(this.constructor.shadowRootOptions);
    return oe(t, this.constructor.elementStyles), t;
  }
  connectedCallback() {
    var t;
    this.renderRoot ?? (this.renderRoot = this.createRenderRoot()), this.enableUpdating(!0), (t = this._$EO) == null || t.forEach((e) => {
      var o;
      return (o = e.hostConnected) == null ? void 0 : o.call(e);
    });
  }
  enableUpdating(t) {
  }
  disconnectedCallback() {
    var t;
    (t = this._$EO) == null || t.forEach((e) => {
      var o;
      return (o = e.hostDisconnected) == null ? void 0 : o.call(e);
    });
  }
  attributeChangedCallback(t, e, o) {
    this._$AK(t, o);
  }
  _$ET(t, e) {
    var r;
    const o = this.constructor.elementProperties.get(t), s = this.constructor._$Eu(t, o);
    if (s !== void 0 && o.reflect === !0) {
      const i = (((r = o.converter) == null ? void 0 : r.toAttribute) !== void 0 ? o.converter : ct).toAttribute(e, o.type);
      this._$Em = t, i == null ? this.removeAttribute(s) : this.setAttribute(s, i), this._$Em = null;
    }
  }
  _$AK(t, e) {
    var r, i;
    const o = this.constructor, s = o._$Eh.get(t);
    if (s !== void 0 && this._$Em !== s) {
      const a = o.getPropertyOptions(s), c = typeof a.converter == "function" ? { fromAttribute: a.converter } : ((r = a.converter) == null ? void 0 : r.fromAttribute) !== void 0 ? a.converter : ct;
      this._$Em = s;
      const l = c.fromAttribute(e, a.type);
      this[s] = l ?? ((i = this._$Ej) == null ? void 0 : i.get(s)) ?? l, this._$Em = null;
    }
  }
  requestUpdate(t, e, o, s = !1, r) {
    var i;
    if (t !== void 0) {
      const a = this.constructor;
      if (s === !1 && (r = this[t]), o ?? (o = a.getPropertyOptions(t)), !((o.hasChanged ?? wt)(r, e) || o.useDefault && o.reflect && r === ((i = this._$Ej) == null ? void 0 : i.get(t)) && !this.hasAttribute(a._$Eu(t, o)))) return;
      this.C(t, e, o);
    }
    this.isUpdatePending === !1 && (this._$ES = this._$EP());
  }
  C(t, e, { useDefault: o, reflect: s, wrapped: r }, i) {
    o && !(this._$Ej ?? (this._$Ej = /* @__PURE__ */ new Map())).has(t) && (this._$Ej.set(t, i ?? e ?? this[t]), r !== !0 || i !== void 0) || (this._$AL.has(t) || (this.hasUpdated || o || (e = void 0), this._$AL.set(t, e)), s === !0 && this._$Em !== t && (this._$Eq ?? (this._$Eq = /* @__PURE__ */ new Set())).add(t));
  }
  async _$EP() {
    this.isUpdatePending = !0;
    try {
      await this._$ES;
    } catch (e) {
      Promise.reject(e);
    }
    const t = this.scheduleUpdate();
    return t != null && await t, !this.isUpdatePending;
  }
  scheduleUpdate() {
    return this.performUpdate();
  }
  performUpdate() {
    var o;
    if (!this.isUpdatePending) return;
    if (!this.hasUpdated) {
      if (this.renderRoot ?? (this.renderRoot = this.createRenderRoot()), this._$Ep) {
        for (const [r, i] of this._$Ep) this[r] = i;
        this._$Ep = void 0;
      }
      const s = this.constructor.elementProperties;
      if (s.size > 0) for (const [r, i] of s) {
        const { wrapped: a } = i, c = this[r];
        a !== !0 || this._$AL.has(r) || c === void 0 || this.C(r, void 0, i, c);
      }
    }
    let t = !1;
    const e = this._$AL;
    try {
      t = this.shouldUpdate(e), t ? (this.willUpdate(e), (o = this._$EO) == null || o.forEach((s) => {
        var r;
        return (r = s.hostUpdate) == null ? void 0 : r.call(s);
      }), this.update(e)) : this._$EM();
    } catch (s) {
      throw t = !1, this._$EM(), s;
    }
    t && this._$AE(e);
  }
  willUpdate(t) {
  }
  _$AE(t) {
    var e;
    (e = this._$EO) == null || e.forEach((o) => {
      var s;
      return (s = o.hostUpdated) == null ? void 0 : s.call(o);
    }), this.hasUpdated || (this.hasUpdated = !0, this.firstUpdated(t)), this.updated(t);
  }
  _$EM() {
    this._$AL = /* @__PURE__ */ new Map(), this.isUpdatePending = !1;
  }
  get updateComplete() {
    return this.getUpdateComplete();
  }
  getUpdateComplete() {
    return this._$ES;
  }
  shouldUpdate(t) {
    return !0;
  }
  update(t) {
    this._$Eq && (this._$Eq = this._$Eq.forEach((e) => this._$ET(e, this[e]))), this._$EM();
  }
  updated(t) {
  }
  firstUpdated(t) {
  }
};
Y.elementStyles = [], Y.shadowRootOptions = { mode: "open" }, Y[Z("elementProperties")] = /* @__PURE__ */ new Map(), Y[Z("finalized")] = /* @__PURE__ */ new Map(), ht == null || ht({ ReactiveElement: Y }), (O.reactiveElementVersions ?? (O.reactiveElementVersions = [])).push("2.1.2");
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const K = globalThis, Bt = (n) => n, lt = K.trustedTypes, Ft = lt ? lt.createPolicy("lit-html", { createHTML: (n) => n }) : void 0, Zt = "$lit$", R = `lit$${Math.random().toFixed(9).slice(2)}$`, Kt = "?" + R, pe = `<${Kt}>`, j = document, Q = () => j.createComment(""), tt = (n) => n === null || typeof n != "object" && typeof n != "function", St = Array.isArray, he = (n) => St(n) || typeof (n == null ? void 0 : n[Symbol.iterator]) == "function", ut = `[ 	
\f\r]`, J = /<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g, Xt = /-->/g, Yt = />/g, H = RegExp(`>|${ut}(?:([^\\s"'>=/]+)(${ut}*=${ut}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`, "g"), qt = /'/g, Wt = /"/g, Qt = /^(?:script|style|textarea|title)$/i, ue = (n) => (t, ...e) => ({ _$litType$: n, strings: t, values: e }), d = ue(1), q = Symbol.for("lit-noChange"), v = Symbol.for("lit-nothing"), Vt = /* @__PURE__ */ new WeakMap(), U = j.createTreeWalker(j, 129);
function te(n, t) {
  if (!St(n) || !n.hasOwnProperty("raw")) throw Error("invalid template strings array");
  return Ft !== void 0 ? Ft.createHTML(t) : t;
}
const me = (n, t) => {
  const e = n.length - 1, o = [];
  let s, r = t === 2 ? "<svg>" : t === 3 ? "<math>" : "", i = J;
  for (let a = 0; a < e; a++) {
    const c = n[a];
    let l, h, p = -1, _ = 0;
    for (; _ < c.length && (i.lastIndex = _, h = i.exec(c), h !== null); ) _ = i.lastIndex, i === J ? h[1] === "!--" ? i = Xt : h[1] !== void 0 ? i = Yt : h[2] !== void 0 ? (Qt.test(h[2]) && (s = RegExp("</" + h[2], "g")), i = H) : h[3] !== void 0 && (i = H) : i === H ? h[0] === ">" ? (i = s ?? J, p = -1) : h[1] === void 0 ? p = -2 : (p = i.lastIndex - h[2].length, l = h[1], i = h[3] === void 0 ? H : h[3] === '"' ? Wt : qt) : i === Wt || i === qt ? i = H : i === Xt || i === Yt ? i = J : (i = H, s = void 0);
    const b = i === H && n[a + 1].startsWith("/>") ? " " : "";
    r += i === J ? c + pe : p >= 0 ? (o.push(l), c.slice(0, p) + Zt + c.slice(p) + R + b) : c + R + (p === -2 ? a : b);
  }
  return [te(n, r + (n[e] || "<?>") + (t === 2 ? "</svg>" : t === 3 ? "</math>" : "")), o];
};
class et {
  constructor({ strings: t, _$litType$: e }, o) {
    let s;
    this.parts = [];
    let r = 0, i = 0;
    const a = t.length - 1, c = this.parts, [l, h] = me(t, e);
    if (this.el = et.createElement(l, o), U.currentNode = this.el.content, e === 2 || e === 3) {
      const p = this.el.content.firstChild;
      p.replaceWith(...p.childNodes);
    }
    for (; (s = U.nextNode()) !== null && c.length < a; ) {
      if (s.nodeType === 1) {
        if (s.hasAttributes()) for (const p of s.getAttributeNames()) if (p.endsWith(Zt)) {
          const _ = h[i++], b = s.getAttribute(p).split(R), y = /([.?@])?(.*)/.exec(_);
          c.push({ type: 1, index: r, name: y[2], strings: b, ctor: y[1] === "." ? fe : y[1] === "?" ? _e : y[1] === "@" ? be : dt }), s.removeAttribute(p);
        } else p.startsWith(R) && (c.push({ type: 6, index: r }), s.removeAttribute(p));
        if (Qt.test(s.tagName)) {
          const p = s.textContent.split(R), _ = p.length - 1;
          if (_ > 0) {
            s.textContent = lt ? lt.emptyScript : "";
            for (let b = 0; b < _; b++) s.append(p[b], Q()), U.nextNode(), c.push({ type: 2, index: ++r });
            s.append(p[_], Q());
          }
        }
      } else if (s.nodeType === 8) if (s.data === Kt) c.push({ type: 2, index: r });
      else {
        let p = -1;
        for (; (p = s.data.indexOf(R, p + 1)) !== -1; ) c.push({ type: 7, index: r }), p += R.length - 1;
      }
      r++;
    }
  }
  static createElement(t, e) {
    const o = j.createElement("template");
    return o.innerHTML = t, o;
  }
}
function W(n, t, e = n, o) {
  var i, a;
  if (t === q) return t;
  let s = o !== void 0 ? (i = e._$Co) == null ? void 0 : i[o] : e._$Cl;
  const r = tt(t) ? void 0 : t._$litDirective$;
  return (s == null ? void 0 : s.constructor) !== r && ((a = s == null ? void 0 : s._$AO) == null || a.call(s, !1), r === void 0 ? s = void 0 : (s = new r(n), s._$AT(n, e, o)), o !== void 0 ? (e._$Co ?? (e._$Co = []))[o] = s : e._$Cl = s), s !== void 0 && (t = W(n, s._$AS(n, t.values), s, o)), t;
}
class ge {
  constructor(t, e) {
    this._$AV = [], this._$AN = void 0, this._$AD = t, this._$AM = e;
  }
  get parentNode() {
    return this._$AM.parentNode;
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  u(t) {
    const { el: { content: e }, parts: o } = this._$AD, s = ((t == null ? void 0 : t.creationScope) ?? j).importNode(e, !0);
    U.currentNode = s;
    let r = U.nextNode(), i = 0, a = 0, c = o[0];
    for (; c !== void 0; ) {
      if (i === c.index) {
        let l;
        c.type === 2 ? l = new st(r, r.nextSibling, this, t) : c.type === 1 ? l = new c.ctor(r, c.name, c.strings, this, t) : c.type === 6 && (l = new ve(r, this, t)), this._$AV.push(l), c = o[++a];
      }
      i !== (c == null ? void 0 : c.index) && (r = U.nextNode(), i++);
    }
    return U.currentNode = j, s;
  }
  p(t) {
    let e = 0;
    for (const o of this._$AV) o !== void 0 && (o.strings !== void 0 ? (o._$AI(t, o, e), e += o.strings.length - 2) : o._$AI(t[e])), e++;
  }
}
class st {
  get _$AU() {
    var t;
    return ((t = this._$AM) == null ? void 0 : t._$AU) ?? this._$Cv;
  }
  constructor(t, e, o, s) {
    this.type = 2, this._$AH = v, this._$AN = void 0, this._$AA = t, this._$AB = e, this._$AM = o, this.options = s, this._$Cv = (s == null ? void 0 : s.isConnected) ?? !0;
  }
  get parentNode() {
    let t = this._$AA.parentNode;
    const e = this._$AM;
    return e !== void 0 && (t == null ? void 0 : t.nodeType) === 11 && (t = e.parentNode), t;
  }
  get startNode() {
    return this._$AA;
  }
  get endNode() {
    return this._$AB;
  }
  _$AI(t, e = this) {
    t = W(this, t, e), tt(t) ? t === v || t == null || t === "" ? (this._$AH !== v && this._$AR(), this._$AH = v) : t !== this._$AH && t !== q && this._(t) : t._$litType$ !== void 0 ? this.$(t) : t.nodeType !== void 0 ? this.T(t) : he(t) ? this.k(t) : this._(t);
  }
  O(t) {
    return this._$AA.parentNode.insertBefore(t, this._$AB);
  }
  T(t) {
    this._$AH !== t && (this._$AR(), this._$AH = this.O(t));
  }
  _(t) {
    this._$AH !== v && tt(this._$AH) ? this._$AA.nextSibling.data = t : this.T(j.createTextNode(t)), this._$AH = t;
  }
  $(t) {
    var r;
    const { values: e, _$litType$: o } = t, s = typeof o == "number" ? this._$AC(t) : (o.el === void 0 && (o.el = et.createElement(te(o.h, o.h[0]), this.options)), o);
    if (((r = this._$AH) == null ? void 0 : r._$AD) === s) this._$AH.p(e);
    else {
      const i = new ge(s, this), a = i.u(this.options);
      i.p(e), this.T(a), this._$AH = i;
    }
  }
  _$AC(t) {
    let e = Vt.get(t.strings);
    return e === void 0 && Vt.set(t.strings, e = new et(t)), e;
  }
  k(t) {
    St(this._$AH) || (this._$AH = [], this._$AR());
    const e = this._$AH;
    let o, s = 0;
    for (const r of t) s === e.length ? e.push(o = new st(this.O(Q()), this.O(Q()), this, this.options)) : o = e[s], o._$AI(r), s++;
    s < e.length && (this._$AR(o && o._$AB.nextSibling, s), e.length = s);
  }
  _$AR(t = this._$AA.nextSibling, e) {
    var o;
    for ((o = this._$AP) == null ? void 0 : o.call(this, !1, !0, e); t !== this._$AB; ) {
      const s = Bt(t).nextSibling;
      Bt(t).remove(), t = s;
    }
  }
  setConnected(t) {
    var e;
    this._$AM === void 0 && (this._$Cv = t, (e = this._$AP) == null || e.call(this, t));
  }
}
class dt {
  get tagName() {
    return this.element.tagName;
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  constructor(t, e, o, s, r) {
    this.type = 1, this._$AH = v, this._$AN = void 0, this.element = t, this.name = e, this._$AM = s, this.options = r, o.length > 2 || o[0] !== "" || o[1] !== "" ? (this._$AH = Array(o.length - 1).fill(new String()), this.strings = o) : this._$AH = v;
  }
  _$AI(t, e = this, o, s) {
    const r = this.strings;
    let i = !1;
    if (r === void 0) t = W(this, t, e, 0), i = !tt(t) || t !== this._$AH && t !== q, i && (this._$AH = t);
    else {
      const a = t;
      let c, l;
      for (t = r[0], c = 0; c < r.length - 1; c++) l = W(this, a[o + c], e, c), l === q && (l = this._$AH[c]), i || (i = !tt(l) || l !== this._$AH[c]), l === v ? t = v : t !== v && (t += (l ?? "") + r[c + 1]), this._$AH[c] = l;
    }
    i && !s && this.j(t);
  }
  j(t) {
    t === v ? this.element.removeAttribute(this.name) : this.element.setAttribute(this.name, t ?? "");
  }
}
class fe extends dt {
  constructor() {
    super(...arguments), this.type = 3;
  }
  j(t) {
    this.element[this.name] = t === v ? void 0 : t;
  }
}
class _e extends dt {
  constructor() {
    super(...arguments), this.type = 4;
  }
  j(t) {
    this.element.toggleAttribute(this.name, !!t && t !== v);
  }
}
class be extends dt {
  constructor(t, e, o, s, r) {
    super(t, e, o, s, r), this.type = 5;
  }
  _$AI(t, e = this) {
    if ((t = W(this, t, e, 0) ?? v) === q) return;
    const o = this._$AH, s = t === v && o !== v || t.capture !== o.capture || t.once !== o.once || t.passive !== o.passive, r = t !== v && (o === v || s);
    s && this.element.removeEventListener(this.name, this, o), r && this.element.addEventListener(this.name, this, t), this._$AH = t;
  }
  handleEvent(t) {
    var e;
    typeof this._$AH == "function" ? this._$AH.call(((e = this.options) == null ? void 0 : e.host) ?? this.element, t) : this._$AH.handleEvent(t);
  }
}
class ve {
  constructor(t, e, o) {
    this.element = t, this.type = 6, this._$AN = void 0, this._$AM = e, this.options = o;
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  _$AI(t) {
    W(this, t);
  }
}
const mt = K.litHtmlPolyfillSupport;
mt == null || mt(et, st), (K.litHtmlVersions ?? (K.litHtmlVersions = [])).push("3.3.3");
const ye = (n, t, e) => {
  const o = (e == null ? void 0 : e.renderBefore) ?? t;
  let s = o._$litPart$;
  if (s === void 0) {
    const r = (e == null ? void 0 : e.renderBefore) ?? null;
    o._$litPart$ = s = new st(t.insertBefore(Q(), r), r, void 0, e ?? {});
  }
  return s._$AI(n), s;
};
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const I = globalThis;
class S extends Y {
  constructor() {
    super(...arguments), this.renderOptions = { host: this }, this._$Do = void 0;
  }
  createRenderRoot() {
    var e;
    const t = super.createRenderRoot();
    return (e = this.renderOptions).renderBefore ?? (e.renderBefore = t.firstChild), t;
  }
  update(t) {
    const e = this.render();
    this.hasUpdated || (this.renderOptions.isConnected = this.isConnected), super.update(t), this._$Do = ye(e, this.renderRoot, this.renderOptions);
  }
  connectedCallback() {
    var t;
    super.connectedCallback(), (t = this._$Do) == null || t.setConnected(!0);
  }
  disconnectedCallback() {
    var t;
    super.disconnectedCallback(), (t = this._$Do) == null || t.setConnected(!1);
  }
  render() {
    return q;
  }
}
var Gt;
S._$litElement$ = !0, S.finalized = !0, (Gt = I.litElementHydrateSupport) == null || Gt.call(I, { LitElement: S });
const gt = I.litElementPolyfillSupport;
gt == null || gt({ LitElement: S });
(I.litElementVersions ?? (I.litElementVersions = [])).push("4.2.2");
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const xe = { attribute: !0, type: String, converter: ct, reflect: !1, hasChanged: wt }, $e = (n = xe, t, e) => {
  const { kind: o, metadata: s } = e;
  let r = globalThis.litPropertyMetadata.get(s);
  if (r === void 0 && globalThis.litPropertyMetadata.set(s, r = /* @__PURE__ */ new Map()), o === "setter" && ((n = Object.create(n)).wrapped = !0), r.set(e.name, n), o === "accessor") {
    const { name: i } = e;
    return { set(a) {
      const c = t.get.call(this);
      t.set.call(this, a), this.requestUpdate(i, c, n, !0, a);
    }, init(a) {
      return a !== void 0 && this.C(i, void 0, n, a), a;
    } };
  }
  if (o === "setter") {
    const { name: i } = e;
    return function(a) {
      const c = this[i];
      t.call(this, a), this.requestUpdate(i, c, n, !0, a);
    };
  }
  throw Error("Unsupported decorator location: " + o);
};
function u(n) {
  return (t, e) => typeof e == "object" ? $e(n, t, e) : ((o, s, r) => {
    const i = s.hasOwnProperty(r);
    return s.constructor.createProperty(r, o), i ? Object.getOwnPropertyDescriptor(s, r) : void 0;
  })(n, t, e);
}
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
function x(n) {
  return u({ ...n, state: !0, attribute: !1 });
}
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const we = (n, t, e) => (e.configurable = !0, e.enumerable = !0, Reflect.decorate && typeof t != "object" && Object.defineProperty(n, t, e), e);
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
function Se(n, t) {
  return (e, o, s) => {
    const r = (i) => {
      var a;
      return ((a = i.renderRoot) == null ? void 0 : a.querySelector(n)) ?? null;
    };
    return we(e, o, { get() {
      return r(this);
    } });
  };
}
class it {
  constructor(t) {
    this.hass = t;
  }
  /** Return the full merged runtime config. */
  getConfig() {
    return this.hass.connection.sendMessagePromise({
      type: "climate_manager/get_config"
    });
  }
  /** Return the current coordinator status snapshot. */
  getStatus() {
    return this.hass.connection.sendMessagePromise({
      type: "climate_manager/get_status"
    });
  }
  /** Set the global heating mode. */
  setGlobalMode(t) {
    return this.hass.connection.sendMessagePromise({
      type: "climate_manager/set_global_mode",
      mode: t
    });
  }
  /** Update default temperatures for all four period modes. */
  setPeriodTemperatures(t) {
    return this.hass.connection.sendMessagePromise({
      type: "climate_manager/set_period_temperatures",
      temperatures: t
    });
  }
  /** Replace the global time program (all 7 day keys required). */
  setTimeProgram(t) {
    return this.hass.connection.sendMessagePromise({
      type: "climate_manager/set_time_program",
      program: t
    });
  }
  /** Sparse-merge a config delta into a specific room. */
  setRoomConfig(t, e) {
    return this.hass.connection.sendMessagePromise({
      type: "climate_manager/set_room_config",
      room_id: t,
      config: e
    });
  }
  /** Sparse-merge a config delta into a specific person. */
  setPersonConfig(t, e) {
    return this.hass.connection.sendMessagePromise({
      type: "climate_manager/set_person_config",
      person_id: t,
      config: e
    });
  }
  /**
   * Subscribe to coordinator status push events.
   * Returns Promise<unsubscribe fn> — store and call on disconnect.
   */
  subscribeStatus(t) {
    return this.hass.connection.subscribeMessage(t, {
      type: "climate_manager/subscribe_status"
    });
  }
}
var Ce = Object.defineProperty, Ct = (n, t, e, o) => {
  for (var s = void 0, r = n.length - 1, i; r >= 0; r--)
    (i = n[r]) && (s = i(t, e, s) || s);
  return s && Ce(t, e, s), s;
};
const Et = class Et extends S {
  constructor() {
    super(...arguments), this._visible = !1, this._message = "", this._isError = !1, this._dismissTimer = null;
  }
  /** Display the toast. Success auto-dismisses after 3s; error persists. */
  show(t, e) {
    this._dismissTimer !== null && (clearTimeout(this._dismissTimer), this._dismissTimer = null), this._message = t, this._isError = e, this._visible = !0, e || (this._dismissTimer = setTimeout(() => {
      this._visible = !1, this._dismissTimer = null;
    }, 3e3));
  }
  /** Programmatically dismiss the toast (e.g. after error recovery). */
  dismiss() {
    this._dismissTimer !== null && (clearTimeout(this._dismissTimer), this._dismissTimer = null), this._visible = !1;
  }
  render() {
    const t = this._isError ? "mdi:alert-circle" : "mdi:check-circle", e = this._isError ? "error" : "success";
    return d`
      <div
        class="toast ${this._visible ? "visible" : ""}"
        role="status"
        aria-live="polite"
        aria-atomic="true"
      >
        <ha-icon
          class="icon ${e}"
          icon="${t}"
        ></ha-icon>
        <span>${this._message}</span>
      </div>
    `;
  }
};
Et.styles = z`
    :host {
      position: fixed;
      bottom: 24px;
      left: 50%;
      transform: translateX(-50%);
      z-index: 9999;
      pointer-events: none;
      display: block;
    }

    .toast {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 12px 16px;
      border-radius: 4px;
      background: var(--card-background-color, #fff);
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
      font-size: 14px;
      font-family: inherit;
      color: var(--primary-text-color, #212121);
      opacity: 0;
      transition: opacity 0.2s ease;
    }

    .toast.visible {
      opacity: 1;
    }

    .icon {
      --icon-size: 20px;
      width: var(--icon-size);
      height: var(--icon-size);
      flex-shrink: 0;
    }

    .icon.success {
      color: var(--primary-color, #03a9f4);
    }

    .icon.error {
      color: var(--error-color, #db4437);
    }
  `;
let V = Et;
Ct([
  x()
], V.prototype, "_visible");
Ct([
  x()
], V.prototype, "_message");
Ct([
  x()
], V.prototype, "_isError");
customElements.define("climate-manager-toast", V);
const F = {
  frost_protection: "#1565C0",
  reduced: "#64B5F6",
  normal: "#F57C00",
  comfort: "#D32F2F"
}, nt = {
  present: "#388E3C",
  absent: "#9E9E9E"
}, ke = {
  frost_protection: "Frost protection",
  reduced: "Reduced",
  normal: "Normal",
  comfort: "Comfort",
  present: "Present",
  absent: "Absent"
};
var Pe = Object.defineProperty, A = (n, t, e, o) => {
  for (var s = void 0, r = n.length - 1, i; r >= 0; r--)
    (i = n[r]) && (s = i(t, e, s) || s);
  return s && Pe(t, e, s), s;
};
const Ee = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], Ae = ["frost_protection", "reduced", "normal", "comfort"], Me = ["present", "absent"], At = class At extends S {
  constructor() {
    super(...arguments), this.days = Array.from(
      { length: 7 },
      () => []
    ), this.mode = "schedule", this._clipboard = null, this._drag = null, this._dragTooltipMinutes = null, this._dragTooltipX = 0, this._dragTooltipY = 0, this._dragPreviewDays = null, this._justDragged = !1, this._popup = null;
  }
  // -----------------------------------------------------------------------
  // Helpers
  // -----------------------------------------------------------------------
  _snapToMinutes(t) {
    return Math.round(t / 15) * 15;
  }
  _pixelToMinutes(t, e) {
    return t / e * 1440;
  }
  _minutesToHHMM(t) {
    const e = Math.max(0, Math.min(1440, t)), o = Math.floor(e / 60), s = e % 60;
    return `${String(o).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  }
  _colorForPeriod(t) {
    const e = this.mode === "presence" ? t.state ?? "absent" : t.mode ?? "frost_protection";
    return this.mode === "presence" ? nt[e] ?? nt.absent : F[e] ?? F.frost_protection;
  }
  _labelForPeriod(t) {
    const e = this.mode === "presence" ? t.state ?? "absent" : t.mode ?? "frost_protection";
    return ke[e] ?? e;
  }
  /**
   * Convert a periods array to renderable segments with computed widths.
   * Always starts at 00:00 — prepends a synthesised period if needed.
   */
  _toSegments(t) {
    if (t.length === 0) return [];
    const e = [...t].sort(
      (a, c) => a.start.localeCompare(c.start)
    ), o = e[0], r = this._timeToMinutes(o.start) > 0 ? [{ start: "00:00", mode: o.mode, state: o.state }, ...e] : e, i = [];
    for (let a = 0; a < r.length; a++) {
      const c = this._timeToMinutes(r[a].start), l = a + 1 < r.length ? this._timeToMinutes(r[a + 1].start) : 1440;
      i.push({ period: r[a], startMin: c, endMin: l });
    }
    return i;
  }
  _timeToMinutes(t) {
    const [e, o] = t.split(":").map(Number);
    return (e ?? 0) * 60 + (o ?? 0);
  }
  /** Emit periods-changed for a specific day. */
  _emitChange(t, e) {
    this.dispatchEvent(
      new CustomEvent("periods-changed", {
        detail: { dayIndex: t, periods: e },
        bubbles: !0,
        composed: !0
      })
    );
  }
  // -----------------------------------------------------------------------
  // Popup helpers
  // -----------------------------------------------------------------------
  _modeOptions() {
    return this.mode === "presence" ? [
      { key: "present", label: "Present", color: nt.present },
      { key: "absent", label: "Absent", color: nt.absent }
    ] : [
      {
        key: "frost_protection",
        label: "Frost protection",
        color: F.frost_protection
      },
      { key: "reduced", label: "Reduced", color: F.reduced },
      { key: "normal", label: "Normal", color: F.normal },
      { key: "comfort", label: "Comfort", color: F.comfort }
    ];
  }
  _closePopup() {
    this._popup = null;
  }
  // -----------------------------------------------------------------------
  // Click on empty bar → split
  // -----------------------------------------------------------------------
  _onBarClick(t, e) {
    if (this._drag) return;
    const s = t.currentTarget.getBoundingClientRect(), r = this._pixelToMinutes(t.clientX - s.left, s.width), i = this._snapToMinutes(r);
    this._popup = {
      kind: "split",
      dayIndex: e,
      snappedMinutes: i,
      x: t.clientX,
      y: t.clientY
    }, t.stopPropagation();
  }
  _onSplitModeSelect(t) {
    if (!this._popup || this._popup.kind !== "split") return;
    const { dayIndex: e, snappedMinutes: o } = this._popup, s = [...this.days[e] ?? []], r = this.mode === "presence" ? { start: this._minutesToHHMM(o ?? 0), state: t } : { start: this._minutesToHHMM(o ?? 0), mode: t };
    s.push(r);
    const i = s.sort((c, l) => c.start.localeCompare(l.start)), a = i.filter(
      (c, l) => l === 0 || c.start !== i[l - 1].start
    );
    this._closePopup(), this._emitChange(e, a);
  }
  // -----------------------------------------------------------------------
  // Click on existing segment → edit/delete popup
  // -----------------------------------------------------------------------
  _onSegmentClick(t, e, o) {
    if (this._justDragged) {
      this._justDragged = !1, t.stopPropagation();
      return;
    }
    if (this._drag) {
      t.stopPropagation();
      return;
    }
    this._popup = {
      kind: "edit",
      dayIndex: e,
      segIndex: o,
      x: t.clientX,
      y: t.clientY
    }, t.stopPropagation();
  }
  _onEditModeSelect(t) {
    if (!this._popup || this._popup.kind !== "edit") return;
    const { dayIndex: e, segIndex: o } = this._popup, r = this._toSegments(this.days[e] ?? [])[o ?? 0];
    if (!r) return;
    const i = (this.days[e] ?? []).map((a) => a.start === r.period.start ? this.mode === "presence" ? { ...a, state: t } : { ...a, mode: t } : a);
    this._closePopup(), this._emitChange(e, i);
  }
  _onDeleteSegment() {
    if (!this._popup || this._popup.kind !== "edit") return;
    const { dayIndex: t, segIndex: e } = this._popup, s = this._toSegments(this.days[t] ?? [])[e ?? 0];
    if (!s) return;
    const r = this.days[t] ?? [];
    if (!r.some((c) => c.start === s.period.start)) return;
    let a = r.filter((c) => c.start !== s.period.start);
    a.length > 0 && a[0].start !== "00:00" && (a = [{ ...a[0], start: "00:00" }, ...a.slice(1)]), this._closePopup(), this._emitChange(t, a);
  }
  /**
   * Split the clicked period at its midpoint (snapped to 15 min).
   * The first half keeps the original type; the second half gets the next
   * type in the cycle:
   *   schedule: frost_protection → reduced → normal → comfort → frost_protection
   *   presence: present → absent → present
   *
   * If the period is too narrow to split (< 30 min, leaving no room for two
   * 15-min halves) the action is silently ignored.
   */
  _onSplitPeriod() {
    if (!this._popup || this._popup.kind !== "edit") return;
    const { dayIndex: t, segIndex: e } = this._popup, s = this._toSegments(this.days[t] ?? [])[e ?? 0];
    if (!s) return;
    const r = s.endMin - s.startMin;
    if (r < 30) return;
    const i = s.startMin + r / 2, a = Math.max(
      s.startMin + 15,
      Math.min(s.endMin - 15, this._snapToMinutes(i))
    ), c = this.mode === "presence" ? Me : Ae, l = this.mode === "presence" ? s.period.state ?? "absent" : s.period.mode ?? "frost_protection", h = c.indexOf(l), p = c[(h + 1) % c.length], _ = this.mode === "presence" ? { start: s.period.start, state: l } : { start: s.period.start, mode: l }, b = this.mode === "presence" ? { start: this._minutesToHHMM(a), state: p } : { start: this._minutesToHHMM(a), mode: p }, y = this.days[t] ?? [], g = y.some(
      (f) => f.start === s.period.start
    );
    let m;
    g ? m = y.flatMap(
      (f) => f.start === s.period.start ? [_, b] : [f]
    ) : m = [b, ...y], this._closePopup(), this._emitChange(t, m);
  }
  // -----------------------------------------------------------------------
  // Drag boundary (D-06)
  // -----------------------------------------------------------------------
  _onDragHandlePointerDown(t, e, o) {
    t.stopPropagation(), t.target.setPointerCapture(t.pointerId);
    const r = this._toSegments(this.days[e] ?? [])[o];
    r && (this._drag = {
      dayIndex: e,
      segIndex: o,
      startX: t.clientX,
      initialBoundaryMinutes: r.endMin
    }, this._dragTooltipMinutes = r.endMin, this._dragTooltipX = t.clientX, this._dragTooltipY = t.clientY);
  }
  _onPointerMove(t) {
    var p;
    if (!this._drag) return;
    const { dayIndex: e, segIndex: o } = this._drag, s = (p = this.shadowRoot) == null ? void 0 : p.querySelector(
      `.day-row:nth-child(${e + 2}) .bar-wrap`
    );
    if (!s) return;
    const r = s.getBoundingClientRect(), i = this._pixelToMinutes(t.clientX - r.left, r.width), a = this._snapToMinutes(i);
    this._dragTooltipMinutes = a, this._dragTooltipX = t.clientX, this._dragTooltipY = t.clientY;
    const c = this._toSegments(this.days[e] ?? []), l = c[o], h = c[o + 1];
    if (l && h) {
      const _ = l.startMin + 15, b = h.endMin - 15, y = Math.max(_, Math.min(b, a)), g = (this.days[e] ?? []).map((f) => f.start === h.period.start ? { ...f, start: this._minutesToHHMM(y) } : f), m = this.days.map(
        (f, $) => $ === e ? g : f
      );
      this._dragPreviewDays = m;
    }
  }
  _onPointerUp(t) {
    var r;
    if (!this._drag) return;
    const { dayIndex: e, segIndex: o } = this._drag, s = (r = this.shadowRoot) == null ? void 0 : r.querySelector(
      `.day-row:nth-child(${e + 2}) .bar-wrap`
    );
    if (s) {
      const i = s.getBoundingClientRect(), a = this._pixelToMinutes(
        t.clientX - i.left,
        i.width
      ), c = this._snapToMinutes(a), l = this._toSegments(this.days[e] ?? []), h = l[o], p = l[o + 1];
      if (h && p) {
        const _ = h.startMin + 15, b = p.endMin - 15, y = Math.max(
          _,
          Math.min(b, c)
        ), g = (this.days[e] ?? []).map((m) => m.start === p.period.start ? { ...m, start: this._minutesToHHMM(y) } : m);
        this._justDragged = !0, this._drag = null, this._dragTooltipMinutes = null, this._dragPreviewDays = null, this._emitChange(e, g);
        return;
      }
    }
    this._justDragged = !0, this._drag = null, this._dragTooltipMinutes = null, this._dragPreviewDays = null;
  }
  // -----------------------------------------------------------------------
  // Copy / Paste
  // -----------------------------------------------------------------------
  _onCopy(t) {
    this._clipboard = JSON.parse(
      JSON.stringify(this.days[t] ?? [])
    );
  }
  _onPaste(t) {
    if (!this._clipboard) return;
    const e = JSON.parse(JSON.stringify(this._clipboard));
    this._emitChange(t, e);
  }
  // -----------------------------------------------------------------------
  // Render
  // -----------------------------------------------------------------------
  render() {
    return d`
      <div
        class="week-grid"
        @pointermove=${this._onPointerMove}
        @pointerup=${this._onPointerUp}
      >
        <!-- Time axis above day rows — identical structure to bottom axis -->
        ${this._renderTimeAxis()}

        ${Ee.map(
      (t, e) => this._renderDayRow(t, e)
    )}

        <!-- Shared time axis below day rows -->
        ${this._renderTimeAxis()}
      </div>

      <!-- Drag tooltip -->
      ${this._drag !== null && this._dragTooltipMinutes !== null ? d`<div
            class="drag-tooltip"
            style="left:${this._dragTooltipX}px;top:${this._dragTooltipY}px"
            aria-live="polite"
          >
            ${this._minutesToHHMM(this._dragTooltipMinutes)}
          </div>` : ""}

      <!-- Popup overlay + popup -->
      ${this._popup ? d`
            <div
              class="popup-overlay"
              @click=${this._closePopup}
            ></div>
            <div
              class="popup"
              style="left:${this._popup.x}px;top:${this._popup.y}px"
            >
              ${this._renderPopup()}
            </div>
          ` : ""}
    `;
  }
  /**
   * Renders the shared time axis row — used for both top (above day rows)
   * and bottom (below day rows). Identical structure and CSS class so both
   * rulers are pixel-perfect matches of each other.
   *
   * Layout: 48px left pad (40px label + 8px gap) + flex bar area +
   * 80px right pad (button column) — mirrors the day row geometry exactly.
   */
  _renderTimeAxis() {
    return d`
      <div class="time-axis">
        <div class="time-axis-inner">
          ${["00:00", "06:00", "12:00", "18:00", "24:00"].map(
      (t) => d`<span class="axis-tick">${t}</span>`
    )}
        </div>
      </div>
    `;
  }
  _renderDayRow(t, e) {
    const s = (this._dragPreviewDays ?? this.days)[e] ?? [], r = this._toSegments(s), i = r.length === 0;
    return d`
      <div class="day-row">
        <div class="day-label">${t}</div>

        <div
          class="bar-wrap"
          @click=${(a) => {
      (a.target.classList.contains("bar-wrap") || a.target.classList.contains("bar-row-inner")) && this._onBarClick(a, e);
    }}
        >
          ${i ? d`<div class="empty-hint">
                Click the bar to add your first period.
              </div>` : d`<div class="bar-row-inner">
                ${r.map(
      (a, c) => this._renderSegment(a, e, c, r.length)
    )}
              </div>`}
        </div>

        <div class="day-actions">
          <ha-icon-button
            .label=${"Copy " + t + " schedule"}
            @click=${() => this._onCopy(e)}
          >
            <ha-icon icon="mdi:content-copy"></ha-icon>
          </ha-icon-button>
          <ha-icon-button
            class=${this._clipboard === null ? "paste-disabled" : ""}
            .label=${"Paste to " + t}
            .disabled=${this._clipboard === null}
            @click=${() => this._onPaste(e)}
          >
            <ha-icon icon="mdi:content-paste"></ha-icon>
          </ha-icon-button>
        </div>
      </div>
    `;
  }
  _renderSegment(t, e, o, s) {
    var l;
    const r = this._colorForPeriod(t.period), i = this._labelForPeriod(t.period), a = (t.endMin - t.startMin) / 1440 * 100, c = this.mode === "presence" ? t.period.state ?? "absent" : ((l = t.period.mode) == null ? void 0 : l.replace(/_/g, " ")) ?? "frost protection";
    return d`
      <div
        class="segment"
        style="width:${a}%;background:${r}"
        aria-label="${c}"
        @click=${(h) => this._onSegmentClick(h, e, o)}
      >
        ${a > 2.7 ? d`<span class="segment-label">${i}</span>` : ""}

        <!-- Drag handle on right border (not on last segment) -->
        ${o < s - 1 ? d`<div
              class="drag-handle"
              @pointerdown=${(h) => this._onDragHandlePointerDown(h, e, o)}
            ></div>` : ""}
      </div>
    `;
  }
  _renderPopup() {
    var t;
    if (!this._popup) return d``;
    if (this._popup.kind === "split") {
      const e = this._minutesToHHMM(this._popup.snappedMinutes ?? 0);
      return d`
        <div class="popup-title">Split at ${e}</div>
        <div class="mode-options">
          ${this._modeOptions().map(
        (o) => d`
              <button
                class="mode-option"
                @click=${() => this._onSplitModeSelect(o.key)}
              >
                <span
                  class="mode-swatch"
                  style="background:${o.color}"
                ></span>
                ${o.label}
              </button>
            `
      )}
        </div>
      `;
    }
    if (this._popup.kind === "edit") {
      const o = this._toSegments(
        this.days[this._popup.dayIndex] ?? []
      )[this._popup.segIndex ?? 0];
      if (!o) return d``;
      const s = `${this._minutesToHHMM(o.startMin)} – ${this._minutesToHHMM(o.endMin)}`, r = this.mode === "presence" ? o.period.state ?? "absent" : ((t = o.period.mode) == null ? void 0 : t.replace(/_/g, " ")) ?? "frost protection", a = o.endMin - o.startMin >= 30, c = (this.days[this._popup.dayIndex] ?? []).length > 1;
      return d`
        <div class="popup-title">${s} · ${r}</div>

        <div class="mode-options">
          <div
            style="font-size:11px;color:var(--secondary-text-color);margin-bottom:4px"
          >
            Change mode
          </div>
          ${this._modeOptions().map(
        (l) => d`
              <button
                class="mode-option"
                @click=${() => this._onEditModeSelect(l.key)}
              >
                <span
                  class="mode-swatch"
                  style="background:${l.color}"
                ></span>
                ${l.label}
              </button>
            `
      )}
        </div>

        <div class="popup-actions">
          <button
            class="popup-btn"
            ?disabled=${!a}
            style=${a ? "" : "opacity:0.4;cursor:default"}
            @click=${this._onSplitPeriod}
          >
            Split period
          </button>
          <button
            class="popup-btn danger"
            ?disabled=${!c}
            style=${c ? "" : "opacity:0.4;cursor:default"}
            @click=${this._onDeleteSegment}
          >
            Delete period
          </button>
        </div>
      `;
    }
    return d``;
  }
};
At.styles = z`
    :host {
      display: block;
      user-select: none;
    }

    .week-grid {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .day-row {
      display: flex;
      align-items: center;
      height: 44px;
    }

    .day-label {
      width: 40px;
      flex-shrink: 0;
      text-align: right;
      font-size: 12px;
      font-weight: 400;
      color: var(--secondary-text-color, #757575);
      padding-right: 8px;
      line-height: 1;
    }

    .bar-wrap {
      flex: 1;
      height: 40px;
      position: relative;
      cursor: pointer;
      overflow: visible;
    }

    .bar-row-inner {
      display: flex;
      width: 100%;
      height: 100%;
      position: relative;
    }

    .segment {
      height: 100%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 11px;
      font-weight: 600;
      color: rgba(255, 255, 255, 0.9);
      overflow: hidden;
      position: relative;
      cursor: pointer;
      box-sizing: border-box;
    }

    .segment-label {
      pointer-events: none;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      max-width: 100%;
      padding: 0 4px;
      box-sizing: border-box;
    }

    .drag-handle {
      position: absolute;
      right: -3px;
      top: 0;
      width: 6px;
      height: 100%;
      cursor: ew-resize;
      z-index: 2;
    }

    .empty-hint {
      width: 100%;
      height: 100%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 12px;
      color: var(--secondary-text-color, #757575);
      background: var(--divider-color, #e0e0e0);
      border-radius: 2px;
    }

    .day-actions {
      display: flex;
      align-items: center;
      flex-shrink: 0;
      margin-left: 4px;
    }

    ha-icon-button.paste-disabled {
      opacity: 0.4;
    }

    /* ---- Shared time axis (above and below day rows) ---------------------- */
    .time-axis {
      display: flex;
      align-items: center;
      margin-top: 2px;
      padding-left: 48px; /* 40px label + 8px padding */
      padding-right: 80px; /* approximate button width */
    }

    .time-axis-inner {
      flex: 1;
      display: flex;
      justify-content: space-between;
    }

    .axis-tick {
      font-size: 11px;
      color: var(--secondary-text-color, #757575);
    }

    /* Drag tooltip */
    .drag-tooltip {
      position: fixed;
      background: rgba(0, 0, 0, 0.75);
      color: #fff;
      font-size: 12px;
      border-radius: 3px;
      padding: 2px 6px;
      pointer-events: none;
      z-index: 9998;
      transform: translate(-50%, -130%);
    }

    /* Mode popup */
    .popup-overlay {
      position: fixed;
      inset: 0;
      z-index: 9990;
    }

    .popup {
      position: fixed;
      background: var(--card-background-color, #fff);
      border-radius: 4px;
      box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25);
      padding: 12px;
      z-index: 9991;
      min-width: 160px;
    }

    .popup-title {
      font-size: 13px;
      font-weight: 600;
      margin-bottom: 8px;
      color: var(--primary-text-color);
    }

    .mode-options {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .mode-option {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 6px 8px;
      border-radius: 3px;
      cursor: pointer;
      font-size: 13px;
      color: var(--primary-text-color);
      border: none;
      background: transparent;
      width: 100%;
      text-align: left;
    }

    .mode-option:hover {
      background: var(--secondary-background-color, #f5f5f5);
    }

    .mode-swatch {
      width: 14px;
      height: 14px;
      border-radius: 2px;
      flex-shrink: 0;
    }

    .popup-actions {
      display: flex;
      flex-direction: column;
      gap: 4px;
      margin-top: 8px;
      padding-top: 8px;
      border-top: 1px solid var(--divider-color, #e0e0e0);
    }

    .popup-btn {
      padding: 6px 8px;
      border-radius: 3px;
      cursor: pointer;
      font-size: 13px;
      border: none;
      background: transparent;
      width: 100%;
      text-align: left;
      color: var(--primary-text-color);
    }

    .popup-btn:hover {
      background: var(--secondary-background-color, #f5f5f5);
    }

    .popup-btn.danger {
      color: var(--error-color, #db4437);
    }
  `;
let C = At;
A([
  u({ type: Array })
], C.prototype, "days");
A([
  u({ type: String })
], C.prototype, "mode");
A([
  x()
], C.prototype, "_clipboard");
A([
  x()
], C.prototype, "_drag");
A([
  x()
], C.prototype, "_dragTooltipMinutes");
A([
  x()
], C.prototype, "_dragTooltipX");
A([
  x()
], C.prototype, "_dragTooltipY");
A([
  x()
], C.prototype, "_dragPreviewDays");
A([
  x()
], C.prototype, "_popup");
customElements.define("climate-manager-time-bar", C);
var Te = Object.defineProperty, pt = (n, t, e, o) => {
  for (var s = void 0, r = n.length - 1, i; r >= 0; r--)
    (i = n[r]) && (s = i(t, e, s) || s);
  return s && Te(t, e, s), s;
};
const ee = [
  "mon",
  "tue",
  "wed",
  "thu",
  "fri",
  "sat",
  "sun"
];
function kt(n) {
  return ee.map((t) => n != null && n[t] ? [...n[t]] : []);
}
function Pt(n) {
  return ee[n] ?? "mon";
}
const bt = "off", vt = "time_program", yt = "time_program_presences", Re = {
  [bt]: "Off",
  [vt]: "Time program",
  [yt]: "Time program & presences"
}, Mt = class Mt extends S {
  constructor() {
    super(...arguments), this.status = null;
  }
  // -----------------------------------------------------------------------
  // Save handlers
  // -----------------------------------------------------------------------
  async _onModeChange(t) {
    const e = t.target.value;
    if (!(!e || e === this.config.global_mode))
      try {
        await this.ws.setGlobalMode(e), this.panel.patchConfig({ global_mode: e }), this.panel.showToast("Saved", !1);
      } catch {
        this.panel.showToast("Save failed", !0);
      }
  }
  async _onTemperatureChange(t) {
    const e = t.target, o = e.dataset.key, s = parseFloat(e.value);
    if (isNaN(s)) return;
    const r = this.config.period_temperatures, i = {
      frost_protection: r.frost_protection ?? 7,
      reduced: r.reduced ?? 18,
      normal: r.normal ?? 20,
      comfort: r.comfort ?? 22,
      [o]: s
    };
    try {
      await this.ws.setPeriodTemperatures(i), await this.panel.reloadConfig(), this.panel.showToast("Saved", !1);
    } catch {
      this.panel.showToast("Save failed — retrying...", !0);
    }
  }
  async _onPeriodsChanged(t) {
    const { dayIndex: e, periods: o } = t.detail, s = { ...this.config.global_time_program }, r = Pt(e);
    s[r] = o, this.panel.patchConfig({ global_time_program: s });
    try {
      await this.ws.setTimeProgram(s), await this.panel.reloadConfig(), this.panel.showToast("Saved", !1);
    } catch {
      this.panel.showToast("Save failed — retrying...", !0);
    }
    t.stopPropagation();
  }
  async _onResetToDefault() {
    const t = [
      { start: "00:00", mode: "reduced" },
      { start: "06:00", mode: "normal" },
      { start: "22:00", mode: "reduced" }
    ], o = Object.fromEntries(["mon", "tue", "wed", "thu", "fri", "sat", "sun"].map((i) => [i, [...t]])), s = { frost_protection: 7, reduced: 18, normal: 20, comfort: 22 }, r = "time_program";
    this.panel.patchConfig({ global_mode: r, period_temperatures: s, global_time_program: o });
    try {
      await this.ws.setGlobalMode(r), await this.ws.setPeriodTemperatures(s), await this.ws.setTimeProgram(o), await this.panel.reloadConfig(), this.panel.showToast("Reset to default", !1);
    } catch {
      this.panel.showToast("Reset failed", !0);
    }
  }
  // -----------------------------------------------------------------------
  // Render helpers
  // -----------------------------------------------------------------------
  _renderStatusCard() {
    var r;
    const t = this.status, e = Re[(t == null ? void 0 : t.global_mode) ?? this.config.global_mode] ?? (t == null ? void 0 : t.global_mode) ?? this.config.global_mode;
    let o = "No active period";
    t != null && t.active_period && (o = t.active_period);
    let s = d`<span class="status-value">No one home</span>`;
    return (r = t == null ? void 0 : t.present_persons) != null && r.length && (s = d`
        <span class="status-value">
          ${t.present_persons.map(
      (i, a) => {
        var c;
        return d`
              <span class="person-dot"></span>${i}${a < (((c = t == null ? void 0 : t.present_persons) == null ? void 0 : c.length) ?? 1) - 1 ? ", " : ""}
            `;
      }
    )}
        </span>
      `), d`
      <ha-card>
        <div class="card-header">Current Status</div>
        <div class="card-content">
          <div class="status-row">
            <span class="status-label">Mode:</span>
            <span class="status-value">${e}</span>
          </div>
          <div class="status-row">
            <span class="status-label">Active period:</span>
            <span class="status-value">${o}</span>
          </div>
          <div class="status-row">
            <span class="status-label">Present persons:</span>
            ${s}
          </div>
        </div>
      </ha-card>
    `;
  }
  _renderConfigCard() {
    const t = this.config.period_temperatures, e = kt(this.config.global_time_program);
    return d`
      <ha-card>
        <div class="card-header">Configuration</div>
        <div class="card-content">

          <div class="select-wrapper">
            <label class="select-label">Global mode</label>
            <select class="mode-select" .value=${this.config.global_mode} @change=${this._onModeChange}>
              <option value=${bt} ?selected=${this.config.global_mode === bt}>Off</option>
              <option value=${vt} ?selected=${this.config.global_mode === vt}>Time program</option>
              <option value=${yt} ?selected=${this.config.global_mode === yt}>Time program &amp; presences</option>
            </select>
          </div>

          <!-- Default temperatures -->
          <div class="section-divider">Default temperatures</div>
          <div class="temp-fields">
            <div class="temp-field">
              <label class="temp-label">Frost protection</label>
              <div class="temp-input-row">
                <input class="temp-input" type="number" step="0.5" min="5" max="30"
                  data-key="frost_protection"
                  .value=${String(t.frost_protection ?? 7)}
                  @change=${this._onTemperatureChange}
                />
                <span class="temp-suffix">°C</span>
              </div>
            </div>
            <div class="temp-field">
              <label class="temp-label">Reduced</label>
              <div class="temp-input-row">
                <input class="temp-input" type="number" step="0.5" min="5" max="30"
                  data-key="reduced"
                  .value=${String(t.reduced ?? 18)}
                  @change=${this._onTemperatureChange}
                />
                <span class="temp-suffix">°C</span>
              </div>
            </div>
            <div class="temp-field">
              <label class="temp-label">Normal</label>
              <div class="temp-input-row">
                <input class="temp-input" type="number" step="0.5" min="5" max="30"
                  data-key="normal"
                  .value=${String(t.normal ?? 20)}
                  @change=${this._onTemperatureChange}
                />
                <span class="temp-suffix">°C</span>
              </div>
            </div>
            <div class="temp-field">
              <label class="temp-label">Comfort</label>
              <div class="temp-input-row">
                <input class="temp-input" type="number" step="0.5" min="5" max="30"
                  data-key="comfort"
                  .value=${String(t.comfort ?? 22)}
                  @change=${this._onTemperatureChange}
                />
                <span class="temp-suffix">°C</span>
              </div>
            </div>
          </div>

          <!-- Global time program editor -->
          <div class="section-divider">Global time program</div>
          <div class="time-program-section">
            <climate-manager-time-bar
              mode="schedule"
              .days=${e}
              @periods-changed=${this._onPeriodsChanged}
            ></climate-manager-time-bar>
          </div>
          <button class="reset-btn" @click=${this._onResetToDefault}>
            Reset to default
          </button>
        </div>
      </ha-card>
    `;
  }
  render() {
    return d`
      ${this._renderStatusCard()}
      ${this._renderConfigCard()}
    `;
  }
};
Mt.styles = z`
    :host {
      display: block;
    }

    ha-card {
      margin-bottom: 16px;
    }

    .card-header {
      padding: 16px 16px 0;
      font-size: 16px;
      font-weight: 600;
      line-height: 1.2;
      color: var(--primary-text-color);
    }

    .card-content {
      padding: 16px;
    }

    /* ---- Status card ---- */
    .status-row {
      display: flex;
      align-items: baseline;
      gap: 8px;
      margin-bottom: 8px;
      font-size: 14px;
      color: var(--primary-text-color);
    }

    .status-label {
      font-weight: 600;
      flex-shrink: 0;
    }

    .status-value {
      color: var(--secondary-text-color);
    }

    .person-dot {
      display: inline-block;
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: #388E3C;
      margin-right: 4px;
      vertical-align: middle;
    }

    /* ---- Config card ---- */
    .section-divider {
      margin: 16px 0 8px;
      font-size: 12px;
      font-weight: 600;
      letter-spacing: 0.5px;
      text-transform: uppercase;
      color: var(--secondary-text-color);
    }

    .temp-fields {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
      margin-bottom: 16px;
    }

    .time-program-section {
      margin-top: 16px;
    }

    .reset-btn {
      margin-top: 12px;
      padding: 8px 16px;
      font-size: 14px;
      font-family: inherit;
      color: var(--primary-color);
      background: none;
      border: 1px solid var(--primary-color);
      border-radius: 4px;
      cursor: pointer;
    }

    .reset-btn:hover {
      background: var(--primary-color);
      color: var(--text-primary-color, #fff);
    }

    .select-wrapper {
      margin-bottom: 16px;
    }

    .select-label {
      display: block;
      font-size: 12px;
      color: var(--secondary-text-color);
      margin-bottom: 4px;
    }

    .mode-select {
      width: 100%;
      padding: 10px 12px;
      font-size: 16px;
      font-family: inherit;
      color: var(--primary-text-color);
      background-color: var(--card-background-color, var(--secondary-background-color));
      border: 1px solid var(--divider-color);
      border-radius: 4px;
      outline: none;
      cursor: pointer;
    }

    .mode-select:focus {
      border-color: var(--primary-color);
      border-width: 2px;
    }

    .temp-field {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .temp-label {
      font-size: 12px;
      color: var(--secondary-text-color);
    }

    .temp-input-row {
      display: flex;
      align-items: center;
      gap: 4px;
    }

    .temp-input {
      flex: 1;
      min-width: 0;
      padding: 10px 12px;
      font-size: 16px;
      font-family: inherit;
      color: var(--primary-text-color);
      background-color: var(--card-background-color, var(--secondary-background-color));
      border: 1px solid var(--divider-color);
      border-radius: 4px;
      outline: none;
    }

    .temp-input:focus {
      border-color: var(--primary-color);
      border-width: 2px;
    }

    .temp-suffix {
      font-size: 14px;
      color: var(--secondary-text-color);
      flex-shrink: 0;
    }
  `;
let L = Mt;
pt([
  u({ attribute: !1 })
], L.prototype, "config");
pt([
  u({ attribute: !1 })
], L.prototype, "status");
pt([
  u({ attribute: !1 })
], L.prototype, "ws");
pt([
  u({ attribute: !1 })
], L.prototype, "panel");
customElements.define("climate-manager-global-settings-tab", L);
var Oe = Object.defineProperty, M = (n, t, e, o) => {
  for (var s = void 0, r = n.length - 1, i; r >= 0; r--)
    (i = n[r]) && (s = i(t, e, s) || s);
  return s && Oe(t, e, s), s;
};
const Tt = class Tt extends S {
  constructor() {
    super(...arguments), this.roomStatus = null, this._expanded = !1;
  }
  connectedCallback() {
    var t;
    super.connectedCallback(), this._expanded = !!((t = this.config) != null && t.time_program);
  }
  // -----------------------------------------------------------------------
  // Save handlers
  // -----------------------------------------------------------------------
  async _onOverrideToggle(t) {
    var s;
    const e = t.target;
    let o;
    if (e.checked) {
      const r = (s = this.panelConfig) == null ? void 0 : s.global_time_program;
      o = r ? { ...r } : { mon: [], tue: [], wed: [], thu: [], fri: [], sat: [], sun: [] };
    } else
      o = null;
    try {
      await this.ws.setRoomConfig(this.roomId, { time_program: o ?? void 0 }), this.panel.showToast("Saved", !1);
    } catch {
      this.panel.showToast("Save failed — retrying...", !0);
    }
  }
  async _onPeriodsChanged(t) {
    const { dayIndex: e, periods: o } = t.detail, r = { ...this.config.time_program ?? {
      mon: [],
      tue: [],
      wed: [],
      thu: [],
      fri: [],
      sat: [],
      sun: []
    } }, i = Pt(e);
    r[i] = o;
    try {
      await this.ws.setRoomConfig(this.roomId, { time_program: r }), this.panel.showToast("Saved", !1);
    } catch {
      this.panel.showToast("Save failed — retrying...", !0);
    }
    t.stopPropagation();
  }
  // -----------------------------------------------------------------------
  // Render helpers
  // -----------------------------------------------------------------------
  _renderStatusRow() {
    const t = this.roomStatus;
    return d`
      <div class="status-row">
        ${(t == null ? void 0 : t.temperature) != null ? d`<span class="status-item">
              <ha-icon icon="mdi:thermometer"></ha-icon>
              ${t.temperature}°C
            </span>` : ""}
        ${(t == null ? void 0 : t.humidity) != null ? d`<span class="status-item">
              <ha-icon icon="mdi:water-percent"></ha-icon>
              ${t.humidity}%
            </span>` : ""}
        ${t != null && t.active_period ? d`<span class="status-item">
              <ha-icon icon="mdi:clock-outline"></ha-icon>
              ${t.active_period}
            </span>` : ""}
      </div>
    `;
  }
  _openMoreInfo(t) {
    this.dispatchEvent(new CustomEvent("hass-more-info", {
      bubbles: !0,
      composed: !0,
      detail: { entityId: t }
    }));
  }
  _renderTrvSection() {
    var e;
    const t = ((e = this.roomStatus) == null ? void 0 : e.entity_ids) ?? [];
    return t.length === 0 ? d`
        <div class="no-trv-badge">
          <ha-icon icon="mdi:alert"></ha-icon>
          No climate entities
        </div>
      ` : d`
      <div class="trv-section">
        <div class="section-label">Climate entities</div>
        ${t.map((o) => {
      var r, i, a;
      const s = ((a = (i = (r = this.hass) == null ? void 0 : r.states[o]) == null ? void 0 : i.attributes) == null ? void 0 : a.friendly_name) ?? o;
      return d`
            <span class="trv-chip" @click=${() => this._openMoreInfo(o)}>
              <ha-icon icon="mdi:radiator"></ha-icon>
              ${s}
            </span>
          `;
    })}
      </div>
    `;
  }
  render() {
    var s;
    const t = !!((s = this.config) != null && s.time_program), e = t ? "custom" : "global", o = t ? "Custom program" : "Global program";
    return d`
      <ha-card>
        <div class="card-header-row" @click=${() => {
      this._expanded = !this._expanded;
    }}>
          <div class="card-header-left">
            <span class="room-name">${this.roomName}</span>
            <span class="program-badge ${e}">${o}</span>
          </div>
          <ha-icon
            class="expand-icon ${this._expanded ? "expanded" : ""}"
            icon="mdi:chevron-down"
          ></ha-icon>
        </div>

        ${this._expanded ? d`
            <div class="card-content">
              ${this._renderStatusRow()}
              ${this._renderTrvSection()}

              <!-- Override toggle -->
              <div class="override-row">
                <span class="override-label">Override global time program</span>
                <ha-switch
                  .checked=${t}
                  @change=${this._onOverrideToggle}
                ></ha-switch>
              </div>

              <!-- Inline time-bar (only when override enabled) -->
              ${t ? d`
                  <div class="time-bar-section">
                    <climate-manager-time-bar
                      mode="schedule"
                      .days=${kt(this.config.time_program)}
                      @periods-changed=${this._onPeriodsChanged}
                    ></climate-manager-time-bar>
                  </div>
                ` : ""}
            </div>
          ` : ""}
      </ha-card>
    `;
  }
};
Tt.styles = z`
    :host {
      display: block;
    }

    ha-card {
      margin-bottom: 12px;
    }

    .card-header-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 12px 16px;
      cursor: pointer;
    }

    .card-header-left {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .room-name {
      font-size: 16px;
      font-weight: 600;
      color: var(--primary-text-color);
    }

    .program-badge {
      display: inline-flex;
      align-items: center;
      padding: 2px 8px;
      border-radius: 12px;
      font-size: 12px;
      font-weight: 400;
    }

    .program-badge.custom {
      background: var(--primary-color, #03a9f4);
      color: var(--text-primary-color, #fff);
    }

    .program-badge.global {
      background: var(--secondary-background-color, #f5f5f5);
      color: var(--secondary-text-color, #757575);
    }

    .card-content {
      padding: 0 16px 16px;
      border-top: 1px solid var(--divider-color, #e0e0e0);
    }

    /* Live status row */
    .status-row {
      display: flex;
      gap: 16px;
      padding: 12px 0 8px;
      font-size: 14px;
      color: var(--secondary-text-color);
      flex-wrap: wrap;
    }

    .status-item {
      display: flex;
      align-items: center;
      gap: 4px;
    }

    .status-item ha-icon {
      width: 18px;
      height: 18px;
      --mdc-icon-size: 18px;
      color: var(--secondary-text-color);
    }

    /* No TRV badge */
    .no-trv-badge {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      padding: 4px 8px;
      border-radius: 4px;
      background: rgba(255, 152, 0, 0.12);
      color: #e65100;
      font-size: 12px;
      margin-bottom: 12px;
    }

    /* TRV entity chips */
    .trv-section {
      margin-bottom: 12px;
    }

    .section-label {
      font-size: 12px;
      font-weight: 600;
      letter-spacing: 0.5px;
      text-transform: uppercase;
      color: var(--secondary-text-color);
      margin-bottom: 8px;
    }

    .trv-chip {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 4px 10px;
      margin: 0 4px 6px 0;
      border-radius: 16px;
      background: var(--secondary-background-color, #f5f5f5);
      border: 1px solid var(--divider-color, #e0e0e0);
      font-size: 13px;
      color: var(--primary-text-color);
      cursor: pointer;
      transition: background 0.15s;
    }

    .trv-chip:hover {
      background: var(--primary-color);
      color: var(--text-primary-color, #fff);
      border-color: var(--primary-color);
    }

    .trv-chip ha-icon {
      --mdc-icon-size: 16px;
      width: 16px;
      height: 16px;
    }

    /* Override toggle row */
    .override-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 8px 0;
      margin-bottom: 8px;
    }

    .override-label {
      font-size: 14px;
      color: var(--primary-text-color);
    }

    /* Inline time bar */
    .time-bar-section {
      margin-top: 12px;
    }

    .expand-icon {
      color: var(--secondary-text-color);
      transition: transform 0.2s;
    }

    .expand-icon.expanded {
      transform: rotate(180deg);
    }
  `;
let k = Tt;
M([
  u({ type: String })
], k.prototype, "roomId");
M([
  u({ type: String })
], k.prototype, "roomName");
M([
  u({ attribute: !1 })
], k.prototype, "config");
M([
  u({ attribute: !1 })
], k.prototype, "roomStatus");
M([
  u({ attribute: !1 })
], k.prototype, "panelConfig");
M([
  u({ attribute: !1 })
], k.prototype, "ws");
M([
  u({ attribute: !1 })
], k.prototype, "panel");
M([
  u({ attribute: !1 })
], k.prototype, "hass");
M([
  x()
], k.prototype, "_expanded");
customElements.define("climate-manager-room-card", k);
var Ne = Object.defineProperty, ot = (n, t, e, o) => {
  for (var s = void 0, r = n.length - 1, i; r >= 0; r--)
    (i = n[r]) && (s = i(t, e, s) || s);
  return s && Ne(t, e, s), s;
};
const Rt = class Rt extends S {
  constructor() {
    super(...arguments), this.status = null;
  }
  _getRoomStatus(t) {
    var e, o;
    return ((o = (e = this.status) == null ? void 0 : e.rooms_status) == null ? void 0 : o.find((s) => s.area_id === t)) ?? null;
  }
  render() {
    var h, p, _, b, y;
    const t = ((h = this.config) == null ? void 0 : h.rooms) ?? {}, e = ((p = this.status) == null ? void 0 : p.rooms_status) ?? [], o = /* @__PURE__ */ new Set([
      ...Object.keys(t),
      ...e.map((g) => g.area_id)
    ]);
    if (o.size === 0)
      return d`
        <div class="empty-state">
          No rooms discovered. Create areas in Home Assistant and assign climate entities.
        </div>
      `;
    const s = (g) => {
      var m, f, $;
      return (($ = (f = (m = this.status) == null ? void 0 : m.rooms_status) == null ? void 0 : f.find((w) => w.area_id === g)) == null ? void 0 : $.name) ?? g.replace(/_/g, " ").replace(/\b\w/g, (w) => w.toUpperCase());
    }, r = /* @__PURE__ */ new Map();
    for (const g of o) {
      const m = ((y = (b = (_ = this.hass) == null ? void 0 : _.areas) == null ? void 0 : b[g]) == null ? void 0 : y.floor_id) ?? null;
      r.has(m) || r.set(m, []), r.get(m).push(g);
    }
    for (const g of r.values())
      g.sort((m, f) => s(m).localeCompare(s(f)));
    const i = [...r.keys()].filter((g) => g !== null).sort(
      (g, m) => {
        var f, $, w, G, zt, Ht;
        return (((w = ($ = (f = this.hass) == null ? void 0 : f.floors) == null ? void 0 : $[m]) == null ? void 0 : w.level) ?? 0) - (((Ht = (zt = (G = this.hass) == null ? void 0 : G.floors) == null ? void 0 : zt[g]) == null ? void 0 : Ht.level) ?? 0);
      }
    ), a = r.get(null) ?? [], c = (g) => {
      const m = t[g] ?? {}, f = this._getRoomStatus(g), $ = s(g);
      return d`
        <climate-manager-room-card
          .roomId=${g}
          .roomName=${$}
          .config=${m}
          .roomStatus=${f}
          .panelConfig=${this.config}
          .ws=${this.ws}
          .panel=${this.panel}
          .hass=${this.hass}
        ></climate-manager-room-card>
      `;
    }, l = (g) => {
      var $, w;
      const m = (w = ($ = this.hass) == null ? void 0 : $.floors) == null ? void 0 : w[g];
      if (m != null && m.icon) return m.icon;
      const f = (m == null ? void 0 : m.level) ?? 0;
      return f === -1 ? "mdi:home-floor-negative-1" : f < 0 ? "mdi:home-floor-b" : f === 1 ? "mdi:home-floor-1" : f === 2 ? "mdi:home-floor-2" : f === 3 || f > 3 ? "mdi:home-floor-3" : "mdi:home-floor-0";
    };
    return d`
      ${i.map((g) => {
      var $, w, G;
      const m = ((G = (w = ($ = this.hass) == null ? void 0 : $.floors) == null ? void 0 : w[g]) == null ? void 0 : G.name) ?? g, f = r.get(g) ?? [];
      return d`
          <div class="floor-header">
            <ha-icon icon=${l(g)}></ha-icon>
            ${m}
          </div>
          ${f.map(c)}
        `;
    })}
      ${a.map(c)}
    `;
  }
};
Rt.styles = z`
    :host {
      display: block;
    }

    .empty-state {
      text-align: center;
      padding: 48px 16px;
      color: var(--secondary-text-color);
      font-size: 14px;
      line-height: 1.5;
    }

    .floor-header {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 12px;
      font-weight: 600;
      letter-spacing: 0.5px;
      text-transform: uppercase;
      color: var(--secondary-text-color);
      padding: 16px 4px 8px;
    }

    .floor-header:first-child {
      padding-top: 0;
    }

    .floor-header ha-icon {
      --mdc-icon-size: 16px;
      width: 16px;
      height: 16px;
      flex-shrink: 0;
    }
  `;
let N = Rt;
ot([
  u({ attribute: !1 })
], N.prototype, "config");
ot([
  u({ attribute: !1 })
], N.prototype, "status");
ot([
  u({ attribute: !1 })
], N.prototype, "ws");
ot([
  u({ attribute: !1 })
], N.prototype, "panel");
ot([
  u({ attribute: !1 })
], N.prototype, "hass");
customElements.define("climate-manager-rooms-tab", N);
var De = Object.defineProperty, B = (n, t, e, o) => {
  for (var s = void 0, r = n.length - 1, i; r >= 0; r--)
    (i = n[r]) && (s = i(t, e, s) || s);
  return s && De(t, e, s), s;
};
const X = "automatic", ft = "present", _t = "absent", Ot = class Ot extends S {
  constructor() {
    super(...arguments), this.roomChoices = [], this._expanded = !1;
  }
  connectedCallback() {
    super.connectedCallback(), this._expanded = this._isNonDefault();
  }
  _isNonDefault() {
    const t = this.config;
    return t ? t.mode != null && t.mode !== X || t.room_ids != null && t.room_ids.length > 0 || t.schedule != null && this._hasSchedulePeriods(t.schedule) : !1;
  }
  _hasSchedulePeriods(t) {
    return Object.values(t).some((e) => e.length > 0);
  }
  // -----------------------------------------------------------------------
  // Save handlers
  // -----------------------------------------------------------------------
  async _onModeChange(t) {
    const e = t.target.value;
    if (e)
      try {
        await this.ws.setPersonConfig(this.personId, { mode: e }), this.panel.showToast("Saved", !1);
      } catch {
        this.panel.showToast("Save failed — retrying...", !0);
      }
  }
  async _onRoomCheckboxToggle(t, e) {
    var r;
    const o = [...((r = this.config) == null ? void 0 : r.room_ids) ?? []];
    let s;
    e ? s = o.includes(t) ? o : [...o, t] : s = o.filter((i) => i !== t);
    try {
      await this.ws.setPersonConfig(this.personId, { room_ids: s }), this.panel.showToast("Saved", !1);
    } catch {
      this.panel.showToast("Save failed — retrying...", !0);
    }
  }
  async _onSchedulePeriodsChanged(t) {
    const { dayIndex: e, periods: o } = t.detail, r = { ...this.config.schedule ?? {
      mon: [],
      tue: [],
      wed: [],
      thu: [],
      fri: [],
      sat: [],
      sun: []
    } }, i = Pt(e);
    r[i] = o;
    try {
      await this.ws.setPersonConfig(this.personId, { schedule: r }), this.panel.showToast("Saved", !1);
    } catch {
      this.panel.showToast("Save failed — retrying...", !0);
    }
    t.stopPropagation();
  }
  // -----------------------------------------------------------------------
  // Render
  // -----------------------------------------------------------------------
  _getBadgeInfo() {
    var e;
    switch (((e = this.config) == null ? void 0 : e.mode) ?? X) {
      case ft:
        return { cls: "present", text: "Present" };
      case _t:
        return { cls: "absent", text: "Absent" };
      default:
        return { cls: "automatic", text: "Automatic" };
    }
  }
  render() {
    var i, a, c;
    const { cls: t, text: e } = this._getBadgeInfo(), o = ((i = this.config) == null ? void 0 : i.mode) ?? X, s = o === X, r = ((a = this.config) == null ? void 0 : a.room_ids) ?? [];
    return d`
      <ha-card>
        <div class="card-header-row" @click=${() => {
      this._expanded = !this._expanded;
    }}>
          <div class="card-header-left">
            <span class="person-name">${this.personName}</span>
            <span class="mode-badge ${t}">${e}</span>
          </div>
          <ha-icon
            class="expand-icon ${this._expanded ? "expanded" : ""}"
            icon="mdi:chevron-down"
          ></ha-icon>
        </div>

        ${this._expanded ? d`
            <div class="card-content">

              <!-- Presence mode selector -->
              <div class="section-label">Presence mode</div>
              <div class="select-wrapper">
                <select class="mode-select" @change=${this._onModeChange}>
                  <option value=${X} ?selected=${o === X}>Automatic</option>
                  <option value=${ft} ?selected=${o === ft}>Present</option>
                  <option value=${_t} ?selected=${o === _t}>Absent</option>
                </select>
              </div>

              <!-- Room associations -->
              ${this.roomChoices.length > 0 ? d`
                  <div class="section-label">Room associations</div>
                  <div class="room-checkboxes">
                    ${this.roomChoices.map(
      (l) => d`
                        <label class="room-checkbox-row">
                          <ha-checkbox
                            .checked=${r.includes(l.id)}
                            @change=${(h) => {
        const p = h.target;
        this._onRoomCheckboxToggle(l.id, p.checked);
      }}
                          ></ha-checkbox>
                          ${l.name}
                        </label>
                      `
    )}
                  </div>
                ` : ""}

              <!-- Presence schedule (only in Automatic mode) -->
              ${s ? d`
                  <div class="section-label">Presence schedule</div>
                  <div class="schedule-section">
                    <climate-manager-time-bar
                      mode="presence"
                      .days=${kt((c = this.config) == null ? void 0 : c.schedule)}
                      @periods-changed=${this._onSchedulePeriodsChanged}
                    ></climate-manager-time-bar>
                  </div>
                ` : ""}
            </div>
          ` : ""}
      </ha-card>
    `;
  }
};
Ot.styles = z`
    :host {
      display: block;
    }

    ha-card {
      margin-bottom: 12px;
    }

    .card-header-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 12px 16px;
      cursor: pointer;
    }

    .card-header-left {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .person-name {
      font-size: 16px;
      font-weight: 600;
      color: var(--primary-text-color);
    }

    .mode-badge {
      display: inline-flex;
      align-items: center;
      padding: 2px 8px;
      border-radius: 12px;
      font-size: 12px;
      font-weight: 400;
    }

    .mode-badge.automatic {
      background: var(--secondary-background-color, #f5f5f5);
      color: var(--secondary-text-color, #757575);
    }

    .mode-badge.present {
      border: 1px solid var(--primary-color, #03a9f4);
      color: var(--primary-color, #03a9f4);
    }

    .mode-badge.absent {
      background: var(--secondary-background-color, #f5f5f5);
      color: var(--secondary-text-color, #757575);
    }

    .expand-icon {
      color: var(--secondary-text-color);
      transition: transform 0.2s;
    }

    .expand-icon.expanded {
      transform: rotate(180deg);
    }

    .card-content {
      padding: 0 16px 16px;
      border-top: 1px solid var(--divider-color, #e0e0e0);
    }

    .section-label {
      font-size: 12px;
      font-weight: 600;
      letter-spacing: 0.5px;
      text-transform: uppercase;
      color: var(--secondary-text-color);
      margin: 12px 0 8px;
    }

    .select-wrapper {
      margin-bottom: 4px;
    }

    .select-label {
      display: block;
      font-size: 12px;
      color: var(--secondary-text-color);
      margin-bottom: 4px;
    }

    .mode-select {
      width: 100%;
      padding: 10px 12px;
      font-size: 16px;
      font-family: inherit;
      color: var(--primary-text-color);
      background-color: var(--card-background-color, var(--secondary-background-color));
      border: 1px solid var(--divider-color);
      border-radius: 4px;
      outline: none;
      cursor: pointer;
    }

    .mode-select:focus {
      border-color: var(--primary-color);
      border-width: 2px;
    }

    /* Room checkboxes */
    .room-checkboxes {
      display: flex;
      flex-direction: column;
      gap: 8px;
      margin-bottom: 16px;
    }

    .room-checkbox-row {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 14px;
      color: var(--primary-text-color);
      cursor: pointer;
    }

    ha-checkbox {
      --mdc-checkbox-unchecked-color: var(--secondary-text-color);
    }

    /* Presence schedule */
    .schedule-section {
      margin-top: 12px;
    }
  `;
let E = Ot;
B([
  u({ type: String })
], E.prototype, "personId");
B([
  u({ type: String })
], E.prototype, "personName");
B([
  u({ attribute: !1 })
], E.prototype, "config");
B([
  u({ attribute: !1 })
], E.prototype, "roomChoices");
B([
  u({ attribute: !1 })
], E.prototype, "ws");
B([
  u({ attribute: !1 })
], E.prototype, "panel");
B([
  x()
], E.prototype, "_expanded");
customElements.define("climate-manager-person-card", E);
var ze = Object.defineProperty, rt = (n, t, e, o) => {
  for (var s = void 0, r = n.length - 1, i; r >= 0; r--)
    (i = n[r]) && (s = i(t, e, s) || s);
  return s && ze(t, e, s), s;
};
const Nt = class Nt extends S {
  constructor() {
    super(...arguments), this.status = null;
  }
  /** Build the room choices list from config.rooms + rooms_status. */
  _getRoomChoices() {
    var s, r;
    const t = ((s = this.config) == null ? void 0 : s.rooms) ?? {}, e = ((r = this.status) == null ? void 0 : r.rooms_status) ?? [];
    return [.../* @__PURE__ */ new Set([
      ...Object.keys(t),
      ...e.map((i) => i.area_id)
    ])].map((i) => {
      var c;
      const a = ((c = e.find((l) => l.area_id === i)) == null ? void 0 : c.name) ?? i.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase());
      return { id: i, name: a };
    });
  }
  /** Determine if a person config has any non-default setting (D-15). */
  _isNonDefault(t) {
    var i, a, c;
    const e = (a = (i = this.config) == null ? void 0 : i.persons) == null ? void 0 : a[t];
    if (!e) return !1;
    const o = e.mode != null && e.mode !== "automatic", s = (((c = e.room_ids) == null ? void 0 : c.length) ?? 0) > 0, r = e.schedule ? Object.values(e.schedule).some((l) => l.length > 0) : !1;
    return o || s || r;
  }
  render() {
    var i, a;
    const t = ((i = this.config) == null ? void 0 : i.persons) ?? {}, e = Object.keys(((a = this.hass) == null ? void 0 : a.states) ?? {}).filter(
      (c) => c.startsWith("person.")
    ), o = [.../* @__PURE__ */ new Set([...e, ...Object.keys(t)])];
    if (o.length === 0)
      return d`
        <div class="empty-state">
          No persons found. Add person entities in Home Assistant.
        </div>
      `;
    const s = [...o].sort((c, l) => {
      const h = this._isNonDefault(c), p = this._isNonDefault(l);
      return h && !p ? -1 : !h && p ? 1 : c.localeCompare(l);
    }), r = this._getRoomChoices();
    return d`
      ${s.map((c) => {
      var p, _, b;
      const l = t[c] ?? {}, h = ((b = (_ = (p = this.hass) == null ? void 0 : p.states[c]) == null ? void 0 : _.attributes) == null ? void 0 : b.friendly_name) ?? c.replace(/^person\./, "").replace(/_/g, " ").replace(/\b\w/g, (y) => y.toUpperCase());
      return d`
          <climate-manager-person-card
            .personId=${c}
            .personName=${h}
            .config=${l}
            .roomChoices=${r}
            .ws=${this.ws}
            .panel=${this.panel}
          ></climate-manager-person-card>
        `;
    })}
    `;
  }
};
Nt.styles = z`
    :host {
      display: block;
    }

    .empty-state {
      text-align: center;
      padding: 48px 16px;
      color: var(--secondary-text-color);
      font-size: 14px;
      line-height: 1.5;
    }
  `;
let D = Nt;
rt([
  u({ attribute: !1 })
], D.prototype, "config");
rt([
  u({ attribute: !1 })
], D.prototype, "status");
rt([
  u({ attribute: !1 })
], D.prototype, "ws");
rt([
  u({ attribute: !1 })
], D.prototype, "panel");
rt([
  u({ attribute: !1 })
], D.prototype, "hass");
customElements.define("climate-manager-persons-tab", D);
var He = Object.defineProperty, T = (n, t, e, o) => {
  for (var s = void 0, r = n.length - 1, i; r >= 0; r--)
    (i = n[r]) && (s = i(t, e, s) || s);
  return s && He(t, e, s), s;
};
const Dt = class Dt extends S {
  constructor() {
    super(...arguments), this.narrow = !1, this.panel = null, this._config = null, this._status = null, this._activeTab = "global", this._unsubStatus = null, this._wsError = !1, this._ws = null;
  }
  connectedCallback() {
    super.connectedCallback(), this._ws = new it(this.hass), this._loadConfig(), this._loadStatus(), this._subscribeStatus();
  }
  disconnectedCallback() {
    super.disconnectedCallback(), this._unsubStatus && (this._unsubStatus.then((t) => t()).catch(() => {
    }), this._unsubStatus = null);
  }
  async _loadConfig() {
    this._ws || (this._ws = new it(this.hass));
    try {
      this._config = await this._ws.getConfig();
    } catch {
      this._wsError = !0;
    }
  }
  async _loadStatus() {
    this._ws || (this._ws = new it(this.hass));
    try {
      this._status = await this._ws.getStatus();
    } catch {
    }
  }
  _subscribeStatus() {
    this._ws || (this._ws = new it(this.hass)), this._unsubStatus = this._ws.subscribeStatus((t) => {
      this._status = t, this._wsError = !1;
    }).catch(() => (this._wsError = !0, () => {
    }));
  }
  /** Show a toast notification. Called by tab components after a save. */
  showToast(t, e) {
    var o;
    (o = this._toast) == null || o.show(t, e);
  }
  /** Patch a subset of _config in-place without a WS round-trip. */
  patchConfig(t) {
    this._config && (this._config = { ...this._config, ...t });
  }
  /**
   * Re-fetch the full config from the backend and update _config.
   *
   * Tab components call this after every successful write so that the parent's
   * _config stays in sync with the backend. Without this, Lit re-renders the
   * tab with the stale .config prop (e.g. the old global_mode), causing
   * ha-select to fire a spurious @selected event that immediately overwrites
   * the value just saved on the backend.
   */
  async reloadConfig() {
    await this._loadConfig();
  }
  _setTab(t) {
    this._activeTab = t;
  }
  render() {
    return this._config ? d`
      <div class="panel-header">Climate Manager</div>

      ${this._wsError ? d`<div class="error-banner">Connection lost. Reconnecting…</div>` : ""}

      <div class="tab-bar">
        <button
          class="tab-btn ${this._activeTab === "global" ? "active" : ""}"
          @click=${() => this._setTab("global")}
        >Global Settings</button>
        <button
          class="tab-btn ${this._activeTab === "rooms" ? "active" : ""}"
          @click=${() => this._setTab("rooms")}
        >Rooms</button>
        <button
          class="tab-btn ${this._activeTab === "persons" ? "active" : ""}"
          @click=${() => this._setTab("persons")}
        >Persons</button>
      </div>

      <div class="tab-content">
        ${this._renderTabContent()}
      </div>

      <climate-manager-toast></climate-manager-toast>
    ` : d`
        <div class="panel-header">Climate Manager</div>
        ${this._wsError ? d`<div class="error-banner">Connection lost. Reconnecting…</div>` : ""}
        <div class="loading">
          <ha-circular-progress active></ha-circular-progress>
        </div>
        <climate-manager-toast></climate-manager-toast>
      `;
  }
  _renderTabContent() {
    switch (this._activeTab) {
      case "global":
        return d`<climate-manager-global-settings-tab
          .config=${this._config}
          .status=${this._status}
          .ws=${this._ws}
          .panel=${this}
        ></climate-manager-global-settings-tab>`;
      case "rooms":
        return d`<climate-manager-rooms-tab
          .config=${this._config}
          .status=${this._status}
          .ws=${this._ws}
          .panel=${this}
          .hass=${this.hass}
        ></climate-manager-rooms-tab>`;
      case "persons":
        return d`<climate-manager-persons-tab
          .config=${this._config}
          .status=${this._status}
          .ws=${this._ws}
          .panel=${this}
          .hass=${this.hass}
        ></climate-manager-persons-tab>`;
      default:
        return d``;
    }
  }
};
Dt.styles = z`
    :host {
      display: block;
      background: var(--primary-background-color);
      min-height: 100%;
      font-family: var(--mdc-typography-body1-font-family, Roboto, sans-serif);
    }

    .panel-header {
      display: flex;
      align-items: center;
      padding: 0 16px;
      height: 56px;
      font-size: 20px;
      font-weight: 400;
      color: var(--app-header-text-color, var(--primary-text-color));
      background: var(--app-header-background-color, var(--primary-background-color));
      border-bottom: 1px solid var(--divider-color, rgba(0,0,0,0.12));
    }

    .loading {
      display: flex;
      justify-content: center;
      align-items: center;
      height: 200px;
    }

    .error-banner {
      background: var(--error-color, #db4437);
      color: #fff;
      padding: 8px 16px;
      font-size: 14px;
      text-align: center;
    }

    .tab-bar {
      display: flex;
      border-bottom: 1px solid var(--divider-color, rgba(0,0,0,0.12));
      background: var(--primary-background-color);
      padding: 0 8px;
      overflow-x: auto;
    }

    .tab-btn {
      background: none;
      border: none;
      border-bottom: 2px solid transparent;
      padding: 12px 16px;
      margin-bottom: -1px;
      cursor: pointer;
      font-size: 14px;
      font-weight: 500;
      color: var(--secondary-text-color);
      text-transform: uppercase;
      letter-spacing: 0.07em;
      white-space: nowrap;
      outline: none;
      transition: color 0.15s;
    }

    .tab-btn.active {
      border-bottom-color: var(--primary-color);
      color: var(--primary-color);
    }

    .tab-btn:hover:not(.active) {
      color: var(--primary-text-color);
    }

    .tab-content {
      padding: 16px;
      max-width: 900px;
      margin: 0 auto;
    }

    .placeholder {
      color: var(--secondary-text-color);
      font-size: 14px;
      padding: 24px 0;
      text-align: center;
    }
  `;
let P = Dt;
T([
  u({ attribute: !1 })
], P.prototype, "hass");
T([
  u({ type: Boolean })
], P.prototype, "narrow");
T([
  u({ attribute: !1 })
], P.prototype, "panel");
T([
  x()
], P.prototype, "_config");
T([
  x()
], P.prototype, "_status");
T([
  x()
], P.prototype, "_activeTab");
T([
  x()
], P.prototype, "_unsubStatus");
T([
  x()
], P.prototype, "_wsError");
T([
  Se("climate-manager-toast")
], P.prototype, "_toast");
customElements.define("climate-manager-panel", P);
export {
  P as ClimateManagerPanel
};
