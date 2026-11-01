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
