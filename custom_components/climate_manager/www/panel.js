/**
 * @license
 * Copyright 2019 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const fe = globalThis,
  Te =
    fe.ShadowRoot &&
    (fe.ShadyCSS === void 0 || fe.ShadyCSS.nativeShadow) &&
    "adoptedStyleSheets" in Document.prototype &&
    "replace" in CSSStyleSheet.prototype,
  Pe = Symbol(),
  Ge = /* @__PURE__ */ new WeakMap();
let dt = class {
  constructor(e, t, o) {
    if (((this._$cssResult$ = !0), o !== Pe))
      throw Error(
        "CSSResult is not constructable. Use `unsafeCSS` or `css` instead.",
      );
    (this.cssText = e), (this.t = t);
  }
  get styleSheet() {
    let e = this.o;
    const t = this.t;
    if (Te && e === void 0) {
      const o = t !== void 0 && t.length === 1;
      o && (e = Ge.get(t)),
        e === void 0 &&
          ((this.o = e = new CSSStyleSheet()).replaceSync(this.cssText),
          o && Ge.set(t, e));
    }
    return e;
  }
  toString() {
    return this.cssText;
  }
};
const pt = (a) => new dt(typeof a == "string" ? a : a + "", void 0, Pe),
  k = (a, ...e) => {
    const t =
      a.length === 1
        ? a[0]
        : e.reduce(
            (o, s, i) =>
              o +
              ((r) => {
                if (r._$cssResult$ === !0) return r.cssText;
                if (typeof r == "number") return r;
                throw Error(
                  "Value passed to 'css' function must be a 'css' function result: " +
                    r +
                    ". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.",
                );
              })(s) +
              a[i + 1],
            a[0],
          );
    return new dt(t, a, Pe);
  },
  vt = (a, e) => {
    if (Te)
      a.adoptedStyleSheets = e.map((t) =>
        t instanceof CSSStyleSheet ? t : t.styleSheet,
      );
    else
      for (const t of e) {
        const o = document.createElement("style"),
          s = fe.litNonce;
        s !== void 0 && o.setAttribute("nonce", s),
          (o.textContent = t.cssText),
          a.appendChild(o);
      }
  },
  Ke = Te
    ? (a) => a
    : (a) =>
        a instanceof CSSStyleSheet
          ? ((e) => {
              let t = "";
              for (const o of e.cssRules) t += o.cssText;
              return pt(t);
            })(a)
          : a;
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const {
    is: yt,
    defineProperty: xt,
    getOwnPropertyDescriptor: $t,
    getOwnPropertyNames: wt,
    getOwnPropertySymbols: kt,
    getPrototypeOf: Ct,
  } = Object,
  F = globalThis,
  Je = F.trustedTypes,
  St = Je ? Je.emptyScript : "",
  $e = F.reactiveElementPolyfillSupport,
  re = (a, e) => a,
  _e = {
    toAttribute(a, e) {
      switch (e) {
        case Boolean:
          a = a ? St : null;
          break;
        case Object:
        case Array:
          a = a == null ? a : JSON.stringify(a);
      }
      return a;
    },
    fromAttribute(a, e) {
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
    },
  },
  Ee = (a, e) => !yt(a, e),
  Qe = {
    attribute: !0,
    type: String,
    converter: _e,
    reflect: !1,
    useDefault: !1,
    hasChanged: Ee,
  };
Symbol.metadata ?? (Symbol.metadata = Symbol("metadata")),
  F.litPropertyMetadata ??
    (F.litPropertyMetadata = /* @__PURE__ */ new WeakMap());
let Y = class extends HTMLElement {
  static addInitializer(e) {
    this._$Ei(), (this.l ?? (this.l = [])).push(e);
  }
  static get observedAttributes() {
    return this.finalize(), this._$Eh && [...this._$Eh.keys()];
  }
  static createProperty(e, t = Qe) {
    if (
      (t.state && (t.attribute = !1),
      this._$Ei(),
      this.prototype.hasOwnProperty(e) && ((t = Object.create(t)).wrapped = !0),
      this.elementProperties.set(e, t),
      !t.noAccessor)
    ) {
      const o = Symbol(),
        s = this.getPropertyDescriptor(e, o, t);
      s !== void 0 && xt(this.prototype, e, s);
    }
  }
  static getPropertyDescriptor(e, t, o) {
    const { get: s, set: i } = $t(this.prototype, e) ?? {
      get() {
        return this[t];
      },
      set(r) {
        this[t] = r;
      },
    };
    return {
      get: s,
      set(r) {
        const n = s == null ? void 0 : s.call(this);
        i == null || i.call(this, r), this.requestUpdate(e, n, o);
      },
      configurable: !0,
      enumerable: !0,
    };
  }
  static getPropertyOptions(e) {
    return this.elementProperties.get(e) ?? Qe;
  }
  static _$Ei() {
    if (this.hasOwnProperty(re("elementProperties"))) return;
    const e = Ct(this);
    e.finalize(),
      e.l !== void 0 && (this.l = [...e.l]),
      (this.elementProperties = new Map(e.elementProperties));
  }
  static finalize() {
    if (this.hasOwnProperty(re("finalized"))) return;
    if (
      ((this.finalized = !0),
      this._$Ei(),
      this.hasOwnProperty(re("properties")))
    ) {
      const t = this.properties,
        o = [...wt(t), ...kt(t)];
      for (const s of o) this.createProperty(s, t[s]);
    }
    const e = this[Symbol.metadata];
    if (e !== null) {
      const t = litPropertyMetadata.get(e);
      if (t !== void 0)
        for (const [o, s] of t) this.elementProperties.set(o, s);
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
      for (const s of o) t.unshift(Ke(s));
    } else e !== void 0 && t.push(Ke(e));
    return t;
  }
  static _$Eu(e, t) {
    const o = t.attribute;
    return o === !1
      ? void 0
      : typeof o == "string"
        ? o
        : typeof e == "string"
          ? e.toLowerCase()
          : void 0;
  }
  constructor() {
    super(),
      (this._$Ep = void 0),
      (this.isUpdatePending = !1),
      (this.hasUpdated = !1),
      (this._$Em = null),
      this._$Ev();
  }
  _$Ev() {
    var e;
    (this._$ES = new Promise((t) => (this.enableUpdating = t))),
      (this._$AL = /* @__PURE__ */ new Map()),
      this._$E_(),
      this.requestUpdate(),
      (e = this.constructor.l) == null || e.forEach((t) => t(this));
  }
  addController(e) {
    var t;
    (this._$EO ?? (this._$EO = /* @__PURE__ */ new Set())).add(e),
      this.renderRoot !== void 0 &&
        this.isConnected &&
        ((t = e.hostConnected) == null || t.call(e));
  }
  removeController(e) {
    var t;
    (t = this._$EO) == null || t.delete(e);
  }
  _$E_() {
    const e = /* @__PURE__ */ new Map(),
      t = this.constructor.elementProperties;
    for (const o of t.keys())
      this.hasOwnProperty(o) && (e.set(o, this[o]), delete this[o]);
    e.size > 0 && (this._$Ep = e);
  }
  createRenderRoot() {
    const e =
      this.shadowRoot ?? this.attachShadow(this.constructor.shadowRootOptions);
    return vt(e, this.constructor.elementStyles), e;
  }
  connectedCallback() {
    var e;
    this.renderRoot ?? (this.renderRoot = this.createRenderRoot()),
      this.enableUpdating(!0),
      (e = this._$EO) == null ||
        e.forEach((t) => {
          var o;
          return (o = t.hostConnected) == null ? void 0 : o.call(t);
        });
  }
  enableUpdating(e) {}
  disconnectedCallback() {
    var e;
    (e = this._$EO) == null ||
      e.forEach((t) => {
        var o;
        return (o = t.hostDisconnected) == null ? void 0 : o.call(t);
      });
  }
  attributeChangedCallback(e, t, o) {
    this._$AK(e, o);
  }
  _$ET(e, t) {
    var i;
    const o = this.constructor.elementProperties.get(e),
      s = this.constructor._$Eu(e, o);
    if (s !== void 0 && o.reflect === !0) {
      const r = (
        ((i = o.converter) == null ? void 0 : i.toAttribute) !== void 0
          ? o.converter
          : _e
      ).toAttribute(t, o.type);
      (this._$Em = e),
        r == null ? this.removeAttribute(s) : this.setAttribute(s, r),
        (this._$Em = null);
    }
  }
  _$AK(e, t) {
    var i, r;
    const o = this.constructor,
      s = o._$Eh.get(e);
    if (s !== void 0 && this._$Em !== s) {
      const n = o.getPropertyOptions(s),
        l =
          typeof n.converter == "function"
            ? { fromAttribute: n.converter }
            : ((i = n.converter) == null ? void 0 : i.fromAttribute) !== void 0
              ? n.converter
              : _e;
      this._$Em = s;
      const d = l.fromAttribute(t, n.type);
      (this[s] = d ?? ((r = this._$Ej) == null ? void 0 : r.get(s)) ?? d),
        (this._$Em = null);
    }
  }
  requestUpdate(e, t, o, s = !1, i) {
    var r;
    if (e !== void 0) {
      const n = this.constructor;
      if (
        (s === !1 && (i = this[e]),
        o ?? (o = n.getPropertyOptions(e)),
        !(
          (o.hasChanged ?? Ee)(i, t) ||
          (o.useDefault &&
            o.reflect &&
            i === ((r = this._$Ej) == null ? void 0 : r.get(e)) &&
            !this.hasAttribute(n._$Eu(e, o)))
        ))
      )
        return;
      this.C(e, t, o);
    }
    this.isUpdatePending === !1 && (this._$ES = this._$EP());
  }
  C(e, t, { useDefault: o, reflect: s, wrapped: i }, r) {
    (o &&
      !(this._$Ej ?? (this._$Ej = /* @__PURE__ */ new Map())).has(e) &&
      (this._$Ej.set(e, r ?? t ?? this[e]), i !== !0 || r !== void 0)) ||
      (this._$AL.has(e) ||
        (this.hasUpdated || o || (t = void 0), this._$AL.set(e, t)),
      s === !0 &&
        this._$Em !== e &&
        (this._$Eq ?? (this._$Eq = /* @__PURE__ */ new Set())).add(e));
  }
  async _$EP() {
    this.isUpdatePending = !0;
    try {
      await this._$ES;
    } catch (t) {
      Promise.reject(t);
    }
    const e = this.scheduleUpdate();
    return e != null && (await e), !this.isUpdatePending;
  }
  scheduleUpdate() {
    return this.performUpdate();
  }
  performUpdate() {
    var o;
    if (!this.isUpdatePending) return;
    if (!this.hasUpdated) {
      if (
        (this.renderRoot ?? (this.renderRoot = this.createRenderRoot()),
        this._$Ep)
      ) {
        for (const [i, r] of this._$Ep) this[i] = r;
        this._$Ep = void 0;
      }
      const s = this.constructor.elementProperties;
      if (s.size > 0)
        for (const [i, r] of s) {
          const { wrapped: n } = r,
            l = this[i];
          n !== !0 ||
            this._$AL.has(i) ||
            l === void 0 ||
            this.C(i, void 0, r, l);
        }
    }
    let e = !1;
    const t = this._$AL;
    try {
      (e = this.shouldUpdate(t)),
        e
          ? (this.willUpdate(t),
            (o = this._$EO) == null ||
              o.forEach((s) => {
                var i;
                return (i = s.hostUpdate) == null ? void 0 : i.call(s);
              }),
            this.update(t))
          : this._$EM();
    } catch (s) {
      throw ((e = !1), this._$EM(), s);
    }
    e && this._$AE(t);
  }
  willUpdate(e) {}
  _$AE(e) {
    var t;
    (t = this._$EO) == null ||
      t.forEach((o) => {
        var s;
        return (s = o.hostUpdated) == null ? void 0 : s.call(o);
      }),
      this.hasUpdated || ((this.hasUpdated = !0), this.firstUpdated(e)),
      this.updated(e);
  }
  _$EM() {
    (this._$AL = /* @__PURE__ */ new Map()), (this.isUpdatePending = !1);
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
    this._$Eq && (this._$Eq = this._$Eq.forEach((t) => this._$ET(t, this[t]))),
      this._$EM();
  }
  updated(e) {}
  firstUpdated(e) {}
};
(Y.elementStyles = []),
  (Y.shadowRootOptions = { mode: "open" }),
  (Y[re("elementProperties")] = /* @__PURE__ */ new Map()),
  (Y[re("finalized")] = /* @__PURE__ */ new Map()),
  $e == null || $e({ ReactiveElement: Y }),
  (F.reactiveElementVersions ?? (F.reactiveElementVersions = [])).push("2.1.2");
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const ae = globalThis,
  et = (a) => a,
  be = ae.trustedTypes,
  tt = be ? be.createPolicy("lit-html", { createHTML: (a) => a }) : void 0,
  ht = "$lit$",
  Z = `lit$${Math.random().toFixed(9).slice(2)}$`,
  ut = "?" + Z,
  Tt = `<${ut}>`,
  V = document,
  le = () => V.createComment(""),
  ce = (a) => a === null || (typeof a != "object" && typeof a != "function"),
  ze = Array.isArray,
  Pt = (a) =>
    ze(a) || typeof (a == null ? void 0 : a[Symbol.iterator]) == "function",
  we = `[ 	
\f\r]`,
  oe = /<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,
  st = /-->/g,
  ot = />/g,
  B = RegExp(
    `>|${we}(?:([^\\s"'>=/]+)(${we}*=${we}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`,
    "g",
  ),
  it = /'/g,
  rt = /"/g,
  mt = /^(?:script|style|textarea|title)$/i,
  Et =
    (a) =>
    (e, ...t) => ({ _$litType$: a, strings: e, values: t }),
  c = Et(1),
  G = Symbol.for("lit-noChange"),
  x = Symbol.for("lit-nothing"),
  at = /* @__PURE__ */ new WeakMap(),
  W = V.createTreeWalker(V, 129);
