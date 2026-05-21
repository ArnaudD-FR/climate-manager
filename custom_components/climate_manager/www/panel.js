/**
 * @license
 * Copyright 2019 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const lt = globalThis, wt = lt.ShadowRoot && (lt.ShadyCSS === void 0 || lt.ShadyCSS.nativeShadow) && "adoptedStyleSheets" in Document.prototype && "replace" in CSSStyleSheet.prototype, St = Symbol(), Lt = /* @__PURE__ */ new WeakMap();
let Qt = class {
  constructor(t, e, o) {
    if (this._$cssResult$ = !0, o !== St) throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");
    this.cssText = t, this.t = e;
  }
  get styleSheet() {
    let t = this.o;
    const e = this.t;
    if (wt && t === void 0) {
      const o = e !== void 0 && e.length === 1;
      o && (t = Lt.get(e)), t === void 0 && ((this.o = t = new CSSStyleSheet()).replaceSync(this.cssText), o && Lt.set(e, t));
    }
    return t;
  }
  toString() {
    return this.cssText;
  }
};
const ie = (n) => new Qt(typeof n == "string" ? n : n + "", void 0, St), E = (n, ...t) => {
  const e = n.length === 1 ? n[0] : t.reduce((o, s, r) => o + ((i) => {
    if (i._$cssResult$ === !0) return i.cssText;
    if (typeof i == "number") return i;
    throw Error("Value passed to 'css' function must be a 'css' function result: " + i + ". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.");
  })(s) + n[r + 1], n[0]);
  return new Qt(e, n, St);
}, ne = (n, t) => {
  if (wt) n.adoptedStyleSheets = t.map((e) => e instanceof CSSStyleSheet ? e : e.styleSheet);
  else for (const e of t) {
    const o = document.createElement("style"), s = lt.litNonce;
    s !== void 0 && o.setAttribute("nonce", s), o.textContent = e.cssText, n.appendChild(o);
  }
}, Bt = wt ? (n) => n : (n) => n instanceof CSSStyleSheet ? ((t) => {
  let e = "";
  for (const o of t.cssRules) e += o.cssText;
  return ie(e);
})(n) : n;
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const { is: ae, defineProperty: ce, getOwnPropertyDescriptor: le, getOwnPropertyNames: de, getOwnPropertySymbols: pe, getPrototypeOf: he } = Object, D = globalThis, Ft = D.trustedTypes, ue = Ft ? Ft.emptyScript : "", mt = D.reactiveElementPolyfillSupport, Q = (n, t) => n, dt = { toAttribute(n, t) {
  switch (t) {
    case Boolean:
      n = n ? ue : null;
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
} }, Ct = (n, t) => !ae(n, t), qt = { attribute: !0, type: String, converter: dt, reflect: !1, useDefault: !1, hasChanged: Ct };
Symbol.metadata ?? (Symbol.metadata = Symbol("metadata")), D.litPropertyMetadata ?? (D.litPropertyMetadata = /* @__PURE__ */ new WeakMap());
let Y = class extends HTMLElement {
  static addInitializer(t) {
    this._$Ei(), (this.l ?? (this.l = [])).push(t);
  }
  static get observedAttributes() {
    return this.finalize(), this._$Eh && [...this._$Eh.keys()];
  }
  static createProperty(t, e = qt) {
    if (e.state && (e.attribute = !1), this._$Ei(), this.prototype.hasOwnProperty(t) && ((e = Object.create(e)).wrapped = !0), this.elementProperties.set(t, e), !e.noAccessor) {
      const o = Symbol(), s = this.getPropertyDescriptor(t, o, e);
      s !== void 0 && ce(this.prototype, t, s);
    }
  }
  static getPropertyDescriptor(t, e, o) {
    const { get: s, set: r } = le(this.prototype, t) ?? { get() {
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
    return this.elementProperties.get(t) ?? qt;
  }
  static _$Ei() {
    if (this.hasOwnProperty(Q("elementProperties"))) return;
    const t = he(this);
    t.finalize(), t.l !== void 0 && (this.l = [...t.l]), this.elementProperties = new Map(t.elementProperties);
  }
  static finalize() {
    if (this.hasOwnProperty(Q("finalized"))) return;
    if (this.finalized = !0, this._$Ei(), this.hasOwnProperty(Q("properties"))) {
      const e = this.properties, o = [...de(e), ...pe(e)];
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
      for (const s of o) e.unshift(Bt(s));
    } else t !== void 0 && e.push(Bt(t));
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
    return ne(t, this.constructor.elementStyles), t;
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
      const i = (((r = o.converter) == null ? void 0 : r.toAttribute) !== void 0 ? o.converter : dt).toAttribute(e, o.type);
      this._$Em = t, i == null ? this.removeAttribute(s) : this.setAttribute(s, i), this._$Em = null;
    }
  }
  _$AK(t, e) {
    var r, i;
    const o = this.constructor, s = o._$Eh.get(t);
    if (s !== void 0 && this._$Em !== s) {
      const a = o.getPropertyOptions(s), c = typeof a.converter == "function" ? { fromAttribute: a.converter } : ((r = a.converter) == null ? void 0 : r.fromAttribute) !== void 0 ? a.converter : dt;
      this._$Em = s;
      const d = c.fromAttribute(e, a.type);
      this[s] = d ?? ((i = this._$Ej) == null ? void 0 : i.get(s)) ?? d, this._$Em = null;
    }
  }
  requestUpdate(t, e, o, s = !1, r) {
    var i;
    if (t !== void 0) {
      const a = this.constructor;
      if (s === !1 && (r = this[t]), o ?? (o = a.getPropertyOptions(t)), !((o.hasChanged ?? Ct)(r, e) || o.useDefault && o.reflect && r === ((i = this._$Ej) == null ? void 0 : i.get(t)) && !this.hasAttribute(a._$Eu(t, o)))) return;
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
Y.elementStyles = [], Y.shadowRootOptions = { mode: "open" }, Y[Q("elementProperties")] = /* @__PURE__ */ new Map(), Y[Q("finalized")] = /* @__PURE__ */ new Map(), mt == null || mt({ ReactiveElement: Y }), (D.reactiveElementVersions ?? (D.reactiveElementVersions = [])).push("2.1.2");
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const tt = globalThis, Xt = (n) => n, pt = tt.trustedTypes, Yt = pt ? pt.createPolicy("lit-html", { createHTML: (n) => n }) : void 0, te = "$lit$", z = `lit$${Math.random().toFixed(9).slice(2)}$`, ee = "?" + z, me = `<${ee}>`, L = document, et = () => L.createComment(""), st = (n) => n === null || typeof n != "object" && typeof n != "function", Pt = Array.isArray, ge = (n) => Pt(n) || typeof (n == null ? void 0 : n[Symbol.iterator]) == "function", gt = `[ 	
\f\r]`, Z = /<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g, Gt = /-->/g, Vt = />/g, H = RegExp(`>|${gt}(?:([^\\s"'>=/]+)(${gt}*=${gt}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`, "g"), Wt = /'/g, Jt = /"/g, se = /^(?:script|style|textarea|title)$/i, fe = (n) => (t, ...e) => ({ _$litType$: n, strings: t, values: e }), l = fe(1), G = Symbol.for("lit-noChange"), x = Symbol.for("lit-nothing"), Kt = /* @__PURE__ */ new WeakMap(), U = L.createTreeWalker(L, 129);
function oe(n, t) {
  if (!Pt(n) || !n.hasOwnProperty("raw")) throw Error("invalid template strings array");
  return Yt !== void 0 ? Yt.createHTML(t) : t;
}
const _e = (n, t) => {
  const e = n.length - 1, o = [];
  let s, r = t === 2 ? "<svg>" : t === 3 ? "<math>" : "", i = Z;
  for (let a = 0; a < e; a++) {
    const c = n[a];
    let d, p, h = -1, _ = 0;
    for (; _ < c.length && (i.lastIndex = _, p = i.exec(c), p !== null); ) _ = i.lastIndex, i === Z ? p[1] === "!--" ? i = Gt : p[1] !== void 0 ? i = Vt : p[2] !== void 0 ? (se.test(p[2]) && (s = RegExp("</" + p[2], "g")), i = H) : p[3] !== void 0 && (i = H) : i === H ? p[0] === ">" ? (i = s ?? Z, h = -1) : p[1] === void 0 ? h = -2 : (h = i.lastIndex - p[2].length, d = p[1], i = p[3] === void 0 ? H : p[3] === '"' ? Jt : Wt) : i === Jt || i === Wt ? i = H : i === Gt || i === Vt ? i = Z : (i = H, s = void 0);
    const b = i === H && n[a + 1].startsWith("/>") ? " " : "";
    r += i === Z ? c + me : h >= 0 ? (o.push(d), c.slice(0, h) + te + c.slice(h) + z + b) : c + z + (h === -2 ? a : b);
  }
  return [oe(n, r + (n[e] || "<?>") + (t === 2 ? "</svg>" : t === 3 ? "</math>" : "")), o];
};
class ot {
  constructor({ strings: t, _$litType$: e }, o) {
    let s;
    this.parts = [];
    let r = 0, i = 0;
    const a = t.length - 1, c = this.parts, [d, p] = _e(t, e);
    if (this.el = ot.createElement(d, o), U.currentNode = this.el.content, e === 2 || e === 3) {
      const h = this.el.content.firstChild;
      h.replaceWith(...h.childNodes);
    }
    for (; (s = U.nextNode()) !== null && c.length < a; ) {
      if (s.nodeType === 1) {
        if (s.hasAttributes()) for (const h of s.getAttributeNames()) if (h.endsWith(te)) {
          const _ = p[i++], b = s.getAttribute(h).split(z), y = /([.?@])?(.*)/.exec(_);
          c.push({ type: 1, index: r, name: y[2], strings: b, ctor: y[1] === "." ? ve : y[1] === "?" ? ye : y[1] === "@" ? xe : ht }), s.removeAttribute(h);
        } else h.startsWith(z) && (c.push({ type: 6, index: r }), s.removeAttribute(h));
        if (se.test(s.tagName)) {
          const h = s.textContent.split(z), _ = h.length - 1;
          if (_ > 0) {
            s.textContent = pt ? pt.emptyScript : "";
            for (let b = 0; b < _; b++) s.append(h[b], et()), U.nextNode(), c.push({ type: 2, index: ++r });
            s.append(h[_], et());
          }
        }
      } else if (s.nodeType === 8) if (s.data === ee) c.push({ type: 2, index: r });
      else {
        let h = -1;
        for (; (h = s.data.indexOf(z, h + 1)) !== -1; ) c.push({ type: 7, index: r }), h += z.length - 1;
      }
      r++;
    }
  }
  static createElement(t, e) {
    const o = L.createElement("template");
    return o.innerHTML = t, o;
  }
}
function V(n, t, e = n, o) {
  var i, a;
  if (t === G) return t;
  let s = o !== void 0 ? (i = e._$Co) == null ? void 0 : i[o] : e._$Cl;
  const r = st(t) ? void 0 : t._$litDirective$;
  return (s == null ? void 0 : s.constructor) !== r && ((a = s == null ? void 0 : s._$AO) == null || a.call(s, !1), r === void 0 ? s = void 0 : (s = new r(n), s._$AT(n, e, o)), o !== void 0 ? (e._$Co ?? (e._$Co = []))[o] = s : e._$Cl = s), s !== void 0 && (t = V(n, s._$AS(n, t.values), s, o)), t;
}
class be {
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
    const { el: { content: e }, parts: o } = this._$AD, s = ((t == null ? void 0 : t.creationScope) ?? L).importNode(e, !0);
    U.currentNode = s;
    let r = U.nextNode(), i = 0, a = 0, c = o[0];
    for (; c !== void 0; ) {
      if (i === c.index) {
        let d;
        c.type === 2 ? d = new rt(r, r.nextSibling, this, t) : c.type === 1 ? d = new c.ctor(r, c.name, c.strings, this, t) : c.type === 6 && (d = new $e(r, this, t)), this._$AV.push(d), c = o[++a];
      }
      i !== (c == null ? void 0 : c.index) && (r = U.nextNode(), i++);
    }
    return U.currentNode = L, s;
  }
  p(t) {
    let e = 0;
    for (const o of this._$AV) o !== void 0 && (o.strings !== void 0 ? (o._$AI(t, o, e), e += o.strings.length - 2) : o._$AI(t[e])), e++;
  }
}
class rt {
  get _$AU() {
    var t;
    return ((t = this._$AM) == null ? void 0 : t._$AU) ?? this._$Cv;
  }
  constructor(t, e, o, s) {
    this.type = 2, this._$AH = x, this._$AN = void 0, this._$AA = t, this._$AB = e, this._$AM = o, this.options = s, this._$Cv = (s == null ? void 0 : s.isConnected) ?? !0;
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
    t = V(this, t, e), st(t) ? t === x || t == null || t === "" ? (this._$AH !== x && this._$AR(), this._$AH = x) : t !== this._$AH && t !== G && this._(t) : t._$litType$ !== void 0 ? this.$(t) : t.nodeType !== void 0 ? this.T(t) : ge(t) ? this.k(t) : this._(t);
  }
  O(t) {
    return this._$AA.parentNode.insertBefore(t, this._$AB);
  }
  T(t) {
    this._$AH !== t && (this._$AR(), this._$AH = this.O(t));
  }
  _(t) {
    this._$AH !== x && st(this._$AH) ? this._$AA.nextSibling.data = t : this.T(L.createTextNode(t)), this._$AH = t;
  }
  $(t) {
    var r;
    const { values: e, _$litType$: o } = t, s = typeof o == "number" ? this._$AC(t) : (o.el === void 0 && (o.el = ot.createElement(oe(o.h, o.h[0]), this.options)), o);
    if (((r = this._$AH) == null ? void 0 : r._$AD) === s) this._$AH.p(e);
    else {
      const i = new be(s, this), a = i.u(this.options);
      i.p(e), this.T(a), this._$AH = i;
    }
  }
  _$AC(t) {
    let e = Kt.get(t.strings);
    return e === void 0 && Kt.set(t.strings, e = new ot(t)), e;
  }
  k(t) {
    Pt(this._$AH) || (this._$AH = [], this._$AR());
    const e = this._$AH;
    let o, s = 0;
    for (const r of t) s === e.length ? e.push(o = new rt(this.O(et()), this.O(et()), this, this.options)) : o = e[s], o._$AI(r), s++;
    s < e.length && (this._$AR(o && o._$AB.nextSibling, s), e.length = s);
  }
  _$AR(t = this._$AA.nextSibling, e) {
    var o;
    for ((o = this._$AP) == null ? void 0 : o.call(this, !1, !0, e); t !== this._$AB; ) {
      const s = Xt(t).nextSibling;
      Xt(t).remove(), t = s;
    }
  }
  setConnected(t) {
    var e;
    this._$AM === void 0 && (this._$Cv = t, (e = this._$AP) == null || e.call(this, t));
  }
}
class ht {
  get tagName() {
    return this.element.tagName;
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  constructor(t, e, o, s, r) {
    this.type = 1, this._$AH = x, this._$AN = void 0, this.element = t, this.name = e, this._$AM = s, this.options = r, o.length > 2 || o[0] !== "" || o[1] !== "" ? (this._$AH = Array(o.length - 1).fill(new String()), this.strings = o) : this._$AH = x;
  }
  _$AI(t, e = this, o, s) {
    const r = this.strings;
    let i = !1;
    if (r === void 0) t = V(this, t, e, 0), i = !st(t) || t !== this._$AH && t !== G, i && (this._$AH = t);
    else {
      const a = t;
      let c, d;
      for (t = r[0], c = 0; c < r.length - 1; c++) d = V(this, a[o + c], e, c), d === G && (d = this._$AH[c]), i || (i = !st(d) || d !== this._$AH[c]), d === x ? t = x : t !== x && (t += (d ?? "") + r[c + 1]), this._$AH[c] = d;
    }
    i && !s && this.j(t);
  }
  j(t) {
    t === x ? this.element.removeAttribute(this.name) : this.element.setAttribute(this.name, t ?? "");
  }
}
class ve extends ht {
  constructor() {
    super(...arguments), this.type = 3;
  }
  j(t) {
    this.element[this.name] = t === x ? void 0 : t;
  }
}
class ye extends ht {
  constructor() {
    super(...arguments), this.type = 4;
  }
  j(t) {
    this.element.toggleAttribute(this.name, !!t && t !== x);
  }
}
class xe extends ht {
  constructor(t, e, o, s, r) {
    super(t, e, o, s, r), this.type = 5;
  }
  _$AI(t, e = this) {
    if ((t = V(this, t, e, 0) ?? x) === G) return;
    const o = this._$AH, s = t === x && o !== x || t.capture !== o.capture || t.once !== o.once || t.passive !== o.passive, r = t !== x && (o === x || s);
    s && this.element.removeEventListener(this.name, this, o), r && this.element.addEventListener(this.name, this, t), this._$AH = t;
  }
  handleEvent(t) {
    var e;
    typeof this._$AH == "function" ? this._$AH.call(((e = this.options) == null ? void 0 : e.host) ?? this.element, t) : this._$AH.handleEvent(t);
  }
}
class $e {
  constructor(t, e, o) {
    this.element = t, this.type = 6, this._$AN = void 0, this._$AM = e, this.options = o;
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  _$AI(t) {
    V(this, t);
  }
}
const ft = tt.litHtmlPolyfillSupport;
ft == null || ft(ot, rt), (tt.litHtmlVersions ?? (tt.litHtmlVersions = [])).push("3.3.3");
const we = (n, t, e) => {
  const o = (e == null ? void 0 : e.renderBefore) ?? t;
  let s = o._$litPart$;
  if (s === void 0) {
    const r = (e == null ? void 0 : e.renderBefore) ?? null;
    o._$litPart$ = s = new rt(t.insertBefore(et(), r), r, void 0, e ?? {});
  }
  return s._$AI(n), s;
};
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const j = globalThis;
class w extends Y {
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
    this.hasUpdated || (this.renderOptions.isConnected = this.isConnected), super.update(t), this._$Do = we(e, this.renderRoot, this.renderOptions);
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
    return G;
  }
}
var Zt;
w._$litElement$ = !0, w.finalized = !0, (Zt = j.litElementHydrateSupport) == null || Zt.call(j, { LitElement: w });
const _t = j.litElementPolyfillSupport;
_t == null || _t({ LitElement: w });
(j.litElementVersions ?? (j.litElementVersions = [])).push("4.2.2");
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const Se = { attribute: !0, type: String, converter: dt, reflect: !1, hasChanged: Ct }, Ce = (n = Se, t, e) => {
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
function m(n) {
  return (t, e) => typeof e == "object" ? Ce(n, t, e) : ((o, s, r) => {
    const i = s.hasOwnProperty(r);
    return s.constructor.createProperty(r, o), i ? Object.getOwnPropertyDescriptor(s, r) : void 0;
  })(n, t, e);
}
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
function v(n) {
  return m({ ...n, state: !0, attribute: !1 });
}
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const Pe = (n, t, e) => (e.configurable = !0, e.enumerable = !0, Reflect.decorate && typeof t != "object" && Object.defineProperty(n, t, e), e);
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
function ke(n, t) {
  return (e, o, s) => {
    const r = (i) => {
      var a;
      return ((a = i.renderRoot) == null ? void 0 : a.querySelector(n)) ?? null;
    };
    return Pe(e, o, { get() {
      return r(this);
    } });
  };
}
class at {
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
var Te = Object.defineProperty, kt = (n, t, e, o) => {
  for (var s = void 0, r = n.length - 1, i; r >= 0; r--)
    (i = n[r]) && (s = i(t, e, s) || s);
  return s && Te(t, e, s), s;
};
const Et = class Et extends w {
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
    return l`
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
Et.styles = E`
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
let W = Et;
kt([
  v()
], W.prototype, "_visible");
kt([
  v()
], W.prototype, "_message");
kt([
  v()
], W.prototype, "_isError");
customElements.define("climate-manager-toast", W);
const q = {
  frost_protection: "#1565C0",
  reduced: "#64B5F6",
  normal: "#F57C00",
  comfort: "#D32F2F"
}, ct = {
  present: "#388E3C",
  absent: "#9E9E9E"
}, Ae = {
  frost_protection: "Frost protection",
  reduced: "Reduced",
  normal: "Normal",
  comfort: "Comfort",
  present: "Present",
  absent: "Absent"
};
var Ee = Object.defineProperty, M = (n, t, e, o) => {
  for (var s = void 0, r = n.length - 1, i; r >= 0; r--)
    (i = n[r]) && (s = i(t, e, s) || s);
  return s && Ee(t, e, s), s;
};
const Me = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], Re = ["frost_protection", "reduced", "normal", "comfort"], Oe = ["present", "absent"], Mt = class Mt extends w {
  constructor() {
    super(...arguments), this.days = Array.from(
      { length: 7 },
      () => []
    ), this.mode = "schedule", this._clipboard = null, this._drag = null, this._dragTooltipMinutes = null, this._dragTooltipX = 0, this._dragTooltipY = 0, this._dragPreviewDays = null, this._popup = null, this._justDragged = !1;
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
    return this.mode === "presence" ? ct[e] ?? ct.absent : q[e] ?? q.frost_protection;
  }
  _labelForPeriod(t) {
    const e = this.mode === "presence" ? t.state ?? "absent" : t.mode ?? "frost_protection";
    return Ae[e] ?? e;
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
      const c = this._timeToMinutes(r[a].start), d = a + 1 < r.length ? this._timeToMinutes(r[a + 1].start) : 1440;
      i.push({ period: r[a], startMin: c, endMin: d });
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
      { key: "present", label: "Present", color: ct.present },
      { key: "absent", label: "Absent", color: ct.absent }
    ] : [
      {
        key: "frost_protection",
        label: "Frost protection",
        color: q.frost_protection
      },
      { key: "reduced", label: "Reduced", color: q.reduced },
      { key: "normal", label: "Normal", color: q.normal },
      { key: "comfort", label: "Comfort", color: q.comfort }
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
    if (this._justDragged) {
      this._justDragged = !1, t.stopPropagation();
      return;
    }
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
    const i = s.sort((c, d) => c.start.localeCompare(d.start)), a = i.filter(
      (c, d) => d === 0 || c.start !== i[d - 1].start
    );
    this._closePopup(), this._emitChange(e, a);
  }
  // -----------------------------------------------------------------------
  // Click on existing segment → edit/delete popup
  // -----------------------------------------------------------------------
  _onSegmentClick(t, e, o) {
    if (this._drag) {
      t.stopPropagation();
      return;
    }
    if (this._justDragged) {
      this._justDragged = !1, t.stopPropagation();
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
    const r = (this.days[t] ?? []).filter(
      (i) => i.start !== s.period.start
    );
    this._closePopup(), this._emitChange(t, r);
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
    ), c = this.mode === "presence" ? Oe : Re, d = this.mode === "presence" ? s.period.state ?? "absent" : s.period.mode ?? "frost_protection", p = c.indexOf(d), h = c[(p + 1) % c.length], _ = this.mode === "presence" ? { start: s.period.start, state: d } : { start: s.period.start, mode: d }, b = this.mode === "presence" ? { start: this._minutesToHHMM(a), state: h } : { start: this._minutesToHHMM(a), mode: h }, y = this.days[t] ?? [], g = y.some(
      (u) => u.start === s.period.start
    );
    let f;
    g ? f = y.flatMap(
      (u) => u.start === s.period.start ? [_, b] : [u]
    ) : f = [b, ...y], this._closePopup(), this._emitChange(t, f);
  }
  // -----------------------------------------------------------------------
  // Drag boundary (D-06)
  // -----------------------------------------------------------------------
  _onDragHandlePointerDown(t, e, o) {
    t.stopPropagation(), t.target.setPointerCapture(t.pointerId), this._dragPreviewDays = null;
    const r = this._toSegments(this.days[e] ?? [])[o];
    r && (this._drag = {
      dayIndex: e,
      segIndex: o,
      startX: t.clientX,
      initialBoundaryMinutes: r.endMin
    }, this._dragTooltipMinutes = r.endMin, this._dragTooltipX = t.clientX, this._dragTooltipY = t.clientY);
  }
  _onPointerMove(t) {
    var h;
    if (!this._drag) return;
    const { dayIndex: e, segIndex: o } = this._drag, s = (h = this.shadowRoot) == null ? void 0 : h.querySelector(
      `.day-row:nth-child(${e + 2}) .bar-wrap`
    );
    if (!s) return;
    const r = s.getBoundingClientRect(), i = this._pixelToMinutes(t.clientX - r.left, r.width), a = this._snapToMinutes(i);
    this._dragTooltipMinutes = a, this._dragTooltipX = t.clientX, this._dragTooltipY = t.clientY;
    const c = this._toSegments(this.days[e] ?? []), d = c[o], p = c[o + 1];
    if (d && p) {
      const _ = d.startMin + 15, b = p.endMin - 15, y = Math.max(_, Math.min(b, a)), g = (this.days[e] ?? []).map((u) => u.start === p.period.start ? { ...u, start: this._minutesToHHMM(y) } : u), f = this.days.map(
        (u, $) => $ === e ? g : u
      );
      this._dragPreviewDays = f;
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
      ), c = this._snapToMinutes(a), d = this._toSegments(this.days[e] ?? []), p = d[o], h = d[o + 1];
      if (p && h) {
        const _ = p.startMin + 15, b = h.endMin - 15, y = Math.max(
          _,
          Math.min(b, c)
        ), g = (this.days[e] ?? []).map((u) => u.start === h.period.start ? { ...u, start: this._minutesToHHMM(y) } : u), f = this.days.map(
          (u, $) => $ === e ? g : u
        );
        this._drag = null, this._dragTooltipMinutes = null, this._dragPreviewDays = f, this._justDragged = !0, this._emitChange(e, g);
        return;
      }
    }
    this._drag = null, this._dragTooltipMinutes = null, this._dragPreviewDays = null, this._justDragged = !0;
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
  updated(t) {
    t.has("days") && this._dragPreviewDays && (this._dragPreviewDays = null);
  }
  render() {
    return l`
      <div
        class="week-grid"
        @pointermove=${this._onPointerMove}
        @pointerup=${this._onPointerUp}
      >
        <!-- Time axis above day rows — identical structure to bottom axis -->
        ${this._renderTimeAxis()}

        ${Me.map(
      (t, e) => this._renderDayRow(t, e)
    )}

        <!-- Shared time axis below day rows -->
        ${this._renderTimeAxis()}
      </div>

      <!-- Drag tooltip -->
      ${this._drag !== null && this._dragTooltipMinutes !== null ? l`<div
            class="drag-tooltip"
            style="left:${this._dragTooltipX}px;top:${this._dragTooltipY}px"
            aria-live="polite"
          >
            ${this._minutesToHHMM(this._dragTooltipMinutes)}
          </div>` : ""}

      <!-- Popup overlay + popup -->
      ${this._popup ? l`
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
    return l`
      <div class="time-axis">
        <div class="time-axis-inner">
          ${["00:00", "06:00", "12:00", "18:00", "24:00"].map(
      (t) => l`<span class="axis-tick">${t}</span>`
    )}
        </div>
      </div>
    `;
  }
  _renderDayRow(t, e) {
    const s = (this._dragPreviewDays ?? this.days)[e] ?? [], r = this._toSegments(s), i = r.length === 0;
    return l`
      <div class="day-row">
        <div class="day-label">${t}</div>

        <div
          class="bar-wrap"
          @click=${(a) => {
      (a.target.classList.contains("bar-wrap") || a.target.classList.contains("bar-row-inner")) && this._onBarClick(a, e);
    }}
        >
          ${i ? l`<div class="empty-hint">
                Click the bar to add your first period.
              </div>` : l`<div class="bar-row-inner">
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
    var d;
    const r = this._colorForPeriod(t.period), i = this._labelForPeriod(t.period), a = (t.endMin - t.startMin) / 1440 * 100, c = this.mode === "presence" ? t.period.state ?? "absent" : ((d = t.period.mode) == null ? void 0 : d.replace(/_/g, " ")) ?? "frost protection";
    return l`
      <div
        class="segment"
        style="width:${a}%;background:${r}"
        aria-label="${c}"
        @click=${(p) => this._onSegmentClick(p, e, o)}
      >
        ${a > 2.7 ? l`<span class="segment-label">${i}</span>` : ""}

        <!-- Drag handle on right border (not on last segment) -->
        ${o < s - 1 ? l`<div
              class="drag-handle"
              @pointerdown=${(p) => this._onDragHandlePointerDown(p, e, o)}
            ></div>` : ""}
      </div>
    `;
  }
  _renderPopup() {
    var t;
    if (!this._popup) return l``;
    if (this._popup.kind === "split") {
      const e = this._minutesToHHMM(this._popup.snappedMinutes ?? 0);
      return l`
        <div class="popup-title">Split at ${e}</div>
        <div class="mode-options">
          ${this._modeOptions().map(
        (o) => l`
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
      if (!o) return l``;
      const s = `${this._minutesToHHMM(o.startMin)} – ${this._minutesToHHMM(o.endMin)}`, r = this.mode === "presence" ? o.period.state ?? "absent" : ((t = o.period.mode) == null ? void 0 : t.replace(/_/g, " ")) ?? "frost protection", a = o.endMin - o.startMin >= 30;
      return l`
        <div class="popup-title">${s} · ${r}</div>

        <div class="mode-options">
          <div
            style="font-size:11px;color:var(--secondary-text-color);margin-bottom:4px"
          >
            Change mode
          </div>
          ${this._modeOptions().map(
        (c) => l`
              <button
                class="mode-option"
                @click=${() => this._onEditModeSelect(c.key)}
              >
                <span
                  class="mode-swatch"
                  style="background:${c.color}"
                ></span>
                ${c.label}
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
            @click=${this._onDeleteSegment}
          >
            Delete period
          </button>
        </div>
      `;
    }
    return l``;
  }
};
Mt.styles = E`
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
let C = Mt;
M([
  m({ type: Array })
], C.prototype, "days");
M([
  m({ type: String })
], C.prototype, "mode");
M([
  v()
], C.prototype, "_clipboard");
M([
  v()
], C.prototype, "_drag");
M([
  v()
], C.prototype, "_dragTooltipMinutes");
M([
  v()
], C.prototype, "_dragTooltipX");
M([
  v()
], C.prototype, "_dragTooltipY");
M([
  v()
], C.prototype, "_dragPreviewDays");
M([
  v()
], C.prototype, "_popup");
customElements.define("climate-manager-time-bar", C);
var ze = Object.defineProperty, ut = (n, t, e, o) => {
  for (var s = void 0, r = n.length - 1, i; r >= 0; r--)
    (i = n[r]) && (s = i(t, e, s) || s);
  return s && ze(t, e, s), s;
};
const re = [
  "mon",
  "tue",
  "wed",
  "thu",
  "fri",
  "sat",
  "sun"
];
function Tt(n) {
  return re.map((t) => n != null && n[t] ? [...n[t]] : []);
}
function At(n) {
  return re[n] ?? "mon";
}
const yt = "off", xt = "time_program", $t = "time_program_presences", De = {
  [yt]: "Off",
  [xt]: "Time program",
  [$t]: "Time program & presences"
}, Ie = {
  frost_protection: 7,
  reduced: 18,
  normal: 20,
  comfort: 22
}, Ne = "time_program", He = (() => {
  const n = () => [
    { start: "00:00", mode: "frost_protection" },
    { start: "06:00", mode: "normal" },
    { start: "22:00", mode: "frost_protection" }
  ];
  return {
    mon: n(),
    tue: n(),
    wed: n(),
    thu: n(),
    fri: n(),
    sat: n(),
    sun: n()
  };
})(), Rt = class Rt extends w {
  constructor() {
    super(...arguments), this.status = null, this._lastProgram = void 0, this._cachedDays = [], this._onModeChange = async (t) => {
      const e = t.target.value;
      if (!(!e || e === this.config.global_mode))
        try {
          await this.ws.setGlobalMode(e), await this.panel.reloadConfig(), this.panel.showToast("Saved", !1);
        } catch {
          this.panel.showToast("Save failed", !0);
        }
    }, this._tempSaveTimer = null, this._onTemperatureInput = () => {
      this._tempSaveTimer !== null && clearTimeout(this._tempSaveTimer), this._tempSaveTimer = setTimeout(() => {
        this._saveTemperatures();
      }, 600);
    }, this._onTemperatureBlur = () => {
      this._tempSaveTimer !== null && (clearTimeout(this._tempSaveTimer), this._tempSaveTimer = null), this._saveTemperatures();
    }, this._onPeriodsChanged = async (t) => {
      const { dayIndex: e, periods: o } = t.detail, s = { ...this.config.global_time_program }, r = At(e);
      s[r] = o;
      try {
        await this.ws.setTimeProgram(s), await this.panel.reloadConfig(), this.panel.showToast("Saved", !1);
      } catch {
        this.panel.showToast("Save failed — retrying...", !0);
      }
      t.stopPropagation();
    }, this._onResetTemperatures = async () => {
      try {
        await this.ws.setPeriodTemperatures(Ie), await this.panel.reloadConfig(), this.panel.showToast("Reset to defaults", !1);
      } catch {
        this.panel.showToast("Reset failed — retrying...", !0);
      }
    }, this._onResetConfiguration = async () => {
      try {
        await this.ws.setGlobalMode(Ne), await this.ws.setTimeProgram(He), await this.panel.reloadConfig(), this.panel.showToast("Reset to defaults", !1);
      } catch {
        this.panel.showToast("Reset failed — retrying...", !0);
      }
    };
  }
  get _days() {
    var e;
    const t = (e = this.config) == null ? void 0 : e.global_time_program;
    return t !== this._lastProgram && (this._lastProgram = t, this._cachedDays = Tt(t)), this._cachedDays;
  }
  async _saveTemperatures() {
    const t = this.shadowRoot;
    if (!t) return;
    const e = (s) => {
      const r = t.querySelector(`#temp-${s}`);
      return r ? parseFloat(r.value) : this.config.period_temperatures[s] ?? 0;
    }, o = {
      frost_protection: e("frost_protection"),
      reduced: e("reduced"),
      normal: e("normal"),
      comfort: e("comfort")
    };
    try {
      await this.ws.setPeriodTemperatures(o), await this.panel.reloadConfig(), this.panel.showToast("Saved", !1);
    } catch {
      this.panel.showToast("Save failed — retrying...", !0);
    }
  }
  // -----------------------------------------------------------------------
  // Render helpers
  // -----------------------------------------------------------------------
  _renderStatusCard() {
    var r;
    const t = this.status, e = De[(t == null ? void 0 : t.global_mode) ?? this.config.global_mode] ?? (t == null ? void 0 : t.global_mode) ?? this.config.global_mode;
    let o = "No active period";
    t != null && t.active_period && (o = t.active_period);
    let s = l`<span class="status-value">No one home</span>`;
    return (r = t == null ? void 0 : t.present_persons) != null && r.length && (s = l`
        <span class="status-value">
          ${t.present_persons.map(
      (i, a) => {
        var c;
        return l`
              <span class="person-dot"></span>${i}${a < (((c = t == null ? void 0 : t.present_persons) == null ? void 0 : c.length) ?? 1) - 1 ? ", " : ""}
            `;
      }
    )}
        </span>
      `), l`
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
  _renderTemperaturesCard() {
    const t = this.config.period_temperatures, e = (o, s, r) => l`
      <div class="temp-field">
        <label class="temp-label" for="temp-${o}">${s}</label>
        <div class="temp-input-row">
          <input
            id="temp-${o}"
            class="temp-input"
            type="number"
            step="0.5"
            min="5"
            max="30"
            data-key="${o}"
            .value=${String(t[o] ?? r)}
            @input=${this._onTemperatureInput}
            @blur=${this._onTemperatureBlur}
            @keydown=${(i) => {
      i.key === "Enter" && i.target.blur();
    }}
          />
          <span class="temp-suffix">°C</span>
        </div>
      </div>
    `;
    return l`
      <ha-card>
        <div class="card-header">Temperatures</div>
        <div class="card-content">
          <div class="temp-fields">
            ${e("frost_protection", "Frost protection", 7)}
            ${e("reduced", "Reduced", 18)}
            ${e("normal", "Normal", 20)}
            ${e("comfort", "Comfort", 22)}
          </div>
          <button class="reset-btn" @click=${this._onResetTemperatures}>Reset to default</button>
        </div>
      </ha-card>
    `;
  }
  _renderConfigCard() {
    return l`
      <ha-card>
        <div class="card-header">Configuration</div>
        <div class="card-content">

          <div class="select-wrapper">
            <label class="select-label">Global mode</label>
            <select class="mode-select" @change=${this._onModeChange}>
              <option value=${yt} ?selected=${this.config.global_mode === yt}>Off</option>
              <option value=${xt} ?selected=${this.config.global_mode === xt}>Time program</option>
              <option value=${$t} ?selected=${this.config.global_mode === $t}>Time program &amp; presences</option>
            </select>
          </div>

          <!-- Global time program editor -->
          <div class="section-divider">Global time program</div>
          <div class="time-program-section">
            <climate-manager-time-bar
              mode="schedule"
              .days=${this._days}
              @periods-changed=${this._onPeriodsChanged}
            ></climate-manager-time-bar>
          </div>

          <button class="reset-btn" @click=${this._onResetConfiguration}>Reset to default</button>
        </div>
      </ha-card>
    `;
  }
  render() {
    return l`
      ${this._renderStatusCard()}
      ${this._renderTemperaturesCard()}
      ${this._renderConfigCard()}
    `;
  }
};
Rt.styles = E`
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

    /* ---- Temperatures card ---- */
    .temp-fields {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
      margin-bottom: 16px;
    }

    .temp-field {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .temp-label {
      display: block;
      font-size: 12px;
      color: var(--secondary-text-color);
    }

    .temp-input-row {
      display: flex;
      align-items: center;
      gap: 4px;
    }

    .temp-input {
      width: 100%;
      padding: 8px 10px;
      font-size: 15px;
      font-family: inherit;
      color: var(--primary-text-color);
      background-color: var(--card-background-color, var(--secondary-background-color));
      border: 1px solid var(--divider-color);
      border-radius: 4px;
      outline: none;
      box-sizing: border-box;
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

    /* ---- Config card ---- */
    .time-program-section {
      margin-top: 16px;
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

    /* Reset button */
    .reset-btn {
      margin-top: 16px;
      padding: 8px 16px;
      font-size: 14px;
      font-family: inherit;
      color: var(--primary-color, #03a9f4);
      background: none;
      border: 1px solid var(--primary-color, #03a9f4);
      border-radius: 4px;
      cursor: pointer;
    }

    .reset-btn:hover {
      background: rgba(3, 169, 244, 0.08);
    }
  `;
let B = Rt;
ut([
  m({ attribute: !1 })
], B.prototype, "config");
ut([
  m({ attribute: !1 })
], B.prototype, "status");
ut([
  m({ attribute: !1 })
], B.prototype, "ws");
ut([
  m({ attribute: !1 })
], B.prototype, "panel");
customElements.define("climate-manager-global-settings-tab", B);
var Ue = Object.defineProperty, J = (n, t, e, o) => {
  for (var s = void 0, r = n.length - 1, i; r >= 0; r--)
    (i = n[r]) && (s = i(t, e, s) || s);
  return s && Ue(t, e, s), s;
};
const Ot = class Ot extends w {
  constructor() {
    super(...arguments), this.items = [], this.placeholder = "Search…", this.triggerLabel = "Add", this.triggerIcon = "mdi:plus", this._open = !1, this._query = "", this._docClickHandler = null;
  }
  // -------------------------------------------------------------------------
  // Popup lifecycle
  // -------------------------------------------------------------------------
  _openPopup() {
    this._open = !0, this._query = "", this.updateComplete.then(() => {
      var e;
      const t = (e = this.shadowRoot) == null ? void 0 : e.querySelector(".search-input");
      t == null || t.focus();
    }), this._docClickHandler = (t) => {
      t.composedPath().includes(this) || this._closePopup();
    }, document.addEventListener("click", this._docClickHandler);
  }
  _closePopup() {
    this._open = !1, this._query = "", this._docClickHandler && (document.removeEventListener("click", this._docClickHandler), this._docClickHandler = null);
  }
  disconnectedCallback() {
    super.disconnectedCallback(), this._docClickHandler && (document.removeEventListener("click", this._docClickHandler), this._docClickHandler = null);
  }
  // -------------------------------------------------------------------------
  // Event handlers
  // -------------------------------------------------------------------------
  _onTriggerClick(t) {
    t.stopPropagation(), this._open ? this._closePopup() : this._openPopup();
  }
  _onSearchInput(t) {
    this._query = t.target.value;
  }
  _onKeydown(t) {
    t.key === "Escape" && (t.stopPropagation(), this._closePopup());
  }
  _onItemClick(t) {
    this.dispatchEvent(
      new CustomEvent("picked", {
        detail: { id: t.id },
        bubbles: !0,
        composed: !0
      })
    ), this._closePopup();
  }
  // -------------------------------------------------------------------------
  // Filtering
  // -------------------------------------------------------------------------
  _filteredItems() {
    if (!this._query) return this.items;
    const t = this._query.toLowerCase();
    return this.items.filter((e) => {
      var r;
      const o = e.label.toLowerCase().includes(t), s = ((r = e.secondary) == null ? void 0 : r.toLowerCase().includes(t)) ?? !1;
      return o || s;
    });
  }
  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------
  render() {
    const t = this._filteredItems();
    return l`
      <button
        class="trigger-btn"
        @click=${this._onTriggerClick}
        aria-expanded=${this._open}
        aria-haspopup="listbox"
      >
        <ha-icon icon=${this.triggerIcon}></ha-icon>
        ${this.triggerLabel}
      </button>

      ${this._open ? l`
          <div class="popup" @click=${(e) => e.stopPropagation()}>
            <div class="search-row">
              <input
                class="search-input"
                type="text"
                .value=${this._query}
                placeholder=${this.placeholder}
                @input=${this._onSearchInput}
                @keydown=${this._onKeydown}
                autocomplete="off"
                spellcheck="false"
              />
            </div>
            ${t.length > 0 ? l`
                <ul class="item-list" role="listbox">
                  ${t.map(
      (e) => l`
                      <li
                        class="item-row"
                        role="option"
                        @click=${() => this._onItemClick(e)}
                      >
                        ${e.icon ? l`<ha-icon class="item-icon" icon=${e.icon}></ha-icon>` : ""}
                        <div class="item-text">
                          <span class="item-label">${e.label}</span>
                          ${e.secondary ? l`<span class="item-secondary">${e.secondary}</span>` : ""}
                        </div>
                      </li>
                    `
    )}
                </ul>
              ` : l`<div class="empty-message">No results</div>`}
          </div>
        ` : ""}
    `;
  }
};
Ot.styles = E`
    :host {
      display: inline-block;
      position: relative;
    }

    /* Trigger button — matches .chip-add style in room-card.ts */
    .trigger-btn {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      padding: 4px 10px;
      border-radius: 16px;
      background: none;
      border: 1px solid var(--primary-color, #03a9f4);
      font-size: 13px;
      color: var(--primary-color, #03a9f4);
      cursor: pointer;
      font-family: inherit;
      outline-color: var(--primary-color);
    }

    .trigger-btn:hover {
      background: rgba(3, 169, 244, 0.08);
    }

    .trigger-btn ha-icon {
      --mdc-icon-size: 16px;
      width: 16px;
      height: 16px;
    }

    /* Popup container — positioned below trigger */
    .popup {
      position: absolute;
      top: 100%;
      left: 0;
      z-index: 999;
      min-width: 240px;
      max-width: 320px;
      margin-top: 4px;
      background: var(--card-background-color, #fff);
      border: 1px solid var(--divider-color, #e0e0e0);
      border-radius: 8px;
      box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
      overflow: hidden;
    }

    /* Search input row */
    .search-row {
      display: flex;
      align-items: center;
      padding: 8px 12px;
      border-bottom: 1px solid var(--divider-color, #e0e0e0);
    }

    .search-input {
      flex: 1;
      border: none;
      outline: none;
      font-size: 14px;
      font-family: inherit;
      color: var(--primary-text-color);
      background: transparent;
    }

    .search-input::placeholder {
      color: var(--secondary-text-color);
    }

    /* Item list */
    .item-list {
      list-style: none;
      margin: 0;
      padding: 4px 0;
      max-height: 240px;
      overflow-y: auto;
    }

    .item-row {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 8px 12px;
      cursor: pointer;
      transition: background 0.1s;
    }

    .item-row:hover {
      background: var(--secondary-background-color, #f5f5f5);
    }

    .item-icon {
      --mdc-icon-size: 18px;
      width: 18px;
      height: 18px;
      flex-shrink: 0;
      color: var(--secondary-text-color);
    }

    .item-text {
      display: flex;
      flex-direction: column;
      gap: 1px;
      min-width: 0;
    }

    .item-label {
      font-size: 14px;
      font-weight: 600;
      color: var(--primary-text-color);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .item-secondary {
      font-size: 12px;
      color: var(--secondary-text-color);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    /* Empty state */
    .empty-message {
      padding: 12px;
      font-size: 13px;
      color: var(--secondary-text-color);
      text-align: center;
    }
  `;
let A = Ot;
J([
  m({ type: Array })
], A.prototype, "items");
J([
  m({ type: String })
], A.prototype, "placeholder");
J([
  m({ type: String })
], A.prototype, "triggerLabel");
J([
  m({ type: String })
], A.prototype, "triggerIcon");
J([
  v()
], A.prototype, "_open");
J([
  v()
], A.prototype, "_query");
customElements.define("search-picker", A);
var je = Object.defineProperty, R = (n, t, e, o) => {
  for (var s = void 0, r = n.length - 1, i; r >= 0; r--)
    (i = n[r]) && (s = i(t, e, s) || s);
  return s && je(t, e, s), s;
};
const zt = class zt extends w {
  constructor() {
    super(...arguments), this.roomStatus = null, this._expanded = !1;
  }
  connectedCallback() {
    var t;
    super.connectedCallback(), this._expanded = ((t = this.config) == null ? void 0 : t.room_mode) === "custom";
  }
  // -----------------------------------------------------------------------
  // Person association handlers
  // -----------------------------------------------------------------------
  _getAssignedPersonIds() {
    var e;
    const t = ((e = this.panelConfig) == null ? void 0 : e.persons) ?? {};
    return Object.entries(t).filter(([, o]) => {
      var s;
      return (s = o.room_ids) == null ? void 0 : s.includes(this.roomId);
    }).map(([o]) => o);
  }
  _getAllPersonIds() {
    var o, s;
    const t = Object.keys(((o = this.hass) == null ? void 0 : o.states) ?? {}).filter(
      (r) => r.startsWith("person.")
    ), e = Object.keys(((s = this.panelConfig) == null ? void 0 : s.persons) ?? {});
    return [.../* @__PURE__ */ new Set([...t, ...e])];
  }
  _getPersonName(t) {
    var e, o, s;
    return ((s = (o = (e = this.hass) == null ? void 0 : e.states[t]) == null ? void 0 : o.attributes) == null ? void 0 : s.friendly_name) ?? t.replace(/^person\./, "").replace(/_/g, " ").replace(/\b\w/g, (r) => r.toUpperCase());
  }
  _getPersonPresenceState(t) {
    var o, s;
    const e = (s = (o = this.hass) == null ? void 0 : o.states[t]) == null ? void 0 : s.state;
    return e === "home" ? "Home" : e === "not_home" ? "Away" : e ? e.charAt(0).toUpperCase() + e.slice(1) : "—";
  }
  _onPersonPicked(t) {
    t.stopPropagation();
    const e = t.detail.id;
    e && this._onAddPerson(e);
  }
  async _onAddPerson(t) {
    var s, r, i;
    const e = [...((i = (r = (s = this.panelConfig) == null ? void 0 : s.persons) == null ? void 0 : r[t]) == null ? void 0 : i.room_ids) ?? []], o = e.includes(this.roomId) ? e : [...e, this.roomId];
    try {
      await this.ws.setPersonConfig(t, { room_ids: o }), await this.panel.reloadConfig(), this.panel.showToast("Saved", !1);
    } catch {
      this.panel.showToast("Save failed — retrying...", !0);
    }
  }
  async _onRemovePerson(t) {
    var s, r, i;
    const o = [...((i = (r = (s = this.panelConfig) == null ? void 0 : s.persons) == null ? void 0 : r[t]) == null ? void 0 : i.room_ids) ?? []].filter((a) => a !== this.roomId);
    try {
      await this.ws.setPersonConfig(t, { room_ids: o }), await this.panel.reloadConfig(), this.panel.showToast("Saved", !1);
    } catch {
      this.panel.showToast("Save failed — retrying...", !0);
    }
  }
  // -----------------------------------------------------------------------
  // Room mode handler (D-20)
  // -----------------------------------------------------------------------
  async _onRoomModeChange(t) {
    var s;
    const e = t.target.value;
    let o;
    e === "custom" && !((s = this.config) != null && s.time_program) ? o = {
      room_mode: "custom",
      time_program: JSON.parse(JSON.stringify(this.panelConfig.global_time_program))
    } : o = { room_mode: e };
    try {
      await this.ws.setRoomConfig(this.roomId, o), await this.panel.reloadConfig(), this.panel.showToast("Saved", !1);
    } catch {
      this.panel.showToast("Save failed — retrying...", !0);
    }
  }
  // -----------------------------------------------------------------------
  // Schedule override handlers
  // -----------------------------------------------------------------------
  async _onPeriodsChanged(t) {
    const { dayIndex: e, periods: o } = t.detail, r = { ...this.config.time_program ?? {
      mon: [],
      tue: [],
      wed: [],
      thu: [],
      fri: [],
      sat: [],
      sun: []
    } }, i = At(e);
    r[i] = o;
    try {
      await this.ws.setRoomConfig(this.roomId, { time_program: r }), await this.panel.reloadConfig(), this.panel.showToast("Saved", !1);
    } catch {
      this.panel.showToast("Save failed — retrying...", !0);
    }
    t.stopPropagation();
  }
  // -----------------------------------------------------------------------
  // Render helpers
  // -----------------------------------------------------------------------
  _renderHeaderStatus() {
    const t = this.roomStatus, e = (t == null ? void 0 : t.temperature) != null ? `${t.temperature}°C` : "—", o = (t == null ? void 0 : t.humidity) != null ? `${t.humidity}%` : "—", s = (t == null ? void 0 : t.active_period) ?? "—", r = this._getAssignedPersonIds().length;
    return l`
      <div class="card-header-status">
        <span class="status-item">
          <ha-icon icon="mdi:thermometer"></ha-icon>
          ${e}
        </span>
        <span class="status-item">
          <ha-icon icon="mdi:water-percent"></ha-icon>
          ${o}
        </span>
        <span class="status-item">
          <ha-icon icon="mdi:clock-outline"></ha-icon>
          ${s}
        </span>
        <span class="status-item">
          <ha-icon icon="mdi:account-group"></ha-icon>
          ${r}
        </span>
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
    return t.length === 0 ? l`
        <div class="no-trv-badge">
          <ha-icon icon="mdi:alert"></ha-icon>
          No climate entities
        </div>
      ` : l`
      <div class="trv-section">
        <div class="section-label">Climate entities</div>
        ${t.map((o) => {
      var r, i, a;
      const s = ((a = (i = (r = this.hass) == null ? void 0 : r.states[o]) == null ? void 0 : i.attributes) == null ? void 0 : a.friendly_name) ?? o;
      return l`
            <span class="trv-chip" @click=${() => this._openMoreInfo(o)}>
              <ha-icon icon="mdi:radiator"></ha-icon>
              ${s}
            </span>
          `;
    })}
      </div>
    `;
  }
  _renderPersonsSection() {
    const t = this._getAssignedPersonIds(), o = this._getAllPersonIds().filter(
      (r) => !t.includes(r)
    ), s = o.map((r) => ({
      id: r,
      label: this._getPersonName(r),
      secondary: this._getPersonPresenceState(r),
      icon: "mdi:account"
    }));
    return l`
      <div class="section-label">Associated persons</div>
      <div class="chips">
        ${t.map((r) => l`
          <span class="chip">
            <ha-icon icon="mdi:account"></ha-icon>
            ${this._getPersonName(r)}
            <button
              class="chip-remove"
              @click=${() => void this._onRemovePerson(r)}
            >×</button>
          </span>
        `)}
        ${o.length > 0 ? l`
            <search-picker
              .items=${s}
              triggerLabel="Add person"
              triggerIcon="mdi:plus"
              placeholder="Search persons…"
              @picked=${(r) => this._onPersonPicked(r)}
            ></search-picker>
          ` : ""}
      </div>
    `;
  }
  render() {
    var s;
    const t = ((s = this.config) == null ? void 0 : s.room_mode) ?? "global", e = t === "frost_protection" ? "frost" : t === "custom" ? "custom" : "global", o = t === "frost_protection" ? "Frost protection" : t === "custom" ? "Custom program" : "Global program";
    return l`
      <ha-card>
        <div class="card-header-row" @click=${() => {
      this._expanded = !this._expanded;
    }}>
          <div class="card-header-left">
            <div class="card-header-top">
              <span class="room-name">${this.roomName}</span>
              <span class="program-badge ${e}">${o}</span>
            </div>
            ${this._renderHeaderStatus()}
          </div>
          <ha-icon
            class="expand-icon ${this._expanded ? "expanded" : ""}"
            icon="mdi:chevron-down"
          ></ha-icon>
        </div>

        ${this._expanded ? l`
            <div class="card-content">
              ${this._renderTrvSection()}
              ${this._renderPersonsSection()}

              <!-- 3-way room mode selector (D-20) -->
              <div class="section-label">Mode</div>
              <div class="select-wrapper">
                <select
                  class="mode-select"
                  .value=${t}
                  @change=${this._onRoomModeChange}
                >
                  <option value="global" ?selected=${t === "global"}>Global program</option>
                  <option value="frost_protection" ?selected=${t === "frost_protection"}>Frost protection</option>
                  <option value="custom" ?selected=${t === "custom"}>Custom program</option>
                </select>
              </div>

              <!-- Inline time-bar (only in Custom mode) -->
              ${t === "custom" ? l`
                  <div class="time-bar-section">
                    <climate-manager-time-bar
                      mode="schedule"
                      .days=${Tt(this.config.time_program ?? void 0)}
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
zt.styles = E`
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
      flex-direction: column;
      gap: 4px;
      min-width: 0;
    }

    .card-header-top {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .room-name {
      font-size: 16px;
      font-weight: 600;
      color: var(--primary-text-color);
    }

    /* Always-visible 4-item status line in the card header (D-14d) */
    .card-header-status {
      display: flex;
      gap: 12px;
      font-size: 13px;
      color: var(--secondary-text-color);
    }

    .card-header-status .status-item {
      display: flex;
      align-items: center;
      gap: 3px;
    }

    .card-header-status .status-item ha-icon {
      width: 15px;
      height: 15px;
      --mdc-icon-size: 15px;
      flex-shrink: 0;
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

    .program-badge.frost {
      background: #1565C0;
      color: #fff;
    }

    .card-content {
      padding: 12px 16px 16px;
      border-top: 1px solid var(--divider-color, #e0e0e0);
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

    /* Person / room association chips */
    .chips {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 16px;
    }

    .chip {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 4px 10px;
      border-radius: 16px;
      background: var(--secondary-background-color, #f5f5f5);
      border: 1px solid var(--divider-color, #e0e0e0);
      font-size: 13px;
      color: var(--primary-text-color);
    }

    .chip ha-icon {
      --mdc-icon-size: 16px;
      width: 16px;
      height: 16px;
      flex-shrink: 0;
    }

    .chip-remove {
      background: none;
      border: none;
      padding: 0 0 0 2px;
      margin: 0;
      cursor: pointer;
      color: var(--secondary-text-color);
      font-size: 18px;
      line-height: 1;
      display: flex;
      align-items: center;
    }

    .chip-remove:hover {
      color: var(--error-color, #f44336);
    }

    .chip-add {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      padding: 4px 10px;
      border-radius: 16px;
      background: none;
      border: 1px solid var(--primary-color, #03a9f4);
      font-size: 13px;
      color: var(--primary-color, #03a9f4);
      cursor: pointer;
      font-family: inherit;
    }

    .chip-add:hover {
      background: rgba(3, 169, 244, 0.08);
    }

    .chip-add ha-icon {
      --mdc-icon-size: 16px;
      width: 16px;
      height: 16px;
    }

    /* 3-way room mode selector (D-20) */
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
let P = zt;
R([
  m({ type: String })
], P.prototype, "roomId");
R([
  m({ type: String })
], P.prototype, "roomName");
R([
  m({ attribute: !1 })
], P.prototype, "config");
R([
  m({ attribute: !1 })
], P.prototype, "roomStatus");
R([
  m({ attribute: !1 })
], P.prototype, "panelConfig");
R([
  m({ attribute: !1 })
], P.prototype, "ws");
R([
  m({ attribute: !1 })
], P.prototype, "panel");
R([
  m({ attribute: !1 })
], P.prototype, "hass");
R([
  v()
], P.prototype, "_expanded");
customElements.define("climate-manager-room-card", P);
var Le = Object.defineProperty, it = (n, t, e, o) => {
  for (var s = void 0, r = n.length - 1, i; r >= 0; r--)
    (i = n[r]) && (s = i(t, e, s) || s);
  return s && Le(t, e, s), s;
};
const Dt = class Dt extends w {
  constructor() {
    super(...arguments), this.status = null;
  }
  _getRoomStatus(t) {
    var e, o;
    return ((o = (e = this.status) == null ? void 0 : e.rooms_status) == null ? void 0 : o.find((s) => s.area_id === t)) ?? null;
  }
  render() {
    var p, h, _, b, y;
    const t = ((p = this.config) == null ? void 0 : p.rooms) ?? {}, e = ((h = this.status) == null ? void 0 : h.rooms_status) ?? [], o = /* @__PURE__ */ new Set([
      ...Object.keys(t),
      ...e.map((g) => g.area_id)
    ]);
    if (o.size === 0)
      return l`
        <div class="empty-state">
          No rooms discovered. Create areas in Home Assistant and assign climate entities.
        </div>
      `;
    const s = (g) => {
      var f, u, $;
      return (($ = (u = (f = this.status) == null ? void 0 : f.rooms_status) == null ? void 0 : u.find((S) => S.area_id === g)) == null ? void 0 : $.name) ?? g.replace(/_/g, " ").replace(/\b\w/g, (S) => S.toUpperCase());
    }, r = /* @__PURE__ */ new Map();
    for (const g of o) {
      const f = ((y = (b = (_ = this.hass) == null ? void 0 : _.areas) == null ? void 0 : b[g]) == null ? void 0 : y.floor_id) ?? null;
      r.has(f) || r.set(f, []), r.get(f).push(g);
    }
    for (const g of r.values())
      g.sort((f, u) => s(f).localeCompare(s(u)));
    const i = [...r.keys()].filter((g) => g !== null).sort(
      (g, f) => {
        var u, $, S, K, Ut, jt;
        return (((S = ($ = (u = this.hass) == null ? void 0 : u.floors) == null ? void 0 : $[f]) == null ? void 0 : S.level) ?? 0) - (((jt = (Ut = (K = this.hass) == null ? void 0 : K.floors) == null ? void 0 : Ut[g]) == null ? void 0 : jt.level) ?? 0);
      }
    ), a = r.get(null) ?? [], c = (g) => {
      const f = t[g] ?? {}, u = this._getRoomStatus(g), $ = s(g);
      return l`
        <climate-manager-room-card
          .roomId=${g}
          .roomName=${$}
          .config=${f}
          .roomStatus=${u}
          .panelConfig=${this.config}
          .ws=${this.ws}
          .panel=${this.panel}
          .hass=${this.hass}
        ></climate-manager-room-card>
      `;
    }, d = (g) => {
      var $, S;
      const f = (S = ($ = this.hass) == null ? void 0 : $.floors) == null ? void 0 : S[g];
      if (f != null && f.icon) return f.icon;
      const u = (f == null ? void 0 : f.level) ?? 0;
      return u === -1 ? "mdi:home-floor-negative-1" : u < 0 ? "mdi:home-floor-b" : u === 1 ? "mdi:home-floor-1" : u === 2 ? "mdi:home-floor-2" : u === 3 || u > 3 ? "mdi:home-floor-3" : "mdi:home-floor-0";
    };
    return l`
      ${i.map((g) => {
      var $, S, K;
      const f = ((K = (S = ($ = this.hass) == null ? void 0 : $.floors) == null ? void 0 : S[g]) == null ? void 0 : K.name) ?? g, u = r.get(g) ?? [];
      return l`
          <div class="floor-header">
            <ha-icon icon=${d(g)}></ha-icon>
            ${f}
          </div>
          ${u.map(c)}
        `;
    })}
      ${a.map(c)}
    `;
  }
};
Dt.styles = E`
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
let I = Dt;
it([
  m({ attribute: !1 })
], I.prototype, "config");
it([
  m({ attribute: !1 })
], I.prototype, "status");
it([
  m({ attribute: !1 })
], I.prototype, "ws");
it([
  m({ attribute: !1 })
], I.prototype, "panel");
it([
  m({ attribute: !1 })
], I.prototype, "hass");
customElements.define("climate-manager-rooms-tab", I);
var Be = Object.defineProperty, F = (n, t, e, o) => {
  for (var s = void 0, r = n.length - 1, i; r >= 0; r--)
    (i = n[r]) && (s = i(t, e, s) || s);
  return s && Be(t, e, s), s;
};
const X = "automatic", bt = "present", vt = "absent", It = class It extends w {
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
        await this.ws.setPersonConfig(this.personId, { mode: e }), await this.panel.reloadConfig(), this.panel.showToast("Saved", !1);
      } catch {
        this.panel.showToast("Save failed — retrying...", !0);
      }
  }
  async _onRoomToggle(t, e) {
    var r;
    const o = [...((r = this.config) == null ? void 0 : r.room_ids) ?? []], s = e ? o.includes(t) ? o : [...o, t] : o.filter((i) => i !== t);
    try {
      await this.ws.setPersonConfig(this.personId, { room_ids: s }), await this.panel.reloadConfig(), this.panel.showToast("Saved", !1);
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
    } }, i = At(e);
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
      case bt:
        return { cls: "present", text: "Present" };
      case vt:
        return { cls: "absent", text: "Absent" };
      default:
        return { cls: "automatic", text: "Automatic" };
    }
  }
  render() {
    var a, c, d;
    const { cls: t, text: e } = this._getBadgeInfo(), o = ((a = this.config) == null ? void 0 : a.mode) ?? X, s = o === X, r = ((c = this.config) == null ? void 0 : c.room_ids) ?? [], i = this.roomChoices.filter((p) => !r.includes(p.id));
    return l`
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

        ${this._expanded ? l`
            <div class="card-content">

              <!-- Presence mode selector -->
              <div class="section-label">Presence mode</div>
              <div class="select-wrapper">
                <select class="mode-select" @change=${this._onModeChange}>
                  <option value=${X} ?selected=${o === X}>Automatic</option>
                  <option value=${bt} ?selected=${o === bt}>Present</option>
                  <option value=${vt} ?selected=${o === vt}>Absent</option>
                </select>
              </div>

              <!-- Room associations as chips -->
              <div class="section-label">Room associations</div>
              <div class="chips">
                ${r.map((p) => {
      const h = this.roomChoices.find((_) => _.id === p);
      return h ? l`
                    <span class="chip">
                      <ha-icon icon="mdi:home-outline"></ha-icon>
                      ${h.name}
                      <button
                        class="chip-remove"
                        @click=${() => void this._onRoomToggle(p, !1)}
                      >×</button>
                    </span>
                  ` : "";
    })}
                ${i.length > 0 ? l`
                    <search-picker
                      .items=${i.map((p) => ({
      id: p.id,
      label: p.name,
      secondary: p.secondary,
      icon: "mdi:home-outline"
    }))}
                      triggerLabel="Add room"
                      triggerIcon="mdi:plus"
                      placeholder="Search rooms…"
                      @picked=${(p) => {
      const { id: h } = p.detail;
      this._onRoomToggle(h, !0);
    }}
                    ></search-picker>
                  ` : ""}
              </div>

              <!-- Presence schedule (only in Automatic mode) -->
              ${s ? l`
                  <div class="section-label">Presence schedule</div>
                  <div class="schedule-section">
                    <climate-manager-time-bar
                      mode="presence"
                      .days=${Tt((d = this.config) == null ? void 0 : d.schedule)}
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
It.styles = E`
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

    /* Chip UI for room associations */
    .chips {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 16px;
    }

    .chip {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 4px 10px;
      border-radius: 16px;
      background: var(--secondary-background-color, #f5f5f5);
      border: 1px solid var(--divider-color, #e0e0e0);
      font-size: 13px;
      color: var(--primary-text-color);
    }

    .chip ha-icon {
      --mdc-icon-size: 16px;
      width: 16px;
      height: 16px;
      flex-shrink: 0;
    }

    .chip-remove {
      background: none;
      border: none;
      padding: 0 0 0 2px;
      margin: 0;
      cursor: pointer;
      color: var(--secondary-text-color);
      font-size: 18px;
      line-height: 1;
      display: flex;
      align-items: center;
    }

    .chip-remove:hover {
      color: var(--error-color, #f44336);
    }

    .chip-add {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      padding: 4px 10px;
      border-radius: 16px;
      background: none;
      border: 1px solid var(--primary-color, #03a9f4);
      font-size: 13px;
      color: var(--primary-color, #03a9f4);
      cursor: pointer;
      font-family: inherit;
    }

    .chip-add:hover {
      background: rgba(3, 169, 244, 0.08);
    }

    .chip-add ha-icon {
      --mdc-icon-size: 16px;
      width: 16px;
      height: 16px;
    }

    /* Presence schedule */
    .schedule-section {
      margin-top: 12px;
    }
  `;
let T = It;
F([
  m({ type: String })
], T.prototype, "personId");
F([
  m({ type: String })
], T.prototype, "personName");
F([
  m({ attribute: !1 })
], T.prototype, "config");
F([
  m({ attribute: !1 })
], T.prototype, "roomChoices");
F([
  m({ attribute: !1 })
], T.prototype, "ws");
F([
  m({ attribute: !1 })
], T.prototype, "panel");
F([
  v()
], T.prototype, "_expanded");
customElements.define("climate-manager-person-card", T);
var Fe = Object.defineProperty, nt = (n, t, e, o) => {
  for (var s = void 0, r = n.length - 1, i; r >= 0; r--)
    (i = n[r]) && (s = i(t, e, s) || s);
  return s && Fe(t, e, s), s;
};
const Nt = class Nt extends w {
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
      var p, h, _, b, y, g, f;
      const a = ((p = e.find((u) => u.area_id === i)) == null ? void 0 : p.name) ?? i.replace(/_/g, " ").replace(/\b\w/g, (u) => u.toUpperCase()), c = ((b = (_ = (h = this.hass) == null ? void 0 : h.areas) == null ? void 0 : _[i]) == null ? void 0 : b.floor_id) ?? null, d = c ? ((f = (g = (y = this.hass) == null ? void 0 : y.floors) == null ? void 0 : g[c]) == null ? void 0 : f.name) ?? void 0 : void 0;
      return { id: i, name: a, secondary: d };
    });
  }
  /** Determine if a person config has any non-default setting (D-15). */
  _isNonDefault(t) {
    var i, a, c;
    const e = (a = (i = this.config) == null ? void 0 : i.persons) == null ? void 0 : a[t];
    if (!e) return !1;
    const o = e.mode != null && e.mode !== "automatic", s = (((c = e.room_ids) == null ? void 0 : c.length) ?? 0) > 0, r = e.schedule ? Object.values(e.schedule).some((d) => d.length > 0) : !1;
    return o || s || r;
  }
  render() {
    var r;
    const t = ((r = this.config) == null ? void 0 : r.persons) ?? {}, e = Object.keys(t);
    if (e.length === 0)
      return l`
        <div class="empty-state">
          No persons found. Add person entities in Home Assistant.
        </div>
      `;
    const o = [...e].sort((i, a) => {
      const c = this._isNonDefault(i), d = this._isNonDefault(a);
      return c && !d ? -1 : !c && d ? 1 : i.localeCompare(a);
    }), s = this._getRoomChoices();
    return l`
      ${o.map((i) => {
      const a = t[i] ?? {}, c = i.replace(/^person\./, "").replace(/_/g, " ").replace(/\b\w/g, (d) => d.toUpperCase());
      return l`
          <climate-manager-person-card
            .personId=${i}
            .personName=${c}
            .config=${a}
            .roomChoices=${s}
            .ws=${this.ws}
            .panel=${this.panel}
          ></climate-manager-person-card>
        `;
    })}
    `;
  }
};
Nt.styles = E`
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
let N = Nt;
nt([
  m({ attribute: !1 })
], N.prototype, "config");
nt([
  m({ attribute: !1 })
], N.prototype, "status");
nt([
  m({ attribute: !1 })
], N.prototype, "ws");
nt([
  m({ attribute: !1 })
], N.prototype, "panel");
nt([
  m({ attribute: !1 })
], N.prototype, "hass");
customElements.define("climate-manager-persons-tab", N);
var qe = Object.defineProperty, O = (n, t, e, o) => {
  for (var s = void 0, r = n.length - 1, i; r >= 0; r--)
    (i = n[r]) && (s = i(t, e, s) || s);
  return s && qe(t, e, s), s;
};
const Ht = class Ht extends w {
  constructor() {
    super(...arguments), this.narrow = !1, this.panel = null, this._config = null, this._status = null, this._activeTab = "global", this._unsubStatus = null, this._wsError = !1, this._ws = null;
  }
  connectedCallback() {
    super.connectedCallback(), this._ws = new at(this.hass), this._loadConfig(), this._loadStatus(), this._subscribeStatus();
  }
  disconnectedCallback() {
    super.disconnectedCallback(), this._unsubStatus && (this._unsubStatus.then((t) => t()).catch(() => {
    }), this._unsubStatus = null);
  }
  async _loadConfig() {
    this._ws || (this._ws = new at(this.hass));
    try {
      this._config = await this._ws.getConfig();
    } catch {
      this._wsError = !0;
    }
  }
  async _loadStatus() {
    this._ws || (this._ws = new at(this.hass));
    try {
      this._status = await this._ws.getStatus();
    } catch {
    }
  }
  _subscribeStatus() {
    this._ws || (this._ws = new at(this.hass)), this._unsubStatus = this._ws.subscribeStatus((t) => {
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
    await Promise.all([this._loadConfig(), this._loadStatus()]);
  }
  _setTab(t) {
    this._activeTab = t;
  }
  render() {
    return this._config ? l`
      <div class="panel-header">Climate Manager</div>

      ${this._wsError ? l`<div class="error-banner">Connection lost. Reconnecting…</div>` : ""}

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
    ` : l`
        <div class="panel-header">Climate Manager</div>
        ${this._wsError ? l`<div class="error-banner">Connection lost. Reconnecting…</div>` : ""}
        <div class="loading">
          <ha-circular-progress active></ha-circular-progress>
        </div>
        <climate-manager-toast></climate-manager-toast>
      `;
  }
  _renderTabContent() {
    switch (this._activeTab) {
      case "global":
        return l`<climate-manager-global-settings-tab
          .config=${this._config}
          .status=${this._status}
          .ws=${this._ws}
          .panel=${this}
        ></climate-manager-global-settings-tab>`;
      case "rooms":
        return l`<climate-manager-rooms-tab
          .config=${this._config}
          .status=${this._status}
          .ws=${this._ws}
          .panel=${this}
          .hass=${this.hass}
        ></climate-manager-rooms-tab>`;
      case "persons":
        return l`<climate-manager-persons-tab
          .config=${this._config}
          .status=${this._status}
          .ws=${this._ws}
          .panel=${this}
          .hass=${this.hass}
        ></climate-manager-persons-tab>`;
      default:
        return l``;
    }
  }
};
Ht.styles = E`
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
let k = Ht;
O([
  m({ attribute: !1 })
], k.prototype, "hass");
O([
  m({ type: Boolean })
], k.prototype, "narrow");
O([
  m({ attribute: !1 })
], k.prototype, "panel");
O([
  v()
], k.prototype, "_config");
O([
  v()
], k.prototype, "_status");
O([
  v()
], k.prototype, "_activeTab");
O([
  v()
], k.prototype, "_unsubStatus");
O([
  v()
], k.prototype, "_wsError");
O([
  ke("climate-manager-toast")
], k.prototype, "_toast");
customElements.define("climate-manager-panel", k);
export {
  k as ClimateManagerPanel
};
