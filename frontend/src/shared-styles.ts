// SPDX-License-Identifier: MIT
/**
 * Shared Lit CSS fragments reused across card components.
 * Import exports and compose via `static styles = [sharedStyle, css`...`]`.
 */

import { css } from "lit";

/** Chip association UI — used by room-card, person-card, zone-tab. */
export const chipStyles = css`
  .chips {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-bottom: 16px;
  }
`;

/** Uppercase section label — used by room-card, person-card, zone-tab. */
export const sectionLabelStyles = css`
  .section-label {
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.5px;
    text-transform: uppercase;
    color: var(--secondary-text-color);
    margin-bottom: 8px;
  }
`;

/** Full-width select ha-selector (mode pickers). */
export const selectStyles = css`
  .mode-select {
    display: block;
    width: 100%;
  }
`;

/** Scheduling behavior hint — rendered below time-bar components. */
export const scheduleHintStyles = css`
  .schedule-hint {
    font-size: 12px;
    color: var(--secondary-text-color);
    margin: 6px 0 12px;
    line-height: 1.5;
  }
`;

/** Animated chevron for collapsible card headers (room-card, person-card). */
export const expandIconStyles = css`
  .expand-icon {
    color: var(--secondary-text-color);
    transition: transform 0.2s;
  }

  .expand-icon.expanded {
    transform: rotate(180deg);
  }
`;

/** Floor group label row — used by zone-tab and person-card. */
export const floorGroupLabelStyles = css`
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
`;

/** Drag-and-drop grouping canvas — used by room-card Matter pairing. */
export const groupDndStyles = css`
  /* Flex row: tree on left + unassign zone on right during drag */
  .climate-pair {
    display: flex;
    gap: 12px;
    align-items: flex-start;
  }

  .climate-tree {
    display: flex;
    flex-direction: column;
    gap: 6px;
    align-items: flex-start;
  }

  .climate-pair .climate-tree {
    flex: 1;
    min-width: 0;
  }

  /* Pairing group — parent chip + indented Matter children */
  .pair-group {
    margin-bottom: 8px;
  }

  .pair-group.drag-over {
    outline: 2px dashed var(--primary-color, #03a9f4);
    outline-offset: 4px;
    border-radius: 8px;
  }

  /* Tree branch — Matter chips indented under their parent */
  .matter-children {
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 6px 10px;
    margin-top: 4px;
    margin-left: 12px;
    border-left: 2px solid var(--primary-color, #03a9f4);
    align-items: flex-start;
  }

  /* Draggable chip modifier */
  .chip-draggable {
    cursor: grab;
    user-select: none;
    -webkit-user-select: none;
  }

  .chip-draggable:active {
    cursor: grabbing;
  }

  /* Temperature span inside a chip */
  .chip-temp {
    color: var(--secondary-text-color);
    font-size: 12px;
    white-space: nowrap;
  }

  /* Drop highlight on an ungrouped pairable chip */
  ha-assist-chip.drag-over {
    outline: 2px dashed var(--primary-color, #03a9f4);
    outline-offset: 2px;
    border-radius: 8px;
  }

  /* Unassign zone — appears to the right during any drag */
  .unassign-drop-zone {
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    width: 64px;
    min-height: 56px;
    border: 2px dashed var(--divider-color, #e0e0e0);
    border-radius: 8px;
    color: var(--secondary-text-color);
    font-size: 11px;
    text-align: center;
    padding: 6px 4px;
    gap: 4px;
  }

  .unassign-drop-zone ha-icon {
    --mdc-icon-size: 18px;
    width: 18px;
    height: 18px;
  }

  .unassign-drop-zone.drag-over {
    border-color: var(--error-color, #f44336);
    color: var(--error-color, #f44336);
  }
`;