function gt(a, e) {
  if (!ze(a) || !a.hasOwnProperty("raw"))
    throw Error("invalid template strings array");
  return tt !== void 0 ? tt.createHTML(e) : e;
}
const zt = (a, e) => {
  const t = a.length - 1,
    o = [];
  let s,
    i = e === 2 ? "<svg>" : e === 3 ? "<math>" : "",
    r = oe;
  for (let n = 0; n < t; n++) {
    const l = a[n];
    let d,
      p,
      h = -1,
      f = 0;
    for (; f < l.length && ((r.lastIndex = f), (p = r.exec(l)), p !== null); )
      (f = r.lastIndex),
        r === oe
          ? p[1] === "!--"
            ? (r = st)
            : p[1] !== void 0
              ? (r = ot)
              : p[2] !== void 0
                ? (mt.test(p[2]) && (s = RegExp("</" + p[2], "g")), (r = B))
                : p[3] !== void 0 && (r = B)
          : r === B
            ? p[0] === ">"
              ? ((r = s ?? oe), (h = -1))
              : p[1] === void 0
                ? (h = -2)
                : ((h = r.lastIndex - p[2].length),
                  (d = p[1]),
                  (r = p[3] === void 0 ? B : p[3] === '"' ? rt : it))
            : r === rt || r === it
              ? (r = B)
              : r === st || r === ot
                ? (r = oe)
                : ((r = B), (s = void 0));
    const g = r === B && a[n + 1].startsWith("/>") ? " " : "";
    i +=
      r === oe
        ? l + Tt
        : h >= 0
          ? (o.push(d), l.slice(0, h) + ht + l.slice(h) + Z + g)
          : l + Z + (h === -2 ? n : g);
  }
  return [
    gt(
      a,
      i + (a[t] || "<?>") + (e === 2 ? "</svg>" : e === 3 ? "</math>" : ""),
    ),
    o,
  ];
};
class de {
  constructor({ strings: e, _$litType$: t }, o) {
    let s;
    this.parts = [];
    let i = 0,
      r = 0;
    const n = e.length - 1,
      l = this.parts,
      [d, p] = zt(e, t);
    if (
      ((this.el = de.createElement(d, o)),
      (W.currentNode = this.el.content),
      t === 2 || t === 3)
    ) {
      const h = this.el.content.firstChild;
      h.replaceWith(...h.childNodes);
    }
    for (; (s = W.nextNode()) !== null && l.length < n; ) {
      if (s.nodeType === 1) {
        if (s.hasAttributes())
          for (const h of s.getAttributeNames())
            if (h.endsWith(ht)) {
              const f = p[r++],
                g = s.getAttribute(h).split(Z),
                v = /([.?@])?(.*)/.exec(f);
              l.push({
                type: 1,
                index: i,
                name: v[2],
                strings: g,
                ctor:
                  v[1] === "."
                    ? Mt
                    : v[1] === "?"
                      ? At
                      : v[1] === "@"
                        ? Dt
                        : ye,
              }),
                s.removeAttribute(h);
            } else
              h.startsWith(Z) &&
                (l.push({ type: 6, index: i }), s.removeAttribute(h));
        if (mt.test(s.tagName)) {
          const h = s.textContent.split(Z),
            f = h.length - 1;
          if (f > 0) {
            s.textContent = be ? be.emptyScript : "";
            for (let g = 0; g < f; g++)
              s.append(h[g], le()),
                W.nextNode(),
                l.push({ type: 2, index: ++i });
            s.append(h[f], le());
          }
        }
      } else if (s.nodeType === 8)
        if (s.data === ut) l.push({ type: 2, index: i });
        else {
          let h = -1;
          for (; (h = s.data.indexOf(Z, h + 1)) !== -1; )
            l.push({ type: 7, index: i }), (h += Z.length - 1);
        }
      i++;
    }
  }
  static createElement(e, t) {
    const o = V.createElement("template");
    return (o.innerHTML = e), o;
  }
}
function K(a, e, t = a, o) {
  var r, n;
  if (e === G) return e;
  let s = o !== void 0 ? ((r = t._$Co) == null ? void 0 : r[o]) : t._$Cl;
  const i = ce(e) ? void 0 : e._$litDirective$;
  return (
    (s == null ? void 0 : s.constructor) !== i &&
      ((n = s == null ? void 0 : s._$AO) == null || n.call(s, !1),
      i === void 0 ? (s = void 0) : ((s = new i(a)), s._$AT(a, t, o)),
      o !== void 0 ? ((t._$Co ?? (t._$Co = []))[o] = s) : (t._$Cl = s)),
    s !== void 0 && (e = K(a, s._$AS(a, e.values), s, o)),
    e
  );
}
class Rt {
  constructor(e, t) {
    (this._$AV = []), (this._$AN = void 0), (this._$AD = e), (this._$AM = t);
  }
  get parentNode() {
    return this._$AM.parentNode;
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  u(e) {
    const {
        el: { content: t },
        parts: o,
      } = this._$AD,
      s = ((e == null ? void 0 : e.creationScope) ?? V).importNode(t, !0);
    W.currentNode = s;
    let i = W.nextNode(),
      r = 0,
      n = 0,
      l = o[0];
    for (; l !== void 0; ) {
      if (r === l.index) {
        let d;
        l.type === 2
          ? (d = new pe(i, i.nextSibling, this, e))
          : l.type === 1
            ? (d = new l.ctor(i, l.name, l.strings, this, e))
            : l.type === 6 && (d = new It(i, this, e)),
          this._$AV.push(d),
          (l = o[++n]);
      }
      r !== (l == null ? void 0 : l.index) && ((i = W.nextNode()), r++);
    }
    return (W.currentNode = V), s;
  }
  p(e) {
    let t = 0;
    for (const o of this._$AV)
      o !== void 0 &&
        (o.strings !== void 0
          ? (o._$AI(e, o, t), (t += o.strings.length - 2))
          : o._$AI(e[t])),
        t++;
  }
}
class pe {
  get _$AU() {
    var e;
    return ((e = this._$AM) == null ? void 0 : e._$AU) ?? this._$Cv;
  }
  constructor(e, t, o, s) {
    (this.type = 2),
      (this._$AH = x),
      (this._$AN = void 0),
      (this._$AA = e),
      (this._$AB = t),
      (this._$AM = o),
      (this.options = s),
      (this._$Cv = (s == null ? void 0 : s.isConnected) ?? !0);
  }
  get parentNode() {
    let e = this._$AA.parentNode;
    const t = this._$AM;
    return (
      t !== void 0 &&
        (e == null ? void 0 : e.nodeType) === 11 &&
        (e = t.parentNode),
      e
    );
  }
  get startNode() {
    return this._$AA;
  }
  get endNode() {
    return this._$AB;
  }
  _$AI(e, t = this) {
    (e = K(this, e, t)),
      ce(e)
        ? e === x || e == null || e === ""
          ? (this._$AH !== x && this._$AR(), (this._$AH = x))
          : e !== this._$AH && e !== G && this._(e)
        : e._$litType$ !== void 0
          ? this.$(e)
          : e.nodeType !== void 0
            ? this.T(e)
            : Pt(e)
              ? this.k(e)
              : this._(e);
  }
  O(e) {
    return this._$AA.parentNode.insertBefore(e, this._$AB);
  }
  T(e) {
    this._$AH !== e && (this._$AR(), (this._$AH = this.O(e)));
  }
  _(e) {
    this._$AH !== x && ce(this._$AH)
      ? (this._$AA.nextSibling.data = e)
      : this.T(V.createTextNode(e)),
      (this._$AH = e);
  }
  $(e) {
    var i;
    const { values: t, _$litType$: o } = e,
      s =
        typeof o == "number"
          ? this._$AC(e)
          : (o.el === void 0 &&
              (o.el = de.createElement(gt(o.h, o.h[0]), this.options)),
            o);
    if (((i = this._$AH) == null ? void 0 : i._$AD) === s) this._$AH.p(t);
    else {
      const r = new Rt(s, this),
        n = r.u(this.options);
      r.p(t), this.T(n), (this._$AH = r);
    }
  }
  _$AC(e) {
    let t = at.get(e.strings);
    return t === void 0 && at.set(e.strings, (t = new de(e))), t;
  }
  k(e) {
    ze(this._$AH) || ((this._$AH = []), this._$AR());
    const t = this._$AH;
    let o,
      s = 0;
    for (const i of e)
      s === t.length
        ? t.push((o = new pe(this.O(le()), this.O(le()), this, this.options)))
        : (o = t[s]),
        o._$AI(i),
        s++;
    s < t.length && (this._$AR(o && o._$AB.nextSibling, s), (t.length = s));
  }
  _$AR(e = this._$AA.nextSibling, t) {
    var o;
    for (
      (o = this._$AP) == null ? void 0 : o.call(this, !1, !0, t);
      e !== this._$AB;

    ) {
      const s = et(e).nextSibling;
      et(e).remove(), (e = s);
    }
  }
  setConnected(e) {
    var t;
    this._$AM === void 0 &&
      ((this._$Cv = e), (t = this._$AP) == null || t.call(this, e));
  }
}
class ye {
  get tagName() {
    return this.element.tagName;
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  constructor(e, t, o, s, i) {
    (this.type = 1),
      (this._$AH = x),
      (this._$AN = void 0),
      (this.element = e),
      (this.name = t),
      (this._$AM = s),
      (this.options = i),
      o.length > 2 || o[0] !== "" || o[1] !== ""
        ? ((this._$AH = Array(o.length - 1).fill(new String())),
          (this.strings = o))
        : (this._$AH = x);
  }
  _$AI(e, t = this, o, s) {
    const i = this.strings;
    let r = !1;
    if (i === void 0)
      (e = K(this, e, t, 0)),
        (r = !ce(e) || (e !== this._$AH && e !== G)),
        r && (this._$AH = e);
    else {
      const n = e;
      let l, d;
      for (e = i[0], l = 0; l < i.length - 1; l++)
        (d = K(this, n[o + l], t, l)),
          d === G && (d = this._$AH[l]),
          r || (r = !ce(d) || d !== this._$AH[l]),
          d === x ? (e = x) : e !== x && (e += (d ?? "") + i[l + 1]),
          (this._$AH[l] = d);
    }
    r && !s && this.j(e);
  }
  j(e) {
    e === x
      ? this.element.removeAttribute(this.name)
      : this.element.setAttribute(this.name, e ?? "");
  }
}
class Mt extends ye {
  constructor() {
    super(...arguments), (this.type = 3);
  }
  j(e) {
    this.element[this.name] = e === x ? void 0 : e;
  }
}
class At extends ye {
  constructor() {
    super(...arguments), (this.type = 4);
  }
  j(e) {
    this.element.toggleAttribute(this.name, !!e && e !== x);
  }
}
class Dt extends ye {
  constructor(e, t, o, s, i) {
    super(e, t, o, s, i), (this.type = 5);
  }
  _$AI(e, t = this) {
    if ((e = K(this, e, t, 0) ?? x) === G) return;
    const o = this._$AH,
      s =
        (e === x && o !== x) ||
        e.capture !== o.capture ||
        e.once !== o.once ||
        e.passive !== o.passive,
      i = e !== x && (o === x || s);
    s && this.element.removeEventListener(this.name, this, o),
      i && this.element.addEventListener(this.name, this, e),
      (this._$AH = e);
  }
  handleEvent(e) {
    var t;
    typeof this._$AH == "function"
      ? this._$AH.call(
          ((t = this.options) == null ? void 0 : t.host) ?? this.element,
          e,
        )
      : this._$AH.handleEvent(e);
  }
}
class It {
  constructor(e, t, o) {
    (this.element = e),
      (this.type = 6),
      (this._$AN = void 0),
      (this._$AM = t),
      (this.options = o);
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  _$AI(e) {
    K(this, e);
  }
}
const ke = ae.litHtmlPolyfillSupport;
ke == null || ke(de, pe),
  (ae.litHtmlVersions ?? (ae.litHtmlVersions = [])).push("3.3.3");
const Ot = (a, e, t) => {
  const o = (t == null ? void 0 : t.renderBefore) ?? e;
  let s = o._$litPart$;
  if (s === void 0) {
    const i = (t == null ? void 0 : t.renderBefore) ?? null;
    o._$litPart$ = s = new pe(e.insertBefore(le(), i), i, void 0, t ?? {});
  }
  return s._$AI(a), s;
};
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const X = globalThis;
class C extends Y {
  constructor() {
    super(...arguments),
      (this.renderOptions = { host: this }),
      (this._$Do = void 0);
  }
  createRenderRoot() {
    var t;
    const e = super.createRenderRoot();
    return (
      (t = this.renderOptions).renderBefore ?? (t.renderBefore = e.firstChild),
      e
    );
  }
  update(e) {
    const t = this.render();
    this.hasUpdated || (this.renderOptions.isConnected = this.isConnected),
      super.update(e),
      (this._$Do = Ot(t, this.renderRoot, this.renderOptions));
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
    return G;
  }
}
var ct;
(C._$litElement$ = !0),
  (C.finalized = !0),
  (ct = X.litElementHydrateSupport) == null || ct.call(X, { LitElement: C });
const Ce = X.litElementPolyfillSupport;
Ce == null || Ce({ LitElement: C });
(X.litElementVersions ?? (X.litElementVersions = [])).push("4.2.2");
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const Nt = {
    attribute: !0,
    type: String,
    converter: _e,
    reflect: !1,
    hasChanged: Ee,
  },
  Ht = (a = Nt, e, t) => {
    const { kind: o, metadata: s } = t;
    let i = globalThis.litPropertyMetadata.get(s);
    if (
      (i === void 0 &&
        globalThis.litPropertyMetadata.set(s, (i = /* @__PURE__ */ new Map())),
      o === "setter" && ((a = Object.create(a)).wrapped = !0),
      i.set(t.name, a),
      o === "accessor")
    ) {
      const { name: r } = t;
      return {
        set(n) {
          const l = e.get.call(this);
          e.set.call(this, n), this.requestUpdate(r, l, a, !0, n);
        },
        init(n) {
          return n !== void 0 && this.C(r, void 0, a, n), n;
        },
      };
    }
    if (o === "setter") {
      const { name: r } = t;
      return function (n) {
        const l = this[r];
        e.call(this, n), this.requestUpdate(r, l, a, !0, n);
      };
    }
    throw Error("Unsupported decorator location: " + o);
  };
function u(a) {
  return (e, t) =>
    typeof t == "object"
      ? Ht(a, e, t)
      : ((o, s, i) => {
          const r = s.hasOwnProperty(i);
          return (
            s.constructor.createProperty(i, o),
            r ? Object.getOwnPropertyDescriptor(s, i) : void 0
          );
        })(a, e, t);
}
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
function y(a) {
  return u({ ...a, state: !0, attribute: !1 });
}
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const Lt = (a, e, t) => (
  (t.configurable = !0),
  (t.enumerable = !0),
  Reflect.decorate && typeof e != "object" && Object.defineProperty(a, e, t),
  t
);
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
function Ut(a, e) {
  return (t, o, s) => {
    const i = (r) => {
      var n;
      return ((n = r.renderRoot) == null ? void 0 : n.querySelector(a)) ?? null;
    };
    return Lt(t, o, {
      get() {
        return i(this);
      },
    });
  };
}
class he {
  constructor(e) {
    this.hass = e;
  }
  /** Return the full merged runtime config. */
  getConfig() {
    return this.hass.connection.sendMessagePromise({
      type: "climate_manager/get_config",
    });
  }
  /** Return the current coordinator status snapshot. */
  getStatus() {
    return this.hass.connection.sendMessagePromise({
      type: "climate_manager/get_status",
    });
  }
  /** Set the global heating mode. */
  setGlobalMode(e) {
    return this.hass.connection.sendMessagePromise({
      type: "climate_manager/set_global_mode",
      mode: e,
    });
  }
  /** Update default temperatures for all four period modes. */
  setPeriodTemperatures(e) {
    return this.hass.connection.sendMessagePromise({
      type: "climate_manager/set_period_temperatures",
      temperatures: e,
    });
  }
  /** Replace the global time program (all 7 day keys required). */
  setTimeProgram(e) {
    return this.hass.connection.sendMessagePromise({
      type: "climate_manager/set_time_program",
      program: e,
    });
  }
  /** Reset period temperatures to backend defaults. */
  resetPeriodTemperatures() {
    return this.hass.connection.sendMessagePromise({
      type: "climate_manager/reset_period_temperatures",
    });
  }
  /** Reset global time program to backend defaults. */
  resetTimeProgram() {
    return this.hass.connection.sendMessagePromise({
      type: "climate_manager/reset_time_program",
    });
  }
  /**
   * Create a new custom zone. Resolves with the new zone id and ZoneConfig.
   */
  createZone(e) {
    return this.hass.connection.sendMessagePromise({
      type: "climate_manager/create_zone",
      name: e,
    });
  }
  /**
   * Delete a custom zone. Rooms revert to Default Zone on the backend.
   */
  deleteZone(e) {
    return this.hass.connection.sendMessagePromise({
      type: "climate_manager/delete_zone",
      zone_id: e,
    });
  }
  /**
   * Rename a zone. Pass zoneId="default" to rename the Default Zone.
   */
  renameZone(e, t) {
    return this.hass.connection.sendMessagePromise({
      type: "climate_manager/rename_zone",
      zone_id: e,
      name: t,
    });
  }
  /**
   * Set the heating mode for a zone. Same enum as global_mode.
   */
  setZoneMode(e, t) {
    return this.hass.connection.sendMessagePromise({
      type: "climate_manager/set_zone_mode",
      zone_id: e,
      mode: t,
    });
  }
  /**
   * Replace the time program for a zone (all 7 day keys required).
   */
  setZoneTimeProgram(e, t) {
    return this.hass.connection.sendMessagePromise({
      type: "climate_manager/set_zone_time_program",
      zone_id: e,
      program: t,
    });
  }
  /**
   * Reset a zone's time program to a named target (see websocket.py).
   */
  resetZoneTimeProgram(e, t) {
    return this.hass.connection.sendMessagePromise({
      type: "climate_manager/reset_zone_time_program",
      zone_id: e,
      target: t,
    });
  }
  /** Reset room time_program to global_time_program (backend deep-copies). */
  resetRoomToGlobalProgram(e) {
    return this.hass.connection.sendMessagePromise({
      type: "climate_manager/reset_room_to_global_program",
      room_id: e,
    });
  }
  /** Sparse-merge a config delta into a specific room. */
  setRoomConfig(e, t) {
    return this.hass.connection.sendMessagePromise({
      type: "climate_manager/set_room_config",
      room_id: e,
      config: t,
    });
  }
  /** Sparse-merge a config delta into a specific person. */
  setPersonConfig(e, t) {
    return this.hass.connection.sendMessagePromise({
      type: "climate_manager/set_person_config",
      person_id: e,
      config: t,
    });
  }
  /**
   * Subscribe to coordinator status push events.
   * Returns Promise<unsubscribe fn> — store and call on disconnect.
   */
  subscribeStatus(e) {
    return this.hass.connection.subscribeMessage(e, {
      type: "climate_manager/subscribe_status",
    });
  }
  /** Enable or disable TRV offset auto-calibration globally. */
  setCalibrationConfig(e) {
    return this.hass.connection.sendMessagePromise({
      type: "climate_manager/set_calibration_config",
      enabled: e,
    });
  }
  /** Return per-TRV calibration status for the TRV Auto-Calibration card. */
  getCalibrationStatus() {
    return this.hass.connection.sendMessagePromise({
      type: "climate_manager/get_calibration_status",
    });
  }
}
const j = {
    frost_protection: "#1565C0",
    reduced: "#0277BD",
    normal: "#F57C00",
    comfort: "#C62828",
  },
  ie = {
    present: "#2E7D32",
    absent: "#9E9E9E",
  },
  Re = {
    frost_protection: "Frost protection",
    reduced: "Reduced",
    normal: "Normal",
    comfort: "Comfort",
    present: "Present",
    absent: "Absent",
  },
  Se = [
    {
      background: "rgba(124, 58, 237, 0.12)",
      color: "#7c3aed",
      border: "rgba(124, 58, 237, 0.25)",
    },
    // violet
    {
      background: "rgba(13, 148, 136, 0.12)",
      color: "#0d9488",
      border: "rgba(13, 148, 136, 0.25)",
    },
    // teal
    {
      background: "rgba(217, 119, 6, 0.12)",
      color: "#d97706",
      border: "rgba(217, 119, 6, 0.25)",
    },
    // amber
    {
      background: "rgba(2, 132, 199, 0.12)",
      color: "#0284c7",
      border: "rgba(2, 132, 199, 0.25)",
    },
    // sky
    {
      background: "rgba(190, 18, 60, 0.12)",
      color: "#be123c",
      border: "rgba(190, 18, 60, 0.25)",
    },
    // rose
  ];
function ve(a) {
  if (!a) return Se[0];
  let e = 0;
  for (let t = 0; t < a.length; t++) e = (e * 31 + a.charCodeAt(t)) >>> 0;
  return Se[1 + (e % (Se.length - 1))];
}
var jt = Object.defineProperty,
  Me = (a, e, t, o) => {
    for (var s = void 0, i = a.length - 1, r; i >= 0; i--)
      (r = a[i]) && (s = r(e, t, s) || s);
    return s && jt(e, t, s), s;
  };
const He = class He extends C {
  constructor() {
    super(...arguments),
      (this._visible = !1),
      (this._message = ""),
      (this._isError = !1),
      (this._dismissTimer = null);
  }
  /** Display the toast. Success auto-dismisses after 3s; error persists. */
  show(e, t) {
    this._dismissTimer !== null &&
      (clearTimeout(this._dismissTimer), (this._dismissTimer = null)),
      (this._message = e),
      (this._isError = t),
      (this._visible = !0),
      t ||
        (this._dismissTimer = setTimeout(() => {
          (this._visible = !1), (this._dismissTimer = null);
        }, 3e3));
  }
  /** Programmatically dismiss the toast (e.g. after error recovery). */
  dismiss() {
    this._dismissTimer !== null &&
      (clearTimeout(this._dismissTimer), (this._dismissTimer = null)),
      (this._visible = !1);
  }
  render() {
    const e = this._isError ? "mdi:alert-circle" : "mdi:check-circle",
      t = this._isError ? "error" : "success";
    return c`
      <div
        class="toast ${this._visible ? "visible" : ""}"
        role="status"
        aria-live="polite"
        aria-atomic="true"
      >
        <ha-icon class="icon ${t}" icon="${e}"></ha-icon>
        <span>${this._message}</span>
      </div>
    `;
  }
};
He.styles = k`
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
      box-shadow: var(--ha-card-box-shadow, 0 2px 8px rgba(0, 0, 0, 0.2));
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
let J = He;
Me([y()], J.prototype, "_visible");
Me([y()], J.prototype, "_message");
Me([y()], J.prototype, "_isError");
customElements.define("climate-manager-toast", J);
var Zt = Object.defineProperty,
  H = (a, e, t, o) => {
    for (var s = void 0, i = a.length - 1, r; i >= 0; i--)
      (r = a[i]) && (s = r(e, t, s) || s);
    return s && Zt(e, t, s), s;
  };
const Ft = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
  Bt = ["frost_protection", "reduced", "normal", "comfort"],
  Wt = ["present", "absent"],
  Le = class Le extends C {
    constructor() {
      super(...arguments),
        (this.days = Array.from({ length: 7 }, () => [])),
        (this.mode = "schedule"),
        (this._clipboard = null),
        (this._drag = null),
        (this._dragTooltipMinutes = null),
        (this._dragTooltipX = 0),
        (this._dragTooltipY = 0),
        (this._dragPreviewDays = null),
        (this._popup = null),
        (this._justDragged = !1);
    }
    // -----------------------------------------------------------------------
    // Helpers
    // -----------------------------------------------------------------------
    _snapToMinutes(e) {
      return Math.round(e / 15) * 15;
    }
    _pixelToMinutes(e, t) {
      return (e / t) * 1440;
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
      const t = Math.max(0, Math.min(1440, e)),
        o = Math.floor(t / 60),
        s = t % 60;
      return `${String(o).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
    }
    _colorForPeriod(e) {
      const t =
        this.mode === "presence"
          ? e.state ?? "absent"
          : e.mode ?? "frost_protection";
      return this.mode === "presence"
        ? ie[t] ?? ie.absent
        : j[t] ?? j.frost_protection;
    }
    _labelForPeriod(e) {
      const t =
        this.mode === "presence"
          ? e.state ?? "absent"
          : e.mode ?? "frost_protection";
      return Re[t] ?? t;
    }
    /**
     * Convert a periods array to renderable segments with computed widths.
     * Always starts at 00:00 — prepends a synthesised period if needed.
     */
    _toSegments(e) {
      if (e.length === 0) return [];
      const t = [...e].sort((n, l) => n.start.localeCompare(l.start)),
        o = t[0],
        i =
          this._timeToMinutes(o.start) > 0
            ? [{ start: "00:00", mode: o.mode, state: o.state }, ...t]
            : t,
        r = [];
      for (let n = 0; n < i.length; n++) {
        const l = this._timeToMinutes(i[n].start),
          d = n + 1 < i.length ? this._timeToMinutes(i[n + 1].start) : 1440;
        r.push({ period: i[n], startMin: l, endMin: d });
      }
      return r;
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
          composed: !0,
        }),
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
        const s = e[o] ?? [],
          i = t[o] ?? [];
        if (s.length !== i.length) return !1;
        for (let r = 0; r < s.length; r++) {
          const n = s[r],
            l = i[r];
          if (n.start !== l.start || n.mode !== l.mode || n.state !== l.state)
            return !1;
        }
      }
      return !0;
    }
    // -----------------------------------------------------------------------
    // Popup helpers
    // -----------------------------------------------------------------------
    _modeOptions() {
      return this.mode === "presence"
        ? [
            { key: "present", label: "Present", color: ie.present },
            { key: "absent", label: "Absent", color: ie.absent },
          ]
        : [
            {
              key: "frost_protection",
              label: "Frost protection",
              color: j.frost_protection,
            },
            { key: "reduced", label: "Reduced", color: j.reduced },
            { key: "normal", label: "Normal", color: j.normal },
            { key: "comfort", label: "Comfort", color: j.comfort },
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
        (this._justDragged = !1), e.stopPropagation();
        return;
      }
      const s = e.currentTarget.getBoundingClientRect(),
        i = this._pixelToMinutes(e.clientX - s.left, s.width),
        r = this._snapToMinutes(i);
      (this._popup = {
        kind: "split",
        dayIndex: t,
        snappedMinutes: r,
        x: e.clientX,
        y: e.clientY,
      }),
        e.stopPropagation();
    }
    _onSplitModeSelect(e) {
      if (!this._popup || this._popup.kind !== "split") return;
      const { dayIndex: t, snappedMinutes: o } = this._popup,
        s = [...(this.days[t] ?? [])],
        i =
          this.mode === "presence"
            ? { start: this._minutesToHHMM(o ?? 0), state: e }
            : { start: this._minutesToHHMM(o ?? 0), mode: e };
      s.push(i);
      const r = s.sort((l, d) => l.start.localeCompare(d.start)),
        n = r.filter((l, d) => d === 0 || l.start !== r[d - 1].start);
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
        (this._justDragged = !1), e.stopPropagation();
        return;
      }
      (this._popup = {
        kind: "edit",
        dayIndex: t,
        segIndex: o,
        x: e.clientX,
        y: e.clientY,
      }),
        e.stopPropagation();
    }
    _onEditModeSelect(e) {
      if (!this._popup || this._popup.kind !== "edit") return;
      const { dayIndex: t, segIndex: o } = this._popup,
        i = this._toSegments(this.days[t] ?? [])[o ?? 0];
      if (!i) return;
      const r = (this.days[t] ?? []).map((n) =>
        n.start === i.period.start
          ? this.mode === "presence"
            ? { ...n, state: e }
            : { ...n, mode: e }
          : n,
      );
      this._closePopup(), this._emitChange(t, r);
    }
    _onDeleteSegment() {
      if (!this._popup || this._popup.kind !== "edit") return;
      const { dayIndex: e, segIndex: t } = this._popup,
        s = this._toSegments(this.days[e] ?? [])[t ?? 0];
      if (!s) return;
      const i = (this.days[e] ?? []).filter((r) => r.start !== s.period.start);
      this._closePopup(), this._emitChange(e, i);
    }
    /**
     * Split the clicked period at its midpoint (snapped to 15 min).
     * The first half keeps the original type; the second half gets the next
     * type in the cycle:
     *   schedule: frost_protection→reduced→normal→comfort→frost_protection
     *   presence: present → absent → present
     *
     * If the period is too narrow to split (< 30 min, leaving no room for two
     * 15-min halves) the action is silently ignored.
     */
    _onSplitPeriod() {
      if (!this._popup || this._popup.kind !== "edit") return;
      const { dayIndex: e, segIndex: t } = this._popup,
        s = this._toSegments(this.days[e] ?? [])[t ?? 0];
      if (!s) return;
      const i = s.endMin - s.startMin;
      if (i < 30) return;
      const r = s.startMin + i / 2,
        n = Math.max(
          s.startMin + 15,
          Math.min(s.endMin - 15, this._snapToMinutes(r)),
        ),
        l = this.mode === "presence" ? Wt : Bt,
        d =
          this.mode === "presence"
            ? s.period.state ?? "absent"
            : s.period.mode ?? "frost_protection",
        p = l.indexOf(d),
        h = l[(p + 1) % l.length],
        f =
          this.mode === "presence"
            ? { start: s.period.start, state: d }
            : { start: s.period.start, mode: d },
        g =
          this.mode === "presence"
            ? { start: this._minutesToHHMM(n), state: h }
            : { start: this._minutesToHHMM(n), mode: h },
        v = this.days[e] ?? [],
        m = v.some((_) => _.start === s.period.start);
      let b;
      m
        ? (b = v.flatMap((_) => (_.start === s.period.start ? [f, g] : [_])))
        : (b = [g, ...v]),
        this._closePopup(),
        this._emitChange(e, b);
    }
    // -----------------------------------------------------------------------
    // Drag boundary (D-06)
    // -----------------------------------------------------------------------
    _onDragHandlePointerDown(e, t, o) {
      e.preventDefault(),
        e.stopPropagation(),
        e.target.setPointerCapture(e.pointerId),
        (this._dragPreviewDays = null);
      const i = this._toSegments(this.days[t] ?? [])[o];
      i &&
        ((this._drag = {
          dayIndex: t,
          segIndex: o,
          startX: e.clientX,
          initialBoundaryMinutes: i.endMin,
        }),
        (this._dragTooltipMinutes = i.endMin),
        (this._dragTooltipX = e.clientX),
        (this._dragTooltipY = e.clientY - this._touchTooltipOffset(e)));
    }
    _onPointerMove(e) {
      var h;
      if (!this._drag) return;
      const { dayIndex: t, segIndex: o } = this._drag,
        s =
          (h = this.shadowRoot) == null
            ? void 0
            : h.querySelector(`.day-row:nth-child(${t + 2}) .bar-wrap`);
      if (!s) return;
      const i = s.getBoundingClientRect(),
        r = this._pixelToMinutes(e.clientX - i.left, i.width),
        n = this._snapToMinutes(r);
      (this._dragTooltipMinutes = n),
        (this._dragTooltipX = e.clientX),
        (this._dragTooltipY = e.clientY - this._touchTooltipOffset(e));
      const l = this._toSegments(this.days[t] ?? []),
        d = l[o],
        p = l[o + 1];
      if (d && p) {
        const f = d.startMin + 15,
          g = p.endMin - 15,
          v = Math.max(f, Math.min(g, n)),
          m = (this.days[t] ?? []).map((_) =>
            _.start === p.period.start
              ? { ..._, start: this._minutesToHHMM(v) }
              : _,
          ),
          b = this.days.map((_, $) => ($ === t ? m : _));
        this._dragPreviewDays = b;
      }
    }
    _onPointerUp(e) {
      var i;
      if (!this._drag) return;
      const { dayIndex: t, segIndex: o } = this._drag,
        s =
          (i = this.shadowRoot) == null
            ? void 0
            : i.querySelector(`.day-row:nth-child(${t + 2}) .bar-wrap`);
      if (s) {
        const r = s.getBoundingClientRect(),
          n = this._pixelToMinutes(e.clientX - r.left, r.width),
          l = this._snapToMinutes(n),
          d = this._toSegments(this.days[t] ?? []),
          p = d[o],
          h = d[o + 1];
        if (p && h) {
          const f = p.startMin + 15,
            g = h.endMin - 15,
            v = Math.max(f, Math.min(g, l)),
            m = (this.days[t] ?? []).map((_) =>
              _.start === h.period.start
                ? { ..._, start: this._minutesToHHMM(v) }
                : _,
            ),
            b = this.days.map((_, $) => ($ === t ? m : _));
          (this._drag = null),
            (this._dragTooltipMinutes = null),
            (this._dragPreviewDays = b),
            (this._justDragged = !0),
            this._emitChange(t, m);
          return;
        }
      }
      (this._drag = null),
        (this._dragTooltipMinutes = null),
        (this._dragPreviewDays = null),
        (this._justDragged = !0);
    }
    _onPointerCancel(e) {
      this._drag &&
        ((this._drag = null),
        (this._dragTooltipMinutes = null),
        (this._dragPreviewDays = null));
    }
    // -----------------------------------------------------------------------
    // Copy / Paste
    // -----------------------------------------------------------------------
    _onCopy(e) {
      this._clipboard = JSON.parse(JSON.stringify(this.days[e] ?? []));
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
      if (
        (e.has("days") &&
          this._dragPreviewDays &&
          (this._previewMatchesDays(this._dragPreviewDays, this.days) ||
            (this._dragPreviewDays = null)),
        this._popup)
      ) {
        const o =
          (t = this.shadowRoot) == null ? void 0 : t.querySelector(".popup");
        if (o) {
          const s = o.getBoundingClientRect(),
            i = 8;
          let { x: r, y: n } = this._popup;
          s.bottom > window.innerHeight - i &&
            (n -= s.bottom - (window.innerHeight - i)),
            s.right > window.innerWidth - i &&
              (r -= s.right - (window.innerWidth - i)),
            (n = Math.max(i, n)),
            (r = Math.max(i, r)),
            (r !== this._popup.x || n !== this._popup.y) &&
              (this._popup = { ...this._popup, x: r, y: n });
        }
      }
    }
    render() {
      return c`
      <div
        class="week-grid"
        @pointermove=${this._onPointerMove}
        @pointerup=${this._onPointerUp}
        @pointercancel=${this._onPointerCancel}
      >
        <!-- Time axis above day rows — identical structure to bottom axis -->
        ${this._renderTimeAxis()}
        ${Ft.map((e, t) => this._renderDayRow(e, t))}

        <!-- Shared time axis below day rows -->
        ${this._renderTimeAxis()}
      </div>

      <!-- Drag tooltip -->
      ${
        this._drag !== null && this._dragTooltipMinutes !== null
          ? c`<div
            class="drag-tooltip"
            style="left:${this._dragTooltipX}px;top:${this._dragTooltipY}px"
            aria-live="polite"
          >
            ${this._minutesToHHMM(this._dragTooltipMinutes)}
          </div>`
          : ""
      }

      <!-- Popup overlay + popup -->
      ${
        this._popup
          ? c`
            <div class="popup-overlay" @click=${this._closePopup}></div>
            <div
              class="popup"
              style="left:${this._popup.x}px;top:${this._popup.y}px"
            >
              ${this._renderPopup()}
            </div>
          `
          : ""
      }
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
      return c`
      <div class="time-axis">
        <div class="time-axis-label-spacer"></div>
        <div class="time-axis-inner">
          ${[0, 3, 6, 9, 12, 15, 18, 21, 24].map((t) => {
            const o =
              t % 12 === 0
                ? ""
                : t % 6 === 0
                  ? "axis-tick--6h"
                  : "axis-tick--3h";
            return c`<span
              class="axis-tick ${o}"
              style="left:${(t / 24) * 100}%"
              >${String(t).padStart(2, "0")}:00</span
            >`;
          })}
        </div>
        <div class="time-axis-actions-ghost" aria-hidden="true">
          <ha-icon-button
            ><ha-icon icon="mdi:content-copy"></ha-icon
          ></ha-icon-button>
          <ha-icon-button
            ><ha-icon icon="mdi:content-paste"></ha-icon
          ></ha-icon-button>
        </div>
      </div>
    `;
    }
    _renderDayRow(e, t) {
      const s = (this._dragPreviewDays ?? this.days)[t] ?? [],
        i = this._toSegments(s),
        r = i.length === 0;
      return c`
      <div class="day-row">
        <div class="day-label">${e}</div>

        <div
          class="bar-wrap"
          @click=${(n) => {
            (n.target.classList.contains("bar-wrap") ||
              n.target.classList.contains("bar-row-inner")) &&
              this._onBarClick(n, t);
          }}
        >
          ${
            r
              ? c`<div class="empty-hint">
                Click the bar to add your first period.
              </div>`
              : c`<div class="bar-row-inner">
                ${i.map((n, l) => this._renderSegment(n, t, l, i.length))}
              </div>`
          }
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
      const i = this._colorForPeriod(e.period),
        r = this._labelForPeriod(e.period),
        n = ((e.endMin - e.startMin) / 1440) * 100,
        l =
          this.mode === "presence"
            ? e.period.state ?? "absent"
            : ((d = e.period.mode) == null ? void 0 : d.replace(/_/g, " ")) ??
              "frost protection";
      return c`
      <div
        class="segment"
        style="width:${n}%;background:${i}"
        aria-label="${l}"
        @click=${(p) => this._onSegmentClick(p, t, o)}
      >
        ${n > 2.7 ? c`<span class="segment-label">${r}</span>` : ""}

        <!-- Drag handle on right border (not on last segment) -->
        ${
          o < s - 1
            ? c`<div
              class="drag-handle"
              @pointerdown=${(p) => this._onDragHandlePointerDown(p, t, o)}
            ></div>`
            : ""
        }
      </div>
    `;
    }
    _renderPopup() {
      var e;
      if (!this._popup) return c``;
      if (this._popup.kind === "split") {
        const t = this._minutesToHHMM(this._popup.snappedMinutes ?? 0);
        return c`
        <div class="popup-title">Split at ${t}</div>
        <div class="mode-options">
          ${this._modeOptions().map(
            (o) => c`
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
            `,
          )}
        </div>
      `;
      }
      if (this._popup.kind === "edit") {
        const o = this._toSegments(this.days[this._popup.dayIndex] ?? [])[
          this._popup.segIndex ?? 0
        ];
        if (!o) return c``;
        const s = this._minutesToHHMM(o.startMin),
          i = this._minutesToHHMM(o.endMin),
          r = `${s} – ${i}`,
          n =
            this.mode === "presence"
              ? o.period.state ?? "absent"
              : ((e = o.period.mode) == null ? void 0 : e.replace(/_/g, " ")) ??
                "frost protection",
          d = o.endMin - o.startMin >= 30;
        return c`
        <div class="popup-title">${r} · ${n}</div>

        <div class="mode-options">
          <div
            style="font-size:11px;color:var(--secondary-text-color);margin-bottom:4px"
          >
            Change mode
          </div>
          ${this._modeOptions().map(
            (p) => c`
              <button
                class="mode-option"
                @click=${() => this._onEditModeSelect(p.key)}
              >
                <span
                  class="mode-swatch"
                  style="background:${p.color}"
                ></span>
                ${p.label}
              </button>
            `,
          )}
        </div>

        <div class="popup-actions">
          <button
            class="popup-btn"
            ?disabled=${!d}
            style=${d ? "" : "opacity:0.4;cursor:default"}
            @click=${this._onSplitPeriod}
          >
            Split period
          </button>
          <button class="popup-btn danger" @click=${this._onDeleteSegment}>
            Delete period
          </button>
        </div>
      `;
      }
      return c``;
    }
  };
