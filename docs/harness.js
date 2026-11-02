// SPDX-License-Identifier: MIT
/**
 * Shared mount of the panel for the docs screenshot harnesses.
 *
 * - ?theme=dark switches ha-theme.css to HA's dark theme.
 * - Mimics HA's router: the panel navigates with pushState +
 *   location-changed (and Back with popstate), and HA hands it the new
 *   route.
 */

/* global document, location, window, URLSearchParams */

const PREFIX = "/climate_manager";

const theme = new URLSearchParams(location.search).get("theme");
if (theme === "dark") document.documentElement.dataset.theme = "dark";

const currentRoute = () => ({
  prefix: PREFIX,
  path: location.pathname.startsWith(PREFIX)
    ? location.pathname.slice(PREFIX.length)
    : "",
});

/** Mount <climate-manager-panel> in #mount with hass already set. */
export function mountPanel(hass) {
  const panel = document.createElement("climate-manager-panel");
  panel.hass = hass;
  panel.narrow = false;
  panel.panel = {};
  panel.route = currentRoute();
  const follow = () => {
    panel.route = currentRoute();
  };
  window.addEventListener("location-changed", follow);
  window.addEventListener("popstate", follow);
  document.getElementById("mount").appendChild(panel);
  window.__panelReady = true;
  return panel;
}
