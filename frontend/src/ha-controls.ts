// SPDX-License-Identifier: MIT
/**
 * Climate Manager Panel — HA form controls, rendered through ha-selector.
 *
 * ha-selector is the schema-driven entry point HA itself uses for card
 * editors, blueprints and automations; it follows the user profile
 * (language, number and time formats) and the HA theme. The elements it
 * renders are loaded at startup by ha-elements.ts.
 */

import { html } from "lit";

import type { Hass } from "./types.js";

export interface SelectOption {
  value: string;
  label: string;
}

interface ControlOptions {
  label?: string;
  /** Extra class on the ha-selector (layout). */
  cls?: string;
  disabled?: boolean;
}

/** The value of an ha-selector value-changed event. */
function changedValue(e: Event): unknown {
  return (e as CustomEvent<{ value?: unknown }>).detail?.value;
}

/**
 * A dropdown of `options`; `onChange` gets the picked value when it
 * differs from `value`.
 */
export function haSelect(
  hass: Hass,
  value: string,
  options: SelectOption[],
  onChange: (value: string) => void,
  { label, cls, disabled = false }: ControlOptions = {},
) {
  return html`<ha-selector
    class=${cls ?? ""}
    .hass=${hass}
    .selector=${{ select: { mode: "dropdown", options } }}
    .value=${value}
    .label=${label}
    .disabled=${disabled}
    .required=${true}
    @value-changed=${(e: Event) => {
      const picked = changedValue(e);
      if (typeof picked === "string" && picked !== value) onChange(picked);
    }}
  ></ha-selector>`;
}

/**
 * An entity picker; `filter` is the entity selector config (domain,
 * device_class, include_entities…). Clearing it gives "" to `onChange`.
 */
export function haEntity(
  hass: Hass,
  value: string,
  filter: Record<string, unknown>,
  onChange: (value: string) => void,
  {
    label,
    cls,
    disabled = false,
    placeholder,
  }: ControlOptions & { placeholder?: string } = {},
) {
  return html`<ha-selector
    class=${cls ?? ""}
    .hass=${hass}
    .selector=${{ entity: filter }}
    .value=${value || undefined}
    .label=${label}
    .placeholder=${placeholder}
    .disabled=${disabled}
    .required=${false}
    @value-changed=${(e: Event) => {
      const picked = changedValue(e);
      const next = typeof picked === "string" ? picked : "";
      if (next !== value) onChange(next);
    }}
  ></ha-selector>`;
}

interface NumberConfig {
  min?: number;
  max?: number;
  step?: number;
  unit?: string;
}

/** Values typed in a number selector, not committed yet. */
const pendingNumbers = new WeakMap<EventTarget, number | undefined>();

/**
 * A number box (with its unit). The number selector reports every
 * keystroke, so the value is committed like a native change event: when
 * the focus leaves the box or on Enter, and only when it is a number in
 * [min, max] that differs from `value`.
 */
export function haNumber(
  hass: Hass,
  value: number | undefined,
  { min, max, step, unit }: NumberConfig,
  onCommit: (value: number) => void,
  { label, cls, disabled = false }: ControlOptions = {},
) {
  const commit = (el: EventTarget) => {
    if (!pendingNumbers.has(el)) return;
    const next = pendingNumbers.get(el);
    pendingNumbers.delete(el);
    if (next === undefined || Number.isNaN(next) || next === value) return;
    if ((min !== undefined && next < min) || (max !== undefined && next > max))
      return;
    onCommit(next);
  };
  return html`<ha-selector
    class=${cls ?? ""}
    .hass=${hass}
    .selector=${{
      number: { mode: "box", min, max, step, unit_of_measurement: unit },
    }}
    .value=${value}
    .label=${label}
    .disabled=${disabled}
    .required=${true}
    @value-changed=${(e: Event) => {
      const next = changedValue(e);
      pendingNumbers.set(
        e.currentTarget as EventTarget,
        typeof next === "number" ? next : undefined,
      );
    }}
    @focusout=${(e: FocusEvent) => {
      const el = e.currentTarget as HTMLElement;
      // Focus may move inside the selector's own shadow trees.
      setTimeout(() => {
        if (!el.matches(":focus-within")) commit(el);
      });
    }}
    @keydown=${(e: KeyboardEvent) => {
      if (e.key === "Enter") commit(e.currentTarget as EventTarget);
    }}
  ></ha-selector>`;
}