Le.styles = k`
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
      /* overflow:visible so the 44px drag handle (positioned right:-22px on
         .segment) stays hittable beyond the segment boundary. overflow:hidden
         clips the handle, making the touch target unreachable on Android. */
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

    /* ---- Shared time axis (above and below day rows) --------------------- */
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

    /* Invisible clone of .day-actions — forces bar-wrap width to match.
       height:0 + overflow:hidden collapses to label height while the browser
       computes the natural button width for flex layout. */
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
    .axis-tick:first-child {
      transform: translateX(0);
    }
    .axis-tick:last-child {
      transform: translateX(-100%);
    }

    /* On narrow screens hide 3h-interval ticks (3, 9, 15, 21) */
    @media (max-width: 479px) {
      .axis-tick--3h {
        display: none;
      }
    }
    /* On very narrow screens also hide 6h-interval ticks (6, 18) */
    @media (max-width: 339px) {
      .axis-tick--6h {
        display: none;
      }
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
      box-shadow: var(--ha-card-box-shadow, 0 4px 16px rgba(0, 0, 0, 0.25));
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
let z = Le;
H([u({ type: Array })], z.prototype, "days");
H([u({ type: String })], z.prototype, "mode");
H([y()], z.prototype, "_clipboard");
H([y()], z.prototype, "_drag");
H([y()], z.prototype, "_dragTooltipMinutes");
H([y()], z.prototype, "_dragTooltipX");
H([y()], z.prototype, "_dragTooltipY");
H([y()], z.prototype, "_dragPreviewDays");
H([y()], z.prototype, "_popup");
customElements.define("climate-manager-time-bar", z);
const xe = k`
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
    cursor: pointer;
  }

  .chip:hover {
    background: var(--secondary-background-color, #eeeeee);
    border-color: var(--primary-color);
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
`,
  Ae = k`
  .section-label {
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.5px;
    text-transform: uppercase;
    color: var(--secondary-text-color);
    margin-bottom: 8px;
  }
`,
  De = k`
  .mode-select {
    width: 100%;
    padding: 10px 12px;
    font-size: 16px;
    font-family: inherit;
    color: var(--primary-text-color);
    background-color: var(
      --card-background-color,
      var(--secondary-background-color)
    );
    border: 1px solid var(--divider-color);
    border-radius: 4px;
    outline: none;
    cursor: pointer;
  }

  .mode-select:focus {
    border-color: var(--primary-color);
    border-width: 2px;
  }
`,
  Ie = k`
  .schedule-hint {
    font-size: 12px;
    color: var(--secondary-text-color);
    margin: 6px 0 12px;
    line-height: 1.5;
  }
`,
  ft = k`
  .expand-icon {
    color: var(--secondary-text-color);
    transition: transform 0.2s;
  }

  .expand-icon.expanded {
    transform: rotate(180deg);
  }
`;
var Xt = Object.defineProperty,
  L = (a, e, t, o) => {
    for (var s = void 0, i = a.length - 1, r; i >= 0; i--)
      (r = a[i]) && (s = r(e, t, s) || s);
    return s && Xt(e, t, s), s;
  };
const Oe = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"];
function ne(a) {
  return Oe.map((e) => (a != null && a[e] ? [...a[e]] : []));
}
function Ne(a) {
  return Oe[a] ?? "mon";
}
function Vt(a, e) {
  if (!a) return null;
  const t = e.getDay(),
    o = t === 0 ? 6 : t - 1,
    s = Oe[o],
    i = a[s] ?? [],
    r = e.getHours() * 60 + e.getMinutes();
  let n = null;
  for (const l of i) {
    const [d = 0, p = 0] = l.start.split(":").map(Number);
    d * 60 + p <= r && (n = "mode" in l ? l.mode : null);
  }
  return n;
}
const _t = "off",
  qt = "time_program",
  Yt = "time_program_presences",
  Gt = {
    [_t]: "Off",
    [qt]: "Time program",
    [Yt]: "Time program & presences",
  },
  Ue = class Ue extends C {
    constructor() {
      super(...arguments),
        (this.status = null),
        (this._trvStatuses = []),
        (this._loadingStatuses = !1),
        (this._tadoXLastFetched = null),
        (this._tadoXScanInterval = null),
        (this._tempSaveTimer = null),
        (this._onTemperatureInput = () => {
          this._tempSaveTimer !== null && clearTimeout(this._tempSaveTimer),
            (this._tempSaveTimer = setTimeout(() => {
              this._saveTemperatures();
            }, 600));
        }),
        (this._onTemperatureBlur = () => {
          this._tempSaveTimer !== null &&
            (clearTimeout(this._tempSaveTimer), (this._tempSaveTimer = null)),
            this._saveTemperatures();
        }),
        (this._onResetTemperatures = async () => {
          try {
            await this.ws.resetPeriodTemperatures(),
              await this.panel.reloadConfig(),
              this.panel.showToast("Reset to defaults", !1);
          } catch {
            this.panel.showToast("Reset failed — retrying...", !0);
          }
        }),
        (this._onCalibrationToggle = async (e) => {
          const t = e.target.checked;
          try {
            await this.ws.setCalibrationConfig(t),
              await this.panel.reloadConfig(),
              this.panel.showToast("Saved", !1),
              t && this._loadCalibrationStatuses();
          } catch {
            this.panel.showToast("Save failed", !0);
          }
        }),
        (this._loadCalibrationStatuses = async () => {
          this._loadingStatuses = !0;
          try {
            const e = await this.ws.getCalibrationStatus();
            (this._trvStatuses = e.trvs),
              (this._tadoXScanInterval = e.tado_x_scan_interval),
              (this._tadoXLastFetched = e.tado_x_last_fetched);
          } catch {
            this._trvStatuses = [];
          } finally {
            this._loadingStatuses = !1;
          }
        });
    }
    async _saveTemperatures() {
      const e = this.shadowRoot;
      if (!e) return;
      const t = (s) => {
          const i = e.querySelector(`#temp-${s}`);
          return i
            ? parseFloat(i.value)
            : this.config.period_temperatures[s] ?? 0;
        },
        o = {
          frost_protection: t("frost_protection"),
          reduced: t("reduced"),
          normal: t("normal"),
          comfort: t("comfort"),
        };
      try {
        await this.ws.setPeriodTemperatures(o),
          await this.panel.reloadConfig(),
          this.panel.showToast("Saved", !1);
      } catch {
        this.panel.showToast("Save failed — retrying...", !0);
      }
    }
    // -----------------------------------------------------------------------
    // Render helpers
    // -----------------------------------------------------------------------
    _getZoneRows() {
      var o, s;
      const e = /* @__PURE__ */ new Date(),
        t = [];
      t.push({
        id: "default",
        name: this.config.default_zone_name,
        mode:
          ((o = this.status) == null ? void 0 : o.global_mode) ??
          this.config.global_mode,
        activePeriod:
          ((s = this.status) == null ? void 0 : s.active_period) ?? null,
      });
      for (const [i, r] of Object.entries(this.config.zones))
        t.push({
          id: i,
          name: r.name,
          mode: r.mode,
          activePeriod: r.mode !== _t ? Vt(r.time_program, e) : null,
        });
      return t;
    }
    _renderStatusCard() {
      var r;
      const e = this.status,
        t = this._getZoneRows(),
        o = Object.keys(((r = this.config) == null ? void 0 : r.persons) ?? {}),
        s = new Set((e == null ? void 0 : e.present_persons) ?? []),
        i =
          o.length === 0
            ? c`<span class="status-value">No persons configured</span>`
            : c`
            <span class="status-value">
              ${o.map((n, l) => {
                var h, f, g;
                const d =
                    ((g =
                      (f = (h = this.hass) == null ? void 0 : h.states[n]) ==
                      null
                        ? void 0
                        : f.attributes) == null
                      ? void 0
                      : g.friendly_name) ?? n,
                  p = s.has(n);
                return c`<span
                    class="person-dot ${p ? "" : "absent"}"
                  ></span
                  >${d}${l < o.length - 1 ? ", " : ""}`;
              })}
            </span>
          `;
      return c`
      <ha-card>
        <div class="card-header">Current Status</div>
        <div class="card-content">
          <div class="zone-status-grid">
            <div class="zone-status-header">
              <span>Zone</span>
              <span>Mode</span>
              <span>Active period</span>
            </div>
            ${t.map((n) => {
              const l = ve(n.id === "default" ? void 0 : n.id),
                d = Gt[n.mode] ?? n.mode,
                p = n.activePeriod ? Re[n.activePeriod] ?? n.activePeriod : "—";
              return c`
                <div class="zone-status-row">
                  <span
                    class="zone-status-name"
                    style="color: ${l.color}; cursor: pointer;"
                    @click=${() =>
                      this.panel.navigateToZone(
                        n.id === "default" ? void 0 : n.id,
                      )}
                    >${n.name}</span
                  >
                  <span class="zone-status-value">${d}</span>
                  <span class="zone-status-value">${p}</span>
                </div>
              `;
            })}
          </div>
          <div class="status-row">
            <span class="status-label">Persons:</span>
            ${i}
          </div>
        </div>
      </ha-card>
    `;
    }
    _renderTemperaturesCard() {
      const e = this.config.period_temperatures,
        t = (o, s) => c`
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
            @keydown=${(i) => {
              i.key === "Enter" && i.target.blur();
            }}
          />
          <span class="temp-suffix">°C</span>
        </div>
      </div>
    `;
      return c`
      <ha-card>
        <div class="card-header">Temperatures</div>
        <div class="card-content">
          <div class="temp-fields">
            ${t("frost_protection", "Frost protection")}
            ${t("reduced", "Reduced")} ${t("normal", "Normal")}
            ${t("comfort", "Comfort")}
          </div>
          <button class="reset-btn" @click=${this._onResetTemperatures}>
            Reset to default
          </button>
        </div>
      </ha-card>
    `;
    }
    _openEntityMoreInfo(e) {
      e &&
        this.dispatchEvent(
          new CustomEvent("hass-more-info", {
            bubbles: !0,
            composed: !0,
            detail: { entityId: e },
          }),
        );
    }
    _getFloorIcon(e) {
      var s, i;
      const t =
        (i = (s = this.hass) == null ? void 0 : s.floors) == null
          ? void 0
          : i[e];
      if (t != null && t.icon) return t.icon;
      const o = (t == null ? void 0 : t.level) ?? 0;
      return o === -1
        ? "mdi:home-floor-negative-1"
        : o < 0
          ? "mdi:home-floor-b"
          : o === 1
            ? "mdi:home-floor-1"
            : o === 2
              ? "mdi:home-floor-2"
              : o === 3 || o > 3
                ? "mdi:home-floor-3"
                : "mdi:home-floor-0";
    }
    _renderTRVRows(e) {
      return e.map(
        (t) => c`
        <tr>
          <td>
            <span
              class="chip"
              @click=${() => this._openEntityMoreInfo(t.entity_id)}
            >
              <ha-icon icon="mdi:thermometer"></ha-icon>
              ${t.friendly_name}
            </span>
          </td>
          <td>
            <span
              class="calib-badge ${
                t.supports_calibration ? "supported" : "unsupported"
              }"
            >
              ${t.supports_calibration ? "Tado X" : "Not supported"}
            </span>
          </td>
          <td>
            ${
              t.trv_temperature != null
                ? c`${t.trv_temperature.toFixed(1)} °C`
                : "—"
            }
          </td>
          <td>
            ${
              t.room_temperature != null
                ? c`${t.room_temperature.toFixed(1)} °C`
                : "—"
            }
          </td>
          <td>
            ${
              t.last_applied_delta != null
                ? c`${
                    t.last_applied_delta > 0 ? "+" : ""
                  }${t.last_applied_delta.toFixed(2)}
                °C`
                : "—"
            }
          </td>
          <td>
            ${
              t.last_calibrated_at
                ? new Date(t.last_calibrated_at).toLocaleString()
                : "Never"
            }
          </td>
        </tr>
      `,
      );
    }
    _renderTRVTable() {
      var n, l, d;
      if (this._trvStatuses.length === 0)
        return this._loadingStatuses
          ? c`<div class="calib-loading">Loading TRV status…</div>`
          : c`
        <button
          class="refresh-btn"
          @click=${this._loadCalibrationStatuses}
          style="margin-top: 8px;"
        >
          Refresh
        </button>
        <div class="calib-empty">No managed TRVs found.</div>
      `;
      const e = /* @__PURE__ */ new Map();
      for (const p of this._trvStatuses) {
        const h =
          ((d =
            (l = (n = this.hass) == null ? void 0 : n.areas) == null
              ? void 0
              : l[p.area_id]) == null
            ? void 0
            : d.floor_id) ?? null;
        e.has(h) || e.set(h, []), e.get(h).push(p);
      }
      for (const p of e.values())
        p.sort((h, f) => h.friendly_name.localeCompare(f.friendly_name));
      const t = [...e.keys()]
          .filter((p) => p !== null)
          .sort((p, h) => {
            var f, g, v, m, b, _;
            return (
              (((v =
                (g = (f = this.hass) == null ? void 0 : f.floors) == null
                  ? void 0
                  : g[h]) == null
                ? void 0
                : v.level) ?? 0) -
              (((_ =
                (b = (m = this.hass) == null ? void 0 : m.floors) == null
                  ? void 0
                  : b[p]) == null
                ? void 0
                : _.level) ?? 0)
            );
          }),
        o = e.get(null) ?? [],
        s = this._trvStatuses.some((p) => p.supports_calibration),
        i = this._tadoXLastFetched
          ? new Date(this._tadoXLastFetched).toLocaleTimeString()
          : null,
        r =
          this._tadoXScanInterval != null
            ? this._tadoXScanInterval >= 60
              ? `${Math.round(this._tadoXScanInterval / 60)} min`
              : `${this._tadoXScanInterval} s`
            : "~30 s";
      return c`
      <div class="calib-table-wrap">
        <button
          class="refresh-btn"
          style="margin-top: 8px; margin-bottom: 8px;"
          ?disabled=${this._loadingStatuses}
          @click=${this._loadCalibrationStatuses}
        >
          ${this._loadingStatuses ? "Refreshing…" : "Refresh"}
        </button>
        ${
          s
            ? c`
              <div class="calib-info-banner">
                <ha-icon icon="mdi:information-outline"></ha-icon>
                <div>
                  Tado X data is fetched from the cloud every ${r} —
                  displayed temperatures may lag behind actual values.
                  ${
                    i
                      ? c`<div class="calib-info-fetched">
                        Last fetched: ${i}
                      </div>`
                      : ""
                  }
                </div>
              </div>
            `
            : ""
        }
        <table class="calib-table">
          <thead>
            <tr>
              <th>TRV</th>
              <th>Auto-calibration</th>
              <th>TRV temp</th>
              <th>Room temp</th>
              <th>Last applied delta</th>
              <th>Last adjusted</th>
            </tr>
          </thead>
          ${t.map((p) => {
            var f, g, v;
            const h =
              ((v =
                (g = (f = this.hass) == null ? void 0 : f.floors) == null
                  ? void 0
                  : g[p]) == null
                ? void 0
                : v.name) ?? p;
            return c`
              <tbody>
                <tr>
                  <td colspan="6" class="calib-floor-header">
                    <ha-icon icon=${this._getFloorIcon(p)}></ha-icon>
                    ${h}
                  </td>
                </tr>
                ${this._renderTRVRows(e.get(p) ?? [])}
              </tbody>
            `;
          })}
          ${
            o.length > 0
              ? c`<tbody>
                ${this._renderTRVRows(o)}
              </tbody>`
              : ""
          }
        </table>
      </div>
    `;
    }
    _renderOptionsCard() {
      const e = this.config.calibration_enabled ?? !1;
      return (
        e &&
          this._trvStatuses.length === 0 &&
          !this._loadingStatuses &&
          this._loadCalibrationStatuses(),
        c`
      <ha-card>
        <div class="card-header">TRV Auto-Calibration</div>
        <div class="card-content">
          <div class="option-row">
            <span class="option-label">Enable auto-calibration</span>
            <ha-switch
              .checked=${e}
              @change=${this._onCalibrationToggle}
            ></ha-switch>
          </div>
          ${e ? this._renderTRVTable() : ""}
        </div>
      </ha-card>
    `
      );
    }
    render() {
      return c`
      ${this._renderStatusCard()} ${this._renderTemperaturesCard()}
      ${this._renderOptionsCard()}
    `;
    }
  };
