/**
 * @license
 * Copyright 2019 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const dt = globalThis, St = dt.ShadowRoot && (dt.ShadyCSS === void 0 || dt.ShadyCSS.nativeShadow) && "adoptedStyleSheets" in Document.prototype && "replace" in CSSStyleSheet.prototype, Ct = Symbol(), Ft = /* @__PURE__ */ new WeakMap();
let ee = class {
  constructor(t, e, o) {
    if (this._$cssResult$ = !0, o !== Ct) throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");
    this.cssText = t, this.t = e;
  }
  get styleSheet() {
    let t = this.o;
    const e = this.t;
    if (St && t === void 0) {
      const o = e !== void 0 && e.length === 1;
      o && (t = Ft.get(e)), t === void 0 && ((this.o = t = new CSSStyleSheet()).replaceSync(this.cssText), o && Ft.set(e, t));
    }
    return t;
  }
  toString() {
    return this.cssText;
  }
};
const se = (a) => new ee(typeof a == "string" ? a : a + "", void 0, Ct), M = (a, ...t) => {
  const e = a.length === 1 ? a[0] : t.reduce((o, s, r) => o + ((i) => {
    if (i._$cssResult$ === !0) return i.cssText;
    if (typeof i == "number") return i;
    throw Error("Value passed to 'css' function must be a 'css' function result: " + i + ". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.");
  })(s) + a[r + 1], a[0]);
  return new ee(e, a, Ct);
}, ce = (a, t) => {
  if (St) a.adoptedStyleSheets = t.map((e) => e instanceof CSSStyleSheet ? e : e.styleSheet);
  else for (const e of t) {
    const o = document.createElement("style"), s = dt.litNonce;
    s !== void 0 && o.setAttribute("nonce", s), o.textContent = e.cssText, a.appendChild(o);
  }
}, qt = St ? (a) => a : (a) => a instanceof CSSStyleSheet ? ((t) => {
  let e = "";
  for (const o of t.cssRules) e += o.cssText;
  return se(e);
})(a) : a;
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const { is: le, defineProperty: de, getOwnPropertyDescriptor: pe, getOwnPropertyNames: he, getOwnPropertySymbols: ue, getPrototypeOf: me } = Object, H = globalThis, Xt = H.trustedTypes, ge = Xt ? Xt.emptyScript : "", mt = H.reactiveElementPolyfillSupport, tt = (a, t) => a, pt = { toAttribute(a, t) {
  switch (t) {
    case Boolean:
      a = a ? ge : null;
      break;
    case Object:
    case Array:
      a = a == null ? a : JSON.stringify(a);
  }
  return a;
}, fromAttribute(a, t) {
  let e = a;
  switch (t) {
    case Boolean:
      e = a !== null;
      break;
    case Number:
      e = a === null ? null : Number(a);
      break;
    case Object:
    case Array:
      try {
        e = JSON.parse(a);
      } catch {
        e = null;
      }
  }
  return e;
} }, Pt = (a, t) => !le(a, t), Yt = { attribute: !0, type: String, converter: pt, reflect: !1, useDefault: !1, hasChanged: Pt };
Symbol.metadata ?? (Symbol.metadata = Symbol("metadata")), H.litPropertyMetadata ?? (H.litPropertyMetadata = /* @__PURE__ */ new WeakMap());
let V = class extends HTMLElement {
  static addInitializer(t) {
    this._$Ei(), (this.l ?? (this.l = [])).push(t);
  }
  static get observedAttributes() {
    return this.finalize(), this._$Eh && [...this._$Eh.keys()];
  }
  static createProperty(t, e = Yt) {
    if (e.state && (e.attribute = !1), this._$Ei(), this.prototype.hasOwnProperty(t) && ((e = Object.create(e)).wrapped = !0), this.elementProperties.set(t, e), !e.noAccessor) {
      const o = Symbol(), s = this.getPropertyDescriptor(t, o, e);
      s !== void 0 && de(this.prototype, t, s);
    }
  }
  static getPropertyDescriptor(t, e, o) {
    const { get: s, set: r } = pe(this.prototype, t) ?? { get() {
      return this[e];
    }, set(i) {
      this[e] = i;
    } };
    return { get: s, set(i) {
      const n = s == null ? void 0 : s.call(this);
      r == null || r.call(this, i), this.requestUpdate(t, n, o);
    }, configurable: !0, enumerable: !0 };
  }
  static getPropertyOptions(t) {
    return this.elementProperties.get(t) ?? Yt;
  }
  static _$Ei() {
    if (this.hasOwnProperty(tt("elementProperties"))) return;
    const t = me(this);
    t.finalize(), t.l !== void 0 && (this.l = [...t.l]), this.elementProperties = new Map(t.elementProperties);
  }
  static finalize() {
    if (this.hasOwnProperty(tt("finalized"))) return;
    if (this.finalized = !0, this._$Ei(), this.hasOwnProperty(tt("properties"))) {
      const e = this.properties, o = [...he(e), ...ue(e)];
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
      for (const s of o) e.unshift(qt(s));
    } else t !== void 0 && e.push(qt(t));
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
    return ce(t, this.constructor.elementStyles), t;
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
      const i = (((r = o.converter) == null ? void 0 : r.toAttribute) !== void 0 ? o.converter : pt).toAttribute(e, o.type);
      this._$Em = t, i == null ? this.removeAttribute(s) : this.setAttribute(s, i), this._$Em = null;
    }
  }
  _$AK(t, e) {
    var r, i;
    const o = this.constructor, s = o._$Eh.get(t);
    if (s !== void 0 && this._$Em !== s) {
      const n = o.getPropertyOptions(s), c = typeof n.converter == "function" ? { fromAttribute: n.converter } : ((r = n.converter) == null ? void 0 : r.fromAttribute) !== void 0 ? n.converter : pt;
      this._$Em = s;
      const l = c.fromAttribute(e, n.type);
      this[s] = l ?? ((i = this._$Ej) == null ? void 0 : i.get(s)) ?? l, this._$Em = null;
    }
  }
  requestUpdate(t, e, o, s = !1, r) {
    var i;
    if (t !== void 0) {
      const n = this.constructor;
      if (s === !1 && (r = this[t]), o ?? (o = n.getPropertyOptions(t)), !((o.hasChanged ?? Pt)(r, e) || o.useDefault && o.reflect && r === ((i = this._$Ej) == null ? void 0 : i.get(t)) && !this.hasAttribute(n._$Eu(t, o)))) return;
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
        const { wrapped: n } = i, c = this[r];
        n !== !0 || this._$AL.has(r) || c === void 0 || this.C(r, void 0, i, c);
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
V.elementStyles = [], V.shadowRootOptions = { mode: "open" }, V[tt("elementProperties")] = /* @__PURE__ */ new Map(), V[tt("finalized")] = /* @__PURE__ */ new Map(), mt == null || mt({ ReactiveElement: V }), (H.reactiveElementVersions ?? (H.reactiveElementVersions = [])).push("2.1.2");
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const et = globalThis, Vt = (a) => a, ht = et.trustedTypes, Gt = ht ? ht.createPolicy("lit-html", { createHTML: (a) => a }) : void 0, oe = "$lit$", z = `lit$${Math.random().toFixed(9).slice(2)}$`, re = "?" + z, fe = `<${re}>`, X = document, st = () => X.createComment(""), ot = (a) => a === null || typeof a != "object" && typeof a != "function", kt = Array.isArray, _e = (a) => kt(a) || typeof (a == null ? void 0 : a[Symbol.iterator]) == "function", gt = `[ 	
\f\r]`, Z = /<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g, Wt = /-->/g, Jt = />/g, j = RegExp(`>|${gt}(?:([^\\s"'>=/]+)(${gt}*=${gt}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`, "g"), Kt = /'/g, Zt = /"/g, ie = /^(?:script|style|textarea|title)$/i, be = (a) => (t, ...e) => ({ _$litType$: a, strings: t, values: e }), d = be(1), G = Symbol.for("lit-noChange"), $ = Symbol.for("lit-nothing"), Qt = /* @__PURE__ */ new WeakMap(), F = X.createTreeWalker(X, 129);
function ae(a, t) {
  if (!kt(a) || !a.hasOwnProperty("raw")) throw Error("invalid template strings array");
  return Gt !== void 0 ? Gt.createHTML(t) : t;
}
const ve = (a, t) => {
  const e = a.length - 1, o = [];
  let s, r = t === 2 ? "<svg>" : t === 3 ? "<math>" : "", i = Z;
  for (let n = 0; n < e; n++) {
    const c = a[n];
    let l, h, p = -1, _ = 0;
    for (; _ < c.length && (i.lastIndex = _, h = i.exec(c), h !== null); ) _ = i.lastIndex, i === Z ? h[1] === "!--" ? i = Wt : h[1] !== void 0 ? i = Jt : h[2] !== void 0 ? (ie.test(h[2]) && (s = RegExp("</" + h[2], "g")), i = j) : h[3] !== void 0 && (i = j) : i === j ? h[0] === ">" ? (i = s ?? Z, p = -1) : h[1] === void 0 ? p = -2 : (p = i.lastIndex - h[2].length, l = h[1], i = h[3] === void 0 ? j : h[3] === '"' ? Zt : Kt) : i === Zt || i === Kt ? i = j : i === Wt || i === Jt ? i = Z : (i = j, s = void 0);
    const b = i === j && a[n + 1].startsWith("/>") ? " " : "";
    r += i === Z ? c + fe : p >= 0 ? (o.push(l), c.slice(0, p) + oe + c.slice(p) + z + b) : c + z + (p === -2 ? n : b);
  }
  return [ae(a, r + (a[e] || "<?>") + (t === 2 ? "</svg>" : t === 3 ? "</math>" : "")), o];
};
class rt {
  constructor({ strings: t, _$litType$: e }, o) {
    let s;
    this.parts = [];
    let r = 0, i = 0;
    const n = t.length - 1, c = this.parts, [l, h] = ve(t, e);
    if (this.el = rt.createElement(l, o), F.currentNode = this.el.content, e === 2 || e === 3) {
      const p = this.el.content.firstChild;
      p.replaceWith(...p.childNodes);
    }
    for (; (s = F.nextNode()) !== null && c.length < n; ) {
      if (s.nodeType === 1) {
        if (s.hasAttributes()) for (const p of s.getAttributeNames()) if (p.endsWith(oe)) {
          const _ = h[i++], b = s.getAttribute(p).split(z), y = /([.?@])?(.*)/.exec(_);
          c.push({ type: 1, index: r, name: y[2], strings: b, ctor: y[1] === "." ? xe : y[1] === "?" ? $e : y[1] === "@" ? we : ut }), s.removeAttribute(p);
        } else p.startsWith(z) && (c.push({ type: 6, index: r }), s.removeAttribute(p));
        if (ie.test(s.tagName)) {
          const p = s.textContent.split(z), _ = p.length - 1;
          if (_ > 0) {
            s.textContent = ht ? ht.emptyScript : "";
            for (let b = 0; b < _; b++) s.append(p[b], st()), F.nextNode(), c.push({ type: 2, index: ++r });
            s.append(p[_], st());
          }
        }
      } else if (s.nodeType === 8) if (s.data === re) c.push({ type: 2, index: r });
      else {
        let p = -1;
        for (; (p = s.data.indexOf(z, p + 1)) !== -1; ) c.push({ type: 7, index: r }), p += z.length - 1;
      }
      r++;
    }
  }
  static createElement(t, e) {
    const o = X.createElement("template");
    return o.innerHTML = t, o;
  }
}
function W(a, t, e = a, o) {
  var i, n;
  if (t === G) return t;
  let s = o !== void 0 ? (i = e._$Co) == null ? void 0 : i[o] : e._$Cl;
  const r = ot(t) ? void 0 : t._$litDirective$;
  return (s == null ? void 0 : s.constructor) !== r && ((n = s == null ? void 0 : s._$AO) == null || n.call(s, !1), r === void 0 ? s = void 0 : (s = new r(a), s._$AT(a, e, o)), o !== void 0 ? (e._$Co ?? (e._$Co = []))[o] = s : e._$Cl = s), s !== void 0 && (t = W(a, s._$AS(a, t.values), s, o)), t;
}
class ye {
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
    const { el: { content: e }, parts: o } = this._$AD, s = ((t == null ? void 0 : t.creationScope) ?? X).importNode(e, !0);
    F.currentNode = s;
    let r = F.nextNode(), i = 0, n = 0, c = o[0];
    for (; c !== void 0; ) {
      if (i === c.index) {
        let l;
        c.type === 2 ? l = new it(r, r.nextSibling, this, t) : c.type === 1 ? l = new c.ctor(r, c.name, c.strings, this, t) : c.type === 6 && (l = new Se(r, this, t)), this._$AV.push(l), c = o[++n];
      }
      i !== (c == null ? void 0 : c.index) && (r = F.nextNode(), i++);
    }
    return F.currentNode = X, s;
  }
  p(t) {
    let e = 0;
    for (const o of this._$AV) o !== void 0 && (o.strings !== void 0 ? (o._$AI(t, o, e), e += o.strings.length - 2) : o._$AI(t[e])), e++;
  }
}
class it {
  get _$AU() {
    var t;
    return ((t = this._$AM) == null ? void 0 : t._$AU) ?? this._$Cv;
  }
  constructor(t, e, o, s) {
    this.type = 2, this._$AH = $, this._$AN = void 0, this._$AA = t, this._$AB = e, this._$AM = o, this.options = s, this._$Cv = (s == null ? void 0 : s.isConnected) ?? !0;
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
    t = W(this, t, e), ot(t) ? t === $ || t == null || t === "" ? (this._$AH !== $ && this._$AR(), this._$AH = $) : t !== this._$AH && t !== G && this._(t) : t._$litType$ !== void 0 ? this.$(t) : t.nodeType !== void 0 ? this.T(t) : _e(t) ? this.k(t) : this._(t);
  }
  O(t) {
    return this._$AA.parentNode.insertBefore(t, this._$AB);
  }
  T(t) {
    this._$AH !== t && (this._$AR(), this._$AH = this.O(t));
  }
  _(t) {
    this._$AH !== $ && ot(this._$AH) ? this._$AA.nextSibling.data = t : this.T(X.createTextNode(t)), this._$AH = t;
  }
  $(t) {
    var r;
    const { values: e, _$litType$: o } = t, s = typeof o == "number" ? this._$AC(t) : (o.el === void 0 && (o.el = rt.createElement(ae(o.h, o.h[0]), this.options)), o);
    if (((r = this._$AH) == null ? void 0 : r._$AD) === s) this._$AH.p(e);
    else {
      const i = new ye(s, this), n = i.u(this.options);
      i.p(e), this.T(n), this._$AH = i;
    }
  }
  _$AC(t) {
    let e = Qt.get(t.strings);
    return e === void 0 && Qt.set(t.strings, e = new rt(t)), e;
  }
  k(t) {
    kt(this._$AH) || (this._$AH = [], this._$AR());
    const e = this._$AH;
    let o, s = 0;
    for (const r of t) s === e.length ? e.push(o = new it(this.O(st()), this.O(st()), this, this.options)) : o = e[s], o._$AI(r), s++;
    s < e.length && (this._$AR(o && o._$AB.nextSibling, s), e.length = s);
  }
  _$AR(t = this._$AA.nextSibling, e) {
    var o;
    for ((o = this._$AP) == null ? void 0 : o.call(this, !1, !0, e); t !== this._$AB; ) {
      const s = Vt(t).nextSibling;
      Vt(t).remove(), t = s;
    }
  }
  setConnected(t) {
    var e;
    this._$AM === void 0 && (this._$Cv = t, (e = this._$AP) == null || e.call(this, t));
  }
}
class ut {
  get tagName() {
    return this.element.tagName;
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  constructor(t, e, o, s, r) {
    this.type = 1, this._$AH = $, this._$AN = void 0, this.element = t, this.name = e, this._$AM = s, this.options = r, o.length > 2 || o[0] !== "" || o[1] !== "" ? (this._$AH = Array(o.length - 1).fill(new String()), this.strings = o) : this._$AH = $;
  }
  _$AI(t, e = this, o, s) {
    const r = this.strings;
    let i = !1;
    if (r === void 0) t = W(this, t, e, 0), i = !ot(t) || t !== this._$AH && t !== G, i && (this._$AH = t);
    else {
      const n = t;
      let c, l;
      for (t = r[0], c = 0; c < r.length - 1; c++) l = W(this, n[o + c], e, c), l === G && (l = this._$AH[c]), i || (i = !ot(l) || l !== this._$AH[c]), l === $ ? t = $ : t !== $ && (t += (l ?? "") + r[c + 1]), this._$AH[c] = l;
    }
    i && !s && this.j(t);
  }
  j(t) {
    t === $ ? this.element.removeAttribute(this.name) : this.element.setAttribute(this.name, t ?? "");
  }
}
class xe extends ut {
  constructor() {
    super(...arguments), this.type = 3;
  }
  j(t) {
    this.element[this.name] = t === $ ? void 0 : t;
  }
}
class $e extends ut {
  constructor() {
    super(...arguments), this.type = 4;
  }
  j(t) {
    this.element.toggleAttribute(this.name, !!t && t !== $);
  }
}
class we extends ut {
  constructor(t, e, o, s, r) {
    super(t, e, o, s, r), this.type = 5;
  }
  _$AI(t, e = this) {
    if ((t = W(this, t, e, 0) ?? $) === G) return;
    const o = this._$AH, s = t === $ && o !== $ || t.capture !== o.capture || t.once !== o.once || t.passive !== o.passive, r = t !== $ && (o === $ || s);
    s && this.element.removeEventListener(this.name, this, o), r && this.element.addEventListener(this.name, this, t), this._$AH = t;
  }
  handleEvent(t) {
    var e;
    typeof this._$AH == "function" ? this._$AH.call(((e = this.options) == null ? void 0 : e.host) ?? this.element, t) : this._$AH.handleEvent(t);
  }
}
class Se {
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
const ft = et.litHtmlPolyfillSupport;
ft == null || ft(rt, it), (et.litHtmlVersions ?? (et.litHtmlVersions = [])).push("3.3.3");
const Ce = (a, t, e) => {
  const o = (e == null ? void 0 : e.renderBefore) ?? t;
  let s = o._$litPart$;
  if (s === void 0) {
    const r = (e == null ? void 0 : e.renderBefore) ?? null;
    o._$litPart$ = s = new it(t.insertBefore(st(), r), r, void 0, e ?? {});
  }
  return s._$AI(a), s;
};
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const q = globalThis;
class S extends V {
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
    this.hasUpdated || (this.renderOptions.isConnected = this.isConnected), super.update(t), this._$Do = Ce(e, this.renderRoot, this.renderOptions);
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
var te;
S._$litElement$ = !0, S.finalized = !0, (te = q.litElementHydrateSupport) == null || te.call(q, { LitElement: S });
const _t = q.litElementPolyfillSupport;
_t == null || _t({ LitElement: S });
(q.litElementVersions ?? (q.litElementVersions = [])).push("4.2.2");
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const Pe = { attribute: !0, type: String, converter: pt, reflect: !1, hasChanged: Pt }, ke = (a = Pe, t, e) => {
  const { kind: o, metadata: s } = e;
  let r = globalThis.litPropertyMetadata.get(s);
  if (r === void 0 && globalThis.litPropertyMetadata.set(s, r = /* @__PURE__ */ new Map()), o === "setter" && ((a = Object.create(a)).wrapped = !0), r.set(e.name, a), o === "accessor") {
    const { name: i } = e;
    return { set(n) {
      const c = t.get.call(this);
      t.set.call(this, n), this.requestUpdate(i, c, a, !0, n);
    }, init(n) {
      return n !== void 0 && this.C(i, void 0, a, n), n;
    } };
  }
  if (o === "setter") {
    const { name: i } = e;
    return function(n) {
      const c = this[i];
      t.call(this, n), this.requestUpdate(i, c, a, !0, n);
    };
  }
  throw Error("Unsupported decorator location: " + o);
};
function m(a) {
  return (t, e) => typeof e == "object" ? ke(a, t, e) : ((o, s, r) => {
    const i = s.hasOwnProperty(r);
    return s.constructor.createProperty(r, o), i ? Object.getOwnPropertyDescriptor(s, r) : void 0;
  })(a, t, e);
}
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
function x(a) {
  return m({ ...a, state: !0, attribute: !1 });
}
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const Ee = (a, t, e) => (e.configurable = !0, e.enumerable = !0, Reflect.decorate && typeof t != "object" && Object.defineProperty(a, t, e), e);
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
function Te(a, t) {
  return (e, o, s) => {
    const r = (i) => {
      var n;
      return ((n = i.renderRoot) == null ? void 0 : n.querySelector(a)) ?? null;
    };
    return Ee(e, o, { get() {
      return r(this);
    } });
  };
}
class lt {
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
var Ae = Object.defineProperty, Et = (a, t, e, o) => {
  for (var s = void 0, r = a.length - 1, i; r >= 0; r--)
    (i = a[r]) && (s = i(t, e, s) || s);
  return s && Ae(t, e, s), s;
};
const Rt = class Rt extends S {
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
Rt.styles = M`
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
let J = Rt;
Et([
  x()
], J.prototype, "_visible");
Et([
  x()
], J.prototype, "_message");
Et([
  x()
], J.prototype, "_isError");
customElements.define("climate-manager-toast", J);
const B = {
  frost_protection: "#1565C0",
  reduced: "#0277BD",
  normal: "#2E7D32",
  comfort: "#E65100"
}, Q = {
  present: "#2E7D32",
  absent: "#9E9E9E"
}, Tt = {
  frost_protection: "Frost protection",
  reduced: "Reduced",
  normal: "Normal",
  comfort: "Comfort",
  present: "Present",
  absent: "Absent"
};
var Me = Object.defineProperty, R = (a, t, e, o) => {
  for (var s = void 0, r = a.length - 1, i; r >= 0; r--)
    (i = a[r]) && (s = i(t, e, s) || s);
  return s && Me(t, e, s), s;
};
const Re = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], De = ["frost_protection", "reduced", "normal", "comfort"], Oe = ["present", "absent"], Dt = class Dt extends S {
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
    return this.mode === "presence" ? Q[e] ?? Q.absent : B[e] ?? B.frost_protection;
  }
  _labelForPeriod(t) {
    const e = this.mode === "presence" ? t.state ?? "absent" : t.mode ?? "frost_protection";
    return Tt[e] ?? e;
  }
  /**
   * Convert a periods array to renderable segments with computed widths.
   * Always starts at 00:00 — prepends a synthesised period if needed.
   */
  _toSegments(t) {
    if (t.length === 0) return [];
    const e = [...t].sort(
      (n, c) => n.start.localeCompare(c.start)
    ), o = e[0], r = this._timeToMinutes(o.start) > 0 ? [{ start: "00:00", mode: o.mode, state: o.state }, ...e] : e, i = [];
    for (let n = 0; n < r.length; n++) {
      const c = this._timeToMinutes(r[n].start), l = n + 1 < r.length ? this._timeToMinutes(r[n + 1].start) : 1440;
      i.push({ period: r[n], startMin: c, endMin: l });
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
      { key: "present", label: "Present", color: Q.present },
      { key: "absent", label: "Absent", color: Q.absent }
    ] : [
      {
        key: "frost_protection",
        label: "Frost protection",
        color: B.frost_protection
      },
      { key: "reduced", label: "Reduced", color: B.reduced },
      { key: "normal", label: "Normal", color: B.normal },
      { key: "comfort", label: "Comfort", color: B.comfort }
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
    const i = s.sort((c, l) => c.start.localeCompare(l.start)), n = i.filter(
      (c, l) => l === 0 || c.start !== i[l - 1].start
    );
    this._closePopup(), this._emitChange(e, n);
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
    const i = (this.days[e] ?? []).map((n) => n.start === r.period.start ? this.mode === "presence" ? { ...n, state: t } : { ...n, mode: t } : n);
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
    const i = s.startMin + r / 2, n = Math.max(
      s.startMin + 15,
      Math.min(s.endMin - 15, this._snapToMinutes(i))
    ), c = this.mode === "presence" ? Oe : De, l = this.mode === "presence" ? s.period.state ?? "absent" : s.period.mode ?? "frost_protection", h = c.indexOf(l), p = c[(h + 1) % c.length], _ = this.mode === "presence" ? { start: s.period.start, state: l } : { start: s.period.start, mode: l }, b = this.mode === "presence" ? { start: this._minutesToHHMM(n), state: p } : { start: this._minutesToHHMM(n), mode: p }, y = this.days[t] ?? [], u = y.some(
      (g) => g.start === s.period.start
    );
    let f;
    u ? f = y.flatMap(
      (g) => g.start === s.period.start ? [_, b] : [g]
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
    var p;
    if (!this._drag) return;
    const { dayIndex: e, segIndex: o } = this._drag, s = (p = this.shadowRoot) == null ? void 0 : p.querySelector(
      `.day-row:nth-child(${e + 2}) .bar-wrap`
    );
    if (!s) return;
    const r = s.getBoundingClientRect(), i = this._pixelToMinutes(t.clientX - r.left, r.width), n = this._snapToMinutes(i);
    this._dragTooltipMinutes = n, this._dragTooltipX = t.clientX, this._dragTooltipY = t.clientY;
    const c = this._toSegments(this.days[e] ?? []), l = c[o], h = c[o + 1];
    if (l && h) {
      const _ = l.startMin + 15, b = h.endMin - 15, y = Math.max(_, Math.min(b, n)), u = (this.days[e] ?? []).map((g) => g.start === h.period.start ? { ...g, start: this._minutesToHHMM(y) } : g), f = this.days.map(
        (g, v) => v === e ? u : g
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
      const i = s.getBoundingClientRect(), n = this._pixelToMinutes(
        t.clientX - i.left,
        i.width
      ), c = this._snapToMinutes(n), l = this._toSegments(this.days[e] ?? []), h = l[o], p = l[o + 1];
      if (h && p) {
        const _ = h.startMin + 15, b = p.endMin - 15, y = Math.max(
          _,
          Math.min(b, c)
        ), u = (this.days[e] ?? []).map((g) => g.start === p.period.start ? { ...g, start: this._minutesToHHMM(y) } : g), f = this.days.map(
          (g, v) => v === e ? u : g
        );
        this._drag = null, this._dragTooltipMinutes = null, this._dragPreviewDays = f, this._justDragged = !0, this._emitChange(e, u);
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
    return d`
      <div
        class="week-grid"
        @pointermove=${this._onPointerMove}
        @pointerup=${this._onPointerUp}
      >
        <!-- Time axis above day rows — identical structure to bottom axis -->
        ${this._renderTimeAxis()}

        ${Re.map(
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
          @click=${(n) => {
      (n.target.classList.contains("bar-wrap") || n.target.classList.contains("bar-row-inner")) && this._onBarClick(n, e);
    }}
        >
          ${i ? d`<div class="empty-hint">
                Click the bar to add your first period.
              </div>` : d`<div class="bar-row-inner">
                ${r.map(
      (n, c) => this._renderSegment(n, e, c, r.length)
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
    const r = this._colorForPeriod(t.period), i = this._labelForPeriod(t.period), n = (t.endMin - t.startMin) / 1440 * 100, c = this.mode === "presence" ? t.period.state ?? "absent" : ((l = t.period.mode) == null ? void 0 : l.replace(/_/g, " ")) ?? "frost protection";
    return d`
      <div
        class="segment"
        style="width:${n}%;background:${r}"
        aria-label="${c}"
        @click=${(h) => this._onSegmentClick(h, e, o)}
      >
        ${n > 2.7 ? d`<span class="segment-label">${i}</span>` : ""}

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
      const s = `${this._minutesToHHMM(o.startMin)} – ${this._minutesToHHMM(o.endMin)}`, r = this.mode === "presence" ? o.period.state ?? "absent" : ((t = o.period.mode) == null ? void 0 : t.replace(/_/g, " ")) ?? "frost protection", n = o.endMin - o.startMin >= 30;
      return d`
        <div class="popup-title">${s} · ${r}</div>

        <div class="mode-options">
          <div
            style="font-size:11px;color:var(--secondary-text-color);margin-bottom:4px"
          >
            Change mode
          </div>
          ${this._modeOptions().map(
        (c) => d`
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
    return d``;
  }
};
Dt.styles = M`
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
let P = Dt;
R([
  m({ type: Array })
], P.prototype, "days");
R([
  m({ type: String })
], P.prototype, "mode");
R([
  x()
], P.prototype, "_clipboard");
R([
  x()
], P.prototype, "_drag");
R([
  x()
], P.prototype, "_dragTooltipMinutes");
R([
  x()
], P.prototype, "_dragTooltipX");
R([
  x()
], P.prototype, "_dragTooltipY");
R([
  x()
], P.prototype, "_dragPreviewDays");
R([
  x()
], P.prototype, "_popup");
customElements.define("climate-manager-time-bar", P);
var ze = Object.defineProperty, at = (a, t, e, o) => {
  for (var s = void 0, r = a.length - 1, i; r >= 0; r--)
    (i = a[r]) && (s = i(t, e, s) || s);
  return s && ze(t, e, s), s;
};
const ne = [
  "mon",
  "tue",
  "wed",
  "thu",
  "fri",
  "sat",
  "sun"
];
function At(a) {
  return ne.map((t) => a != null && a[t] ? [...a[t]] : []);
}
function Mt(a) {
  return ne[a] ?? "mon";
}
const xt = "off", $t = "time_program", wt = "time_program_presences", He = {
  [xt]: "Off",
  [$t]: "Time program",
  [wt]: "Time program & presences"
}, Ie = {
  frost_protection: 7,
  reduced: 18,
  normal: 20,
  comfort: 22
}, Ne = "time_program", Ue = (() => {
  const a = () => [
    { start: "00:00", mode: "reduced" },
    { start: "06:00", mode: "normal" },
    { start: "22:00", mode: "reduced" }
  ];
  return {
    mon: a(),
    tue: a(),
    wed: a(),
    thu: a(),
    fri: a(),
    sat: a(),
    sun: a()
  };
})(), Ot = class Ot extends S {
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
      const { dayIndex: e, periods: o } = t.detail, s = { ...this.config.global_time_program }, r = Mt(e);
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
        await this.ws.setGlobalMode(Ne), await this.ws.setTimeProgram(Ue), await this.panel.reloadConfig(), this.panel.showToast("Reset to defaults", !1);
      } catch {
        this.panel.showToast("Reset failed — retrying...", !0);
      }
    };
  }
  get _days() {
    var e;
    const t = (e = this.config) == null ? void 0 : e.global_time_program;
    return t !== this._lastProgram && (this._lastProgram = t, this._cachedDays = At(t)), this._cachedDays;
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
    const t = this.status, e = He[(t == null ? void 0 : t.global_mode) ?? this.config.global_mode] ?? (t == null ? void 0 : t.global_mode) ?? this.config.global_mode;
    let o = "No active period";
    t != null && t.active_period && (o = Tt[t.active_period] ?? t.active_period);
    let s = d`<span class="status-value">No one home</span>`;
    return (r = t == null ? void 0 : t.present_persons) != null && r.length && (s = d`
        <span class="status-value">
          ${t.present_persons.map(
      (i, n) => {
        var l, h, p, _;
        const c = ((p = (h = (l = this.hass) == null ? void 0 : l.states[i]) == null ? void 0 : h.attributes) == null ? void 0 : p.friendly_name) ?? i;
        return d`<span class="person-dot"></span>${c}${n < (((_ = t == null ? void 0 : t.present_persons) == null ? void 0 : _.length) ?? 1) - 1 ? ", " : ""}`;
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
  _renderTemperaturesCard() {
    const t = this.config.period_temperatures, e = (o, s, r) => d`
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
    return d`
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
    return d`
      <ha-card>
        <div class="card-header">Configuration</div>
        <div class="card-content">

          <div class="select-wrapper">
            <label class="select-label">Global mode</label>
            <select class="mode-select" @change=${this._onModeChange}>
              <option value=${xt} ?selected=${this.config.global_mode === xt}>Off</option>
              <option value=${$t} ?selected=${this.config.global_mode === $t}>Time program</option>
              <option value=${wt} ?selected=${this.config.global_mode === wt}>Time program &amp; presences</option>
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
    return d`
      ${this._renderStatusCard()}
      ${this._renderTemperaturesCard()}
      ${this._renderConfigCard()}
    `;
  }
};
Ot.styles = M`
    :host {
      display: block;
      --present-color: ${se(Q.present)};
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
let I = Ot;
at([
  m({ attribute: !1 })
], I.prototype, "config");
at([
  m({ attribute: !1 })
], I.prototype, "status");
at([
  m({ attribute: !1 })
], I.prototype, "ws");
at([
  m({ attribute: !1 })
], I.prototype, "panel");
at([
  m({ attribute: !1 })
], I.prototype, "hass");
customElements.define("climate-manager-global-settings-tab", I);
var Le = Object.defineProperty, K = (a, t, e, o) => {
  for (var s = void 0, r = a.length - 1, i; r >= 0; r--)
    (i = a[r]) && (s = i(t, e, s) || s);
  return s && Le(t, e, s), s;
};
const zt = class zt extends S {
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
    return d`
      <button
        class="trigger-btn"
        @click=${this._onTriggerClick}
        aria-expanded=${this._open}
        aria-haspopup="listbox"
      >
        <ha-icon icon=${this.triggerIcon}></ha-icon>
        ${this.triggerLabel}
      </button>

      ${this._open ? d`
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
            ${t.length > 0 ? d`
                <ul class="item-list" role="listbox">
                  ${t.map(
      (e) => d`
                      <li
                        class="item-row"
                        role="option"
                        @click=${() => this._onItemClick(e)}
                      >
                        ${e.icon ? d`<ha-icon class="item-icon" icon=${e.icon}></ha-icon>` : ""}
                        <div class="item-text">
                          <span class="item-label">${e.label}</span>
                          ${e.secondary ? d`<span class="item-secondary">${e.secondary}</span>` : ""}
                        </div>
                      </li>
                    `
    )}
                </ul>
              ` : d`<div class="empty-message">No results</div>`}
          </div>
        ` : ""}
    `;
  }
};
zt.styles = M`
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
let A = zt;
K([
  m({ type: Array })
], A.prototype, "items");
K([
  m({ type: String })
], A.prototype, "placeholder");
K([
  m({ type: String })
], A.prototype, "triggerLabel");
K([
  m({ type: String })
], A.prototype, "triggerIcon");
K([
  x()
], A.prototype, "_open");
K([
  x()
], A.prototype, "_query");
customElements.define("search-picker", A);
var je = Object.defineProperty, T = (a, t, e, o) => {
  for (var s = void 0, r = a.length - 1, i; r >= 0; r--)
    (i = a[r]) && (s = i(t, e, s) || s);
  return s && je(t, e, s), s;
};
const Ht = class Ht extends S {
  constructor() {
    super(...arguments), this.roomStatus = null, this.status = null, this._expanded = !1, this._trvCards = /* @__PURE__ */ new Map();
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
    const o = [...((i = (r = (s = this.panelConfig) == null ? void 0 : s.persons) == null ? void 0 : r[t]) == null ? void 0 : i.room_ids) ?? []].filter((n) => n !== this.roomId);
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
    } }, i = Mt(e);
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
    var f, g, v, w, O;
    const t = this.roomStatus, e = (t == null ? void 0 : t.temperature) != null ? `${t.temperature}°C` : "—", o = (t == null ? void 0 : t.humidity) != null ? `${t.humidity}%` : "—", s = (t == null ? void 0 : t.active_period) ?? null, r = s ? Tt[s] ?? s : "—", i = s != null ? (g = (f = this.panelConfig) == null ? void 0 : f.period_temperatures) == null ? void 0 : g[s] : void 0, n = i != null ? `${r} · ${i}°C` : r, l = this._getAssignedPersonIds().length, h = ((v = this.status) == null ? void 0 : v.global_mode) ?? ((w = this.panelConfig) == null ? void 0 : w.global_mode) ?? "", p = h === "time_program_presences", _ = p ? ((O = this.roomStatus) == null ? void 0 : O.present_person_count) ?? 0 : null, b = _ != null ? `${_}/${l}` : `${l}`, u = {
      off: "Off",
      time_program: "Time program",
      time_program_presences: "Time & presence"
    }[h] ?? h;
    return d`
      <div class="card-header-status">
        <span class="status-item" title="Mode: ${u}">
          <ha-icon icon="mdi:thermometer"></ha-icon>
          ${e}
        </span>
        <span class="status-item">
          <ha-icon icon="mdi:water-percent"></ha-icon>
          ${o}
        </span>
        <span class="status-item" title="${u}">
          <ha-icon icon="mdi:clock-outline"></ha-icon>
          ${n}
        </span>
        <span class="status-item" title="${p ? `${_} present / ${l} assigned` : `${l} assigned`}">
          <ha-icon icon="mdi:account-group"></ha-icon>
          ${b}
        </span>
      </div>
    `;
  }
  _getTrvCard(t) {
    let e = this._trvCards.get(t);
    return e || (e = document.createElement("hui-thermostat-card"), e.setConfig({
      type: "thermostat",
      entity: t
    }), this._trvCards.set(t, e)), e.hass = this.hass, e;
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
        ${t.map((o) => this._getTrvCard(o))}
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
    return d`
      <div class="section-label">Associated persons</div>
      <div class="chips">
        ${t.map((r) => d`
          <span class="chip">
            <ha-icon icon="mdi:account"></ha-icon>
            ${this._getPersonName(r)}
            <button
              class="chip-remove"
              @click=${() => void this._onRemovePerson(r)}
            >×</button>
          </span>
        `)}
        ${o.length > 0 ? d`
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
    return d`
      <ha-card>
        <div class="card-header-row" @click=${() => {
      this._expanded = !this._expanded;
    }}>
          <div class="card-header-left">
            <div class="card-header-top">
              <span class="room-name">${this.roomName}</span>
              <span
                class="program-badge ${e}"
                style=${e === "frost" ? `background: ${B.frost_protection}; color: white;` : ""}
              >${o}</span>
            </div>
            ${this._renderHeaderStatus()}
          </div>
          <ha-icon
            class="expand-icon ${this._expanded ? "expanded" : ""}"
            icon="mdi:chevron-down"
          ></ha-icon>
        </div>

        ${this._expanded ? d`
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
              ${t === "custom" ? d`
                  <div class="time-bar-section">
                    <climate-manager-time-bar
                      mode="schedule"
                      .days=${At(this.config.time_program ?? void 0)}
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
Ht.styles = M`
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
  `;
let C = Ht;
T([
  m({ type: String })
], C.prototype, "roomId");
T([
  m({ type: String })
], C.prototype, "roomName");
T([
  m({ attribute: !1 })
], C.prototype, "config");
T([
  m({ attribute: !1 })
], C.prototype, "roomStatus");
T([
  m({ attribute: !1 })
], C.prototype, "panelConfig");
T([
  m({ attribute: !1 })
], C.prototype, "status");
T([
  m({ attribute: !1 })
], C.prototype, "ws");
T([
  m({ attribute: !1 })
], C.prototype, "panel");
T([
  m({ attribute: !1 })
], C.prototype, "hass");
T([
  x()
], C.prototype, "_expanded");
customElements.define("climate-manager-room-card", C);
var Be = Object.defineProperty, nt = (a, t, e, o) => {
  for (var s = void 0, r = a.length - 1, i; r >= 0; r--)
    (i = a[r]) && (s = i(t, e, s) || s);
  return s && Be(t, e, s), s;
};
const It = class It extends S {
  constructor() {
    super(...arguments), this.status = null;
  }
  _getRoomStatus(t) {
    var e, o;
    return ((o = (e = this.status) == null ? void 0 : e.rooms_status) == null ? void 0 : o.find((s) => s.area_id === t)) ?? null;
  }
  render() {
    var h, p, _, b, y;
    const t = ((h = this.config) == null ? void 0 : h.rooms) ?? {}, e = (((p = this.status) == null ? void 0 : p.rooms_status) ?? []).filter((u) => u.has_trv !== !1), o = /* @__PURE__ */ new Set([
      ...e.map((u) => u.area_id)
    ]);
    if (o.size === 0)
      return d`
        <div class="empty-state">
          No rooms discovered. Create areas in Home Assistant and assign climate entities.
        </div>
      `;
    const s = (u) => {
      var f, g, v;
      return ((v = (g = (f = this.status) == null ? void 0 : f.rooms_status) == null ? void 0 : g.find((w) => w.area_id === u)) == null ? void 0 : v.name) ?? u.replace(/_/g, " ").replace(/\b\w/g, (w) => w.toUpperCase());
    }, r = /* @__PURE__ */ new Map();
    for (const u of o) {
      const f = ((y = (b = (_ = this.hass) == null ? void 0 : _.areas) == null ? void 0 : b[u]) == null ? void 0 : y.floor_id) ?? null;
      r.has(f) || r.set(f, []), r.get(f).push(u);
    }
    for (const u of r.values())
      u.sort((f, g) => s(f).localeCompare(s(g)));
    const i = [...r.keys()].filter((u) => u !== null).sort(
      (u, f) => {
        var g, v, w, O, jt, Bt;
        return (((w = (v = (g = this.hass) == null ? void 0 : g.floors) == null ? void 0 : v[f]) == null ? void 0 : w.level) ?? 0) - (((Bt = (jt = (O = this.hass) == null ? void 0 : O.floors) == null ? void 0 : jt[u]) == null ? void 0 : Bt.level) ?? 0);
      }
    ), n = r.get(null) ?? [], c = (u) => {
      const f = t[u] ?? {}, g = this._getRoomStatus(u), v = s(u);
      return d`
        <climate-manager-room-card
          .roomId=${u}
          .roomName=${v}
          .config=${f}
          .roomStatus=${g}
          .panelConfig=${this.config}
          .status=${this.status}
          .ws=${this.ws}
          .panel=${this.panel}
          .hass=${this.hass}
        ></climate-manager-room-card>
      `;
    }, l = (u) => {
      var v, w;
      const f = (w = (v = this.hass) == null ? void 0 : v.floors) == null ? void 0 : w[u];
      if (f != null && f.icon) return f.icon;
      const g = (f == null ? void 0 : f.level) ?? 0;
      return g === -1 ? "mdi:home-floor-negative-1" : g < 0 ? "mdi:home-floor-b" : g === 1 ? "mdi:home-floor-1" : g === 2 ? "mdi:home-floor-2" : g === 3 || g > 3 ? "mdi:home-floor-3" : "mdi:home-floor-0";
    };
    return d`
      ${i.map((u) => {
      var v, w, O;
      const f = ((O = (w = (v = this.hass) == null ? void 0 : v.floors) == null ? void 0 : w[u]) == null ? void 0 : O.name) ?? u, g = r.get(u) ?? [];
      return d`
          <div class="floor-header">
            <ha-icon icon=${l(u)}></ha-icon>
            ${f}
          </div>
          ${g.map(c)}
        `;
    })}
      ${n.map(c)}
    `;
  }
};
It.styles = M`
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
let N = It;
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
customElements.define("climate-manager-rooms-tab", N);
var Fe = Object.defineProperty, L = (a, t, e, o) => {
  for (var s = void 0, r = a.length - 1, i; r >= 0; r--)
    (i = a[r]) && (s = i(t, e, s) || s);
  return s && Fe(t, e, s), s;
};
const Y = "scheduled", bt = "ha", vt = "force_present", yt = "force_absent", qe = {
  mon: [{ start: "00:00", state: "present" }, { start: "08:00", state: "absent" }, { start: "18:00", state: "present" }],
  tue: [{ start: "00:00", state: "present" }, { start: "08:00", state: "absent" }, { start: "18:00", state: "present" }],
  wed: [{ start: "00:00", state: "present" }, { start: "08:00", state: "absent" }, { start: "18:00", state: "present" }],
  thu: [{ start: "00:00", state: "present" }, { start: "08:00", state: "absent" }, { start: "18:00", state: "present" }],
  fri: [{ start: "00:00", state: "present" }, { start: "08:00", state: "absent" }, { start: "18:00", state: "present" }],
  sat: [{ start: "00:00", state: "present" }],
  sun: [{ start: "00:00", state: "present" }]
}, Nt = class Nt extends S {
  constructor() {
    super(...arguments), this.roomChoices = [], this.status = null, this._expanded = !1, this._lastSchedule = void 0, this._cachedDays = [];
  }
  get _days() {
    var e;
    const t = (e = this.config) == null ? void 0 : e.schedule;
    return t !== this._lastSchedule && (this._lastSchedule = t, this._cachedDays = At(t)), this._cachedDays;
  }
  connectedCallback() {
    super.connectedCallback(), this._expanded = !1;
  }
  // -----------------------------------------------------------------------
  // Save handlers
  // -----------------------------------------------------------------------
  async _onModeChange(t) {
    var o;
    const e = t.target.value;
    if (e)
      try {
        const s = !!((o = this.config) != null && o.schedule) && Object.values(this.config.schedule).some((r) => r.length > 0);
        e === Y && !s ? await this.ws.setPersonConfig(this.personId, { mode: e, schedule: qe }) : await this.ws.setPersonConfig(this.personId, { mode: e }), await this.panel.reloadConfig(), this.panel.showToast("Saved", !1);
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
    } }, i = Mt(e);
    r[i] = o;
    try {
      await this.ws.setPersonConfig(this.personId, { schedule: r }), await this.panel.reloadConfig(), this.panel.showToast("Saved", !1);
    } catch {
      this.panel.showToast("Save failed — retrying...", !0);
    }
    t.stopPropagation();
  }
  // -----------------------------------------------------------------------
  // Helpers
  // -----------------------------------------------------------------------
  _isCurrentlyPresent() {
    var t, e;
    return ((e = (t = this.status) == null ? void 0 : t.present_persons) == null ? void 0 : e.includes(this.personId)) ?? !1;
  }
  // -----------------------------------------------------------------------
  // Render
  // -----------------------------------------------------------------------
  _getBadgeInfo() {
    var e;
    switch (((e = this.config) == null ? void 0 : e.mode) ?? Y) {
      case vt:
        return { cls: "force-present", text: "Force Present" };
      case yt:
        return { cls: "force-absent", text: "Force Absent" };
      case bt:
        return { cls: "ha", text: "HA" };
      default:
        return { cls: "scheduled", text: "Scheduled" };
    }
  }
  render() {
    var n, c;
    const { cls: t, text: e } = this._getBadgeInfo(), o = ((n = this.config) == null ? void 0 : n.mode) ?? Y, s = o === Y, r = ((c = this.config) == null ? void 0 : c.room_ids) ?? [], i = this.roomChoices.filter((l) => !r.includes(l.id));
    return d`
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
                  <option value=${Y} ?selected=${o === Y}>Scheduled</option>
                  <option value=${bt} ?selected=${o === bt}>HA</option>
                  <option value=${vt} ?selected=${o === vt}>Force Present</option>
                  <option value=${yt} ?selected=${o === yt}>Force Absent</option>
                </select>
              </div>

              <!-- Room associations as chips -->
              <div class="section-label">Room associations</div>
              <div class="chips">
                ${r.map((l) => {
      const h = this.roomChoices.find((p) => p.id === l);
      return h ? d`
                    <span class="chip">
                      <ha-icon icon="mdi:home-outline"></ha-icon>
                      ${h.name}
                      <button
                        class="chip-remove"
                        @click=${() => void this._onRoomToggle(l, !1)}
                      >×</button>
                    </span>
                  ` : "";
    })}
                ${i.length > 0 ? d`
                    <search-picker
                      .items=${i.map((l) => ({
      id: l.id,
      label: l.name,
      secondary: l.secondary,
      icon: "mdi:home-outline"
    }))}
                      triggerLabel="Add room"
                      triggerIcon="mdi:plus"
                      placeholder="Search rooms…"
                      @picked=${(l) => {
      const { id: h } = l.detail;
      this._onRoomToggle(h, !0);
    }}
                    ></search-picker>
                  ` : ""}
              </div>

              <!-- Presence schedule (only in Scheduled mode) -->
              ${s ? d`
                  <div class="section-label">Presence schedule</div>
                  <div class="schedule-section">
                    <climate-manager-time-bar
                      mode="presence"
                      .days=${this._days}
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
Nt.styles = M`
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
  `;
let E = Nt;
L([
  m({ type: String })
], E.prototype, "personId");
L([
  m({ type: String })
], E.prototype, "personName");
L([
  m({ attribute: !1 })
], E.prototype, "config");
L([
  m({ attribute: !1 })
], E.prototype, "roomChoices");
L([
  m({ attribute: !1 })
], E.prototype, "ws");
L([
  m({ attribute: !1 })
], E.prototype, "panel");
L([
  m({ attribute: !1 })
], E.prototype, "status");
L([
  x()
], E.prototype, "_expanded");
customElements.define("climate-manager-person-card", E);
var Xe = Object.defineProperty, ct = (a, t, e, o) => {
  for (var s = void 0, r = a.length - 1, i; r >= 0; r--)
    (i = a[r]) && (s = i(t, e, s) || s);
  return s && Xe(t, e, s), s;
};
const Ut = class Ut extends S {
  constructor() {
    super(...arguments), this.status = null;
  }
  /** Build the room choices list — only TRV rooms (excludes chaudière/boiler). */
  _getRoomChoices() {
    var o;
    const t = (((o = this.status) == null ? void 0 : o.rooms_status) ?? []).filter((s) => s.has_trv !== !1);
    return [.../* @__PURE__ */ new Set([
      ...t.map((s) => s.area_id)
    ])].map((s) => {
      var c, l, h, p, _, b, y;
      const r = ((c = t.find((u) => u.area_id === s)) == null ? void 0 : c.name) ?? s.replace(/_/g, " ").replace(/\b\w/g, (u) => u.toUpperCase()), i = ((p = (h = (l = this.hass) == null ? void 0 : l.areas) == null ? void 0 : h[s]) == null ? void 0 : p.floor_id) ?? null, n = i ? ((y = (b = (_ = this.hass) == null ? void 0 : _.floors) == null ? void 0 : b[i]) == null ? void 0 : y.name) ?? void 0 : void 0;
      return { id: s, name: r, secondary: n };
    });
  }
  /** Determine if a person config has any non-default setting (D-15). */
  _isNonDefault(t) {
    var i, n, c;
    const e = (n = (i = this.config) == null ? void 0 : i.persons) == null ? void 0 : n[t];
    if (!e) return !1;
    const o = e.mode != null && e.mode !== "scheduled", s = (((c = e.room_ids) == null ? void 0 : c.length) ?? 0) > 0, r = e.schedule ? Object.values(e.schedule).some((l) => l.length > 0) : !1;
    return o || s || r;
  }
  render() {
    var r;
    const t = ((r = this.config) == null ? void 0 : r.persons) ?? {}, e = Object.keys(t);
    if (e.length === 0)
      return d`
        <div class="empty-state">
          No persons found. Add person entities in Home Assistant.
        </div>
      `;
    const o = [...e].sort((i, n) => {
      const c = this._isNonDefault(i), l = this._isNonDefault(n);
      return c && !l ? -1 : !c && l ? 1 : i.localeCompare(n);
    }), s = this._getRoomChoices();
    return d`
      ${o.map((i) => {
      const n = t[i] ?? {}, c = i.replace(/^person\./, "").replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase());
      return d`
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
Ut.styles = M`
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
let U = Ut;
ct([
  m({ attribute: !1 })
], U.prototype, "config");
ct([
  m({ attribute: !1 })
], U.prototype, "status");
ct([
  m({ attribute: !1 })
], U.prototype, "ws");
ct([
  m({ attribute: !1 })
], U.prototype, "panel");
ct([
  m({ attribute: !1 })
], U.prototype, "hass");
customElements.define("climate-manager-persons-tab", U);
var Ye = Object.defineProperty, D = (a, t, e, o) => {
  for (var s = void 0, r = a.length - 1, i; r >= 0; r--)
    (i = a[r]) && (s = i(t, e, s) || s);
  return s && Ye(t, e, s), s;
};
const Lt = class Lt extends S {
  constructor() {
    super(...arguments), this.narrow = !1, this.panel = null, this._config = null, this._status = null, this._activeTab = (() => {
      const t = localStorage.getItem("climate-manager-tab");
      return ["global", "rooms", "persons"].includes(t ?? "") ? t : "global";
    })(), this._unsubStatus = null, this._wsError = !1, this._ws = null;
  }
  connectedCallback() {
    super.connectedCallback(), this._ws = new lt(this.hass), this._loadConfig(), this._loadStatus(), this._subscribeStatus();
  }
  disconnectedCallback() {
    super.disconnectedCallback(), this._unsubStatus && (this._unsubStatus.then((t) => t()).catch(() => {
    }), this._unsubStatus = null);
  }
  async _loadConfig() {
    this._ws || (this._ws = new lt(this.hass));
    try {
      this._config = await this._ws.getConfig();
    } catch {
      this._wsError = !0;
    }
  }
  async _loadStatus() {
    this._ws || (this._ws = new lt(this.hass));
    try {
      this._status = await this._ws.getStatus();
    } catch {
    }
  }
  _subscribeStatus() {
    this._ws || (this._ws = new lt(this.hass)), this._unsubStatus = this._ws.subscribeStatus((t) => {
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
    this._activeTab = t, localStorage.setItem("climate-manager-tab", t);
  }
  render() {
    return this._config ? d`
      <div class="panel-header">Climate Manager</div>

      ${this._wsError ? d`<div class="error-banner">Connection lost. Reconnecting…</div>` : ""}

      <div class="tab-bar">
        <button
          class="tab-btn ${this._activeTab === "global" ? "active" : ""}"
          @click=${() => this._setTab("global")}
        >Overview</button>
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
          .hass=${this.hass}
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
Lt.styles = M`
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
  `;
let k = Lt;
D([
  m({ attribute: !1 })
], k.prototype, "hass");
D([
  m({ type: Boolean })
], k.prototype, "narrow");
D([
  m({ attribute: !1 })
], k.prototype, "panel");
D([
  x()
], k.prototype, "_config");
D([
  x()
], k.prototype, "_status");
D([
  x()
], k.prototype, "_activeTab");
D([
  x()
], k.prototype, "_unsubStatus");
D([
  x()
], k.prototype, "_wsError");
D([
  Te("climate-manager-toast")
], k.prototype, "_toast");
customElements.define("climate-manager-panel", k);
export {
  k as ClimateManagerPanel
};
