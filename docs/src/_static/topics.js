/*
 * Copyright (c) 2026, tephpy Contributors.
 *
 * This file is part of tephpy and is distributed under the 3-Clause BSD license.
 * See the LICENSE file in the package root directory for licensing details.
 */

/*
 * The topic index's filter (topics spec §3.6).
 *
 * Modelled on sphinx-gallery's `sg-tags.js`, and deliberately not a copy of it:
 * that script discovers its buttons from the tags present on the page, and this
 * one is handed the promoted set the build computed (topics spec §3.4), which is
 * the difference the whole feature turns on.
 *
 * Two rows, two semantics, and the difference is forced by the data rather than
 * chosen. Topics are AND, as they are in `sg-tags.js`: an item carries several,
 * so narrowing by a second one is meaningful. Quadrants are OR, because an item
 * sits in exactly one -- ANDing "Tutorials" with "How-To Guides" would select
 * nothing every time, and a control whose second click always empties the page
 * is broken rather than strict. The two rows are then ANDed together, which is
 * what makes "how-tos about parcels" expressible at all.
 *
 * The bar is emitted `hidden` and unhidden here, so a reader with scripting off
 * gets the list rather than a row of controls that do nothing.
 *
 * Sphinx places `add_js_file` scripts in `<head>`, undeferred, which runs this
 * before `<body>` exists -- `sg-tags.js` is loaded the same way and waits on
 * `DOMContentLoaded` for exactly that reason. Without it, `getElementById`
 * returns `null` for a bar that has not been parsed yet, and the early return
 * below would fire on every load, silently, forever.
 */

document.addEventListener("DOMContentLoaded", () => {
  const PARAM = "topics";
  const QUADRANT_PARAM = "quadrants";

  const bar = document.getElementById("teph-topic-filter");
  if (bar === null) {
    return;
  }
  const clear = document.getElementById("teph-topic-clear");
  const empty = document.getElementById("teph-topic-empty");
  const buttons = Array.from(bar.querySelectorAll(".teph-topic-button"));
  const quadrantButtons = Array.from(
    bar.querySelectorAll(".teph-quadrant-button"),
  );
  const items = Array.from(document.querySelectorAll(".teph-topic-item"));
  const selected = new Set();
  const selectedQuadrants = new Set();

  const render = () => {
    let shown = 0;
    items.forEach((item) => {
      let tags = [];
      try {
        tags = JSON.parse(item.dataset.topics);
      } catch {
        tags = [];
      }
      const held = new Set(tags);
      const inQuadrant =
        selectedQuadrants.size === 0 ||
        selectedQuadrants.has(item.dataset.quadrant);
      const matches =
        inQuadrant && Array.from(selected).every((tag) => held.has(tag));
      item.hidden = !matches;
      if (matches) {
        shown += 1;
      }
    });

    buttons.forEach((button) => {
      const active = selected.has(button.dataset.topic);
      button.classList.toggle("active", active);
      button.setAttribute("aria-pressed", active ? "true" : "false");
    });

    quadrantButtons.forEach((button) => {
      const active = selectedQuadrants.has(button.dataset.quadrant);
      button.classList.toggle("active", active);
      button.setAttribute("aria-pressed", active ? "true" : "false");
    });

    clear.hidden = selected.size === 0 && selectedQuadrants.size === 0;
    empty.hidden = shown > 0;

    const params = new URLSearchParams(window.location.search);
    if (selected.size > 0) {
      params.set(PARAM, Array.from(selected).sort().join(","));
    } else {
      params.delete(PARAM);
    }
    if (selectedQuadrants.size > 0) {
      params.set(
        QUADRANT_PARAM,
        Array.from(selectedQuadrants).sort().join(","),
      );
    } else {
      params.delete(QUADRANT_PARAM);
    }
    const query = params.toString();
    window.history.replaceState(
      {},
      "",
      query ? `${window.location.pathname}?${query}` : window.location.pathname,
    );
  };

  buttons.forEach((button) => {
    button.setAttribute("aria-pressed", "false");
    button.addEventListener("click", () => {
      const tag = button.dataset.topic;
      if (selected.has(tag)) {
        selected.delete(tag);
      } else {
        selected.add(tag);
      }
      render();
    });
  });

  quadrantButtons.forEach((button) => {
    button.setAttribute("aria-pressed", "false");
    button.addEventListener("click", () => {
      const quadrant = button.dataset.quadrant;
      if (selectedQuadrants.has(quadrant)) {
        selectedQuadrants.delete(quadrant);
      } else {
        selectedQuadrants.add(quadrant);
      }
      render();
    });
  });

  // `clear` clears both rows. A control that emptied one and left the other
  // would leave the list filtered with nothing obviously still set.
  clear.addEventListener("click", () => {
    selected.clear();
    selectedQuadrants.clear();
    render();
  });

  // Only a term that earned a button is honoured, so a stale or hand-written
  // `?topics=` cannot filter the list down to nothing with no control to undo it.
  const query = new URLSearchParams(window.location.search);
  const offered = new Set(buttons.map((button) => button.dataset.topic));
  const requested = query.get(PARAM);
  if (requested) {
    requested
      .split(",")
      .filter((tag) => offered.has(tag))
      .forEach((tag) => selected.add(tag));
  }
  const offeredQuadrants = new Set(
    quadrantButtons.map((button) => button.dataset.quadrant),
  );
  const requestedQuadrants = query.get(QUADRANT_PARAM);
  if (requestedQuadrants) {
    requestedQuadrants
      .split(",")
      .filter((quadrant) => offeredQuadrants.has(quadrant))
      .forEach((quadrant) => selectedQuadrants.add(quadrant));
  }

  bar.hidden = false;
  render();
});