Ue.styles = [
  xe,
  k`
      :host {
        display: block;
        --present-color: ${pt(ie.present)};
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

      .person-dot.absent {
        background: var(--secondary-text-color, #9e9e9e);
      }

      /* ---- Zone status grid ---- */
      .zone-status-grid {
        margin-bottom: 12px;
      }

      .zone-status-header {
        display: grid;
        grid-template-columns: 1.2fr 1fr 1fr;
        gap: 8px;
        padding-bottom: 4px;
        border-bottom: 1px solid var(--divider-color);
        margin-bottom: 2px;
        font-size: 11px;
        font-weight: 600;
        color: var(--secondary-text-color);
        text-transform: uppercase;
        letter-spacing: 0.05em;
      }

      .zone-status-row {
        display: grid;
        grid-template-columns: 1.2fr 1fr 1fr;
        gap: 8px;
        padding: 5px 0;
        border-bottom: 1px solid var(--divider-color);
        font-size: 13px;
        align-items: center;
      }

      .zone-status-grid .zone-status-row:last-child {
        border-bottom: none;
      }

      .zone-status-name {
        font-weight: 500;
      }

      .zone-status-name:hover {
        text-decoration: underline;
      }

      .zone-status-value {
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
        background-color: var(
          --card-background-color,
          var(--secondary-background-color)
        );
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

      /* ---- Options card ---- */
      .option-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 8px;
        font-size: 14px;
        color: var(--primary-text-color);
      }

      .option-label {
        font-weight: 500;
        flex: 1;
        margin-right: 16px;
      }

      /* ---- TRV calibration status table ---- */
      .calib-table-wrap {
        margin-top: 16px;
        overflow-x: auto;
      }

      .calib-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 13px;
        color: var(--primary-text-color);
      }

      .calib-table th {
        text-align: left;
        font-weight: 600;
        padding: 6px 8px;
        border-bottom: 1px solid var(--divider-color, #e0e0e0);
        white-space: nowrap;
      }

      .calib-table td {
        padding: 6px 8px;
        border-bottom: 1px solid var(--divider-color, #e0e0e0);
        vertical-align: middle;
      }

      .calib-table tr:last-child td {
        border-bottom: none;
      }

      .calib-badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 10px;
        font-size: 11px;
        font-weight: 600;
      }

      .calib-badge.supported {
        background: rgba(34, 197, 94, 0.15);
        color: #15803d;
      }

      .calib-badge.unsupported {
        background: rgba(0, 0, 0, 0.06);
        color: var(--secondary-text-color);
      }

      .calib-loading {
        text-align: center;
        padding: 16px;
        color: var(--secondary-text-color);
        font-size: 13px;
      }

      .calib-empty {
        text-align: center;
        padding: 16px;
        color: var(--secondary-text-color);
        font-size: 13px;
      }

      .refresh-btn {
        margin-top: 8px;
        background: none;
        border: 1px solid var(--divider-color, #e0e0e0);
        border-radius: 4px;
        padding: 4px 10px;
        font-size: 12px;
        cursor: pointer;
        color: var(--primary-text-color);
      }

      .refresh-btn:hover {
        background: var(--secondary-background-color, #f5f5f5);
      }

      /* ---- Tado X info banner ---- */
      .calib-info-banner {
        display: flex;
        align-items: flex-start;
        gap: 8px;
        padding: 8px 10px;
        margin-bottom: 10px;
        border-radius: 4px;
        background: rgba(3, 169, 244, 0.08);
        border: 1px solid rgba(3, 169, 244, 0.25);
        font-size: 12px;
        color: var(--secondary-text-color);
        line-height: 1.5;
      }

      .calib-info-banner ha-icon {
        --mdc-icon-size: 16px;
        width: 16px;
        height: 16px;
        flex-shrink: 0;
        color: #0288d1;
        margin-top: 1px;
      }

      .calib-info-fetched {
        margin-top: 2px;
        font-size: 11px;
        color: var(--secondary-text-color);
        opacity: 0.75;
      }

      /* ---- TRV floor section headers ---- */
      .calib-floor-header {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 11px;
        font-weight: 600;
        letter-spacing: 0.5px;
        text-transform: uppercase;
        color: var(--secondary-text-color);
        padding: 10px 8px 4px;
        border-bottom: 1px solid var(--divider-color, #e0e0e0);
      }

      .calib-floor-header ha-icon {
        --mdc-icon-size: 14px;
        width: 14px;
        height: 14px;
        flex-shrink: 0;
      }
    `,
];
let R = Ue;
L([u({ attribute: !1 })], R.prototype, "config");
L([u({ attribute: !1 })], R.prototype, "status");
L([u({ attribute: !1 })], R.prototype, "ws");
L([u({ attribute: !1 })], R.prototype, "panel");
L([u({ attribute: !1 })], R.prototype, "hass");
L([y()], R.prototype, "_trvStatuses");
L([y()], R.prototype, "_loadingStatuses");
L([y()], R.prototype, "_tadoXLastFetched");
L([y()], R.prototype, "_tadoXScanInterval");
customElements.define("climate-manager-global-settings-tab", R);
var Kt = Object.defineProperty,
  Q = (a, e, t, o) => {
    for (var s = void 0, i = a.length - 1, r; i >= 0; i--)
      (r = a[i]) && (s = r(e, t, s) || s);
    return s && Kt(e, t, s), s;
  };
