/**
 * @license
 * Copyright 2019 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const he = globalThis, Te = he.ShadowRoot && (he.ShadyCSS === void 0 || he.ShadyCSS.nativeShadow) && "adoptedStyleSheets" in Document.prototype && "replace" in CSSStyleSheet.prototype, Me = Symbol(), Ze = /* @__PURE__ */ new WeakMap();
let it = class {
  constructor(e, t, o) {
    if (this._$cssResult$ = !0, o !== Me) throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");
    this.cssText = e, this.t = t;
  }
  get styleSheet() {
    let e = this.o;
    const t = this.t;
    if (Te && e === void 0) {
      const o = t !== void 0 && t.length === 1;
      o && (e = Ze.get(t)), e === void 0 && ((this.o = e = new CSSStyleSheet()).replaceSync(this.cssText), o && Ze.set(t, e));
    }
    return e;
  }
  toString() {
    return this.cssText;
  }
};
const at = (a) => new it(typeof a == "string" ? a : a + "", void 0, Me), A = (a, ...e) => {
  const t = a.length === 1 ? a[0] : e.reduce((o, s, r) => o + ((i) => {
    if (i._$cssResult$ === !0) return i.cssText;
    if (typeof i == "number") return i;
    throw Error("Value passed to 'css' function must be a 'css' function result: " + i + ". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.");
  })(s) + a[r + 1], a[0]);
  return new it(t, a, Me);
}, ht = (a, e) => {
  if (Te) a.adoptedStyleSheets = e.map((t) => t instanceof CSSStyleSheet ? t : t.styleSheet);
  else for (const t of e) {
    const o = document.createElement("style"), s = he.litNonce;
    s !== void 0 && o.setAttribute("nonce", s), o.textContent = t.cssText, a.appendChild(o);
  }
}, Xe = Te ? (a) => a : (a) => a instanceof CSSStyleSheet ? ((e) => {
  let t = "";
  for (const o of e.cssRules) t += o.cssText;
  return at(t);
})(a) : a;
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const { is: ut, defineProperty: mt, getOwnPropertyDescriptor: gt, getOwnPropertyNames: ft, getOwnPropertySymbols: _t, getPrototypeOf: bt } = Object, H = globalThis, We = H.trustedTypes, vt = We ? We.emptyScript : "", ve = H.reactiveElementPolyfillSupport, se = (a, e) => a, me = { toAttribute(a, e) {
  switch (e) {
    case Boolean:
      a = a ? vt : null;
      break;
    case Object:
    case Array:
      a = a == null ? a : JSON.stringify(a);
  }
  return a;
}, fromAttribute(a, e) {
  let t = a;
  switch (e) {
    case Boolean:
      t = a !== null;
      break;
    case Number:
      t = a === null ? null : Number(a);
      break;
    case Object:
    case Array:
      try {
        t = JSON.parse(a);
      } catch {
        t = null;
      }
  }
  return t;
} }, Ae = (a, e) => !ut(a, e), Ye = { attribute: !0, type: String, converter: me, reflect: !1, useDefault: !1, hasChanged: Ae };
Symbol.metadata ?? (Symbol.metadata = Symbol("metadata")), H.litPropertyMetadata ?? (H.litPropertyMetadata = /* @__PURE__ */ new WeakMap());
let W = class extends HTMLElement {
  static addInitializer(e) {
    this._$Ei(), (this.l ?? (this.l = [])).push(e);
  }
  static get observedAttributes() {
    return this.finalize(), this._$Eh && [...this._$Eh.keys()];
  }
  static createProperty(e, t = Ye) {
    if (t.state && (t.attribute = !1), this._$Ei(), this.prototype.hasOwnProperty(e) && ((t = Object.create(t)).wrapped = !0), this.elementProperties.set(e, t), !t.noAccessor) {
      const o = Symbol(), s = this.getPropertyDescriptor(e, o, t);
      s !== void 0 && mt(this.prototype, e, s);
    }
  }
  static getPropertyDescriptor(e, t, o) {
    const { get: s, set: r } = gt(this.prototype, e) ?? { get() {
      return this[t];
    }, set(i) {
      this[t] = i;
    } };
    return { get: s, set(i) {
      const n = s == null ? void 0 : s.call(this);
      r == null || r.call(this, i), this.requestUpdate(e, n, o);
    }, configurable: !0, enumerable: !0 };
  }
  static getPropertyOptions(e) {
    return this.elementProperties.get(e) ?? Ye;
  }
  static _$Ei() {
    if (this.hasOwnProperty(se("elementProperties"))) return;
    const e = bt(this);
    e.finalize(), e.l !== void 0 && (this.l = [...e.l]), this.elementProperties = new Map(e.elementProperties);
  }
  static finalize() {
    if (this.hasOwnProperty(se("finalized"))) return;
    if (this.finalized = !0, this._$Ei(), this.hasOwnProperty(se("properties"))) {
      const t = this.properties, o = [...ft(t), ..._t(t)];
      for (const s of o) this.createProperty(s, t[s]);
    }
    const e = this[Symbol.metadata];
    if (e !== null) {
      const t = litPropertyMetadata.get(e);
      if (t !== void 0) for (const [o, s] of t) this.elementProperties.set(o, s);
    }
    this._$Eh = /* @__PURE__ */ new Map();
    for (const [t, o] of this.elementProperties) {
      const s = this._$Eu(t, o);
      s !== void 0 && this._$Eh.set(s, t);
    }
    this.elementStyles = this.finalizeStyles(this.styles);
  }
  static finalizeStyles(e) {
    const t = [];
    if (Array.isArray(e)) {
      const o = new Set(e.flat(1 / 0).reverse());
      for (const s of o) t.unshift(Xe(s));
    } else e !== void 0 && t.push(Xe(e));
    return t;
  }
  static _$Eu(e, t) {
    const o = t.attribute;
    return o === !1 ? void 0 : typeof o == "string" ? o : typeof e == "string" ? e.toLowerCase() : void 0;
  }
  constructor() {
    super(), this._$Ep = void 0, this.isUpdatePending = !1, this.hasUpdated = !1, this._$Em = null, this._$Ev();
  }
  _$Ev() {
    var e;
    this._$ES = new Promise((t) => this.enableUpdating = t), this._$AL = /* @__PURE__ */ new Map(), this._$E_(), this.requestUpdate(), (e = this.constructor.l) == null || e.forEach((t) => t(this));
  }
  addController(e) {
    var t;
    (this._$EO ?? (this._$EO = /* @__PURE__ */ new Set())).add(e), this.renderRoot !== void 0 && this.isConnected && ((t = e.hostConnected) == null || t.call(e));
  }
  removeController(e) {
    var t;
    (t = this._$EO) == null || t.delete(e);
  }
  _$E_() {
    const e = /* @__PURE__ */ new Map(), t = this.constructor.elementProperties;
    for (const o of t.keys()) this.hasOwnProperty(o) && (e.set(o, this[o]), delete this[o]);
    e.size > 0 && (this._$Ep = e);
  }
  createRenderRoot() {
    const e = this.shadowRoot ?? this.attachShadow(this.constructor.shadowRootOptions);
    return ht(e, this.constructor.elementStyles), e;
  }
  connectedCallback() {
    var e;
    this.renderRoot ?? (this.renderRoot = this.createRenderRoot()), this.enableUpdating(!0), (e = this._$EO) == null || e.forEach((t) => {
      var o;
      return (o = t.hostConnected) == null ? void 0 : o.call(t);
    });
  }
  enableUpdating(e) {
  }
  disconnectedCallback() {
    var e;
    (e = this._$EO) == null || e.forEach((t) => {
      var o;
      return (o = t.hostDisconnected) == null ? void 0 : o.call(t);
    });
  }
  attributeChangedCallback(e, t, o) {
    this._$AK(e, o);
  }
  _$ET(e, t) {
    var r;
    const o = this.constructor.elementProperties.get(e), s = this.constructor._$Eu(e, o);
    if (s !== void 0 && o.reflect === !0) {
      const i = (((r = o.converter) == null ? void 0 : r.toAttribute) !== void 0 ? o.converter : me).toAttribute(t, o.type);
      this._$Em = e, i == null ? this.removeAttribute(s) : this.setAttribute(s, i), this._$Em = null;
    }
  }
  _$AK(e, t) {
    var r, i;
    const o = this.constructor, s = o._$Eh.get(e);
    if (s !== void 0 && this._$Em !== s) {
      const n = o.getPropertyOptions(s), c = typeof n.converter == "function" ? { fromAttribute: n.converter } : ((r = n.converter) == null ? void 0 : r.fromAttribute) !== void 0 ? n.converter : me;
      this._$Em = s;
      const d = c.fromAttribute(t, n.type);
      this[s] = d ?? ((i = this._$Ej) == null ? void 0 : i.get(s)) ?? d, this._$Em = null;
    }
  }
  requestUpdate(e, t, o, s = !1, r) {
    var i;
    if (e !== void 0) {
      const n = this.constructor;
      if (s === !1 && (r = this[e]), o ?? (o = n.getPropertyOptions(e)), !((o.hasChanged ?? Ae)(r, t) || o.useDefault && o.reflect && r === ((i = this._$Ej) == null ? void 0 : i.get(e)) && !this.hasAttribute(n._$Eu(e, o)))) return;
      this.C(e, t, o);
    }
    this.isUpdatePending === !1 && (this._$ES = this._$EP());
  }
  C(e, t, { useDefault: o, reflect: s, wrapped: r }, i) {
    o && !(this._$Ej ?? (this._$Ej = /* @__PURE__ */ new Map())).has(e) && (this._$Ej.set(e, i ?? t ?? this[e]), r !== !0 || i !== void 0) || (this._$AL.has(e) || (this.hasUpdated || o || (t = void 0), this._$AL.set(e, t)), s === !0 && this._$Em !== e && (this._$Eq ?? (this._$Eq = /* @__PURE__ */ new Set())).add(e));
  }
  async _$EP() {
    this.isUpdatePending = !0;
    try {
      await this._$ES;
    } catch (t) {
      Promise.reject(t);
    }
    const e = this.scheduleUpdate();
    return e != null && await e, !this.isUpdatePending;
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
        const { wrapped: n } = i, c = this[r];
        n !== !0 || this._$AL.has(r) || c === void 0 || this.C(r, void 0, i, c);
      }
    }
    let e = !1;
    const t = this._$AL;
    try {
      e = this.shouldUpdate(t), e ? (this.willUpdate(t), (o = this._$EO) == null || o.forEach((s) => {
        var r;
        return (r = s.hostUpdate) == null ? void 0 : r.call(s);
      }), this.update(t)) : this._$EM();
    } catch (s) {
      throw e = !1, this._$EM(), s;
    }
    e && this._$AE(t);
  }
  willUpdate(e) {
  }
  _$AE(e) {
    var t;
    (t = this._$EO) == null || t.forEach((o) => {
      var s;
      return (s = o.hostUpdated) == null ? void 0 : s.call(o);
    }), this.hasUpdated || (this.hasUpdated = !0, this.firstUpdated(e)), this.updated(e);
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
  shouldUpdate(e) {
    return !0;
  }
  update(e) {
    this._$Eq && (this._$Eq = this._$Eq.forEach((t) => this._$ET(t, this[t]))), this._$EM();
  }
  updated(e) {
  }
  firstUpdated(e) {
  }
};
W.elementStyles = [], W.shadowRootOptions = { mode: "open" }, W[se("elementProperties")] = /* @__PURE__ */ new Map(), W[se("finalized")] = /* @__PURE__ */ new Map(), ve == null || ve({ ReactiveElement: W }), (H.reactiveElementVersions ?? (H.reactiveElementVersions = [])).push("2.1.2");
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const oe = globalThis, Ge = (a) => a, ge = oe.trustedTypes, Je = ge ? ge.createPolicy("lit-html", { createHTML: (a) => a }) : void 0, nt = "$lit$", N = `lit$${Math.random().toFixed(9).slice(2)}$`, ct = "?" + N, yt = `<${ct}>`, Z = document, re = () => Z.createComment(""), ie = (a) => a === null || typeof a != "object" && typeof a != "function", ze = Array.isArray, xt = (a) => ze(a) || typeof (a == null ? void 0 : a[Symbol.iterator]) == "function", ye = `[ 	
\f\r]`, ee = /<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g, Ke = /-->/g, Qe = />/g, F = RegExp(`>|${ye}(?:([^\\s"'>=/]+)(${ye}*=${ye}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`, "g"), et = /'/g, tt = /"/g, lt = /^(?:script|style|textarea|title)$/i, $t = (a) => (e, ...t) => ({ _$litType$: a, strings: e, values: t }), l = $t(1), Y = Symbol.for("lit-noChange"), x = Symbol.for("lit-nothing"), st = /* @__PURE__ */ new WeakMap(), q = Z.createTreeWalker(Z, 129);
function dt(a, e) {
  if (!ze(a) || !a.hasOwnProperty("raw")) throw Error("invalid template strings array");
  return Je !== void 0 ? Je.createHTML(e) : e;
}
const wt = (a, e) => {
  const t = a.length - 1, o = [];
  let s, r = e === 2 ? "<svg>" : e === 3 ? "<math>" : "", i = ee;
  for (let n = 0; n < t; n++) {
    const c = a[n];
    let d, h, p = -1, _ = 0;
    for (; _ < c.length && (i.lastIndex = _, h = i.exec(c), h !== null); ) _ = i.lastIndex, i === ee ? h[1] === "!--" ? i = Ke : h[1] !== void 0 ? i = Qe : h[2] !== void 0 ? (lt.test(h[2]) && (s = RegExp("</" + h[2], "g")), i = F) : h[3] !== void 0 && (i = F) : i === F ? h[0] === ">" ? (i = s ?? ee, p = -1) : h[1] === void 0 ? p = -2 : (p = i.lastIndex - h[2].length, d = h[1], i = h[3] === void 0 ? F : h[3] === '"' ? tt : et) : i === tt || i === et ? i = F : i === Ke || i === Qe ? i = ee : (i = F, s = void 0);
    const b = i === F && a[n + 1].startsWith("/>") ? " " : "";
    r += i === ee ? c + yt : p >= 0 ? (o.push(d), c.slice(0, p) + nt + c.slice(p) + N + b) : c + N + (p === -2 ? n : b);
  }
  return [dt(a, r + (a[t] || "<?>") + (e === 2 ? "</svg>" : e === 3 ? "</math>" : "")), o];
};
class ae {
  constructor({ strings: e, _$litType$: t }, o) {
    let s;
    this.parts = [];
    let r = 0, i = 0;
    const n = e.length - 1, c = this.parts, [d, h] = wt(e, t);
    if (this.el = ae.createElement(d, o), q.currentNode = this.el.content, t === 2 || t === 3) {
      const p = this.el.content.firstChild;
      p.replaceWith(...p.childNodes);
    }
    for (; (s = q.nextNode()) !== null && c.length < n; ) {
      if (s.nodeType === 1) {
        if (s.hasAttributes()) for (const p of s.getAttributeNames()) if (p.endsWith(nt)) {
          const _ = h[i++], b = s.getAttribute(p).split(N), y = /([.?@])?(.*)/.exec(_);
          c.push({ type: 1, index: r, name: y[2], strings: b, ctor: y[1] === "." ? kt : y[1] === "?" ? St : y[1] === "@" ? Pt : fe }), s.removeAttribute(p);
        } else p.startsWith(N) && (c.push({ type: 6, index: r }), s.removeAttribute(p));
        if (lt.test(s.tagName)) {
          const p = s.textContent.split(N), _ = p.length - 1;
          if (_ > 0) {
            s.textContent = ge ? ge.emptyScript : "";
            for (let b = 0; b < _; b++) s.append(p[b], re()), q.nextNode(), c.push({ type: 2, index: ++r });
            s.append(p[_], re());
          }
        }
      } else if (s.nodeType === 8) if (s.data === ct) c.push({ type: 2, index: r });
      else {
        let p = -1;
        for (; (p = s.data.indexOf(N, p + 1)) !== -1; ) c.push({ type: 7, index: r }), p += N.length - 1;
      }
      r++;
    }
  }
  static createElement(e, t) {
    const o = Z.createElement("template");
    return o.innerHTML = e, o;
  }
}
function G(a, e, t = a, o) {
  var i, n;
  if (e === Y) return e;
  let s = o !== void 0 ? (i = t._$Co) == null ? void 0 : i[o] : t._$Cl;
  const r = ie(e) ? void 0 : e._$litDirective$;
  return (s == null ? void 0 : s.constructor) !== r && ((n = s == null ? void 0 : s._$AO) == null || n.call(s, !1), r === void 0 ? s = void 0 : (s = new r(a), s._$AT(a, t, o)), o !== void 0 ? (t._$Co ?? (t._$Co = []))[o] = s : t._$Cl = s), s !== void 0 && (e = G(a, s._$AS(a, e.values), s, o)), e;
}
class Ct {
  constructor(e, t) {
    this._$AV = [], this._$AN = void 0, this._$AD = e, this._$AM = t;
  }
  get parentNode() {
    return this._$AM.parentNode;
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  u(e) {
    const { el: { content: t }, parts: o } = this._$AD, s = ((e == null ? void 0 : e.creationScope) ?? Z).importNode(t, !0);
    q.currentNode = s;
    let r = q.nextNode(), i = 0, n = 0, c = o[0];
    for (; c !== void 0; ) {
      if (i === c.index) {
        let d;
        c.type === 2 ? d = new ne(r, r.nextSibling, this, e) : c.type === 1 ? d = new c.ctor(r, c.name, c.strings, this, e) : c.type === 6 && (d = new Tt(r, this, e)), this._$AV.push(d), c = o[++n];
      }
      i !== (c == null ? void 0 : c.index) && (r = q.nextNode(), i++);
    }
    return q.currentNode = Z, s;
  }
  p(e) {
    let t = 0;
    for (const o of this._$AV) o !== void 0 && (o.strings !== void 0 ? (o._$AI(e, o, t), t += o.strings.length - 2) : o._$AI(e[t])), t++;
  }
}
class ne {
  get _$AU() {
    var e;
    return ((e = this._$AM) == null ? void 0 : e._$AU) ?? this._$Cv;
  }
  constructor(e, t, o, s) {
    this.type = 2, this._$AH = x, this._$AN = void 0, this._$AA = e, this._$AB = t, this._$AM = o, this.options = s, this._$Cv = (s == null ? void 0 : s.isConnected) ?? !0;
  }
  get parentNode() {
    let e = this._$AA.parentNode;
    const t = this._$AM;
    return t !== void 0 && (e == null ? void 0 : e.nodeType) === 11 && (e = t.parentNode), e;
  }
  get startNode() {
    return this._$AA;
  }
  get endNode() {
    return this._$AB;
  }
  _$AI(e, t = this) {
    e = G(this, e, t), ie(e) ? e === x || e == null || e === "" ? (this._$AH !== x && this._$AR(), this._$AH = x) : e !== this._$AH && e !== Y && this._(e) : e._$litType$ !== void 0 ? this.$(e) : e.nodeType !== void 0 ? this.T(e) : xt(e) ? this.k(e) : this._(e);
  }
  O(e) {
    return this._$AA.parentNode.insertBefore(e, this._$AB);
  }
  T(e) {
    this._$AH !== e && (this._$AR(), this._$AH = this.O(e));
  }
  _(e) {
    this._$AH !== x && ie(this._$AH) ? this._$AA.nextSibling.data = e : this.T(Z.createTextNode(e)), this._$AH = e;
  }
  $(e) {
    var r;
    const { values: t, _$litType$: o } = e, s = typeof o == "number" ? this._$AC(e) : (o.el === void 0 && (o.el = ae.createElement(dt(o.h, o.h[0]), this.options)), o);
    if (((r = this._$AH) == null ? void 0 : r._$AD) === s) this._$AH.p(t);
    else {
      const i = new Ct(s, this), n = i.u(this.options);
      i.p(t), this.T(n), this._$AH = i;
    }
  }
  _$AC(e) {
    let t = st.get(e.strings);
    return t === void 0 && st.set(e.strings, t = new ae(e)), t;
  }
  k(e) {
    ze(this._$AH) || (this._$AH = [], this._$AR());
    const t = this._$AH;
    let o, s = 0;
    for (const r of e) s === t.length ? t.push(o = new ne(this.O(re()), this.O(re()), this, this.options)) : o = t[s], o._$AI(r), s++;
    s < t.length && (this._$AR(o && o._$AB.nextSibling, s), t.length = s);
  }
  _$AR(e = this._$AA.nextSibling, t) {
    var o;
    for ((o = this._$AP) == null ? void 0 : o.call(this, !1, !0, t); e !== this._$AB; ) {
      const s = Ge(e).nextSibling;
      Ge(e).remove(), e = s;
    }
  }
  setConnected(e) {
    var t;
    this._$AM === void 0 && (this._$Cv = e, (t = this._$AP) == null || t.call(this, e));
  }
}
class fe {
  get tagName() {
    return this.element.tagName;
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  constructor(e, t, o, s, r) {
    this.type = 1, this._$AH = x, this._$AN = void 0, this.element = e, this.name = t, this._$AM = s, this.options = r, o.length > 2 || o[0] !== "" || o[1] !== "" ? (this._$AH = Array(o.length - 1).fill(new String()), this.strings = o) : this._$AH = x;
  }
  _$AI(e, t = this, o, s) {
    const r = this.strings;
    let i = !1;
    if (r === void 0) e = G(this, e, t, 0), i = !ie(e) || e !== this._$AH && e !== Y, i && (this._$AH = e);
    else {
      const n = e;
      let c, d;
      for (e = r[0], c = 0; c < r.length - 1; c++) d = G(this, n[o + c], t, c), d === Y && (d = this._$AH[c]), i || (i = !ie(d) || d !== this._$AH[c]), d === x ? e = x : e !== x && (e += (d ?? "") + r[c + 1]), this._$AH[c] = d;
    }
    i && !s && this.j(e);
  }
  j(e) {
    e === x ? this.element.removeAttribute(this.name) : this.element.setAttribute(this.name, e ?? "");
  }
}
class kt extends fe {
  constructor() {
    super(...arguments), this.type = 3;
  }
  j(e) {
    this.element[this.name] = e === x ? void 0 : e;
  }
}
class St extends fe {
  constructor() {
    super(...arguments), this.type = 4;
  }
  j(e) {
    this.element.toggleAttribute(this.name, !!e && e !== x);
  }
}
class Pt extends fe {
  constructor(e, t, o, s, r) {
    super(e, t, o, s, r), this.type = 5;
  }
  _$AI(e, t = this) {
    if ((e = G(this, e, t, 0) ?? x) === Y) return;
    const o = this._$AH, s = e === x && o !== x || e.capture !== o.capture || e.once !== o.once || e.passive !== o.passive, r = e !== x && (o === x || s);
    s && this.element.removeEventListener(this.name, this, o), r && this.element.addEventListener(this.name, this, e), this._$AH = e;
  }
  handleEvent(e) {
    var t;
    typeof this._$AH == "function" ? this._$AH.call(((t = this.options) == null ? void 0 : t.host) ?? this.element, e) : this._$AH.handleEvent(e);
  }
}
class Tt {
  constructor(e, t, o) {
    this.element = e, this.type = 6, this._$AN = void 0, this._$AM = t, this.options = o;
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  _$AI(e) {
    G(this, e);
  }
}
const xe = oe.litHtmlPolyfillSupport;
xe == null || xe(ae, ne), (oe.litHtmlVersions ?? (oe.litHtmlVersions = [])).push("3.3.3");
const Mt = (a, e, t) => {
  const o = (t == null ? void 0 : t.renderBefore) ?? e;
  let s = o._$litPart$;
  if (s === void 0) {
    const r = (t == null ? void 0 : t.renderBefore) ?? null;
    o._$litPart$ = s = new ne(e.insertBefore(re(), r), r, void 0, t ?? {});
  }
  return s._$AI(a), s;
};
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const V = globalThis;
class w extends W {
  constructor() {
    super(...arguments), this.renderOptions = { host: this }, this._$Do = void 0;
  }
  createRenderRoot() {
    var t;
    const e = super.createRenderRoot();
    return (t = this.renderOptions).renderBefore ?? (t.renderBefore = e.firstChild), e;
  }
  update(e) {
    const t = this.render();
    this.hasUpdated || (this.renderOptions.isConnected = this.isConnected), super.update(e), this._$Do = Mt(t, this.renderRoot, this.renderOptions);
  }
  connectedCallback() {
    var e;
    super.connectedCallback(), (e = this._$Do) == null || e.setConnected(!0);
  }
  disconnectedCallback() {
    var e;
    super.disconnectedCallback(), (e = this._$Do) == null || e.setConnected(!1);
  }
  render() {
    return Y;
  }
}
var rt;
w._$litElement$ = !0, w.finalized = !0, (rt = V.litElementHydrateSupport) == null || rt.call(V, { LitElement: w });
const $e = V.litElementPolyfillSupport;
$e == null || $e({ LitElement: w });
(V.litElementVersions ?? (V.litElementVersions = [])).push("4.2.2");
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const At = { attribute: !0, type: String, converter: me, reflect: !1, hasChanged: Ae }, zt = (a = At, e, t) => {
  const { kind: o, metadata: s } = t;
  let r = globalThis.litPropertyMetadata.get(s);
  if (r === void 0 && globalThis.litPropertyMetadata.set(s, r = /* @__PURE__ */ new Map()), o === "setter" && ((a = Object.create(a)).wrapped = !0), r.set(t.name, a), o === "accessor") {
    const { name: i } = t;
    return { set(n) {
      const c = e.get.call(this);
      e.set.call(this, n), this.requestUpdate(i, c, a, !0, n);
    }, init(n) {
      return n !== void 0 && this.C(i, void 0, a, n), n;
    } };
  }
  if (o === "setter") {
    const { name: i } = t;
    return function(n) {
      const c = this[i];
      e.call(this, n), this.requestUpdate(i, c, a, !0, n);
    };
  }
  throw Error("Unsupported decorator location: " + o);
};
function u(a) {
  return (e, t) => typeof t == "object" ? zt(a, e, t) : ((o, s, r) => {
    const i = s.hasOwnProperty(r);
    return s.constructor.createProperty(r, o), i ? Object.getOwnPropertyDescriptor(s, r) : void 0;
  })(a, e, t);
}
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
function v(a) {
  return u({ ...a, state: !0, attribute: !1 });
}
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const Et = (a, e, t) => (t.configurable = !0, t.enumerable = !0, Reflect.decorate && typeof e != "object" && Object.defineProperty(a, e, t), t);
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
function Rt(a, e) {
  return (t, o, s) => {
    const r = (i) => {
      var n;
      return ((n = i.renderRoot) == null ? void 0 : n.querySelector(a)) ?? null;
    };
    return Et(t, o, { get() {
      return r(this);
    } });
  };
}
class pe {
  constructor(e) {
    this.hass = e;
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
  setGlobalMode(e) {
    return this.hass.connection.sendMessagePromise({
      type: "climate_manager/set_global_mode",
      mode: e
    });
  }
  /** Update default temperatures for all four period modes. */
  setPeriodTemperatures(e) {
    return this.hass.connection.sendMessagePromise({
      type: "climate_manager/set_period_temperatures",
      temperatures: e
    });
  }
  /** Replace the global time program (all 7 day keys required). */
  setTimeProgram(e) {
    return this.hass.connection.sendMessagePromise({
      type: "climate_manager/set_time_program",
      program: e
    });
  }
  /** Reset period temperatures to backend defaults (DEFAULT_PERIOD_TEMPERATURES in const.py). */
  resetPeriodTemperatures() {
    return this.hass.connection.sendMessagePromise({
      type: "climate_manager/reset_period_temperatures"
    });
  }
  /** Reset global time program to backend defaults (_DEFAULT_DAILY_PROGRAM in const.py). */
  resetTimeProgram() {
    return this.hass.connection.sendMessagePromise({
      type: "climate_manager/reset_time_program"
    });
  }
  /**
   * Create a new custom zone. Resolves with the new zone's id and full ZoneConfig (D-02/D-03 phase 6).
   */
  createZone(e) {
    return this.hass.connection.sendMessagePromise({
      type: "climate_manager/create_zone",
      name: e
    });
  }
  /**
   * Delete a custom zone. Assigned rooms revert to the Default Zone on the backend (Phase 5 EVAL behaviour).
   */
  deleteZone(e) {
    return this.hass.connection.sendMessagePromise({
      type: "climate_manager/delete_zone",
      zone_id: e
    });
  }
  /**
   * Rename a zone. Pass zoneId="default" to rename the Default Zone (D-05 phase 5 sentinel).
   */
  renameZone(e, t) {
    return this.hass.connection.sendMessagePromise({
      type: "climate_manager/rename_zone",
      zone_id: e,
      name: t
    });
  }
  /**
   * Set the heating mode for a zone. Same enum as global_mode (off / time_program / time_program_presences).
   */
  setZoneMode(e, t) {
    return this.hass.connection.sendMessagePromise({
      type: "climate_manager/set_zone_mode",
      zone_id: e,
      mode: t
    });
  }
  /**
   * Replace the time program for a zone (all 7 day keys required).
   */
  setZoneTimeProgram(e, t) {
    return this.hass.connection.sendMessagePromise({
      type: "climate_manager/set_zone_time_program",
      zone_id: e,
      program: t
    });
  }
  /**
   * Reset a zone's time program to a target (verify the backend's accepted target values against websocket.py before passing user input).
   */
  resetZoneTimeProgram(e, t) {
    return this.hass.connection.sendMessagePromise({
      type: "climate_manager/reset_zone_time_program",
      zone_id: e,
      target: t
    });
  }
  /** Reset a room's time_program to the current global_time_program (deep-copied on the backend). */
  resetRoomToGlobalProgram(e) {
    return this.hass.connection.sendMessagePromise({
      type: "climate_manager/reset_room_to_global_program",
      room_id: e
    });
  }
  /** Sparse-merge a config delta into a specific room. */
  setRoomConfig(e, t) {
    return this.hass.connection.sendMessagePromise({
      type: "climate_manager/set_room_config",
      room_id: e,
      config: t
    });
  }
  /** Sparse-merge a config delta into a specific person. */
  setPersonConfig(e, t) {
    return this.hass.connection.sendMessagePromise({
      type: "climate_manager/set_person_config",
      person_id: e,
      config: t
    });
  }
  /**
   * Subscribe to coordinator status push events.
   * Returns Promise<unsubscribe fn> — store and call on disconnect.
   */
  subscribeStatus(e) {
    return this.hass.connection.subscribeMessage(e, {
      type: "climate_manager/subscribe_status"
    });
  }
}
var Dt = Object.defineProperty, Ee = (a, e, t, o) => {
  for (var s = void 0, r = a.length - 1, i; r >= 0; r--)
    (i = a[r]) && (s = i(e, t, s) || s);
  return s && Dt(e, t, s), s;
};
const De = class De extends w {
  constructor() {
    super(...arguments), this._visible = !1, this._message = "", this._isError = !1, this._dismissTimer = null;
  }
  /** Display the toast. Success auto-dismisses after 3s; error persists. */
  show(e, t) {
    this._dismissTimer !== null && (clearTimeout(this._dismissTimer), this._dismissTimer = null), this._message = e, this._isError = t, this._visible = !0, t || (this._dismissTimer = setTimeout(() => {
      this._visible = !1, this._dismissTimer = null;
    }, 3e3));
  }
  /** Programmatically dismiss the toast (e.g. after error recovery). */
  dismiss() {
    this._dismissTimer !== null && (clearTimeout(this._dismissTimer), this._dismissTimer = null), this._visible = !1;
  }
  render() {
    const e = this._isError ? "mdi:alert-circle" : "mdi:check-circle", t = this._isError ? "error" : "success";
    return l`
      <div
        class="toast ${this._visible ? "visible" : ""}"
        role="status"
        aria-live="polite"
        aria-atomic="true"
      >
        <ha-icon
          class="icon ${t}"
          icon="${e}"
        ></ha-icon>
        <span>${this._message}</span>
      </div>
    `;
  }
};
De.styles = A`
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
      box-shadow: var(--ha-card-box-shadow, 0 2px 8px rgba(0,0,0,0.2));
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
let J = De;
Ee([
  v()
], J.prototype, "_visible");
Ee([
  v()
], J.prototype, "_message");
Ee([
  v()
], J.prototype, "_isError");
customElements.define("climate-manager-toast", J);
const O = {
  frost_protection: "#1565C0",
  reduced: "#0277BD",
  normal: "#F57C00",
  comfort: "#C62828"
}, te = {
  present: "#2E7D32",
  absent: "#9E9E9E"
}, Re = {
  frost_protection: "Frost protection",
  reduced: "Reduced",
  normal: "Normal",
  comfort: "Comfort",
  present: "Present",
  absent: "Absent"
};
var It = Object.defineProperty, D = (a, e, t, o) => {
  for (var s = void 0, r = a.length - 1, i; r >= 0; r--)
    (i = a[r]) && (s = i(e, t, s) || s);
  return s && It(e, t, s), s;
};
const Ot = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], Nt = ["frost_protection", "reduced", "normal", "comfort"], Ht = ["present", "absent"], Ie = class Ie extends w {
  constructor() {
    super(...arguments), this.days = Array.from(
      { length: 7 },
      () => []
    ), this.mode = "schedule", this._clipboard = null, this._drag = null, this._dragTooltipMinutes = null, this._dragTooltipX = 0, this._dragTooltipY = 0, this._dragPreviewDays = null, this._popup = null, this._justDragged = !1;
  }
  // -----------------------------------------------------------------------
  // Helpers
  // -----------------------------------------------------------------------
  _snapToMinutes(e) {
    return Math.round(e / 15) * 15;
  }
  _pixelToMinutes(e, t) {
    return e / t * 1440;
  }
  /**
   * Extra upward offset (px) to apply to the drag tooltip Y position for touch
   * events. CSS transform already shifts ~23px above `top`; adding 28px on
   * touch gives ~51px total clearance — just above one row (40px) height.
   * Mouse/pen events get 0 — the CSS offset alone is sufficient.
   */
  _touchTooltipOffset(e) {
    return e.pointerType === "touch" ? 28 : 0;
  }
  _minutesToHHMM(e) {
    const t = Math.max(0, Math.min(1440, e)), o = Math.floor(t / 60), s = t % 60;
    return `${String(o).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  }
  _colorForPeriod(e) {
    const t = this.mode === "presence" ? e.state ?? "absent" : e.mode ?? "frost_protection";
    return this.mode === "presence" ? te[t] ?? te.absent : O[t] ?? O.frost_protection;
  }
  _labelForPeriod(e) {
    const t = this.mode === "presence" ? e.state ?? "absent" : e.mode ?? "frost_protection";
    return Re[t] ?? t;
  }
  /**
   * Convert a periods array to renderable segments with computed widths.
   * Always starts at 00:00 — prepends a synthesised period if needed.
   */
  _toSegments(e) {
    if (e.length === 0) return [];
    const t = [...e].sort(
      (n, c) => n.start.localeCompare(c.start)
    ), o = t[0], r = this._timeToMinutes(o.start) > 0 ? [{ start: "00:00", mode: o.mode, state: o.state }, ...t] : t, i = [];
    for (let n = 0; n < r.length; n++) {
      const c = this._timeToMinutes(r[n].start), d = n + 1 < r.length ? this._timeToMinutes(r[n + 1].start) : 1440;
      i.push({ period: r[n], startMin: c, endMin: d });
    }
    return i;
  }
  _timeToMinutes(e) {
    const [t, o] = e.split(":").map(Number);
    return (t ?? 0) * 60 + (o ?? 0);
  }
  /** Emit periods-changed for a specific day. */
  _emitChange(e, t) {
    this.dispatchEvent(
      new CustomEvent("periods-changed", {
        detail: { dayIndex: e, periods: t },
        bubbles: !0,
        composed: !0
      })
    );
  }
  /**
   * Returns true if every period in `preview` has identical start + mode/state
   * to the corresponding period in `days` for the same day index.
   *
   * Used by updated() to avoid clearing _dragPreviewDays when the incoming
   * `days` prop changes by reference but not by content — which happens when
   * _loadStatus() re-renders GlobalSettingsTab before _loadConfig() completes,
   * causing programToDays() to produce new array objects with the same values.
   */
  _previewMatchesDays(e, t) {
    if (e.length !== t.length) return !1;
    for (let o = 0; o < t.length; o++) {
      const s = e[o] ?? [], r = t[o] ?? [];
      if (s.length !== r.length) return !1;
      for (let i = 0; i < s.length; i++) {
        const n = s[i], c = r[i];
        if (n.start !== c.start || n.mode !== c.mode || n.state !== c.state)
          return !1;
      }
    }
    return !0;
  }
  // -----------------------------------------------------------------------
  // Popup helpers
  // -----------------------------------------------------------------------
  _modeOptions() {
    return this.mode === "presence" ? [
      { key: "present", label: "Present", color: te.present },
      { key: "absent", label: "Absent", color: te.absent }
    ] : [
      {
        key: "frost_protection",
        label: "Frost protection",
        color: O.frost_protection
      },
      { key: "reduced", label: "Reduced", color: O.reduced },
      { key: "normal", label: "Normal", color: O.normal },
      { key: "comfort", label: "Comfort", color: O.comfort }
    ];
  }
  _closePopup() {
    this._popup = null;
  }
  // -----------------------------------------------------------------------
  // Click on empty bar → split
  // -----------------------------------------------------------------------
  _onBarClick(e, t) {
    if (this._drag) return;
    if (this._justDragged) {
      this._justDragged = !1, e.stopPropagation();
      return;
    }
    const s = e.currentTarget.getBoundingClientRect(), r = this._pixelToMinutes(e.clientX - s.left, s.width), i = this._snapToMinutes(r);
    this._popup = {
      kind: "split",
      dayIndex: t,
      snappedMinutes: i,
      x: e.clientX,
      y: e.clientY
    }, e.stopPropagation();
  }
  _onSplitModeSelect(e) {
    if (!this._popup || this._popup.kind !== "split") return;
    const { dayIndex: t, snappedMinutes: o } = this._popup, s = [...this.days[t] ?? []], r = this.mode === "presence" ? { start: this._minutesToHHMM(o ?? 0), state: e } : { start: this._minutesToHHMM(o ?? 0), mode: e };
    s.push(r);
    const i = s.sort((c, d) => c.start.localeCompare(d.start)), n = i.filter(
      (c, d) => d === 0 || c.start !== i[d - 1].start
    );
    this._closePopup(), this._emitChange(t, n);
  }
  // -----------------------------------------------------------------------
  // Click on existing segment → edit/delete popup
  // -----------------------------------------------------------------------
  _onSegmentClick(e, t, o) {
    if (this._drag) {
      e.stopPropagation();
      return;
    }
    if (this._justDragged) {
      this._justDragged = !1, e.stopPropagation();
      return;
    }
    this._popup = {
      kind: "edit",
      dayIndex: t,
      segIndex: o,
      x: e.clientX,
      y: e.clientY
    }, e.stopPropagation();
  }
  _onEditModeSelect(e) {
    if (!this._popup || this._popup.kind !== "edit") return;
    const { dayIndex: t, segIndex: o } = this._popup, r = this._toSegments(this.days[t] ?? [])[o ?? 0];
    if (!r) return;
    const i = (this.days[t] ?? []).map((n) => n.start === r.period.start ? this.mode === "presence" ? { ...n, state: e } : { ...n, mode: e } : n);
    this._closePopup(), this._emitChange(t, i);
  }
  _onDeleteSegment() {
    if (!this._popup || this._popup.kind !== "edit") return;
    const { dayIndex: e, segIndex: t } = this._popup, s = this._toSegments(this.days[e] ?? [])[t ?? 0];
    if (!s) return;
    const r = (this.days[e] ?? []).filter(
      (i) => i.start !== s.period.start
    );
    this._closePopup(), this._emitChange(e, r);
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
    const { dayIndex: e, segIndex: t } = this._popup, s = this._toSegments(this.days[e] ?? [])[t ?? 0];
    if (!s) return;
    const r = s.endMin - s.startMin;
    if (r < 30) return;
    const i = s.startMin + r / 2, n = Math.max(
      s.startMin + 15,
      Math.min(s.endMin - 15, this._snapToMinutes(i))
    ), c = this.mode === "presence" ? Ht : Nt, d = this.mode === "presence" ? s.period.state ?? "absent" : s.period.mode ?? "frost_protection", h = c.indexOf(d), p = c[(h + 1) % c.length], _ = this.mode === "presence" ? { start: s.period.start, state: d } : { start: s.period.start, mode: d }, b = this.mode === "presence" ? { start: this._minutesToHHMM(n), state: p } : { start: this._minutesToHHMM(n), mode: p }, y = this.days[e] ?? [], m = y.some(
      (g) => g.start === s.period.start
    );
    let f;
    m ? f = y.flatMap(
      (g) => g.start === s.period.start ? [_, b] : [g]
    ) : f = [b, ...y], this._closePopup(), this._emitChange(e, f);
  }
  // -----------------------------------------------------------------------
  // Drag boundary (D-06)
  // -----------------------------------------------------------------------
  _onDragHandlePointerDown(e, t, o) {
    e.preventDefault(), e.stopPropagation(), e.target.setPointerCapture(e.pointerId), this._dragPreviewDays = null;
    const r = this._toSegments(this.days[t] ?? [])[o];
    r && (this._drag = {
      dayIndex: t,
      segIndex: o,
      startX: e.clientX,
      initialBoundaryMinutes: r.endMin
    }, this._dragTooltipMinutes = r.endMin, this._dragTooltipX = e.clientX, this._dragTooltipY = e.clientY - this._touchTooltipOffset(e));
  }
  _onPointerMove(e) {
    var p;
    if (!this._drag) return;
    const { dayIndex: t, segIndex: o } = this._drag, s = (p = this.shadowRoot) == null ? void 0 : p.querySelector(
      `.day-row:nth-child(${t + 2}) .bar-wrap`
    );
    if (!s) return;
    const r = s.getBoundingClientRect(), i = this._pixelToMinutes(e.clientX - r.left, r.width), n = this._snapToMinutes(i);
    this._dragTooltipMinutes = n, this._dragTooltipX = e.clientX, this._dragTooltipY = e.clientY - this._touchTooltipOffset(e);
    const c = this._toSegments(this.days[t] ?? []), d = c[o], h = c[o + 1];
    if (d && h) {
      const _ = d.startMin + 15, b = h.endMin - 15, y = Math.max(_, Math.min(b, n)), m = (this.days[t] ?? []).map((g) => g.start === h.period.start ? { ...g, start: this._minutesToHHMM(y) } : g), f = this.days.map(
        (g, $) => $ === t ? m : g
      );
      this._dragPreviewDays = f;
    }
  }
  _onPointerUp(e) {
    var r;
    if (!this._drag) return;
    const { dayIndex: t, segIndex: o } = this._drag, s = (r = this.shadowRoot) == null ? void 0 : r.querySelector(
      `.day-row:nth-child(${t + 2}) .bar-wrap`
    );
    if (s) {
      const i = s.getBoundingClientRect(), n = this._pixelToMinutes(
        e.clientX - i.left,
        i.width
      ), c = this._snapToMinutes(n), d = this._toSegments(this.days[t] ?? []), h = d[o], p = d[o + 1];
      if (h && p) {
        const _ = h.startMin + 15, b = p.endMin - 15, y = Math.max(
          _,
          Math.min(b, c)
        ), m = (this.days[t] ?? []).map((g) => g.start === p.period.start ? { ...g, start: this._minutesToHHMM(y) } : g), f = this.days.map(
          (g, $) => $ === t ? m : g
        );
        this._drag = null, this._dragTooltipMinutes = null, this._dragPreviewDays = f, this._justDragged = !0, this._emitChange(t, m);
        return;
      }
    }
    this._drag = null, this._dragTooltipMinutes = null, this._dragPreviewDays = null, this._justDragged = !0;
  }
  _onPointerCancel(e) {
    this._drag && (this._drag = null, this._dragTooltipMinutes = null, this._dragPreviewDays = null);
  }
  // -----------------------------------------------------------------------
  // Copy / Paste
  // -----------------------------------------------------------------------
  _onCopy(e) {
    this._clipboard = JSON.parse(
      JSON.stringify(this.days[e] ?? [])
    );
  }
  _onPaste(e) {
    if (!this._clipboard) return;
    const t = JSON.parse(JSON.stringify(this._clipboard));
    this._emitChange(e, t);
  }
  // -----------------------------------------------------------------------
  // Render
  // -----------------------------------------------------------------------
  updated(e) {
    var t;
    if (e.has("days") && this._dragPreviewDays && (this._previewMatchesDays(this._dragPreviewDays, this.days) || (this._dragPreviewDays = null)), this._popup) {
      const o = (t = this.shadowRoot) == null ? void 0 : t.querySelector(".popup");
      if (o) {
        const s = o.getBoundingClientRect(), r = 8;
        let { x: i, y: n } = this._popup;
        s.bottom > window.innerHeight - r && (n -= s.bottom - (window.innerHeight - r)), s.right > window.innerWidth - r && (i -= s.right - (window.innerWidth - r)), n = Math.max(r, n), i = Math.max(r, i), (i !== this._popup.x || n !== this._popup.y) && (this._popup = { ...this._popup, x: i, y: n });
      }
    }
  }
  render() {
    return l`
      <div
        class="week-grid"
        @pointermove=${this._onPointerMove}
        @pointerup=${this._onPointerUp}
        @pointercancel=${this._onPointerCancel}
      >
        <!-- Time axis above day rows — identical structure to bottom axis -->
        ${this._renderTimeAxis()}

        ${Ot.map(
      (e, t) => this._renderDayRow(e, t)
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
   * and bottom (below day rows).
   *
   * Mirrors the exact 3-column layout of a day row:
   *   [label spacer 40px+8px] [bar area flex:1] [invisible action buttons]
   * so ticks align pixel-perfectly with the bar regardless of button size.
   */
  _renderTimeAxis() {
    return l`
      <div class="time-axis">
        <div class="time-axis-label-spacer"></div>
        <div class="time-axis-inner">
          ${[0, 3, 6, 9, 12, 15, 18, 21, 24].map((t) => {
      const o = t % 12 === 0 ? "" : t % 6 === 0 ? "axis-tick--6h" : "axis-tick--3h";
      return l`<span
              class="axis-tick ${o}"
              style="left:${t / 24 * 100}%"
            >${String(t).padStart(2, "0")}:00</span>`;
    })}
        </div>
        <div class="time-axis-actions-ghost" aria-hidden="true">
          <ha-icon-button><ha-icon icon="mdi:content-copy"></ha-icon></ha-icon-button>
          <ha-icon-button><ha-icon icon="mdi:content-paste"></ha-icon></ha-icon-button>
        </div>
      </div>
    `;
  }
  _renderDayRow(e, t) {
    const s = (this._dragPreviewDays ?? this.days)[t] ?? [], r = this._toSegments(s), i = r.length === 0;
    return l`
      <div class="day-row">
        <div class="day-label">${e}</div>

        <div
          class="bar-wrap"
          @click=${(n) => {
      (n.target.classList.contains("bar-wrap") || n.target.classList.contains("bar-row-inner")) && this._onBarClick(n, t);
    }}
        >
          ${i ? l`<div class="empty-hint">
                Click the bar to add your first period.
              </div>` : l`<div class="bar-row-inner">
                ${r.map(
      (n, c) => this._renderSegment(n, t, c, r.length)
    )}
              </div>`}
        </div>

        <div class="day-actions">
          <ha-icon-button
            style="--mdc-icon-button-size:32px"
            .label=${"Copy " + e + " schedule"}
            @click=${() => this._onCopy(t)}
          >
            <ha-icon icon="mdi:content-copy"></ha-icon>
          </ha-icon-button>
          <ha-icon-button
            style="--mdc-icon-button-size:32px"
            class=${this._clipboard === null ? "paste-disabled" : ""}
            .label=${"Paste to " + e}
            .disabled=${this._clipboard === null}
            @click=${() => this._onPaste(t)}
          >
            <ha-icon icon="mdi:content-paste"></ha-icon>
          </ha-icon-button>
        </div>
      </div>
    `;
  }
  _renderSegment(e, t, o, s) {
    var d;
    const r = this._colorForPeriod(e.period), i = this._labelForPeriod(e.period), n = (e.endMin - e.startMin) / 1440 * 100, c = this.mode === "presence" ? e.period.state ?? "absent" : ((d = e.period.mode) == null ? void 0 : d.replace(/_/g, " ")) ?? "frost protection";
    return l`
      <div
        class="segment"
        style="width:${n}%;background:${r}"
        aria-label="${c}"
        @click=${(h) => this._onSegmentClick(h, t, o)}
      >
        ${n > 2.7 ? l`<span class="segment-label">${i}</span>` : ""}

        <!-- Drag handle on right border (not on last segment) -->
        ${o < s - 1 ? l`<div
              class="drag-handle"
              @pointerdown=${(h) => this._onDragHandlePointerDown(h, t, o)}
            ></div>` : ""}
      </div>
    `;
  }
  _renderPopup() {
    var e;
    if (!this._popup) return l``;
    if (this._popup.kind === "split") {
      const t = this._minutesToHHMM(this._popup.snappedMinutes ?? 0);
      return l`
        <div class="popup-title">Split at ${t}</div>
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
      const s = `${this._minutesToHHMM(o.startMin)} – ${this._minutesToHHMM(o.endMin)}`, r = this.mode === "presence" ? o.period.state ?? "absent" : ((e = o.period.mode) == null ? void 0 : e.replace(/_/g, " ")) ?? "frost protection", n = o.endMin - o.startMin >= 30;
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
            ?disabled=${!n}
            style=${n ? "" : "opacity:0.4;cursor:default"}
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
Ie.styles = A`
    :host {
      display: block;
      user-select: none;
    }

    .week-grid {
      display: flex;
      flex-direction: column;
      gap: 4px;
      /* Prevent Android WebView from consuming touch events as scroll gestures
         before pointer events fire on child elements (drag handles). */
      touch-action: none;
    }

    .day-row {
      display: flex;
      align-items: center;
      height: 40px;
      /* overflow must be visible so the 44px drag handle (positioned right:-22px
         on .segment) extends beyond the segment boundary and remains hittable.
         overflow:hidden clips the protruding half of the handle, making the
         touch target unreachable on Android WebView. */
      overflow: visible;
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
      min-width: 0;
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
      color: var(--text-primary-color, white);
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
      right: -22px;
      top: 0;
      width: 44px;
      height: 100%;
      cursor: ew-resize;
      z-index: 2;
      touch-action: none;
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
      margin-left: 2px;
      gap: 0;
    }

    ha-icon-button.paste-disabled {
      opacity: 0.4;
    }

    /* ---- Shared time axis (above and below day rows) ---------------------- */
    /* Mirrors the exact 3-column layout of .day-row so ticks align pixel-
       perfectly with the bar area regardless of button size. */
    .time-axis {
      display: flex;
      align-items: center;
      margin-top: 2px;
    }

    .time-axis-label-spacer {
      width: 40px;
      flex-shrink: 0;
      padding-right: 8px;
    }

    .time-axis-inner {
      position: relative;
      flex: 1;
      height: 1em;
    }

    /* Invisible clone of .day-actions — forces the inner to match bar-wrap width.
       height:0 + overflow:hidden collapses the row to label height only while
       still letting the browser compute the natural button width for flex layout. */
    .time-axis-actions-ghost {
      display: flex;
      flex-shrink: 0;
      margin-left: 4px;
      gap: 0;
      visibility: hidden;
      pointer-events: none;
      --mdc-icon-button-size: 32px;
      height: 0;
      overflow: hidden;
    }

    .axis-tick {
      position: absolute;
      transform: translateX(-50%);
      font-size: 10px;
      color: var(--secondary-text-color, #757575);
      white-space: nowrap;
    }
    .axis-tick:first-child { transform: translateX(0); }
    .axis-tick:last-child  { transform: translateX(-100%); }

    /* On narrow screens hide 3h-interval ticks (3, 9, 15, 21) */
    @media (max-width: 479px) {
      .axis-tick--3h { display: none; }
    }
    /* On very narrow screens also hide 6h-interval ticks (6, 18) */
    @media (max-width: 339px) {
      .axis-tick--6h { display: none; }
    }

    /* Drag tooltip */
    .drag-tooltip {
      position: fixed;
      background: var(--app-header-background-color, rgba(0, 0, 0, 0.75));
      color: var(--text-primary-color, white);
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
      box-shadow: var(--ha-card-box-shadow, 0 4px 16px rgba(0,0,0,0.25));
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
let P = Ie;
D([
  u({ type: Array })
], P.prototype, "days");
D([
  u({ type: String })
], P.prototype, "mode");
D([
  v()
], P.prototype, "_clipboard");
D([
  v()
], P.prototype, "_drag");
D([
  v()
], P.prototype, "_dragTooltipMinutes");
D([
  v()
], P.prototype, "_dragTooltipX");
D([
  v()
], P.prototype, "_dragTooltipY");
D([
  v()
], P.prototype, "_dragPreviewDays");
D([
  v()
], P.prototype, "_popup");
customElements.define("climate-manager-time-bar", P);
var Ut = Object.defineProperty, ce = (a, e, t, o) => {
  for (var s = void 0, r = a.length - 1, i; r >= 0; r--)
    (i = a[r]) && (s = i(e, t, s) || s);
  return s && Ut(e, t, s), s;
};
const pt = [
  "mon",
  "tue",
  "wed",
  "thu",
  "fri",
  "sat",
  "sun"
];
function _e(a) {
  return pt.map((e) => a != null && a[e] ? [...a[e]] : []);
}
function be(a) {
  return pt[a] ?? "mon";
}
const Se = "off", ue = "time_program", Pe = "time_program_presences", jt = {
  [Se]: "Off",
  [ue]: "Time program",
  [Pe]: "Time program & presences"
}, Oe = class Oe extends w {
  constructor() {
    super(...arguments), this.status = null, this._lastProgram = void 0, this._cachedDays = [], this._onModeChange = async (e) => {
      const t = e.target.value;
      if (!(!t || t === this.config.global_mode))
        try {
          await this.ws.setGlobalMode(t), await this.panel.reloadConfig(), this.panel.showToast("Saved", !1);
        } catch {
          this.panel.showToast("Save failed", !0);
        }
    }, this._tempSaveTimer = null, this._onTemperatureInput = () => {
      this._tempSaveTimer !== null && clearTimeout(this._tempSaveTimer), this._tempSaveTimer = setTimeout(() => {
        this._saveTemperatures();
      }, 600);
    }, this._onTemperatureBlur = () => {
      this._tempSaveTimer !== null && (clearTimeout(this._tempSaveTimer), this._tempSaveTimer = null), this._saveTemperatures();
    }, this._onPeriodsChanged = async (e) => {
      const { dayIndex: t, periods: o } = e.detail, s = { ...this.config.global_time_program }, r = be(t);
      s[r] = o;
      try {
        await this.ws.setTimeProgram(s), await this.panel.reloadConfig(), this.panel.showToast("Saved", !1);
      } catch {
        this.panel.showToast("Save failed — retrying...", !0);
      }
      e.stopPropagation();
    }, this._onResetTemperatures = async () => {
      try {
        await this.ws.resetPeriodTemperatures(), await this.panel.reloadConfig(), this.panel.showToast("Reset to defaults", !1);
      } catch {
        this.panel.showToast("Reset failed — retrying...", !0);
      }
    }, this._onResetConfiguration = async () => {
      try {
        await this.ws.resetTimeProgram(), await this.ws.setGlobalMode(ue), await this.panel.reloadConfig(), this.panel.showToast("Reset to defaults", !1);
      } catch {
        this.panel.showToast("Reset failed — retrying...", !0);
      }
    };
  }
  get _days() {
    var t;
    const e = (t = this.config) == null ? void 0 : t.global_time_program;
    return e !== this._lastProgram && (this._lastProgram = e, this._cachedDays = _e(e)), this._cachedDays;
  }
  async _saveTemperatures() {
    const e = this.shadowRoot;
    if (!e) return;
    const t = (s) => {
      const r = e.querySelector(`#temp-${s}`);
      return r ? parseFloat(r.value) : this.config.period_temperatures[s] ?? 0;
    }, o = {
      frost_protection: t("frost_protection"),
      reduced: t("reduced"),
      normal: t("normal"),
      comfort: t("comfort")
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
    const e = this.status, t = jt[(e == null ? void 0 : e.global_mode) ?? this.config.global_mode] ?? (e == null ? void 0 : e.global_mode) ?? this.config.global_mode;
    let o = "No active period";
    e != null && e.active_period && (o = Re[e.active_period] ?? e.active_period);
    let s = l`<span class="status-value">No one home</span>`;
    return (r = e == null ? void 0 : e.present_persons) != null && r.length && (s = l`
        <span class="status-value">
          ${e.present_persons.map(
      (i, n) => {
        var d, h, p, _;
        const c = ((p = (h = (d = this.hass) == null ? void 0 : d.states[i]) == null ? void 0 : h.attributes) == null ? void 0 : p.friendly_name) ?? i;
        return l`<span class="person-dot"></span>${c}${n < (((_ = e == null ? void 0 : e.present_persons) == null ? void 0 : _.length) ?? 1) - 1 ? ", " : ""}`;
      }
    )}
        </span>
      `), l`
      <ha-card>
        <div class="card-header">Current Status</div>
        <div class="card-content">
          <div class="status-row">
            <span class="status-label">Mode:</span>
            <span class="status-value">${t}</span>
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
    const e = this.config.period_temperatures, t = (o, s) => l`
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
            .value=${e[o] != null ? String(e[o]) : ""}
            @input=${this._onTemperatureInput}
            @blur=${this._onTemperatureBlur}
            @keydown=${(r) => {
      r.key === "Enter" && r.target.blur();
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
            ${t("frost_protection", "Frost protection")}
            ${t("reduced", "Reduced")}
            ${t("normal", "Normal")}
            ${t("comfort", "Comfort")}
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
              <option value=${Se} ?selected=${this.config.global_mode === Se}>Off</option>
              <option value=${ue} ?selected=${this.config.global_mode === ue}>Time program</option>
              <option value=${Pe} ?selected=${this.config.global_mode === Pe}>Time program &amp; presences</option>
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
Oe.styles = A`
    :host {
      display: block;
      --present-color: ${at(te.present)};
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
      background: var(--present-color);
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
      background: var(--secondary-background-color);
    }
  `;
let U = Oe;
ce([
  u({ attribute: !1 })
], U.prototype, "config");
ce([
  u({ attribute: !1 })
], U.prototype, "status");
ce([
  u({ attribute: !1 })
], U.prototype, "ws");
ce([
  u({ attribute: !1 })
], U.prototype, "panel");
ce([
  u({ attribute: !1 })
], U.prototype, "hass");
customElements.define("climate-manager-global-settings-tab", U);
var Lt = Object.defineProperty, K = (a, e, t, o) => {
  for (var s = void 0, r = a.length - 1, i; r >= 0; r--)
    (i = a[r]) && (s = i(e, t, s) || s);
  return s && Lt(e, t, s), s;
};
const Ne = class Ne extends w {
  constructor() {
    super(...arguments), this.items = [], this.placeholder = "Search…", this.triggerLabel = "Add", this.triggerIcon = "mdi:plus", this._open = !1, this._query = "", this._docClickHandler = null;
  }
  // -------------------------------------------------------------------------
  // Popup lifecycle
  // -------------------------------------------------------------------------
  _openPopup() {
    this._open = !0, this._query = "", this.updateComplete.then(() => {
      var t;
      const e = (t = this.shadowRoot) == null ? void 0 : t.querySelector(".search-input");
      e == null || e.focus();
    }), this._docClickHandler = (e) => {
      e.composedPath().includes(this) || this._closePopup();
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
  _onTriggerClick(e) {
    e.stopPropagation(), this._open ? this._closePopup() : this._openPopup();
  }
  _onSearchInput(e) {
    this._query = e.target.value;
  }
  _onKeydown(e) {
    e.key === "Escape" && (e.stopPropagation(), this._closePopup());
  }
  _onItemClick(e) {
    this.dispatchEvent(
      new CustomEvent("picked", {
        detail: { id: e.id },
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
    const e = this._query.toLowerCase();
    return this.items.filter((t) => {
      var r;
      const o = t.label.toLowerCase().includes(e), s = ((r = t.secondary) == null ? void 0 : r.toLowerCase().includes(e)) ?? !1;
      return o || s;
    });
  }
  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------
  render() {
    const e = this._filteredItems();
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
          <div class="popup" @click=${(t) => t.stopPropagation()}>
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
            ${e.length > 0 ? l`
                <ul class="item-list" role="listbox">
                  ${e.map(
      (t) => l`
                      <li
                        class="item-row"
                        role="option"
                        @click=${() => this._onItemClick(t)}
                      >
                        ${t.icon ? l`<ha-icon class="item-icon" icon=${t.icon}></ha-icon>` : ""}
                        <div class="item-text">
                          <span class="item-label">${t.label}</span>
                          ${t.secondary ? l`<span class="item-secondary">${t.secondary}</span>` : ""}
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
Ne.styles = A`
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
      background: var(--secondary-background-color);
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
      box-shadow: var(--ha-card-box-shadow, 0 4px 16px rgba(0,0,0,0.15));
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
let R = Ne;
K([
  u({ type: Array })
], R.prototype, "items");
K([
  u({ type: String })
], R.prototype, "placeholder");
K([
  u({ type: String })
], R.prototype, "triggerLabel");
K([
  u({ type: String })
], R.prototype, "triggerIcon");
K([
  v()
], R.prototype, "_open");
K([
  v()
], R.prototype, "_query");
customElements.define("search-picker", R);
var Bt = Object.defineProperty, z = (a, e, t, o) => {
  for (var s = void 0, r = a.length - 1, i; r >= 0; r--)
    (i = a[r]) && (s = i(e, t, s) || s);
  return s && Bt(e, t, s), s;
};
const He = class He extends w {
  constructor() {
    super(...arguments), this.roomStatus = null, this.status = null, this._expanded = !1, this._lastTimeProgram = void 0, this._cachedDays = [], this._trvCards = /* @__PURE__ */ new Map();
  }
  get _days() {
    var t;
    const e = (t = this.config) == null ? void 0 : t.time_program;
    return e !== this._lastTimeProgram && (this._lastTimeProgram = e, this._cachedDays = _e(e ?? void 0)), this._cachedDays;
  }
  connectedCallback() {
    super.connectedCallback(), this._expanded = !1;
  }
  // -----------------------------------------------------------------------
  // Person association handlers
  // -----------------------------------------------------------------------
  _getAssignedPersonIds() {
    var t;
    const e = ((t = this.panelConfig) == null ? void 0 : t.persons) ?? {};
    return Object.entries(e).filter(([, o]) => {
      var s;
      return (s = o.room_ids) == null ? void 0 : s.includes(this.roomId);
    }).map(([o]) => o);
  }
  _getAllPersonIds() {
    var o, s;
    const e = Object.keys(((o = this.hass) == null ? void 0 : o.states) ?? {}).filter(
      (r) => r.startsWith("person.")
    ), t = Object.keys(((s = this.panelConfig) == null ? void 0 : s.persons) ?? {});
    return [.../* @__PURE__ */ new Set([...e, ...t])];
  }
  _getPersonName(e) {
    var t, o, s;
    return ((s = (o = (t = this.hass) == null ? void 0 : t.states[e]) == null ? void 0 : o.attributes) == null ? void 0 : s.friendly_name) ?? e.replace(/^person\./, "").replace(/_/g, " ").replace(/\b\w/g, (r) => r.toUpperCase());
  }
  _getPersonPresenceState(e) {
    var o, s;
    const t = (s = (o = this.hass) == null ? void 0 : o.states[e]) == null ? void 0 : s.state;
    return t === "home" ? "Home" : t === "not_home" ? "Away" : t ? t.charAt(0).toUpperCase() + t.slice(1) : "—";
  }
  _onPersonPicked(e) {
    e.stopPropagation();
    const t = e.detail.id;
    t && this._onAddPerson(t);
  }
  async _onAddPerson(e) {
    var s, r, i;
    const t = [...((i = (r = (s = this.panelConfig) == null ? void 0 : s.persons) == null ? void 0 : r[e]) == null ? void 0 : i.room_ids) ?? []], o = t.includes(this.roomId) ? t : [...t, this.roomId];
    try {
      await this.ws.setPersonConfig(e, { room_ids: o }), await this.panel.reloadConfig(), this.panel.showToast("Saved", !1);
    } catch {
      this.panel.showToast("Save failed — retrying...", !0);
    }
  }
  async _onRemovePerson(e) {
    var s, r, i;
    const o = [...((i = (r = (s = this.panelConfig) == null ? void 0 : s.persons) == null ? void 0 : r[e]) == null ? void 0 : i.room_ids) ?? []].filter((n) => n !== this.roomId);
    try {
      await this.ws.setPersonConfig(e, { room_ids: o }), await this.panel.reloadConfig(), this.panel.showToast("Saved", !1);
    } catch {
      this.panel.showToast("Save failed — retrying...", !0);
    }
  }
  // -----------------------------------------------------------------------
  // Room mode handler (D-20)
  // -----------------------------------------------------------------------
  async _onRoomModeChange(e) {
    var s;
    const t = e.target.value;
    let o;
    t === "custom" && !((s = this.config) != null && s.time_program) ? o = {
      room_mode: "custom",
      time_program: JSON.parse(JSON.stringify(this.panelConfig.global_time_program))
    } : o = { room_mode: t };
    try {
      await this.ws.setRoomConfig(this.roomId, o), await this.panel.reloadConfig(), this.panel.showToast("Saved", !1);
    } catch {
      this.panel.showToast("Save failed — retrying...", !0);
    }
  }
  // -----------------------------------------------------------------------
  // Schedule override handlers
  // -----------------------------------------------------------------------
  async _onPeriodsChanged(e) {
    const { dayIndex: t, periods: o } = e.detail, r = { ...this.config.time_program ?? {
      mon: [],
      tue: [],
      wed: [],
      thu: [],
      fri: [],
      sat: [],
      sun: []
    } }, i = be(t);
    r[i] = o;
    try {
      await this.ws.setRoomConfig(this.roomId, { time_program: r }), await this.panel.reloadConfig(), this.panel.showToast("Saved", !1);
    } catch {
      this.panel.showToast("Save failed — retrying...", !0);
    }
    e.stopPropagation();
  }
  async _onResetToGlobal() {
    try {
      await this.ws.resetRoomToGlobalProgram(this.roomId), await this.panel.reloadConfig(), this.panel.showToast("Saved", !1);
    } catch {
      this.panel.showToast("Save failed — retrying...", !0);
    }
  }
  // -----------------------------------------------------------------------
  // Render helpers
  // -----------------------------------------------------------------------
  /** D-32: render period badge for row 1 of the card header.
   *
   * Returns empty when:
   *   - resolvedMode is "frost_protection" (mode badge already conveys state)
   *   - active_period is null/undefined (no active period to display)
   *
   * Returns gray "Off" badge when globalMode is "off".
   * Otherwise returns a colored pill: "${name} · ${temp}°C".
   */
  _renderPeriodBadge() {
    var n, c, d, h, p, _;
    if ((((n = this.config) == null ? void 0 : n.room_mode) ?? "global") === "frost_protection") return l``;
    if ((((c = this.status) == null ? void 0 : c.global_mode) ?? ((d = this.panelConfig) == null ? void 0 : d.global_mode) ?? "") === "off")
      return l`
        <span
          class="program-badge"
          style="background: var(--secondary-background-color); color: var(--secondary-text-color);"
        >Off</span>
      `;
    const o = ((h = this.roomStatus) == null ? void 0 : h.active_period) ?? null;
    if (o == null) return l``;
    const s = Re[o] ?? o, r = (_ = (p = this.panelConfig) == null ? void 0 : p.period_temperatures) == null ? void 0 : _[o], i = r != null ? `${s} · ${r}°C` : s;
    return l`
      <span
        class="program-badge"
        style="background: ${O[o]}; color: white;"
      >${i}</span>
    `;
  }
  _renderHeaderStatus() {
    var b, y, m;
    const e = this.roomStatus, t = (e == null ? void 0 : e.temperature) != null ? parseFloat(String(e.temperature)) : null, o = t != null && !isNaN(t) ? `${t.toFixed(1)}°C` : "—", s = (e == null ? void 0 : e.humidity) != null ? `${e.humidity}%` : "—", r = ((b = this.status) == null ? void 0 : b.global_mode) ?? ((y = this.panelConfig) == null ? void 0 : y.global_mode) ?? "", i = r === "time_program_presences", c = {
      off: "Off",
      time_program: "Time program",
      time_program_presences: "Time & presence"
    }[r] ?? r, h = this._getAssignedPersonIds().length, p = i ? ((m = this.roomStatus) == null ? void 0 : m.present_person_count) ?? 0 : null, _ = p != null ? `${p}/${h}` : `${h}`;
    return l`
      <div class="card-header-status">
        <span class="status-item" title="Mode: ${c}">
          <ha-icon icon="mdi:thermometer"></ha-icon>
          ${o}
        </span>
        <span class="status-item">
          <ha-icon icon="mdi:water-percent"></ha-icon>
          ${s}
        </span>
        <span class="status-item" title="${i ? `${p} present / ${h} assigned` : `${h} assigned`}">
          <ha-icon icon="mdi:account-group"></ha-icon>
          ${_}
        </span>
      </div>
    `;
  }
  _getTrvCard(e) {
    let t = this._trvCards.get(e);
    return t || (t = document.createElement("hui-thermostat-card"), t.setConfig({
      type: "thermostat",
      entity: e
    }), this._trvCards.set(e, t)), t.hass = this.hass, t;
  }
  _renderTrvSection() {
    var t;
    const e = ((t = this.roomStatus) == null ? void 0 : t.entity_ids) ?? [];
    return e.length === 0 ? l`
        <div class="no-trv-badge">
          <ha-icon icon="mdi:alert"></ha-icon>
          No climate entities
        </div>
      ` : l`
      <div class="trv-section">
        ${e.map((o) => this._getTrvCard(o))}
      </div>
    `;
  }
  _renderPersonsSection() {
    const e = this._getAssignedPersonIds(), o = this._getAllPersonIds().filter(
      (r) => !e.includes(r)
    ), s = o.map((r) => ({
      id: r,
      label: this._getPersonName(r),
      secondary: this._getPersonPresenceState(r),
      icon: "mdi:account"
    }));
    return l`
      <div class="section-label">Associated persons</div>
      <div class="chips">
        ${e.map((r) => l`
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
    const e = ((s = this.config) == null ? void 0 : s.room_mode) ?? "global", t = e === "frost_protection" ? "frost" : e === "custom" ? "custom" : "global", o = e === "frost_protection" ? "Frost protection" : e === "custom" ? "Custom program" : "Global program";
    return l`
      <ha-card>
        <div class="card-header-row" @click=${() => {
      this._expanded = !this._expanded;
    }}>
          <div class="card-header-left">
            <div class="card-header-top">
              <span class="room-name">${this.roomName}</span>
              ${this._renderPeriodBadge()}
              <span
                class="program-badge ${t}"
                style=${t === "frost" ? `background: ${O.frost_protection}; color: white;` : ""}
              >${o}</span>
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
              <!-- 3-way room mode selector (D-20) -->
              <div class="section-label">Mode</div>
              <div class="select-wrapper">
                <select
                  class="mode-select"
                  .value=${e}
                  @change=${this._onRoomModeChange}
                >
                  <option value="global" ?selected=${e === "global"}>Global program</option>
                  <option value="frost_protection" ?selected=${e === "frost_protection"}>Frost protection</option>
                  <option value="custom" ?selected=${e === "custom"}>Custom program</option>
                </select>
              </div>

              <!-- Inline time-bar (only in Custom mode) -->
              ${e === "custom" ? l`
                  <div class="section-label">Schedule</div>
                  <div class="time-bar-section">
                    <climate-manager-time-bar
                      mode="schedule"
                      .days=${this._days}
                      @periods-changed=${this._onPeriodsChanged}
                    ></climate-manager-time-bar>
                  </div>
                  <button class="reset-btn" @click=${() => void this._onResetToGlobal()}>Reset to global configuration</button>
                ` : ""}

              ${this._renderPersonsSection()}

              <div class="section-label">Climate entities</div>
              ${this._renderTrvSection()}
            </div>
          ` : ""}
      </ha-card>
    `;
  }
};
He.styles = A`
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

    /* Always-visible 3-item status line in the card header (D-14d, D-32) */
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
      background: var(--secondary-background-color);
      color: var(--warning-color, #e65100);
      font-size: 12px;
      margin-bottom: 12px;
    }

    /* TRV section */
    .trv-section {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
      gap: 8px;
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
      background: var(--secondary-background-color);
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

    .reset-btn {
      margin-top: 12px;
      margin-bottom: 12px;
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
      background: var(--secondary-background-color);
    }
  `;
let C = He;
z([
  u({ type: String })
], C.prototype, "roomId");
z([
  u({ type: String })
], C.prototype, "roomName");
z([
  u({ attribute: !1 })
], C.prototype, "config");
z([
  u({ attribute: !1 })
], C.prototype, "roomStatus");
z([
  u({ attribute: !1 })
], C.prototype, "panelConfig");
z([
  u({ attribute: !1 })
], C.prototype, "status");
z([
  u({ attribute: !1 })
], C.prototype, "ws");
z([
  u({ attribute: !1 })
], C.prototype, "panel");
z([
  u({ attribute: !1 })
], C.prototype, "hass");
z([
  v()
], C.prototype, "_expanded");
customElements.define("climate-manager-room-card", C);
var Ft = Object.defineProperty, le = (a, e, t, o) => {
  for (var s = void 0, r = a.length - 1, i; r >= 0; r--)
    (i = a[r]) && (s = i(e, t, s) || s);
  return s && Ft(e, t, s), s;
};
const Ue = class Ue extends w {
  constructor() {
    super(...arguments), this.status = null;
  }
  _getRoomStatus(e) {
    var t, o;
    return ((o = (t = this.status) == null ? void 0 : t.rooms_status) == null ? void 0 : o.find((s) => s.area_id === e)) ?? null;
  }
  render() {
    var h, p, _, b, y;
    const e = ((h = this.config) == null ? void 0 : h.rooms) ?? {}, t = (((p = this.status) == null ? void 0 : p.rooms_status) ?? []).filter((m) => m.has_trv !== !1), o = /* @__PURE__ */ new Set([
      ...t.map((m) => m.area_id)
    ]);
    if (o.size === 0)
      return l`
        <div class="empty-state">
          No rooms discovered. Create areas in Home Assistant and assign climate entities.
        </div>
      `;
    const s = (m) => {
      var f, g, $;
      return (($ = (g = (f = this.status) == null ? void 0 : f.rooms_status) == null ? void 0 : g.find((S) => S.area_id === m)) == null ? void 0 : $.name) ?? m.replace(/_/g, " ").replace(/\b\w/g, (S) => S.toUpperCase());
    }, r = /* @__PURE__ */ new Map();
    for (const m of o) {
      const f = ((y = (b = (_ = this.hass) == null ? void 0 : _.areas) == null ? void 0 : b[m]) == null ? void 0 : y.floor_id) ?? null;
      r.has(f) || r.set(f, []), r.get(f).push(m);
    }
    for (const m of r.values())
      m.sort((f, g) => s(f).localeCompare(s(g)));
    const i = [...r.keys()].filter((m) => m !== null).sort(
      (m, f) => {
        var g, $, S, Q, qe, Ve;
        return (((S = ($ = (g = this.hass) == null ? void 0 : g.floors) == null ? void 0 : $[f]) == null ? void 0 : S.level) ?? 0) - (((Ve = (qe = (Q = this.hass) == null ? void 0 : Q.floors) == null ? void 0 : qe[m]) == null ? void 0 : Ve.level) ?? 0);
      }
    ), n = r.get(null) ?? [], c = (m) => {
      const f = e[m] ?? {}, g = this._getRoomStatus(m), $ = s(m);
      return l`
        <climate-manager-room-card
          .roomId=${m}
          .roomName=${$}
          .config=${f}
          .roomStatus=${g}
          .panelConfig=${this.config}
          .status=${this.status}
          .ws=${this.ws}
          .panel=${this.panel}
          .hass=${this.hass}
        ></climate-manager-room-card>
      `;
    }, d = (m) => {
      var $, S;
      const f = (S = ($ = this.hass) == null ? void 0 : $.floors) == null ? void 0 : S[m];
      if (f != null && f.icon) return f.icon;
      const g = (f == null ? void 0 : f.level) ?? 0;
      return g === -1 ? "mdi:home-floor-negative-1" : g < 0 ? "mdi:home-floor-b" : g === 1 ? "mdi:home-floor-1" : g === 2 ? "mdi:home-floor-2" : g === 3 || g > 3 ? "mdi:home-floor-3" : "mdi:home-floor-0";
    };
    return l`
      ${i.map((m) => {
      var $, S, Q;
      const f = ((Q = (S = ($ = this.hass) == null ? void 0 : $.floors) == null ? void 0 : S[m]) == null ? void 0 : Q.name) ?? m, g = r.get(m) ?? [];
      return l`
          <div class="floor-header">
            <ha-icon icon=${d(m)}></ha-icon>
            ${f}
          </div>
          ${g.map(c)}
        `;
    })}
      ${n.map(c)}
    `;
  }
};
Ue.styles = A`
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
let j = Ue;
le([
  u({ attribute: !1 })
], j.prototype, "config");
le([
  u({ attribute: !1 })
], j.prototype, "status");
le([
  u({ attribute: !1 })
], j.prototype, "ws");
le([
  u({ attribute: !1 })
], j.prototype, "panel");
le([
  u({ attribute: !1 })
], j.prototype, "hass");
customElements.define("climate-manager-rooms-tab", j);
var qt = Object.defineProperty, B = (a, e, t, o) => {
  for (var s = void 0, r = a.length - 1, i; r >= 0; r--)
    (i = a[r]) && (s = i(e, t, s) || s);
  return s && qt(e, t, s), s;
};
const X = "scheduled", we = "ha", Ce = "force_present", ke = "force_absent", ot = {
  mon: [{ start: "00:00", state: "present" }, { start: "08:00", state: "absent" }, { start: "18:00", state: "present" }],
  tue: [{ start: "00:00", state: "present" }, { start: "08:00", state: "absent" }, { start: "18:00", state: "present" }],
  wed: [{ start: "00:00", state: "present" }, { start: "08:00", state: "absent" }, { start: "18:00", state: "present" }],
  thu: [{ start: "00:00", state: "present" }, { start: "08:00", state: "absent" }, { start: "18:00", state: "present" }],
  fri: [{ start: "00:00", state: "present" }, { start: "08:00", state: "absent" }, { start: "18:00", state: "present" }],
  sat: [{ start: "00:00", state: "present" }],
  sun: [{ start: "00:00", state: "present" }]
}, je = class je extends w {
  constructor() {
    super(...arguments), this.roomChoices = [], this.status = null, this._expanded = !1, this._lastSchedule = void 0, this._cachedDays = [];
  }
  get _days() {
    var t;
    const e = (t = this.config) == null ? void 0 : t.schedule;
    return e !== this._lastSchedule && (this._lastSchedule = e, this._cachedDays = _e(e)), this._cachedDays;
  }
  connectedCallback() {
    super.connectedCallback(), this._expanded = !1;
  }
  // -----------------------------------------------------------------------
  // Save handlers
  // -----------------------------------------------------------------------
  async _onModeChange(e) {
    var o;
    const t = e.target.value;
    if (t)
      try {
        const s = !!((o = this.config) != null && o.schedule) && Object.values(this.config.schedule).some((r) => r.length > 0);
        t === X && !s ? await this.ws.setPersonConfig(this.personId, { mode: t, schedule: ot }) : await this.ws.setPersonConfig(this.personId, { mode: t }), await this.panel.reloadConfig(), this.panel.showToast("Saved", !1);
      } catch {
        this.panel.showToast("Save failed — retrying...", !0);
      }
  }
  async _onRoomToggle(e, t) {
    var r;
    const o = [...((r = this.config) == null ? void 0 : r.room_ids) ?? []], s = t ? o.includes(e) ? o : [...o, e] : o.filter((i) => i !== e);
    try {
      await this.ws.setPersonConfig(this.personId, { room_ids: s }), await this.panel.reloadConfig(), this.panel.showToast("Saved", !1);
    } catch {
      this.panel.showToast("Save failed — retrying...", !0);
    }
  }
  async _onResetSchedule() {
    try {
      await this.ws.setPersonConfig(this.personId, { schedule: ot }), await this.panel.reloadConfig(), this.panel.showToast("Reset to defaults", !1);
    } catch {
      this.panel.showToast("Reset failed — retrying...", !0);
    }
  }
  async _onSchedulePeriodsChanged(e) {
    const { dayIndex: t, periods: o } = e.detail, r = { ...this.config.schedule ?? {
      mon: [],
      tue: [],
      wed: [],
      thu: [],
      fri: [],
      sat: [],
      sun: []
    } }, i = be(t);
    r[i] = o;
    try {
      await this.ws.setPersonConfig(this.personId, { schedule: r }), await this.panel.reloadConfig(), this.panel.showToast("Saved", !1);
    } catch {
      this.panel.showToast("Save failed — retrying...", !0);
    }
    e.stopPropagation();
  }
  // -----------------------------------------------------------------------
  // Helpers
  // -----------------------------------------------------------------------
  _isCurrentlyPresent() {
    var e, t;
    return ((t = (e = this.status) == null ? void 0 : e.present_persons) == null ? void 0 : t.includes(this.personId)) ?? !1;
  }
  // -----------------------------------------------------------------------
  // Render
  // -----------------------------------------------------------------------
  _getBadgeInfo() {
    var t;
    switch (((t = this.config) == null ? void 0 : t.mode) ?? X) {
      case Ce:
        return { cls: "force-present", text: "Force Present" };
      case ke:
        return { cls: "force-absent", text: "Force Absent" };
      case we:
        return { cls: "ha", text: "HA" };
      default:
        return { cls: "scheduled", text: "Scheduled" };
    }
  }
  render() {
    var n, c;
    const { cls: e, text: t } = this._getBadgeInfo(), o = ((n = this.config) == null ? void 0 : n.mode) ?? X, s = o === X, r = ((c = this.config) == null ? void 0 : c.room_ids) ?? [], i = this.roomChoices.filter((d) => !r.includes(d.id));
    return l`
      <ha-card>
        <div class="card-header-row" @click=${() => {
      this._expanded = !this._expanded;
    }}>
          <div class="card-header-left">
            <span
              class="presence-dot ${this._isCurrentlyPresent() ? "present" : "absent"}"
              title="Currently ${this._isCurrentlyPresent() ? "present" : "absent"}"
            >●</span>
            <span class="person-name">${this.personName}</span>
            <span class="mode-badge ${e}">${t}</span>
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
                  <option value=${X} ?selected=${o === X}>Scheduled</option>
                  <option value=${we} ?selected=${o === we}>HA</option>
                  <option value=${Ce} ?selected=${o === Ce}>Force Present</option>
                  <option value=${ke} ?selected=${o === ke}>Force Absent</option>
                </select>
              </div>

              <!-- Room associations as chips -->
              <div class="section-label">Room associations</div>
              <div class="chips">
                ${r.map((d) => {
      const h = this.roomChoices.find((p) => p.id === d);
      return h ? l`
                    <span class="chip">
                      <ha-icon icon="mdi:home-outline"></ha-icon>
                      ${h.name}
                      <button
                        class="chip-remove"
                        @click=${() => void this._onRoomToggle(d, !1)}
                      >×</button>
                    </span>
                  ` : "";
    })}
                ${i.length > 0 ? l`
                    <search-picker
                      .items=${i.map((d) => ({
      id: d.id,
      label: d.name,
      secondary: d.secondary,
      icon: "mdi:home-outline"
    }))}
                      triggerLabel="Add room"
                      triggerIcon="mdi:plus"
                      placeholder="Search rooms…"
                      @picked=${(d) => {
      const { id: h } = d.detail;
      this._onRoomToggle(h, !0);
    }}
                    ></search-picker>
                  ` : ""}
              </div>

              <!-- Presence schedule (only in Scheduled mode) -->
              ${s ? l`
                  <div class="section-label">Presence schedule</div>
                  <div class="schedule-section">
                    <climate-manager-time-bar
                      mode="presence"
                      .days=${this._days}
                      @periods-changed=${this._onSchedulePeriodsChanged}
                    ></climate-manager-time-bar>
                  </div>
                  <button class="reset-btn" @click=${() => void this._onResetSchedule()}>Reset to default</button>
                ` : ""}
            </div>
          ` : ""}
      </ha-card>
    `;
  }
};
je.styles = A`
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

    .mode-badge.scheduled {
      background: var(--secondary-background-color, #f5f5f5);
      color: var(--secondary-text-color, #757575);
    }

    .mode-badge.force-present {
      border: 1px solid var(--primary-color, #03a9f4);
      color: var(--primary-color, #03a9f4);
    }

    .mode-badge.force-absent {
      background: var(--secondary-background-color, #f5f5f5);
      color: var(--secondary-text-color, #757575);
    }

    .mode-badge.ha {
      background: var(--secondary-background-color, #f5f5f5);
      color: var(--secondary-text-color, #757575);
    }

    .presence-dot {
      font-size: 12px;
      line-height: 1;
    }

    .presence-dot.present {
      color: var(--success-color, #4caf50);
    }

    .presence-dot.absent {
      color: var(--secondary-text-color, #9e9e9e);
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
      background: var(--secondary-background-color);
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

    .reset-btn {
      margin-top: 12px;
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
      background: var(--secondary-background-color);
    }
  `;
let M = je;
B([
  u({ type: String })
], M.prototype, "personId");
B([
  u({ type: String })
], M.prototype, "personName");
B([
  u({ attribute: !1 })
], M.prototype, "config");
B([
  u({ attribute: !1 })
], M.prototype, "roomChoices");
B([
  u({ attribute: !1 })
], M.prototype, "ws");
B([
  u({ attribute: !1 })
], M.prototype, "panel");
B([
  u({ attribute: !1 })
], M.prototype, "status");
B([
  v()
], M.prototype, "_expanded");
customElements.define("climate-manager-person-card", M);
var Vt = Object.defineProperty, de = (a, e, t, o) => {
  for (var s = void 0, r = a.length - 1, i; r >= 0; r--)
    (i = a[r]) && (s = i(e, t, s) || s);
  return s && Vt(e, t, s), s;
};
const Le = class Le extends w {
  constructor() {
    super(...arguments), this.status = null;
  }
  /** Build the room choices list — only TRV rooms (excludes chaudière/boiler). */
  _getRoomChoices() {
    var o;
    const e = (((o = this.status) == null ? void 0 : o.rooms_status) ?? []).filter((s) => s.has_trv !== !1);
    return [.../* @__PURE__ */ new Set([
      ...e.map((s) => s.area_id)
    ])].map((s) => {
      var c, d, h, p, _, b, y;
      const r = ((c = e.find((m) => m.area_id === s)) == null ? void 0 : c.name) ?? s.replace(/_/g, " ").replace(/\b\w/g, (m) => m.toUpperCase()), i = ((p = (h = (d = this.hass) == null ? void 0 : d.areas) == null ? void 0 : h[s]) == null ? void 0 : p.floor_id) ?? null, n = i ? ((y = (b = (_ = this.hass) == null ? void 0 : _.floors) == null ? void 0 : b[i]) == null ? void 0 : y.name) ?? void 0 : void 0;
      return { id: s, name: r, secondary: n };
    });
  }
  /** Determine if a person config has any non-default setting (D-15). */
  _isNonDefault(e) {
    var i, n, c;
    const t = (n = (i = this.config) == null ? void 0 : i.persons) == null ? void 0 : n[e];
    if (!t) return !1;
    const o = t.mode != null && t.mode !== "scheduled", s = (((c = t.room_ids) == null ? void 0 : c.length) ?? 0) > 0, r = t.schedule ? Object.values(t.schedule).some((d) => d.length > 0) : !1;
    return o || s || r;
  }
  render() {
    var r;
    const e = ((r = this.config) == null ? void 0 : r.persons) ?? {}, t = Object.keys(e);
    if (t.length === 0)
      return l`
        <div class="empty-state">
          No persons found. Add person entities in Home Assistant.
        </div>
      `;
    const o = [...t].sort((i, n) => {
      const c = this._isNonDefault(i), d = this._isNonDefault(n);
      return c && !d ? -1 : !c && d ? 1 : i.localeCompare(n);
    }), s = this._getRoomChoices();
    return l`
      ${o.map((i) => {
      const n = e[i] ?? {}, c = i.replace(/^person\./, "").replace(/_/g, " ").replace(/\b\w/g, (d) => d.toUpperCase());
      return l`
          <climate-manager-person-card
            .personId=${i}
            .personName=${c}
            .config=${n}
            .roomChoices=${s}
            .ws=${this.ws}
            .panel=${this.panel}
            .status=${this.status}
          ></climate-manager-person-card>
        `;
    })}
    `;
  }
};
Le.styles = A`
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
let L = Le;
de([
  u({ attribute: !1 })
], L.prototype, "config");
de([
  u({ attribute: !1 })
], L.prototype, "status");
de([
  u({ attribute: !1 })
], L.prototype, "ws");
de([
  u({ attribute: !1 })
], L.prototype, "panel");
de([
  u({ attribute: !1 })
], L.prototype, "hass");
customElements.define("climate-manager-persons-tab", L);
var Zt = Object.defineProperty, E = (a, e, t, o) => {
  for (var s = void 0, r = a.length - 1, i; r >= 0; r--)
    (i = a[r]) && (s = i(e, t, s) || s);
  return s && Zt(e, t, s), s;
};
const Be = class Be extends w {
  constructor() {
    super(...arguments), this.isDefault = !1, this._editingName = !1, this._nameInputValue = "", this._confirmingDelete = !1, this._lastProgram = void 0, this._cachedDays = [], this._onModeChange = async (e) => {
      const t = e.target.value;
      if (!(!t || t === this.zoneConfig.mode))
        try {
          await this.ws.setZoneMode(this.zoneId, t), await this.panel.reloadConfig(), this.panel.showToast("Saved", !1);
        } catch {
          this.panel.showToast("Save failed", !0);
        }
    }, this._onPeriodsChanged = async (e) => {
      const { dayIndex: t, periods: o } = e.detail, s = { ...this.zoneConfig.time_program }, r = be(t);
      s[r] = o;
      try {
        await this.ws.setZoneTimeProgram(this.zoneId, s), await this.panel.reloadConfig(), this.panel.showToast("Saved", !1);
      } catch {
        this.panel.showToast("Save failed — retrying...", !0);
      }
      e.stopPropagation();
    };
  }
  get _days() {
    var t;
    const e = (t = this.zoneConfig) == null ? void 0 : t.time_program;
    return e !== this._lastProgram && (this._lastProgram = e, this._cachedDays = _e(e)), this._cachedDays;
  }
  // -------------------------------------------------------------------------
  // Handlers
  // -------------------------------------------------------------------------
  /** Click on zone name — enter edit mode and focus the input. */
  _onNameClick() {
    this._nameInputValue = this.zoneConfig.name, this._editingName = !0, this.updateComplete.then(() => {
      var e, t;
      (t = (e = this.shadowRoot) == null ? void 0 : e.querySelector(".zone-name-input")) == null || t.focus();
    });
  }
  /** Update internal name value as user types. */
  _onNameInput(e) {
    this._nameInputValue = e.target.value;
  }
  /**
   * Blur on name input — save if changed, cancel otherwise.
   * zoneId="default" routes to backend default_zone_name rename (D-05/D-07).
   */
  async _onNameBlur() {
    if (!this._editingName) return;
    this._editingName = !1;
    const e = this._nameInputValue.trim();
    if (!(!e || e === this.zoneConfig.name))
      try {
        await this.ws.renameZone(this.zoneId, e), await this.panel.reloadConfig(), this.panel.showToast("Saved", !1);
      } catch {
        this.panel.showToast("Save failed", !0);
      }
  }
  /** Enter key blurs (triggers save), Escape key cancels. */
  _onNameKeydown(e) {
    e.key === "Enter" ? e.target.blur() : e.key === "Escape" && (this._editingName = !1);
  }
  /**
   * Add a room to this zone (D-09).
   * For Default Zone (zoneId="default"), sends zone_id="default" — backend treats as Default Zone membership.
   * NOTE: If backend rejects "default" here, flag it rather than silently dropping the assignment.
   */
  async _onAddRoom(e) {
    try {
      await this.ws.setRoomConfig(e, { zone_id: this.zoneId }), await this.panel.reloadConfig(), this.panel.showToast("Saved", !1);
    } catch {
      this.panel.showToast("Save failed — retrying...", !0);
    }
  }
  /**
   * Remove a room from a custom zone (D-08).
   * Sends setRoomConfig with zone_id: undefined so the sparse model removes the key.
   * Absent zone_id = Default Zone member (D-06 phase 4).
   * Not rendered for Default Zone (rooms can't be removed — no other zone to send them to).
   */
  async _onRemoveRoom(e) {
    const t = { zone_id: void 0 };
    try {
      await this.ws.setRoomConfig(e, t), await this.panel.reloadConfig(), this.panel.showToast("Saved", !1);
    } catch {
      this.panel.showToast("Save failed — retrying...", !0);
    }
  }
  /** search-picker @picked event — add the selected room to this zone. */
  _onRoomPicked(e) {
    e.stopPropagation();
    const t = e.detail.id;
    t && this._onAddRoom(t);
  }
  /** First click on delete — show inline confirm row (D-05). */
  _onDeleteClick() {
    this._confirmingDelete = !0;
  }
  /** Cancel delete — hide confirm row. */
  _onCancelDelete() {
    this._confirmingDelete = !1;
  }
  /**
   * Confirm delete — delete zone and reload config.
   * After successful delete, parent main.ts detects missing tab via _validateActiveTab()
   * and falls back to "global". This component does not navigate.
   */
  async _onConfirmDelete() {
    try {
      await this.ws.deleteZone(this.zoneId), await this.panel.reloadConfig(), this.panel.showToast("Zone deleted", !1);
    } catch {
      this.panel.showToast("Delete failed", !0);
    }
  }
  // -------------------------------------------------------------------------
  // Helpers
  // -------------------------------------------------------------------------
  /**
   * Resolve a room's display name from the HA areas registry.
   * Rooms are HA areas; areas[roomId].name is the canonical display name.
   */
  _getRoomName(e) {
    var t;
    return ((t = this.hass.areas[e]) == null ? void 0 : t.name) ?? e;
  }
  /**
   * Returns IDs of rooms assigned to this zone.
   * For custom zones: rooms whose zone_id === this.zoneId.
   * For Default Zone: rooms whose zone_id is undefined OR points to a non-existent zone (orphan-safe, D-06 phase 4).
   */
  _getAssignedRoomIds() {
    var t;
    if (!((t = this.config) != null && t.rooms)) return [];
    const e = Object.keys(this.config.zones ?? {});
    return Object.entries(this.config.rooms).filter(([, o]) => this.isDefault || this.zoneId === "default" ? !o.zone_id || !e.includes(o.zone_id) : o.zone_id === this.zoneId).map(([o]) => o);
  }
  /**
   * Returns rooms NOT assigned to this zone, shaped for the search-picker.
   * Per D-10: includes rooms in other zones (valid reassignment targets).
   */
  _getUnassignedRoomItems() {
    var t;
    const e = new Set(this._getAssignedRoomIds());
    return (t = this.config) != null && t.rooms ? Object.keys(this.config.rooms).filter((o) => !e.has(o)).map((o) => ({
      id: o,
      label: this._getRoomName(o),
      icon: "mdi:home-outline"
    })) : [];
  }
  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------
  render() {
    const e = this._getAssignedRoomIds(), t = this._getUnassignedRoomItems();
    return l`
      <!-- 1. Delete row (custom zones only, D-05) -->
      ${this.isDefault ? "" : l`
          <div class="delete-row">
            ${this._confirmingDelete ? l`
                <span>Delete zone?</span>
                <button class="cancel-btn" @click=${this._onCancelDelete}>Cancel</button>
                <button class="danger-btn" @click=${() => void this._onConfirmDelete()}>Confirm</button>
              ` : l`
                <button class="delete-btn" @click=${this._onDeleteClick}>Delete zone</button>
              `}
          </div>
        `}

      <!-- 2. Zone name (click-to-edit, D-06 / D-07) -->
      ${this._editingName ? l`
          <input
            class="zone-name-input"
            type="text"
            .value=${this._nameInputValue}
            @input=${this._onNameInput}
            @blur=${() => void this._onNameBlur()}
            @keydown=${this._onNameKeydown}
          />
        ` : l`
          <h2 class="zone-name" @click=${this._onNameClick} title="Click to rename">
            ${this.zoneConfig.name}
          </h2>
        `}

      <!-- 3. Mode picker -->
      <div class="select-wrapper">
        <label class="select-label">Zone mode</label>
        <select class="mode-select" @change=${this._onModeChange}>
          <option value="off" ?selected=${this.zoneConfig.mode === "off"}>Off</option>
          <option value="time_program" ?selected=${this.zoneConfig.mode === "time_program"}>Time program</option>
          <option value="time_program_presences" ?selected=${this.zoneConfig.mode === "time_program_presences"}>Time program &amp; presences</option>
        </select>
      </div>

      <!-- 4. Time-bar -->
      <climate-manager-time-bar
        mode="schedule"
        .days=${this._days}
        @periods-changed=${this._onPeriodsChanged}
      ></climate-manager-time-bar>

      <!-- 5. Assigned Rooms section (D-08 / D-09 / D-10) -->
      <div class="section-divider"></div>
      <div class="section-label">Assigned rooms</div>
      <div class="chips">
        ${e.map((o) => l`
          <span class="chip">
            <ha-icon icon="mdi:home-outline"></ha-icon>
            ${this._getRoomName(o)}
            ${this.isDefault ? "" : l`<button class="chip-remove" @click=${() => void this._onRemoveRoom(o)}>×</button>`}
          </span>
        `)}
        ${t.length > 0 ? l`
            <search-picker
              .items=${t}
              triggerLabel="Add room"
              triggerIcon="mdi:plus"
              placeholder="Search rooms…"
              @picked=${this._onRoomPicked}
            ></search-picker>
          ` : ""}
      </div>
    `;
  }
};
Be.styles = A`
    :host {
      display: block;
    }

    /* Zone name display and edit */
    .zone-name {
      font-size: 20px;
      font-weight: 500;
      margin: 0 0 16px 0;
      padding: 4px 8px;
      border-radius: 4px;
      cursor: pointer;
      color: var(--primary-text-color);
      display: inline-block;
    }

    .zone-name:hover {
      background: var(--secondary-background-color);
    }

    .zone-name-input {
      font-size: 20px;
      font-weight: 500;
      width: 100%;
      padding: 4px 8px;
      margin-bottom: 16px;
      font-family: inherit;
      color: var(--primary-text-color);
      background-color: var(--card-background-color, var(--secondary-background-color));
      border: 1px solid var(--primary-color);
      border-width: 2px;
      border-radius: 4px;
      outline: none;
      box-sizing: border-box;
    }

    /* Delete row (top of zone tab, custom zones only) */
    .delete-row {
      display: flex;
      flex-direction: row;
      align-items: center;
      gap: 8px;
      justify-content: flex-end;
      margin-bottom: 8px;
    }

    .delete-btn {
      background: none;
      border: 1px solid var(--divider-color, rgba(0,0,0,0.12));
      color: var(--secondary-text-color);
      padding: 6px 12px;
      border-radius: 4px;
      cursor: pointer;
      font-size: 14px;
      font-family: inherit;
    }

    .delete-btn:hover {
      background: var(--secondary-background-color);
    }

    .cancel-btn {
      background: none;
      border: 1px solid var(--divider-color, rgba(0,0,0,0.12));
      color: var(--secondary-text-color);
      padding: 6px 12px;
      border-radius: 4px;
      cursor: pointer;
      font-size: 14px;
      font-family: inherit;
    }

    .cancel-btn:hover {
      background: var(--secondary-background-color);
    }

    .danger-btn {
      background: var(--error-color, #db4437);
      color: white;
      border: none;
      padding: 6px 12px;
      border-radius: 4px;
      cursor: pointer;
      font-size: 14px;
      font-family: inherit;
    }

    .danger-btn:hover {
      opacity: 0.9;
    }

    /* Mode select — from global-settings-tab.ts */
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

    /* Section labels — from global-settings-tab.ts */
    .section-divider {
      margin: 16px 0 8px;
      font-size: 12px;
      font-weight: 600;
      letter-spacing: 0.5px;
      text-transform: uppercase;
      color: var(--secondary-text-color);
    }

    .section-label {
      font-size: 12px;
      font-weight: 600;
      letter-spacing: 0.5px;
      text-transform: uppercase;
      color: var(--secondary-text-color);
      margin-bottom: 8px;
    }

    /* Chip association UI — from room-card.ts */
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
      background: var(--secondary-background-color);
    }

    .chip-add ha-icon {
      --mdc-icon-size: 16px;
      width: 16px;
      height: 16px;
    }
  `;
let k = Be;
E([
  u({ attribute: !1 })
], k.prototype, "config");
E([
  u({ attribute: !1 })
], k.prototype, "zoneId");
E([
  u({ attribute: !1 })
], k.prototype, "zoneConfig");
E([
  u({ type: Boolean })
], k.prototype, "isDefault");
E([
  u({ attribute: !1 })
], k.prototype, "ws");
E([
  u({ attribute: !1 })
], k.prototype, "panel");
E([
  u({ attribute: !1 })
], k.prototype, "hass");
E([
  v()
], k.prototype, "_editingName");
E([
  v()
], k.prototype, "_nameInputValue");
E([
  v()
], k.prototype, "_confirmingDelete");
customElements.define("climate-manager-zone-tab", k);
var Xt = Object.defineProperty, I = (a, e, t, o) => {
  for (var s = void 0, r = a.length - 1, i; r >= 0; r--)
    (i = a[r]) && (s = i(e, t, s) || s);
  return s && Xt(e, t, s), s;
};
const Fe = class Fe extends w {
  constructor() {
    super(...arguments), this.narrow = !1, this.panel = null, this._config = null, this._status = null, this._activeTab = localStorage.getItem("climate-manager-tab") ?? "global", this._unsubStatus = null, this._wsError = !1, this._ws = null;
  }
  connectedCallback() {
    super.connectedCallback(), this._ws = new pe(this.hass), this._loadConfig(), this._loadStatus(), this._subscribeStatus();
  }
  disconnectedCallback() {
    super.disconnectedCallback(), this._unsubStatus && (this._unsubStatus.then((e) => e()).catch(() => {
    }), this._unsubStatus = null);
  }
  _validateActiveTab() {
    if (this._config && !(this._activeTab === "global" || this._activeTab === "rooms" || this._activeTab === "persons" || this._activeTab === "zone_default")) {
      if (this._activeTab.startsWith("zone_")) {
        const e = this._activeTab.slice(5);
        this._config.zones[e] || (this._activeTab = "global", localStorage.setItem("climate-manager-tab", "global"));
        return;
      }
      this._activeTab = "global", localStorage.setItem("climate-manager-tab", "global");
    }
  }
  async _loadConfig() {
    this._ws || (this._ws = new pe(this.hass));
    try {
      this._config = await this._ws.getConfig(), this._validateActiveTab();
    } catch {
      this._wsError = !0;
    }
  }
  async _loadStatus() {
    this._ws || (this._ws = new pe(this.hass));
    try {
      this._status = await this._ws.getStatus();
    } catch {
    }
  }
  _subscribeStatus() {
    this._ws || (this._ws = new pe(this.hass)), this._unsubStatus = this._ws.subscribeStatus((e) => {
      this._status = e, this._wsError = !1;
    }).catch(() => (this._wsError = !0, () => {
    }));
  }
  /** Show a toast notification. Called by tab components after a save. */
  showToast(e, t) {
    var o;
    (o = this._toast) == null || o.show(e, t);
  }
  /** Patch a subset of _config in-place without a WS round-trip. */
  patchConfig(e) {
    this._config && (this._config = { ...this._config, ...e });
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
  async _onCreateZone() {
    var t, o, s;
    if (!this._config || !this._ws) return;
    const e = `Zone ${Object.keys(this._config.zones).length + 1}`;
    try {
      const r = await this._ws.createZone(e);
      await this._loadConfig(), this._setTab("zone_" + r.zone_id), await this.updateComplete;
      const i = (t = this.shadowRoot) == null ? void 0 : t.querySelector("climate-manager-zone-tab");
      (s = (o = i == null ? void 0 : i.shadowRoot) == null ? void 0 : o.querySelector(".zone-name")) == null || s.click(), this.showToast("Zone created", !1);
    } catch {
      this.showToast("Create zone failed", !0);
    }
  }
  _setTab(e) {
    this._activeTab = e, localStorage.setItem("climate-manager-tab", e);
  }
  render() {
    return this._config ? l`
      <div class="panel-header">Climate Manager</div>

      ${this._wsError ? l`<div class="error-banner">Connection lost. Reconnecting…</div>` : ""}

      <div class="tab-bar">
        <button
          class="tab-btn ${this._activeTab === "global" ? "active" : ""}"
          @click=${() => this._setTab("global")}
        >Overview</button>
        <button
          class="tab-btn ${this._activeTab === "zone_default" ? "active" : ""}"
          @click=${() => this._setTab("zone_default")}
        >${this._config.default_zone_name}</button>
        ${Object.entries(this._config.zones).map(([e, t]) => l`
          <button
            class="tab-btn ${this._activeTab === "zone_" + e ? "active" : ""}"
            @click=${() => this._setTab("zone_" + e)}
          >${t.name}</button>
        `)}
        <button
          class="tab-btn add-zone-btn"
          title="Add zone"
          @click=${() => void this._onCreateZone()}
        >+</button>
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
    if (this._activeTab === "zone_default")
      return l`<climate-manager-zone-tab
        .config=${this._config}
        .zoneId=${"default"}
        .zoneConfig=${{
        name: this._config.default_zone_name,
        mode: this._config.global_mode,
        time_program: this._config.global_time_program
      }}
        .isDefault=${!0}
        .ws=${this._ws}
        .panel=${this}
        .hass=${this.hass}
      ></climate-manager-zone-tab>`;
    if (this._activeTab.startsWith("zone_")) {
      const e = this._activeTab.slice(5), t = this._config.zones[e];
      return t ? l`<climate-manager-zone-tab
        .config=${this._config}
        .zoneId=${e}
        .zoneConfig=${t}
        .isDefault=${!1}
        .ws=${this._ws}
        .panel=${this}
        .hass=${this.hass}
      ></climate-manager-zone-tab>` : l``;
    }
    switch (this._activeTab) {
      case "global":
        return l`<climate-manager-global-settings-tab
          .config=${this._config}
          .status=${this._status}
          .ws=${this._ws}
          .panel=${this}
          .hass=${this.hass}
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
Fe.styles = A`
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
      color: var(--text-primary-color, white);
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

    .add-zone-btn {
      font-size: 18px;
      font-weight: 300;
      padding: 12px 14px;
    }
  `;
let T = Fe;
I([
  u({ attribute: !1 })
], T.prototype, "hass");
I([
  u({ type: Boolean })
], T.prototype, "narrow");
I([
  u({ attribute: !1 })
], T.prototype, "panel");
I([
  v()
], T.prototype, "_config");
I([
  v()
], T.prototype, "_status");
I([
  v()
], T.prototype, "_activeTab");
I([
  v()
], T.prototype, "_unsubStatus");
I([
  v()
], T.prototype, "_wsError");
I([
  Rt("climate-manager-toast")
], T.prototype, "_toast");
customElements.define("climate-manager-panel", T);
export {
  T as ClimateManagerPanel
};