const je = class je extends C {
  constructor() {
    super(...arguments),
      (this.items = []),
      (this.placeholder = "Search…"),
      (this.triggerLabel = "Add"),
      (this.triggerIcon = "mdi:plus"),
      (this._open = !1),
      (this._query = ""),
      (this._docClickHandler = null);
  }
  // -------------------------------------------------------------------------
  // Popup lifecycle
  // -------------------------------------------------------------------------
  _openPopup() {
    (this._open = !0),
      (this._query = ""),
      this.updateComplete.then(() => {
        var t;
        const e =
          (t = this.shadowRoot) == null
            ? void 0
            : t.querySelector(".search-input");
        e == null || e.focus();
      }),
      (this._docClickHandler = (e) => {
        e.composedPath().includes(this) || this._closePopup();
      }),
      document.addEventListener("click", this._docClickHandler);
  }
  _closePopup() {
    (this._open = !1),
      (this._query = ""),
      this._docClickHandler &&
        (document.removeEventListener("click", this._docClickHandler),
        (this._docClickHandler = null));
  }
  disconnectedCallback() {
    super.disconnectedCallback(),
      this._docClickHandler &&
        (document.removeEventListener("click", this._docClickHandler),
        (this._docClickHandler = null));
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
        composed: !0,
      }),
    ),
      this._closePopup();
  }
  // -------------------------------------------------------------------------
  // Filtering
  // -------------------------------------------------------------------------
  _filteredItems() {
    if (!this._query) return this.items;
    const e = this._query.toLowerCase();
    return this.items.filter((t) => {
      var i;
      const o = t.label.toLowerCase().includes(e),
        s =
          ((i = t.secondary) == null ? void 0 : i.toLowerCase().includes(e)) ??
          !1;
      return o || s;
    });
  }
  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------
  render() {
    const e = this._filteredItems();
    return c`
      <button
        class="trigger-btn"
        @click=${this._onTriggerClick}
        aria-expanded=${this._open}
        aria-haspopup="listbox"
      >
        <ha-icon icon=${this.triggerIcon}></ha-icon>
        ${this.triggerLabel}
      </button>

      ${
        this._open
          ? c`
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
              ${
                e.length > 0
                  ? c`
                    <ul class="item-list" role="listbox">
                      ${e.map(
                        (t) => c`
                          <li
                            class="item-row"
                            role="option"
                            @click=${() => this._onItemClick(t)}
                          >
                            ${
                              t.icon
                                ? c`<ha-icon
                                  class="item-icon"
                                  icon=${t.icon}
                                ></ha-icon>`
                                : ""
                            }
                            <div class="item-text">
                              <span class="item-label">${t.label}</span>
                              ${
                                t.secondary
                                  ? c`<span class="item-secondary"
                                    >${t.secondary}</span
                                  >`
                                  : ""
                              }
                            </div>
                          </li>
                        `,
                      )}
                    </ul>
                  `
                  : c`<div class="empty-message">No results</div>`
              }
            </div>
          `
          : ""
      }
    `;
  }
};
je.styles = k`
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
      box-shadow: var(--ha-card-box-shadow, 0 4px 16px rgba(0, 0, 0, 0.15));
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
let I = je;
Q([u({ type: Array })], I.prototype, "items");
Q([u({ type: String })], I.prototype, "placeholder");
Q([u({ type: String })], I.prototype, "triggerLabel");
Q([u({ type: String })], I.prototype, "triggerIcon");
Q([y()], I.prototype, "_open");
Q([y()], I.prototype, "_query");
customElements.define("search-picker", I);
var Jt = Object.defineProperty,
  A = (a, e, t, o) => {
    for (var s = void 0, i = a.length - 1, r; i >= 0; i--)
      (r = a[i]) && (s = r(e, t, s) || s);
    return s && Jt(e, t, s), s;
  };
const Ze = class Ze extends C {
  constructor() {
    super(...arguments),
      (this.roomStatus = null),
      (this.status = null),
      (this.autoExpand = !1),
      (this._expanded = !1),
      (this._lastTimeProgram = void 0),
      (this._cachedDays = []);
  }
  get _days() {
    var t;
    const e = (t = this.config) == null ? void 0 : t.time_program;
    return (
      e !== this._lastTimeProgram &&
        ((this._lastTimeProgram = e), (this._cachedDays = ne(e ?? void 0))),
      this._cachedDays
    );
  }
  connectedCallback() {
    super.connectedCallback(), (this._expanded = !1);
  }
  updated(e) {
    e.has("autoExpand") &&
      this.autoExpand &&
      ((this._expanded = !0),
      setTimeout(() => {
        const t = this.getBoundingClientRect();
        this.scrollIntoView({
          behavior: "smooth",
          block: t.height <= window.innerHeight ? "nearest" : "start",
        });
      }, 0));
  }
  // -----------------------------------------------------------------------
  // Person association handlers
  // -----------------------------------------------------------------------
  _getAssignedPersonIds() {
    var t;
    const e = ((t = this.panelConfig) == null ? void 0 : t.persons) ?? {};
    return Object.entries(e)
      .filter(([, o]) => {
        var s;
        return (s = o.room_ids) == null ? void 0 : s.includes(this.roomId);
      })
      .map(([o]) => o);
  }
  _getAllPersonIds() {
    var o, s;
    const e = Object.keys(
        ((o = this.hass) == null ? void 0 : o.states) ?? {},
      ).filter((i) => i.startsWith("person.")),
      t = Object.keys(
        ((s = this.panelConfig) == null ? void 0 : s.persons) ?? {},
      );
    return [.../* @__PURE__ */ new Set([...e, ...t])];
  }
  _getPersonName(e) {
    var t, o, s;
    return (
      ((s =
        (o = (t = this.hass) == null ? void 0 : t.states[e]) == null
          ? void 0
          : o.attributes) == null
        ? void 0
        : s.friendly_name) ??
      e
        .replace(/^person\./, "")
        .replace(/_/g, " ")
        .replace(/\b\w/g, (i) => i.toUpperCase())
    );
  }
  _getPersonPresenceState(e) {
    var o, s;
    const t =
      (s = (o = this.hass) == null ? void 0 : o.states[e]) == null
        ? void 0
        : s.state;
    return t === "home"
      ? "Home"
      : t === "not_home"
        ? "Away"
        : t
          ? t.charAt(0).toUpperCase() + t.slice(1)
          : "—";
  }
  _onPersonPicked(e) {
    e.stopPropagation();
    const t = e.detail.id;
    t && this._onAddPerson(t);
  }
  async _onAddPerson(e) {
    var s, i, r;
    const t = [
        ...(((r =
          (i = (s = this.panelConfig) == null ? void 0 : s.persons) == null
            ? void 0
            : i[e]) == null
          ? void 0
          : r.room_ids) ?? []),
      ],
      o = t.includes(this.roomId) ? t : [...t, this.roomId];
    try {
      await this.ws.setPersonConfig(e, { room_ids: o }),
        await this.panel.reloadConfig(),
        this.panel.showToast("Saved", !1);
    } catch {
      this.panel.showToast("Save failed — retrying...", !0);
    }
  }
  async _onRemovePerson(e) {
    var s, i, r;
    const o = [
      ...(((r =
        (i = (s = this.panelConfig) == null ? void 0 : s.persons) == null
          ? void 0
          : i[e]) == null
        ? void 0
        : r.room_ids) ?? []),
    ].filter((n) => n !== this.roomId);
    try {
      await this.ws.setPersonConfig(e, { room_ids: o }),
        await this.panel.reloadConfig(),
        this.panel.showToast("Saved", !1);
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
    t === "custom" && !((s = this.config) != null && s.time_program)
      ? (o = {
          room_mode: "custom",
          time_program: JSON.parse(
            JSON.stringify(this.panelConfig.global_time_program),
          ),
        })
      : (o = { room_mode: t });
    try {
      await this.ws.setRoomConfig(this.roomId, o),
        await this.panel.reloadConfig(),
        this.panel.showToast("Saved", !1);
    } catch {
      this.panel.showToast("Save failed — retrying...", !0);
    }
  }
  // -----------------------------------------------------------------------
  // Schedule override handlers
  // -----------------------------------------------------------------------
  async _onPeriodsChanged(e) {
    const { dayIndex: t, periods: o } = e.detail,
      i = {
        ...(this.config.time_program ?? {
          mon: [],
          tue: [],
          wed: [],
          thu: [],
          fri: [],
          sat: [],
          sun: [],
        }),
      },
      r = Ne(t);
    i[r] = o;
    try {
      await this.ws.setRoomConfig(this.roomId, { time_program: i }),
        await this.panel.reloadConfig(),
        this.panel.showToast("Saved", !1);
    } catch {
      this.panel.showToast("Save failed — retrying...", !0);
    }
    e.stopPropagation();
  }
  async _onResetToGlobal() {
    try {
      await this.ws.resetRoomToGlobalProgram(this.roomId),
        await this.panel.reloadConfig(),
        this.panel.showToast("Saved", !1);
    } catch {
      this.panel.showToast("Save failed — retrying...", !0);
    }
  }
  // -----------------------------------------------------------------------
  // Zone assignment handler (ASSIGN-02)
  // -----------------------------------------------------------------------
  _getZoneName() {
    var t, o, s, i, r, n;
    const e = (t = this.config) == null ? void 0 : t.zone_id;
    return e
      ? ((r =
          (i = (s = this.panelConfig) == null ? void 0 : s.zones) == null
            ? void 0
            : i[e]) == null
          ? void 0
          : r.name) ??
          ((n = this.panelConfig) == null ? void 0 : n.default_zone_name) ??
          "Default Zone"
      : ((o = this.panelConfig) == null ? void 0 : o.default_zone_name) ??
          "Default Zone";
  }
  async _onZoneChange(e) {
    const t = e.target.value,
      o = t ? { zone_id: t } : { zone_id: null };
    try {
      await this.ws.setRoomConfig(this.roomId, o),
        await this.panel.reloadConfig(),
        this.panel.showToast("Saved", !1);
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
    var n, l, d, p, h, f;
    if (
      (((n = this.config) == null ? void 0 : n.room_mode) ?? "global") ===
      "frost_protection"
    )
      return c``;
    if (
      (((l = this.status) == null ? void 0 : l.global_mode) ??
        ((d = this.panelConfig) == null ? void 0 : d.global_mode) ??
        "") === "off"
    )
      return c`
        <span
          class="program-badge"
          style="background: var(--secondary-background-color); color: var(--secondary-text-color);"
          >Off</span
        >
      `;
    const o =
      ((p = this.roomStatus) == null ? void 0 : p.active_period) ?? null;
    if (o == null) return c``;
    const s = Re[o] ?? o,
      i =
        (f = (h = this.panelConfig) == null ? void 0 : h.period_temperatures) ==
        null
          ? void 0
          : f[o],
      r = i != null ? `${s} · ${i}°C` : s;
    return c`
      <span
        class="program-badge"
        style="background: ${j[o]}; color: white;"
        >${r}</span
      >
    `;
  }
  _renderHeaderStatus() {
    var g, v, m;
    const e = this.roomStatus,
      t =
        (e == null ? void 0 : e.temperature) != null
          ? parseFloat(String(e.temperature))
          : null,
      o = t != null && !isNaN(t) ? `${t.toFixed(1)}°C` : "—",
      s = (e == null ? void 0 : e.humidity) != null ? `${e.humidity}%` : "—",
      i =
        ((g = this.status) == null ? void 0 : g.global_mode) ??
        ((v = this.panelConfig) == null ? void 0 : v.global_mode) ??
        "",
      r = i === "time_program_presences",
      l =
        {
          off: "Off",
          time_program: "Time program",
          time_program_presences: "Time & presence",
        }[i] ?? i,
      p = this._getAssignedPersonIds().length,
      h = r
        ? ((m = this.roomStatus) == null ? void 0 : m.present_person_count) ?? 0
        : null,
      f = h != null ? `${h}/${p}` : `${p}`;
    return c`
      <div class="card-header-status">
        <span class="status-item" title="Mode: ${l}">
          <ha-icon icon="mdi:thermometer"></ha-icon>
          ${o}
        </span>
        <span class="status-item">
          <ha-icon icon="mdi:water-percent"></ha-icon>
          ${s}
        </span>
        <span
          class="status-item"
          title="${r ? `${h} present / ${p} assigned` : `${p} assigned`}"
        >
          <ha-icon icon="mdi:account-group"></ha-icon>
          ${f}
        </span>
      </div>
    `;
  }
  _renderTrvSection() {
    var t;
    const e = ((t = this.roomStatus) == null ? void 0 : t.entity_ids) ?? [];
    return e.length === 0
      ? c`
        <div class="no-trv-badge">
          <ha-icon icon="mdi:alert"></ha-icon>
          No climate entities
        </div>
      `
      : c`
      <div class="chips">
        ${e.map((o) => {
          var n, l, d;
          const s = (n = this.hass) == null ? void 0 : n.states[o],
            i =
              ((l = s == null ? void 0 : s.attributes) == null
                ? void 0
                : l.friendly_name) ?? o,
            r =
              ((d = s == null ? void 0 : s.attributes) == null
                ? void 0
                : d.current_temperature) != null
                ? `${s.attributes.current_temperature}°C`
                : "—";
          return c`
            <span
              class="chip"
              @click=${() => this._openEntityMoreInfo(o)}
            >
              <ha-icon icon="mdi:thermometer"></ha-icon>
              ${i}
              <span
                style="color:var(--secondary-text-color);margin-left:4px;font-size:12px;"
                >${r}</span
              >
            </span>
          `;
        })}
      </div>
    `;
  }
  _renderPersonsSection() {
    const e = this._getAssignedPersonIds(),
      o = this._getAllPersonIds().filter((i) => !e.includes(i)),
      s = o.map((i) => ({
        id: i,
        label: this._getPersonName(i),
        secondary: this._getPersonPresenceState(i),
        icon: "mdi:account",
      }));
    return c`
      <div class="section-label" title="Persons whose presence heats this room">
        Associated persons
      </div>
      <div class="chips">
        ${e.map(
          (i) => c`
            <span
              class="chip"
              @click=${() => void this.panel.navigateToPerson(i)}
            >
              <ha-icon icon="mdi:account"></ha-icon>
              ${this._getPersonName(i)}
              <button
                class="chip-remove"
                @click=${(r) => {
                  r.stopPropagation(), this._onRemovePerson(i);
                }}
              >
                ×
              </button>
            </span>
          `,
        )}
        ${
          o.length > 0
            ? c`
              <search-picker
                .items=${s}
                triggerLabel="Add person"
                triggerIcon="mdi:plus"
                placeholder="Search persons…"
                @picked=${(i) => this._onPersonPicked(i)}
              ></search-picker>
            `
            : ""
        }
      </div>
    `;
  }
  _renderRoomModeDescription(e) {
    let t;
    return (
      e === "frost_protection"
        ? (t =
            "Heating is disabled. Room kept at frost protection temperature.")
        : e === "custom"
          ? (t =
              "Room uses its own custom schedule. Zone Off mode still applies.")
          : (t = "This room follows the zone's heating schedule."),
      c`<p class="schedule-hint">${t}</p>`
    );
  }
  _openEntityMoreInfo(e) {
    this.dispatchEvent(
      new CustomEvent("hass-more-info", {
        bubbles: !0,
        composed: !0,
        detail: { entityId: e },
      }),
    );
  }
  render() {
    var s, i, r, n;
    const e = ((s = this.config) == null ? void 0 : s.room_mode) ?? "global",
      t =
        e === "frost_protection"
          ? "frost"
          : e === "custom"
            ? "custom"
            : "global",
      o =
        e === "frost_protection"
          ? "Off"
          : e === "custom"
            ? "Custom program"
            : "Zone program";
    return c`
      <ha-card>
        <div
          class="card-header-row"
          @click=${() => {
            this._expanded = !this._expanded;
          }}
        >
          <div class="card-header-left">
            <div class="card-header-top">
              <span class="room-name">${this.roomName}</span>
              ${this._renderPeriodBadge()}
              <span
                class="program-badge ${t}"
                style=${
                  t === "frost"
                    ? `background: ${j.frost_protection}; color: white;`
                    : ""
                }
                >${o}</span
              >
              <span
                class="zone-badge"
                style=${(() => {
                  var d;
                  const l = ve((d = this.config) == null ? void 0 : d.zone_id);
                  return `background:${l.background};color:${l.color};border-color:${l.border}`;
                })()}
                @click=${(l) => {
                  var d;
                  l.stopPropagation(),
                    this.panel.navigateToZone(
                      (d = this.config) == null ? void 0 : d.zone_id,
                    );
                }}
                >${this._getZoneName()}</span
              >
            </div>
            ${this._renderHeaderStatus()}
          </div>
          <ha-icon
            class="expand-icon ${this._expanded ? "expanded" : ""}"
            icon="mdi:chevron-down"
          ></ha-icon>
        </div>

        ${
          this._expanded
            ? c`
              <div class="card-content">
                <!-- 3-way room mode selector (D-20) -->
                <div
                  class="section-label"
                  title="Zone: zone sched. Custom: room sched. Off: frost only."
                >
                  Mode
                </div>
                <div class="select-wrapper">
                  <select
                    class="mode-select"
                    .value=${e}
                    @change=${this._onRoomModeChange}
                  >
                    <option
                      value="frost_protection"
                      ?selected=${e === "frost_protection"}
                    >
                      Off
                    </option>
                    <option
                      value="global"
                      ?selected=${e === "global"}
                    >
                      Zone program
                    </option>
                    <option
                      value="custom"
                      ?selected=${e === "custom"}
                    >
                      Custom program
                    </option>
                  </select>
                </div>
                ${this._renderRoomModeDescription(e)}

                <!-- Zone picker (ASSIGN-02, D-12) -->
                <div
                  class="section-label"
                  title="Zone — rooms in a zone share a schedule"
                >
                  Zone
                </div>
                <div class="select-wrapper">
                  <select class="mode-select" @change=${this._onZoneChange}>
                    <option value="" ?selected=${!(
                      (i = this.config) != null && i.zone_id
                    )}>
                      ${
                        ((r = this.panelConfig) == null
                          ? void 0
                          : r.default_zone_name) ?? "Default Zone"
                      }
                    </option>
                    ${Object.entries(
                      ((n = this.panelConfig) == null ? void 0 : n.zones) ?? {},
                    ).map(([l, d]) => {
                      var p;
                      return c`
                        <option
                          value=${l}
                          ?selected=${
                            ((p = this.config) == null ? void 0 : p.zone_id) ===
                            l
                          }
                        >
                          ${d.name}
                        </option>
                      `;
                    })}
                  </select>
                </div>

                <!-- Inline time-bar (only in Custom mode) -->
                ${
                  e === "custom"
                    ? c`
                      <div
                        class="section-label"
                        title="Custom schedule — overrides the zone program"
                      >
                        Schedule
                      </div>
                      <div class="time-bar-section">
                        <climate-manager-time-bar
                          mode="schedule"
                          .days=${this._days}
                          @periods-changed=${this._onPeriodsChanged}
                        ></climate-manager-time-bar>
                      </div>
                      <button
                        class="reset-btn"
                        @click=${() => void this._onResetToGlobal()}
                      >
                        Reset to global configuration
                      </button>
                    `
                    : ""
                }
                ${this._renderPersonsSection()}

                <div
                  class="section-label"
                  title="TRV climate entities controlled in this room"
                >
                  Climate entities
                </div>
                ${this._renderTrvSection()}
              </div>
            `
            : ""
        }
      </ha-card>
    `;
  }
};
Ze.styles = [
  xe,
  Ae,
  De,
  ft,
  Ie,
  k`
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

      .zone-badge {
        display: inline-flex;
        align-items: center;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 400;
        border: 1px solid;
        cursor: pointer;
      }

      .zone-badge:hover {
        opacity: 0.8;
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

      /* 3-way room mode selector (D-20) */
      .select-wrapper {
        margin-bottom: 16px;
      }

      /* Inline time bar */
      .time-bar-section {
        margin-top: 12px;
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
    `,
];
let S = Ze;
A([u({ type: String })], S.prototype, "roomId");
A([u({ type: String })], S.prototype, "roomName");
A([u({ attribute: !1 })], S.prototype, "config");
A([u({ attribute: !1 })], S.prototype, "roomStatus");
A([u({ attribute: !1 })], S.prototype, "panelConfig");
A([u({ attribute: !1 })], S.prototype, "status");
A([u({ attribute: !1 })], S.prototype, "ws");
A([u({ attribute: !1 })], S.prototype, "panel");
A([u({ attribute: !1 })], S.prototype, "hass");
A([u({ type: Boolean })], S.prototype, "autoExpand");
A([y()], S.prototype, "_expanded");
customElements.define("climate-manager-room-card", S);
var Qt = Object.defineProperty,
  ee = (a, e, t, o) => {
    for (var s = void 0, i = a.length - 1, r; i >= 0; i--)
      (r = a[i]) && (s = r(e, t, s) || s);
    return s && Qt(e, t, s), s;
  };
const Fe = class Fe extends C {
  constructor() {
    super(...arguments), (this.status = null), (this.expandRoomId = null);
  }
  _getRoomStatus(e) {
    var t, o;
    return (
      ((o = (t = this.status) == null ? void 0 : t.rooms_status) == null
        ? void 0
        : o.find((s) => s.area_id === e)) ?? null
    );
  }
  render() {
    var p, h, f, g, v;
    const e = ((p = this.config) == null ? void 0 : p.rooms) ?? {},
      t = (((h = this.status) == null ? void 0 : h.rooms_status) ?? []).filter(
        (m) => m.has_trv !== !1,
      ),
      o = /* @__PURE__ */ new Set([...t.map((m) => m.area_id)]);
    if (o.size === 0)
      return c`
        <div class="empty-state">
          No rooms discovered. Create areas in Home Assistant and assign climate
          entities.
        </div>
      `;
    const s = (m) => {
        var b, _, $;
        return (
          (($ =
            (_ = (b = this.status) == null ? void 0 : b.rooms_status) == null
              ? void 0
              : _.find((E) => E.area_id === m)) == null
            ? void 0
            : $.name) ??
          m.replace(/_/g, " ").replace(/\b\w/g, (E) => E.toUpperCase())
        );
      },
      i = /* @__PURE__ */ new Map();
    for (const m of o) {
      const b =
        ((v =
          (g = (f = this.hass) == null ? void 0 : f.areas) == null
            ? void 0
            : g[m]) == null
          ? void 0
          : v.floor_id) ?? null;
      i.has(b) || i.set(b, []), i.get(b).push(m);
    }
    for (const m of i.values()) m.sort((b, _) => s(b).localeCompare(s(_)));
    const r = [...i.keys()]
        .filter((m) => m !== null)
        .sort((m, b) => {
          var _, $, E, se, qe, Ye;
          return (
            (((E =
              ($ = (_ = this.hass) == null ? void 0 : _.floors) == null
                ? void 0
                : $[b]) == null
              ? void 0
              : E.level) ?? 0) -
            (((Ye =
              (qe = (se = this.hass) == null ? void 0 : se.floors) == null
                ? void 0
                : qe[m]) == null
              ? void 0
              : Ye.level) ?? 0)
          );
        }),
      n = i.get(null) ?? [],
      l = (m) => {
        const b = e[m] ?? {},
          _ = this._getRoomStatus(m),
          $ = s(m);
        return c`
        <climate-manager-room-card
          .roomId=${m}
          .roomName=${$}
          .config=${b}
          .roomStatus=${_}
          .panelConfig=${this.config}
          .status=${this.status}
          .ws=${this.ws}
          .panel=${this.panel}
          .hass=${this.hass}
          .autoExpand=${this.expandRoomId === m}
        ></climate-manager-room-card>
      `;
      },
      d = (m) => {
        var $, E;
        const b =
          (E = ($ = this.hass) == null ? void 0 : $.floors) == null
            ? void 0
            : E[m];
        if (b != null && b.icon) return b.icon;
        const _ = (b == null ? void 0 : b.level) ?? 0;
        return _ === -1
          ? "mdi:home-floor-negative-1"
          : _ < 0
            ? "mdi:home-floor-b"
            : _ === 1
              ? "mdi:home-floor-1"
              : _ === 2
                ? "mdi:home-floor-2"
                : _ === 3 || _ > 3
                  ? "mdi:home-floor-3"
                  : "mdi:home-floor-0";
      };
    return c`
      ${r.map((m) => {
        var $, E, se;
        const b =
            ((se =
              (E = ($ = this.hass) == null ? void 0 : $.floors) == null
                ? void 0
                : E[m]) == null
              ? void 0
              : se.name) ?? m,
          _ = i.get(m) ?? [];
        return c`
          <div class="floor-header">
            <ha-icon icon=${d(m)}></ha-icon>
            ${b}
          </div>
          ${_.map(l)}
        `;
      })}
      ${n.map(l)}
    `;
  }
};
Fe.styles = k`
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
let O = Fe;
ee([u({ attribute: !1 })], O.prototype, "config");
ee([u({ attribute: !1 })], O.prototype, "status");
ee([u({ attribute: !1 })], O.prototype, "ws");
ee([u({ attribute: !1 })], O.prototype, "panel");
ee([u({ attribute: !1 })], O.prototype, "hass");
ee([u({ attribute: !1 })], O.prototype, "expandRoomId");
customElements.define("climate-manager-rooms-tab", O);
function bt(a) {
  const e = new Date(Date.UTC(a.getFullYear(), a.getMonth(), a.getDate())),
    t = e.getUTCDay() || 7;
  e.setUTCDate(e.getUTCDate() + 4 - t);
  const o = new Date(Date.UTC(e.getUTCFullYear(), 0, 1));
  return Math.ceil(((e.getTime() - o.getTime()) / 864e5 + 1) / 7);
}
function nt(a) {
  return bt(a) % 2 === 0 ? "even" : "odd";
}
var es = Object.defineProperty,
  D = (a, e, t, o) => {
    for (var s = void 0, i = a.length - 1, r; i >= 0; i--)
      (r = a[i]) && (s = r(e, t, s) || s);
    return s && es(e, t, s), s;
  };
const q = "scheduled",
  ue = "ha",
  me = "force_present",
  ge = "force_absent",
  lt = {
    mon: [
      { start: "00:00", state: "present" },
      { start: "08:00", state: "absent" },
      { start: "18:00", state: "present" },
    ],
    tue: [
      { start: "00:00", state: "present" },
      { start: "08:00", state: "absent" },
      { start: "18:00", state: "present" },
    ],
    wed: [
      { start: "00:00", state: "present" },
      { start: "08:00", state: "absent" },
      { start: "18:00", state: "present" },
    ],
    thu: [
      { start: "00:00", state: "present" },
      { start: "08:00", state: "absent" },
      { start: "18:00", state: "present" },
    ],
    fri: [
      { start: "00:00", state: "present" },
      { start: "08:00", state: "absent" },
      { start: "18:00", state: "present" },
    ],
    sat: [{ start: "00:00", state: "present" }],
    sun: [{ start: "00:00", state: "present" }],
  },
  Be = class Be extends C {
    constructor() {
      super(...arguments),
        (this.roomChoices = []),
        (this.status = null),
        (this._expanded = !1),
        (this._activeWeek = "even"),
        (this.autoExpand = !1),
        (this._lastSchedule = void 0),
        (this._cachedDays = []),
        (this._lastScheduleEven = void 0),
        (this._cachedDaysEven = []),
        (this._lastScheduleOdd = void 0),
        (this._cachedDaysOdd = []);
    }
    get _days() {
      var t;
      const e = (t = this.config) == null ? void 0 : t.schedule;
      return (
        e !== this._lastSchedule &&
          ((this._lastSchedule = e), (this._cachedDays = ne(e))),
        this._cachedDays
      );
    }
    get _daysEven() {
      var t;
      const e = (t = this.config) == null ? void 0 : t.schedule_even;
      return (
        e !== this._lastScheduleEven &&
          ((this._lastScheduleEven = e), (this._cachedDaysEven = ne(e))),
        this._cachedDaysEven
      );
    }
    get _daysOdd() {
      var t;
      const e = (t = this.config) == null ? void 0 : t.schedule_odd;
      return (
        e !== this._lastScheduleOdd &&
          ((this._lastScheduleOdd = e), (this._cachedDaysOdd = ne(e))),
        this._cachedDaysOdd
      );
    }
    connectedCallback() {
      super.connectedCallback(), (this._expanded = !1);
    }
    updated(e) {
      e.has("_expanded") &&
        this._expanded &&
        (this._activeWeek = nt(/* @__PURE__ */ new Date())),
        e.has("autoExpand") &&
          this.autoExpand &&
          ((this._expanded = !0),
          setTimeout(() => {
            const t = this.getBoundingClientRect();
            this.scrollIntoView({
              behavior: "smooth",
              block: t.height <= window.innerHeight ? "nearest" : "start",
            });
          }, 0));
    }
    // -----------------------------------------------------------------------
    // Save handlers
    // -----------------------------------------------------------------------
    async _onModeChange(e) {
      var o;
      const t = e.target.value;
      if (t)
        try {
          const s =
            !!((o = this.config) != null && o.schedule) &&
            Object.values(this.config.schedule).some((i) => i.length > 0);
          t === q && !s
            ? await this.ws.setPersonConfig(this.personId, {
                mode: t,
                schedule: lt,
              })
            : await this.ws.setPersonConfig(this.personId, { mode: t }),
            await this.panel.reloadConfig(),
            this.panel.showToast("Saved", !1);
        } catch {
          this.panel.showToast("Save failed — retrying...", !0);
        }
    }
    async _onRoomToggle(e, t) {
      var i;
      const o = [...(((i = this.config) == null ? void 0 : i.room_ids) ?? [])],
        s = t ? (o.includes(e) ? o : [...o, e]) : o.filter((r) => r !== e);
      try {
        await this.ws.setPersonConfig(this.personId, { room_ids: s }),
          await this.panel.reloadConfig(),
          this.panel.showToast("Saved", !1);
      } catch {
        this.panel.showToast("Save failed — retrying...", !0);
      }
    }
    async _onScheduleTypeChange(e) {
      const t = e.target.value;
      try {
        await this.ws.setPersonConfig(this.personId, {
          schedule_type: t,
        }),
          await this.panel.reloadConfig(),
          this.panel.showToast("Saved", !1);
      } catch {
        this.panel.showToast("Save failed — retrying...", !0);
      }
    }
    async _onResetSchedule() {
      const t =
        (this.config.schedule_type ?? "single") === "even_odd"
          ? this._activeWeek === "even"
            ? "schedule_even"
            : "schedule_odd"
          : "schedule";
      try {
        await this.ws.setPersonConfig(this.personId, {
          [t]: lt,
        }),
          await this.panel.reloadConfig(),
          this.panel.showToast("Reset done", !1);
      } catch {
        this.panel.showToast("Reset failed — retrying...", !0);
      }
    }
    async _onSchedulePeriodsChanged(e) {
      const { dayIndex: t, periods: o } = e.detail,
        s = (this.config.schedule_type ?? "single") === "even_odd",
        n = {
          ...((s
            ? this._activeWeek === "even"
              ? this.config.schedule_even
              : this.config.schedule_odd
            : this.config.schedule) ?? {
            mon: [],
            tue: [],
            wed: [],
            thu: [],
            fri: [],
            sat: [],
            sun: [],
          }),
        };
      n[Ne(t)] = o;
      const l = s
        ? this._activeWeek === "even"
          ? "schedule_even"
          : "schedule_odd"
        : "schedule";
      try {
        await this.ws.setPersonConfig(this.personId, {
          [l]: n,
        }),
          await this.panel.reloadConfig(),
          this.panel.showToast("Saved", !1);
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
      return (
        ((t = (e = this.status) == null ? void 0 : e.present_persons) == null
          ? void 0
          : t.includes(this.personId)) ?? !1
      );
    }
    // -----------------------------------------------------------------------
    // Render
    // -----------------------------------------------------------------------
    _getBadgeInfo() {
      var t;
      switch (((t = this.config) == null ? void 0 : t.mode) ?? q) {
        case me:
          return { cls: "force-present", text: "Force Present" };
        case ge:
          return { cls: "force-absent", text: "Force Absent" };
        case ue:
          return { cls: "ha", text: "HA home tracking" };
        default:
          return { cls: "scheduled", text: "Scheduled" };
      }
    }
    render() {
      var p, h, f;
      const { cls: e, text: t } = this._getBadgeInfo(),
        o = ((p = this.config) == null ? void 0 : p.mode) ?? q,
        s = o === q,
        i = ((h = this.config) == null ? void 0 : h.schedule_type) ?? "single",
        r = i === "even_odd",
        n = r
          ? this._activeWeek === "even"
            ? "Reset Even week to default"
            : "Reset Odd week to default"
          : "Reset to default",
        l = ((f = this.config) == null ? void 0 : f.room_ids) ?? [],
        d = this.roomChoices.filter((g) => !l.includes(g.id));
      return c`
      <ha-card>
        <div
          class="card-header-row"
          @click=${() => {
            this._expanded = !this._expanded;
          }}
        >
          <div class="card-header-left">
            <span
              class="presence-dot ${
                this._isCurrentlyPresent() ? "present" : "absent"
              }"
              title="Currently ${
                this._isCurrentlyPresent() ? "present" : "absent"
              }"
              >●</span
            >
            <span class="person-name">${this.personName}</span>
            <span class="mode-badge ${e}">${t}</span>
          </div>
          <ha-icon
            class="expand-icon ${this._expanded ? "expanded" : ""}"
            icon="mdi:chevron-down"
          ></ha-icon>
        </div>

        ${
          this._expanded
            ? c`
              <div class="card-content">
                <!-- Presence mode selector -->
                <div
                  class="section-label"
                  title="How this person's presence is determined"
                >
                  Presence mode
                </div>
                <div class="select-wrapper">
                  <select class="mode-select" @change=${this._onModeChange}>
                    <option
                      value=${q}
                      ?selected=${o === q}
                    >
                      Scheduled
                    </option>
                    <option
                      value=${ue}
                      ?selected=${o === ue}
                    >
                      HA home tracking
                    </option>
                    <option
                      value=${me}
                      ?selected=${o === me}
                    >
                      Force Present
                    </option>
                    <option
                      value=${ge}
                      ?selected=${o === ge}
                    >
                      Force Absent
                    </option>
                  </select>
                </div>
                <p class="schedule-hint">
                  ${
                    o === me
                      ? "Always considered present, regardless of schedule."
                      : o === ge
                        ? "Always absent. Rooms are not heated for presence."
                        : o === ue
                          ? "Presence mirrors Home Assistant home/away tracking."
                          : "Presence follows a weekly schedule."
                  }
                </p>

                <!-- Room associations as chips -->
                <div
                  class="section-label"
                  title="Rooms heated by this person's presence"
                >
                  Room associations
                </div>
                <div class="chips">
                  ${l.map((g) => {
                    const v = this.roomChoices.find((m) => m.id === g);
                    return v
                      ? c`
                      <span
                        class="chip"
                        @click=${() => void this.panel.navigateToRoom(g)}
                      >
                        <ha-icon icon="mdi:home-outline"></ha-icon>
                        ${v.name}
                        <button
                          class="chip-remove"
                          @click=${(m) => {
                            m.stopPropagation(), this._onRoomToggle(g, !1);
                          }}
                        >
                          ×
                        </button>
                      </span>
                    `
                      : "";
                  })}
                  ${
                    d.length > 0
                      ? c`
                        <search-picker
                          .items=${d.map((g) => ({
                            id: g.id,
                            label: g.name,
                            secondary: g.secondary,
                            icon: "mdi:home-outline",
                          }))}
                          triggerLabel="Add room"
                          triggerIcon="mdi:plus"
                          placeholder="Search rooms…"
                          @picked=${(g) => {
                            const { id: v } = g.detail;
                            this._onRoomToggle(v, !0);
                          }}
                        ></search-picker>
                      `
                      : ""
                  }
                </div>

                <!-- Presence schedule (only in Scheduled mode) -->
                ${
                  s
                    ? c`
                      <div
                        class="section-label"
                        title="When this person is considered present"
                      >
                        Presence schedule
                      </div>
                      <div class="section-label">Schedule type</div>
                      <div class="select-wrapper">
                        <select
                          class="mode-select"
                          @change=${this._onScheduleTypeChange}
                        >
                          <option
                            value="single"
                            ?selected=${i === "single"}
                          >
                            Single week
                          </option>
                          <option
                            value="even_odd"
                            ?selected=${i === "even_odd"}
                          >
                            Even / Odd weeks
                          </option>
                        </select>
                      </div>
                      ${
                        r
                          ? c`
                            <p class="schedule-hint">
                              Week ${bt(
                                /* @__PURE__ */ new Date(),
                              )} is currently
                              active (${nt(/* @__PURE__ */ new Date())} week).
                            </p>
                            <div class="week-switcher">
                              <button
                                class="tab-btn ${
                                  this._activeWeek === "even" ? "active" : ""
                                }"
                                @click=${() => {
                                  this._activeWeek = "even";
                                }}
                              >
                                Even
                              </button>
                              <button
                                class="tab-btn ${
                                  this._activeWeek === "odd" ? "active" : ""
                                }"
                                @click=${() => {
                                  this._activeWeek = "odd";
                                }}
                              >
                                Odd
                              </button>
                            </div>
                          `
                          : ""
                      }
                      <div class="schedule-section">
                        <climate-manager-time-bar
                          mode="presence"
                          .days=${
                            r
                              ? this._activeWeek === "even"
                                ? this._daysEven
                                : this._daysOdd
                              : this._days
                          }
                          @periods-changed=${this._onSchedulePeriodsChanged}
                        ></climate-manager-time-bar>
                      </div>
                      <button
                        class="reset-btn"
                        @click=${() => void this._onResetSchedule()}
                      >
                        ${n}
                      </button>
                    `
                    : ""
                }
              </div>
            `
            : ""
        }
      </ha-card>
    `;
    }
  };
Be.styles = [
  xe,
  Ae,
  De,
  ft,
  Ie,
  k`
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

      .card-content {
        padding: 0 16px 16px;
        border-top: 1px solid var(--divider-color, #e0e0e0);
      }

      .section-label {
        margin-top: 12px;
      }

      .select-wrapper {
        margin-bottom: 4px;
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

      /* Even/Odd week switcher (D-06, D-07) */
      .week-switcher {
        display: flex;
        gap: 4px;
        margin-bottom: 8px;
      }

      .week-switcher .tab-btn {
        background: none;
        border: none;
        border-bottom: 2px solid transparent;
        padding: 8px 16px;
        cursor: pointer;
        font-size: 14px;
        font-weight: 500;
        color: var(--secondary-text-color);
        text-transform: uppercase;
        letter-spacing: 0.07em;
        font-family: inherit;
        outline: none;
      }

      .week-switcher .tab-btn.active {
        border-bottom-color: var(--primary-color);
        color: var(--primary-color);
      }
    `,
];
let T = Be;
D([u({ type: String })], T.prototype, "personId");
D([u({ type: String })], T.prototype, "personName");
D([u({ attribute: !1 })], T.prototype, "config");
D([u({ attribute: !1 })], T.prototype, "roomChoices");
D([u({ attribute: !1 })], T.prototype, "ws");
D([u({ attribute: !1 })], T.prototype, "panel");
D([u({ attribute: !1 })], T.prototype, "status");
D([y()], T.prototype, "_expanded");
D([y()], T.prototype, "_activeWeek");
D([u({ type: Boolean })], T.prototype, "autoExpand");
customElements.define("climate-manager-person-card", T);
var ts = Object.defineProperty,
  te = (a, e, t, o) => {
    for (var s = void 0, i = a.length - 1, r; i >= 0; i--)
      (r = a[i]) && (s = r(e, t, s) || s);
    return s && ts(e, t, s), s;
  };
const We = class We extends C {
  constructor() {
    super(...arguments), (this.status = null), (this.expandPersonId = null);
  }
  /** Room choices: only TRV rooms (excludes boiler-only rooms). */
  _getRoomChoices() {
    var o;
    const e = (
      ((o = this.status) == null ? void 0 : o.rooms_status) ?? []
    ).filter((s) => s.has_trv !== !1);
    return [.../* @__PURE__ */ new Set([...e.map((s) => s.area_id)])].map(
      (s) => {
        var l, d, p, h, f, g, v;
        const i =
            ((l = e.find((m) => m.area_id === s)) == null ? void 0 : l.name) ??
            s.replace(/_/g, " ").replace(/\b\w/g, (m) => m.toUpperCase()),
          r =
            ((h =
              (p = (d = this.hass) == null ? void 0 : d.areas) == null
                ? void 0
                : p[s]) == null
              ? void 0
              : h.floor_id) ?? null,
          n = r
            ? ((v =
                (g = (f = this.hass) == null ? void 0 : f.floors) == null
                  ? void 0
                  : g[r]) == null
                ? void 0
                : v.name) ?? void 0
            : void 0;
        return { id: s, name: i, secondary: n };
      },
    );
  }
  /** Determine if a person config has any non-default setting (D-15). */
  _isNonDefault(e) {
    var r, n, l;
    const t =
      (n = (r = this.config) == null ? void 0 : r.persons) == null
        ? void 0
        : n[e];
    if (!t) return !1;
    const o = t.mode != null && t.mode !== "scheduled",
      s = (((l = t.room_ids) == null ? void 0 : l.length) ?? 0) > 0,
      i = t.schedule ? Object.values(t.schedule).some((d) => d.length > 0) : !1;
    return o || s || i;
  }
  render() {
    var r, n;
    const e = ((r = this.config) == null ? void 0 : r.persons) ?? {},
      t = Object.keys(
        ((n = this.hass) == null ? void 0 : n.states) ?? {},
      ).filter((l) => l.startsWith("person.")),
      o = [.../* @__PURE__ */ new Set([...t, ...Object.keys(e)])];
    if (o.length === 0)
      return c`
        <div class="empty-state">
          No persons found. Add person entities in Home Assistant.
        </div>
      `;
    const s = [...o].sort((l, d) => {
        const p = this._isNonDefault(l),
          h = this._isNonDefault(d);
        return p && !h ? -1 : !p && h ? 1 : l.localeCompare(d);
      }),
      i = this._getRoomChoices();
    return c`
      ${s.map((l) => {
        const d = e[l] ?? {},
          p = l
            .replace(/^person\./, "")
            .replace(/_/g, " ")
            .replace(/\b\w/g, (h) => h.toUpperCase());
        return c`
          <climate-manager-person-card
            .personId=${l}
            .personName=${p}
            .config=${d}
            .roomChoices=${i}
            .ws=${this.ws}
            .panel=${this.panel}
            .status=${this.status}
            .autoExpand=${this.expandPersonId === l}
          ></climate-manager-person-card>
        `;
      })}
    `;
  }
};
We.styles = k`
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
let N = We;
te([u({ attribute: !1 })], N.prototype, "config");
te([u({ attribute: !1 })], N.prototype, "status");
te([u({ attribute: !1 })], N.prototype, "ws");
te([u({ attribute: !1 })], N.prototype, "panel");
te([u({ attribute: !1 })], N.prototype, "hass");
te([u({ attribute: !1 })], N.prototype, "expandPersonId");
customElements.define("climate-manager-persons-tab", N);
var ss = Object.defineProperty,
  U = (a, e, t, o) => {
    for (var s = void 0, i = a.length - 1, r; i >= 0; i--)
      (r = a[i]) && (s = r(e, t, s) || s);
    return s && ss(e, t, s), s;
  };
const Xe = class Xe extends C {
  constructor() {
    super(...arguments),
      (this.isDefault = !1),
      (this.status = null),
      (this._confirmingDelete = !1),
      (this._lastProgram = void 0),
      (this._cachedDays = []),
      (this._onModeChange = async (e) => {
        const t = e.target.value;
        if (!(!t || t === this.zoneConfig.mode))
          try {
            this.isDefault
              ? await this.ws.setGlobalMode(t)
              : await this.ws.setZoneMode(this.zoneId, t),
              await this.panel.reloadConfig(),
              this.panel.showToast("Saved", !1);
          } catch {
            this.panel.showToast("Save failed", !0);
          }
      }),
      (this._onResetToDefault = async () => {
        try {
          this.isDefault
            ? await this.ws.resetTimeProgram()
            : await this.ws.resetZoneTimeProgram(this.zoneId, "default"),
            await this.panel.reloadConfig(),
            this.panel.showToast("Reset to default", !1);
        } catch {
          this.panel.showToast("Reset failed", !0);
        }
      }),
      (this._onResetToGlobal = async () => {
        try {
          await this.ws.resetZoneTimeProgram(this.zoneId, "global"),
            await this.panel.reloadConfig(),
            this.panel.showToast(
              `Reset to ${this.config.default_zone_name}`,
              !1,
            );
        } catch {
          this.panel.showToast("Reset failed", !0);
        }
      }),
      (this._onPeriodsChanged = async (e) => {
        const { dayIndex: t, periods: o } = e.detail,
          s = { ...this.zoneConfig.time_program },
          i = Ne(t);
        s[i] = o;
        try {
          this.isDefault
            ? await this.ws.setTimeProgram(s)
            : await this.ws.setZoneTimeProgram(this.zoneId, s),
            await this.panel.reloadConfig(),
            this.panel.showToast("Saved", !1);
        } catch {
          this.panel.showToast("Save failed — retrying...", !0);
        }
        e.stopPropagation();
      });
  }
  get _days() {
    var t;
    const e = (t = this.zoneConfig) == null ? void 0 : t.time_program;
    return (
      e !== this._lastProgram &&
        ((this._lastProgram = e), (this._cachedDays = ne(e))),
      this._cachedDays
    );
  }
  /**
   * Add a room to this zone (D-09).
   * isDefault: zone_id: null — backend pops zone_id (D-06 sparse model).
   */
  async _onAddRoom(e) {
    try {
      this.isDefault
        ? await this.ws.setRoomConfig(e, {
            zone_id: null,
          })
        : await this.ws.setRoomConfig(e, { zone_id: this.zoneId }),
        await this.panel.reloadConfig(),
        this.panel.showToast("Saved", !1);
    } catch {
      this.panel.showToast("Save failed — retrying...", !0);
    }
  }
  /**
   * Remove a room from a custom zone (D-08).
   * Sends zone_id: null — backend pops zone_id (D-06 sparse model).
   * Absent zone_id = Default Zone member. Not rendered for Default Zone.
   */
  async _onRemoveRoom(e) {
    const t = {
      zone_id: null,
    };
    try {
      await this.ws.setRoomConfig(e, t),
        await this.panel.reloadConfig(),
        this.panel.showToast("Saved", !1);
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
   * On success, main.ts detects missing tab via _validateActiveTab()
   * and falls back to "global". This component does not navigate.
   */
  async _onConfirmDelete() {
    try {
      await this.ws.deleteZone(this.zoneId),
        await this.panel.reloadConfig(),
        this.panel.showToast("Zone deleted", !1);
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
    var t, o, s, i;
    return (
      ((s =
        (o = (t = this.status) == null ? void 0 : t.rooms_status) == null
          ? void 0
          : o.find((r) => r.area_id === e)) == null
        ? void 0
        : s.name) ??
      ((i = this.hass.areas[e]) == null ? void 0 : i.name) ??
      e
    );
  }
  /** All TRV room IDs from status; falls back to config.rooms keys. */
  _allRoomIds() {
    var t, o, s;
    const e =
      (o = (t = this.status) == null ? void 0 : t.rooms_status) == null
        ? void 0
        : o.filter((i) => i.has_trv !== !1);
    return e != null && e.length
      ? e.map((i) => i.area_id)
      : Object.keys(((s = this.config) == null ? void 0 : s.rooms) ?? {});
  }
  /**
   * Returns IDs of rooms assigned to this zone.
   * For custom zones: rooms whose zone_id === this.zoneId.
   * Default Zone: rooms with undefined or orphaned zone_id (D-06 phase 4).
   * Universe is all TRV rooms so unconfigured rooms appear.
   */
  _getAssignedRoomIds() {
    var t;
    const e = Object.keys(((t = this.config) == null ? void 0 : t.zones) ?? {});
    return this._allRoomIds().filter((o) => {
      var i, r;
      const s =
        (r = (i = this.config) == null ? void 0 : i.rooms) == null
          ? void 0
          : r[o];
      return this.isDefault || this.zoneId === "default"
        ? !(s != null && s.zone_id) || !e.includes(s.zone_id)
        : (s == null ? void 0 : s.zone_id) === this.zoneId;
    });
  }
  /** Rooms grouped by floor (alpha-sorted), floors descending by level. */
  _getSortedAssignedRoomGroups() {
    var r, n, l;
    const e = this._getAssignedRoomIds(),
      t = /* @__PURE__ */ new Map();
    for (const d of e) {
      const p =
        ((l =
          (n = (r = this.hass) == null ? void 0 : r.areas) == null
            ? void 0
            : n[d]) == null
          ? void 0
          : l.floor_id) ?? null;
      t.has(p) || t.set(p, []), t.get(p).push(d);
    }
    for (const d of t.values())
      d.sort((p, h) =>
        this._getRoomName(p).localeCompare(this._getRoomName(h)),
      );
    const s = [...t.keys()]
        .filter((d) => d !== null)
        .sort((d, p) => {
          var h, f, g, v, m, b;
          return (
            (((g =
              (f = (h = this.hass) == null ? void 0 : h.floors) == null
                ? void 0
                : f[p]) == null
              ? void 0
              : g.level) ?? 0) -
            (((b =
              (m = (v = this.hass) == null ? void 0 : v.floors) == null
                ? void 0
                : m[d]) == null
              ? void 0
              : b.level) ?? 0)
          );
        })
        .map((d) => {
          var p, h, f;
          return {
            floorId: d,
            floorName:
              ((f =
                (h = (p = this.hass) == null ? void 0 : p.floors) == null
                  ? void 0
                  : h[d]) == null
                ? void 0
                : f.name) ?? d,
            roomIds: t.get(d),
          };
        }),
      i = t.get(null) ?? [];
    return i.length && s.push({ floorId: null, floorName: "", roomIds: i }), s;
  }
  /**
   * Returns rooms NOT assigned to this zone, shaped for the search-picker.
   * Per D-10: includes rooms in other zones (valid reassignment targets).
   */
  _getUnassignedRoomItems() {
    const e = new Set(this._getAssignedRoomIds());
    return this._allRoomIds()
      .filter((t) => !e.has(t))
      .map((t) => ({
        id: t,
        label: this._getRoomName(t),
        icon: "mdi:home-outline",
      }));
  }
  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------
  _renderModeDescription() {
    var t;
    const e = (t = this.zoneConfig) == null ? void 0 : t.mode;
    return e === "off"
      ? c`<p class="schedule-hint">
        Zone is off. All assigned rooms are kept at frost protection temperature
        only.
      </p>`
      : e === "time_program_presences"
        ? c`
        <p class="schedule-hint">
          Rooms heat according to the schedule when an assigned person is
          present. While present, the room stays heated from the first
          Normal/Comfort period to the last — Reduced or Frost gaps in between
          are held at the preceding Normal/Comfort temperature. When everyone is
          absent, the room stays at Reduced temperature regardless of the
          schedule.
        </p>
        <p class="schedule-hint">
          <em>Example:</em> schedule Normal 06:00, Reduced 09:00, Normal 17:00,
          Frost 22:00 — if present, the room heats 06:00–22:00 and holds Normal
          temperature during the 09:00–17:00 gap. If absent, the room stays at
          Reduced all day.
        </p>
      `
        : c`<p class="schedule-hint">
      Rooms follow the weekly schedule. Each period sets the target temperature
      for all assigned rooms.
    </p>`;
  }
  _getFloorIcon(e) {
    var s, i;
    const t =
      (i = (s = this.hass) == null ? void 0 : s.floors) == null ? void 0 : i[e];
    if (t != null && t.icon) return t.icon;
    const o = (t == null ? void 0 : t.level) ?? 0;
    return o === -1
      ? "mdi:home-floor-negative-1"
      : o < 0
        ? "mdi:home-floor-b"
        : o === 1
          ? "mdi:home-floor-1"
          : o === 2
            ? "mdi:home-floor-2"
            : o === 3 || o > 3
              ? "mdi:home-floor-3"
              : "mdi:home-floor-0";
  }
  render() {
    const e = this._getSortedAssignedRoomGroups(),
      t = this._getUnassignedRoomItems(),
      o = (s) => c`
      <span class="chip" @click=${() => void this.panel.navigateToRoom(s)}>
        <ha-icon icon="mdi:home-outline"></ha-icon>
        ${this._getRoomName(s)}
        ${
          this.isDefault
            ? ""
            : c`<button
              class="chip-remove"
              @click=${(i) => {
                i.stopPropagation(), this._onRemoveRoom(s);
              }}
            >
              ×
            </button>`
        }
      </span>
    `;
    return c`
      <!-- 1. Mode picker -->
      <div
        class="section-label"
        title="Controls how rooms in this zone are heated"
      >
        Mode
      </div>
      <div class="select-wrapper">
        <select class="mode-select" @change=${this._onModeChange}>
          <option value="off" ?selected=${this.zoneConfig.mode === "off"}>
            Off
          </option>
          <option
            value="time_program"
            ?selected=${this.zoneConfig.mode === "time_program"}
          >
            Time program
          </option>
          <option
            value="time_program_presences"
            ?selected=${this.zoneConfig.mode === "time_program_presences"}
          >
            Time program &amp; presences
          </option>
        </select>
      </div>
      ${this._renderModeDescription()}

      <!-- 4. Time-bar -->
      <climate-manager-time-bar
        mode="schedule"
        .days=${this._days}
        @periods-changed=${this._onPeriodsChanged}
      ></climate-manager-time-bar>

      <!-- Reset row: Default Zone gets one button; custom zones get two -->
      <div class="reset-row">
        ${
          this.isDefault
            ? ""
            : c`<button class="reset-btn" @click=${this._onResetToGlobal}>
              Reset to ${this.config.default_zone_name}
            </button>`
        }
        <button class="reset-btn" @click=${this._onResetToDefault}>
          Reset to default
        </button>
      </div>

      <!-- 5. Assigned Rooms section (D-08 / D-09 / D-10) -->
      <div class="section-divider"></div>
      <div class="section-label" title="Rooms that follow this zone's schedule">
        Assigned rooms
      </div>
      ${e.map(
        (s) => c`
          ${
            s.floorId !== null
              ? c`<div class="floor-group-label">
                <ha-icon icon=${this._getFloorIcon(s.floorId)}></ha-icon
                >${s.floorName}
              </div>`
              : ""
          }
          <div class="chips">${s.roomIds.map(o)}</div>
        `,
      )}
      ${
        t.length > 0
          ? c`
            <div class="chips">
              <search-picker
                .items=${t}
                triggerLabel="Add room"
                triggerIcon="mdi:plus"
                placeholder="Search rooms…"
                @picked=${this._onRoomPicked}
              ></search-picker>
            </div>
          `
          : ""
      }

      <!-- Delete row (custom zones only, D-05) -->
      ${
        this.isDefault
          ? ""
          : c`
            <div class="delete-row">
              ${
                this._confirmingDelete
                  ? c`
                    <span>Delete zone?</span>
                    <button class="cancel-btn" @click=${this._onCancelDelete}>
                      Cancel
                    </button>
                    <button
                      class="danger-btn"
                      @click=${() => void this._onConfirmDelete()}
                    >
                      Confirm
                    </button>
                  `
                  : c`
                    <button class="delete-btn" @click=${this._onDeleteClick}>
                      Delete zone
                    </button>
                  `
              }
            </div>
          `
      }
    `;
  }
};
Xe.styles = [
  xe,
  Ae,
  De,
  Ie,
  k`
      :host {
        display: block;
      }

      /* Delete row (top of zone tab, custom zones only) */
      .delete-row {
        display: flex;
        flex-direction: row;
        align-items: center;
        gap: 8px;
        justify-content: flex-end;
        margin-top: 24px;
      }

      .delete-btn {
        background: none;
        border: 1px solid var(--divider-color, rgba(0, 0, 0, 0.12));
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
        border: 1px solid var(--divider-color, rgba(0, 0, 0, 0.12));
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

      .select-wrapper {
        margin-bottom: 16px;
      }

      .section-divider {
        margin: 16px 0 8px;
      }

      .floor-group-label {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 11px;
        font-weight: 600;
        letter-spacing: 0.5px;
        text-transform: uppercase;
        color: var(--secondary-text-color);
        margin: 8px 0 4px;
      }

      .floor-group-label ha-icon {
        --mdc-icon-size: 14px;
        width: 14px;
        height: 14px;
        flex-shrink: 0;
      }

      .reset-row {
        display: flex;
        gap: 8px;
        margin-top: 8px;
        margin-bottom: 8px;
        justify-content: flex-end;
      }

      .reset-btn {
        background: none;
        border: 1px solid var(--divider-color, rgba(0, 0, 0, 0.12));
        color: var(--secondary-text-color);
        padding: 5px 12px;
        border-radius: 4px;
        cursor: pointer;
        font-size: 13px;
        font-family: inherit;
      }

      .reset-btn:hover {
        background: var(--secondary-background-color);
      }
    `,
];
let M = Xe;
U([u({ attribute: !1 })], M.prototype, "config");
U([u({ attribute: !1 })], M.prototype, "zoneId");
U([u({ attribute: !1 })], M.prototype, "zoneConfig");
U([u({ type: Boolean })], M.prototype, "isDefault");
U([u({ attribute: !1 })], M.prototype, "ws");
U([u({ attribute: !1 })], M.prototype, "panel");
U([u({ attribute: !1 })], M.prototype, "hass");
U([u({ attribute: !1 })], M.prototype, "status");
U([y()], M.prototype, "_confirmingDelete");
customElements.define("climate-manager-zone-tab", M);
var os = Object.defineProperty,
  P = (a, e, t, o) => {
    for (var s = void 0, i = a.length - 1, r; i >= 0; i--)
      (r = a[i]) && (s = r(e, t, s) || s);
    return s && os(e, t, s), s;
  };
const Ve = class Ve extends C {
  constructor() {
    super(...arguments),
      (this.narrow = !1),
      (this.panel = null),
      (this._config = null),
      (this._status = null),
      (this._activeTab =
        localStorage.getItem("climate-manager-tab") ?? "global"),
      (this._unsubStatus = null),
      (this._wsError = !1),
      (this._editingTabId = null),
      (this._tabNameInput = ""),
      (this._expandRoomId = null),
      (this._expandPersonId = null),
      (this._ws = null);
  }
  connectedCallback() {
    super.connectedCallback(),
      (this._ws = new he(this.hass)),
      this._loadConfig(),
      this._loadStatus(),
      this._subscribeStatus();
  }
  disconnectedCallback() {
    super.disconnectedCallback(),
      this._unsubStatus &&
        (this._unsubStatus.then((e) => e()).catch(() => {}),
        (this._unsubStatus = null));
  }
  _validateActiveTab() {
    if (
      this._config &&
      !(
        this._activeTab === "global" ||
        this._activeTab === "rooms" ||
        this._activeTab === "persons" ||
        this._activeTab === "zone_default"
      )
    ) {
      if (this._activeTab.startsWith("zone_")) {
        const e = this._activeTab.slice(5);
        this._config.zones[e] ||
          ((this._activeTab = "global"),
          localStorage.setItem("climate-manager-tab", "global"));
        return;
      }
      (this._activeTab = "global"),
        localStorage.setItem("climate-manager-tab", "global");
    }
  }
  async _loadConfig() {
    this._ws || (this._ws = new he(this.hass));
    try {
      (this._config = await this._ws.getConfig()), this._validateActiveTab();
    } catch {
      this._wsError = !0;
    }
  }
  async _loadStatus() {
    this._ws || (this._ws = new he(this.hass));
    try {
      this._status = await this._ws.getStatus();
    } catch {}
  }
  _subscribeStatus() {
    this._ws || (this._ws = new he(this.hass)),
      (this._unsubStatus = this._ws
        .subscribeStatus((e) => {
          (this._status = e), (this._wsError = !1);
        })
        .catch(() => ((this._wsError = !0), () => {})));
  }
  /** Show a toast notification. Called by tab components after a save. */
  showToast(e, t) {
    var o;
    (o = this._toast) == null || o.show(e, t);
  }
  /** Navigate to a zone tab. Pass undefined/null for the Default Zone. */
  navigateToZone(e) {
    this._setTab(e ? "zone_" + e : "zone_default");
  }
  /** Navigate to the Rooms tab and auto-expand the given room card. */
  async navigateToRoom(e) {
    this._setTab("rooms"),
      (this._expandRoomId = e),
      await this.updateComplete,
      (this._expandRoomId = null);
  }
  /** Navigate to the Persons tab and auto-expand the given person card. */
  async navigateToPerson(e) {
    this._setTab("persons"),
      (this._expandPersonId = e),
      await this.updateComplete,
      (this._expandPersonId = null);
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
      const i = await this._ws.createZone(e);
      await this._loadConfig(),
        this._setTab("zone_" + i.zone_id),
        await this.updateComplete;
      const r =
        (t = this.shadowRoot) == null
          ? void 0
          : t.querySelector("climate-manager-zone-tab");
      (s =
        (o = r == null ? void 0 : r.shadowRoot) == null
          ? void 0
          : o.querySelector(".zone-name")) == null || s.click(),
        this.showToast("Zone created", !1);
    } catch {
      this.showToast("Create zone failed", !0);
    }
  }
  async _onTabRename(e, t, o) {
    var s, i;
    o.stopPropagation(),
      (this._editingTabId = e),
      (this._tabNameInput = t),
      await this.updateComplete,
      (i =
        (s = this.shadowRoot) == null
          ? void 0
          : s.querySelector(`input[data-zone="${e}"]`)) == null || i.select();
  }
  _onTabNameInput(e) {
    this._tabNameInput = e.target.value;
  }
  async _onTabNameBlur(e) {
    if (this._editingTabId !== e) return;
    this._editingTabId = null;
    const t = this._tabNameInput.trim();
    if (!(!t || !this._ws))
      try {
        await this._ws.renameZone(e, t),
          await this._loadConfig(),
          this.showToast("Renamed", !1);
      } catch {
        this.showToast("Rename failed", !0);
      }
  }
  _onTabNameKeydown(e, t) {
    t.key === "Enter"
      ? t.target.blur()
      : t.key === "Escape" && (this._editingTabId = null);
  }
  _setTab(e) {
    (this._activeTab = e), localStorage.setItem("climate-manager-tab", e);
  }
  render() {
    return this._config
      ? c`
      <div class="panel-header">Climate Manager</div>

      ${
        this._wsError
          ? c`<div class="error-banner">Connection lost. Reconnecting…</div>`
          : ""
      }

      <div class="tab-bar">
        <button
          class="tab-btn ${this._activeTab === "global" ? "active" : ""}"
          @click=${() => this._setTab("global")}
        >
          Overview
        </button>
        <button
          class="tab-btn ${this._activeTab === "rooms" ? "active" : ""}"
          @click=${() => this._setTab("rooms")}
        >
          Rooms
        </button>
        <button
          class="tab-btn ${this._activeTab === "persons" ? "active" : ""}"
          @click=${() => this._setTab("persons")}
        >
          Persons
        </button>
        <button
          class="tab-btn ${this._activeTab === "zone_default" ? "active" : ""}"
          @click=${() => this._setTab("zone_default")}
          @dblclick=${(e) =>
            this._onTabRename("default", this._config.default_zone_name, e)}
        >
          ${
            this._editingTabId === "default"
              ? c`<input
                data-zone="default"
                class="tab-name-input"
                .value=${this._tabNameInput}
                @input=${this._onTabNameInput}
                @blur=${() => this._onTabNameBlur("default")}
                @keydown=${(e) => this._onTabNameKeydown("default", e)}
                @click=${(e) => e.stopPropagation()}
              />`
              : c`<span
                  class="zone-dot"
                  style="background:${ve(void 0).color}"
                ></span
                >${this._config.default_zone_name}`
          }
        </button>
        ${Object.entries(this._config.zones).map(
          ([e, t]) => c`
            <button
              class="tab-btn ${this._activeTab === "zone_" + e ? "active" : ""}"
              @click=${() => this._setTab("zone_" + e)}
              @dblclick=${(o) => this._onTabRename(e, t.name, o)}
            >
              ${
                this._editingTabId === e
                  ? c`<input
                    data-zone="${e}"
                    class="tab-name-input"
                    .value=${this._tabNameInput}
                    @input=${this._onTabNameInput}
                    @blur=${() => this._onTabNameBlur(e)}
                    @keydown=${(o) => this._onTabNameKeydown(e, o)}
                    @click=${(o) => o.stopPropagation()}
                  />`
                  : c`<span
                      class="zone-dot"
                      style="background:${ve(e).color}"
                    ></span
                    >${t.name}`
              }
            </button>
          `,
        )}
        <button
          class="tab-btn add-zone-btn"
          title="Add zone"
          @click=${() => void this._onCreateZone()}
        >
          +
        </button>
      </div>

      <div class="tab-content">${this._renderTabContent()}</div>

      <climate-manager-toast></climate-manager-toast>
    `
      : c`
        <div class="panel-header">Climate Manager</div>
        ${
          this._wsError
            ? c`<div class="error-banner">Connection lost. Reconnecting…</div>`
            : ""
        }
        <div class="loading">
          <ha-circular-progress active></ha-circular-progress>
        </div>
        <climate-manager-toast></climate-manager-toast>
      `;
  }
  _renderTabContent() {
    if (this._activeTab === "zone_default")
      return c`<climate-manager-zone-tab
        .config=${this._config}
        .zoneId=${"default"}
        .zoneConfig=${{
          name: this._config.default_zone_name,
          mode: this._config.global_mode,
          time_program: this._config.global_time_program,
        }}
        .isDefault=${!0}
        .status=${this._status}
        .ws=${this._ws}
        .panel=${this}
        .hass=${this.hass}
      ></climate-manager-zone-tab>`;
    if (this._activeTab.startsWith("zone_")) {
      const e = this._activeTab.slice(5),
        t = this._config.zones[e];
      return t
        ? c`<climate-manager-zone-tab
        .config=${this._config}
        .zoneId=${e}
        .zoneConfig=${t}
        .isDefault=${!1}
        .status=${this._status}
        .ws=${this._ws}
        .panel=${this}
        .hass=${this.hass}
      ></climate-manager-zone-tab>`
        : c``;
    }
    switch (this._activeTab) {
      case "global":
        return c`<climate-manager-global-settings-tab
          .config=${this._config}
          .status=${this._status}
          .ws=${this._ws}
          .panel=${this}
          .hass=${this.hass}
        ></climate-manager-global-settings-tab>`;
      case "rooms":
        return c`<climate-manager-rooms-tab
          .config=${this._config}
          .status=${this._status}
          .ws=${this._ws}
          .panel=${this}
          .hass=${this.hass}
          .expandRoomId=${this._expandRoomId}
        ></climate-manager-rooms-tab>`;
      case "persons":
        return c`<climate-manager-persons-tab
          .config=${this._config}
          .status=${this._status}
          .ws=${this._ws}
          .panel=${this}
          .hass=${this.hass}
          .expandPersonId=${this._expandPersonId}
        ></climate-manager-persons-tab>`;
      default:
        return c``;
    }
  }
};
Ve.styles = k`
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
      background: var(
        --app-header-background-color,
        var(--primary-background-color)
      );
      border-bottom: 1px solid var(--divider-color, rgba(0, 0, 0, 0.12));
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
      border-bottom: 1px solid var(--divider-color, rgba(0, 0, 0, 0.12));
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

    .zone-dot {
      display: inline-block;
      width: 8px;
      height: 8px;
      border-radius: 50%;
      vertical-align: middle;
      margin-right: 6px;
      flex-shrink: 0;
    }

    .tab-name-input {
      font-size: 14px;
      font-weight: 500;
      text-transform: uppercase;
      letter-spacing: 0.07em;
      border: none;
      border-bottom: 2px solid var(--primary-color);
      outline: none;
      background: transparent;
      color: var(--primary-color);
      padding: 0;
      width: 10ch;
      max-width: 20ch;
    }
  `;
let w = Ve;
P([u({ attribute: !1 })], w.prototype, "hass");
P([u({ type: Boolean })], w.prototype, "narrow");
P([u({ attribute: !1 })], w.prototype, "panel");
P([y()], w.prototype, "_config");
P([y()], w.prototype, "_status");
P([y()], w.prototype, "_activeTab");
P([y()], w.prototype, "_unsubStatus");
P([y()], w.prototype, "_wsError");
P([y()], w.prototype, "_editingTabId");
P([y()], w.prototype, "_tabNameInput");
P([y()], w.prototype, "_expandRoomId");
P([y()], w.prototype, "_expandPersonId");
P([Ut("climate-manager-toast")], w.prototype, "_toast");
customElements.define("climate-manager-panel", w);
export { w as ClimateManagerPanel };
