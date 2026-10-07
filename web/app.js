"use strict";

const $ = (id) => document.getElementById(id);
const state = {
  catalogue: null,
  current: null,
  result: null,
  revision: 0,
  chronology: null,
  chronologyResult: null,
  chronologyRevision: 0,
  page: 0,
  materialQuery: null,
};
const element = (tag, text, className) => {
  const node = document.createElement(tag);
  if (text !== undefined && text !== null) node.textContent = text;
  if (className) node.className = className;
  return node;
};
function append(parent, ...children) {
  parent.append(...children);
  return parent;
}
function status(id, message, error = false) {
  $(id).textContent = message;
  $(id).classList.toggle("error", error);
}
async function api(path, body) {
  const response = await fetch(
    path,
    body === undefined
      ? {}
      : {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        },
  );
  const result = await response.json();
  if (!response.ok || result.error)
    throw new Error(result.error || `Request failed (${response.status})`);
  return result;
}
function download(name, value) {
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(value, null, 2) + "\n"], {
      type: "application/json",
    }),
  );
  const a = element("a");
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function tone(value) {
  return (
    value
      ?.replace(/^vb-PKC-/, "PKC tone ")
      .replace(/^vb-/, "")
      .replace(/-([FLRMH1-4])$/, " $1") || "unobserved tone"
  );
}
function form(value) {
  if (value === null || value === undefined) return "unobserved";
  if (typeof value === "string") return value;
  if (!Array.isArray(value)) {
    if ("segments" in value)
      return (
        (value.segments.length
          ? form(value.segments) + (value.tone ? " · " : "")
          : "") +
        (value.tone ? tone(value.tone) : value.segments.length ? "" : "∅")
      );
    if ("form" in value) return form(value.form);
    return JSON.stringify(value);
  }
  return (
    value
      .map((c) =>
        typeof c === "string"
          ? c
          : c.kind === "unknown"
            ? "?"
            : c.kind === "morpheme"
              ? "+"
              : (c.value ?? "∅"),
      )
      .join("") || "∅"
  );
}
function predicted(value) {
  try {
    return form(JSON.parse(value));
  } catch {
    return value;
  }
}
function checkRow(name, value, title, note, checked = true, disabled = false) {
  const label = element("label", null, "check-row");
  const input = element("input");
  input.type = "checkbox";
  input.name = name;
  input.value = value;
  input.checked = checked;
  input.disabled = disabled;
  const text = element("span");
  text.append(element("b", title));
  if (note) text.append(element("small", note));
  return append(label, input, text);
}
function chosen(name) {
  return [...document.querySelectorAll(`input[name="${name}"]:checked`)].map(
    (x) => x.value,
  );
}
function rawDetails(value, label = "Full certificate (JSON)") {
  const d = element("details", null, "details-json");
  append(
    d,
    element("summary", label),
    element("pre", JSON.stringify(value, null, 2)),
  );
  return d;
}
function heading(title, note) {
  return append(
    element("div", null, "section-heading"),
    element("h3", title),
    element("span", note),
  );
}
function link(label, href) {
  const a = element("a", label);
  a.href = href;
  a.target = "_blank";
  a.rel = "noreferrer";
  return a;
}

function setTab(name, focus = false) {
  document.querySelectorAll("[role=tab]").forEach((t) => {
    const on = t.dataset.tab === name;
    t.setAttribute("aria-selected", String(on));
    t.tabIndex = on ? 0 : -1;
    $(t.getAttribute("aria-controls")).hidden = !on;
    if (on && focus) t.focus();
  });
  if (name === "materials" && !state.materialQuery) loadMaterials(true);
}
document.querySelectorAll("[role=tab]").forEach((tab, index, tabs) => {
  tab.addEventListener("click", () => setTab(tab.dataset.tab));
  tab.addEventListener("keydown", (event) => {
    let next;
    if (event.key === "ArrowRight") next = (index + 1) % tabs.length;
    if (event.key === "ArrowLeft")
      next = (index + tabs.length - 1) % tabs.length;
    if (event.key === "Home") next = 0;
    if (event.key === "End") next = tabs.length - 1;
    if (next !== undefined) {
      event.preventDefault();
      setTab(tabs[next].dataset.tab, true);
    }
  });
});
document.querySelectorAll('input[name="theme"]').forEach((radio) =>
  radio.addEventListener("change", () => {
    document.documentElement.dataset.time = radio.value;
    try {
      localStorage.setItem("comparative-theme", radio.value);
    } catch {}
  }),
);
try {
  const theme = localStorage.getItem("comparative-theme");
  if (["day", "dusk", "night"].includes(theme)) {
    document.documentElement.dataset.time = theme;
    document.querySelector(`input[name="theme"][value="${theme}"]`).checked =
      true;
  }
} catch {}

function axisName(id) {
  return (
    state.current?.axes.find((a) => a.id === id)?.label ||
    id.replaceAll("-", " ")
  );
}
function analysisName(id) {
  return state.current?.hypotheses.find((a) => a.id === id)?.label || id;
}
// Group exact proto-forms, retaining the complete checked histories beneath each.
function canonical(value) {
  if (Array.isArray(value)) return value.map(canonical);
  if (value && typeof value === "object")
    return Object.fromEntries(
      Object.keys(value)
        .sort()
        .map((k) => [k, canonical(value[k])]),
    );
  return value;
}
function reconstructionGroups(r) {
  const ids = new Set(r.analysis.survivors),
    groups = new Map();
  r.histories
    .filter((h) => ids.has(h.id))
    .forEach((h) => {
      const key = JSON.stringify(canonical(h.protoform));
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(h);
    });
  return [...groups.values()];
}
function candidateForms(c) {
  if (c.kind === "paradigm") return c.request.pool;
  if (c.kind === "pool") return (c.request.batch || c.request).inverse[0].pool;
  return [];
}
function updateQuery() {
  const c = state.current;
  if (!c) return;
  const hypotheses = chosen("hypothesis"),
    selected = chosen("observation");
  let count, space;
  if (c.kind === "bounded") {
    const length = Number($("max-length").value);
    const alphabet =
      chosen("segment").length + Number(c.request.allow_morphemes);
    const valid = Number.isInteger(length) && length >= 0 && length <= 16;
    count = valid
      ? Array.from({ length: length + 1 }, (_, i) => alphabet ** i).reduce(
          (a, b) => a + b,
          0,
        )
      : null;
    space = valid
      ? `${count.toLocaleString()} token sequences, from length 0 to ${length}`
      : "Choose a maximum length from 0 to 16";
    $("space-description").textContent =
      space +
      (c.request.allow_morphemes ? "; morpheme boundaries included." : ".");
  } else {
    count = candidateForms(c).length;
    space = `${count} candidate ${c.key === "tones" ? "tone categories" : "forms"} in the supplied pool`;
    $("space-description").textContent =
      space + ". Open the list below to inspect the whole search space.";
  }
  const names = selected.map(axisName).join(", ");
  $("query-summary").textContent = !hypotheses.length
    ? "Select at least one analysis."
    : `Test ${space} under ${hypotheses.length} allowed ${hypotheses.length === 1 ? "analysis" : "analyses"}. ` +
      (selected.length
        ? `Require a match to ${names}.`
        : "No daughter forms are required; every candidate is allowed under each selected analysis.");
}
function showSpace(data) {
  $("word-bounds").hidden = data.kind !== "bounded";
  $("pool-preview").hidden = data.kind === "bounded";
  $("segment-options").replaceChildren();
  if (data.kind === "bounded") {
    data.request.proto_inventory.forEach((x) =>
      $("segment-options").append(checkRow("segment", x, x, "")),
    );
    $("max-length").value = data.request.max_length;
    document
      .querySelectorAll('input[name="segment"]')
      .forEach((x) => x.addEventListener("change", markChanged));
  } else
    $("pool-forms").textContent = candidateForms(data)
      .map((x) => "*" + form(x))
      .join(" · ");
  updateQuery();
}
function markChanged() {
  state.revision++;
  $("export").disabled = true;
  // A changed query can be run even if the superseded request is still finishing.
  $("run").disabled = !state.current;
  $("results").setAttribute("aria-busy", "false");
  updateQuery();
  if (state.result) {
    status(
      "run-status",
      "Selections changed. Enumerate again to update the result.",
    );
    $("results").replaceChildren(
      append(
        element("div", null, "empty-state"),
        element("h3", "Ready to enumerate again"),
        element(
          "p",
          "The constraints have changed. Enumerate again to see every form they now allow.",
        ),
      ),
    );
    state.result = null;
  }
}
function fillCases() {
  const collection = $("collection").value;
  const previous = $("case").value;
  $("case").replaceChildren();
  let options;
  if (collection === "worked")
    options = state.catalogue.examples
      .filter((x) => x.kind !== "chronology")
      .map((x) => [x.key, x.title]);
  else
    options = [
      ...new Map(
        state.catalogue.pools
          .find((p) => p.id === collection)
          .queries.filter((q) => q.scope === "all-groups")
          .map((q) => [q.case, q.title]),
      ).entries(),
    ];
  const query = $("case-search").value.trim().toLocaleLowerCase();
  options = options.filter(([id, title]) =>
    (title + " " + id).toLocaleLowerCase().includes(query),
  );
  options.forEach(([value, label]) => {
    const o = element("option", label);
    o.value = value;
    $("case").append(o);
  });
  $("case-search-status").textContent =
    `${options.length} ${options.length === 1 ? "choice" : "choices"}`;
  $("case").disabled = !options.length;
  if (options.some(([value]) => value === previous)) $("case").value = previous;
  if (options.length) loadCase();
  else {
    markChanged();
    state.current = null;
    $("run").disabled = true;
    status(
      "run-status",
      "No matching material. Try another word or clear the search.",
    );
    $("query-summary").textContent = "Choose material to set constraints.";
    $("hypothesis-options").replaceChildren();
    $("observation-options").replaceChildren();
  }
}
async function loadCase() {
  markChanged();
  const revision = state.revision;
  state.current = null;
  $("run").disabled = true;
  status("run-status", "Loading the analyses and daughter forms…");
  try {
    const params = new URLSearchParams(
      $("collection").value === "worked"
        ? { key: $("case").value }
        : { dataset: $("collection").value, case: $("case").value },
    );
    const data = await api("/api/case?" + params);
    if (revision !== state.revision) return;
    showCase(data);
    status("run-status", "Ready to enumerate with these constraints.");
  } catch (e) {
    status("run-status", e.message, true);
  } finally {
    if (revision === state.revision) $("run").disabled = !state.current;
  }
}
function showCase(data) {
  state.current = data;
  $("study-title").textContent = data.title;
  $("study-subtitle").textContent = data.subtitle;
  $("case-kind").textContent =
    data.kind === "pool"
      ? "Declared candidate pool"
      : data.kind === "paradigm"
        ? "Linked paradigm · finite roots"
        : "Bounded word enumeration";
  $("case-description").textContent = data.description;
  $("hypothesis-options").replaceChildren();
  $("observation-options").replaceChildren();
  data.hypotheses.forEach((h) => {
    const row = checkRow("hypothesis", h.id, h.label, "");
    row.title = h.description || h.id;
    $("hypothesis-options").append(row);
  });
  data.axes.forEach((a) => {
    const row = checkRow(
      "observation",
      a.id,
      a.label || axisName(a.id),
      form(a.expected),
      data.defaults?.includes(a.id) ?? a.observed,
      !a.observed,
    );
    row.querySelector("small")?.classList.add("observation-form");
    row.title = a.source_ref || a.id;
    $("observation-options").append(row);
  });
  const note = $("reading-note");
  note.replaceChildren();
  note.hidden = data.key !== "tones";
  if (!note.hidden) {
    append(
      note,
      element(
        "p",
        "Source discrepancy retained: Table 164 gives Hakha Lai L for PKC tone 2; Table 166 prints F. Select either reading or keep both as whole analyses. Tone categories are source-specific; this example projects away the segments.",
      ),
      link("Table 164 · PDF p. 482 ↗", "/sources/vanbik2009.pdf#page=482"),
      link("Table 166 · PDF p. 493 ↗", "/sources/vanbik2009.pdf#page=493"),
    );
  }
  document
    .querySelectorAll("#hypothesis-options input,#observation-options input")
    .forEach((c) => c.addEventListener("change", markChanged));
  showSpace(data);
}
function activeBody() {
  const c = state.current;
  if (!c) throw new Error("Choose a case first.");
  const hypotheses = chosen("hypothesis");
  if (!hypotheses.length)
    throw new Error("Select at least one allowed analysis.");
  const budget = Number($("subset-budget").value);
  if (!Number.isInteger(budget) || budget < 0 || budget > 4096)
    throw new Error(
      "Conflict subset budget must be an integer from 0 to 4,096.",
    );
  return {
    kind: c.kind,
    ...(c.imported
      ? { request: c.request }
      : c.key
        ? { key: c.key }
        : { dataset: c.dataset, case: c.case, scope: c.scope }),
    hypotheses,
    ...(c.kind === "bounded"
      ? {
          bounds: {
            proto_inventory: chosen("segment"),
            max_length: Number($("max-length").value),
          },
        }
      : {}),
    selected: chosen("observation"),
    subset_budget: budget,
  };
}
async function runEvidence() {
  const revision = state.revision;
  $("run").disabled = true;
  $("results").setAttribute("aria-busy", "true");
  $("export").disabled = true;
  status(
    "run-status",
    "Enumerating in Lean and comparing independent results…",
  );
  try {
    const data = await api("/api/run", activeBody());
    if (revision !== state.revision) return;
    state.result = data;
    renderEvidence(data.result);
    $("export").disabled = false;
    status(
      "run-status",
      data.result.complete
        ? "Every allowed reconstruction is listed. Open a form to inspect its analyses."
        : "Reconstruction enumeration is complete. The search for conflicting constraints is incomplete.",
    );
  } catch (e) {
    if (revision === state.revision) {
      state.result = null;
      $("results").replaceChildren(
        append(element("div", null, "source-note"), element("p", e.message)),
      );
      status("run-status", e.message, true);
    }
  } finally {
    if (revision === state.revision) {
      $("run").disabled = !state.current;
      $("results").setAttribute("aria-busy", "false");
    }
  }
}
function traceLine(before, after, name) {
  return append(
    element("div", null, "trace-line"),
    element("span", name, "rule-name"),
    element("span", form(before)),
    element("span", "→", "arrow"),
    element("span", form(after)),
  );
}
function certificateView(c, axis) {
  const box = element("div", null, "derivation");
  box.append(element("h4", axis));
  if ("allomorph_input" in c) {
    if (JSON.stringify(c.input.segments) !== JSON.stringify(c.allomorph_input))
      box.append(
        traceLine(
          c.input.segments,
          c.allomorph_input,
          "Declared stem allomorph",
        ),
      );
    appendTrace(box, c.stem_steps, c.allomorph_input);
    if (c.prefix.length || c.suffix.length)
      box.append(traceLine(c.stem_output, c.affixed, "Affixation"));
    appendTrace(box, c.sound_steps, c.affixed);
    (c.tone_steps || [])
      .filter((t) => t.applied)
      .forEach((t) =>
        box.append(
          traceLine(
            tone(t.input),
            tone(t.output),
            t.rule_id + " · conditioned on " + t.conditioning,
          ),
        ),
      );
    const unchanged = (c.tone_steps || []).filter((t) => !t.applied).length;
    if (unchanged)
      box.append(
        element(
          "p",
          `${unchanged} unchanged tone rules; see the full certificate.`,
          "footnote",
        ),
      );
  } else appendTrace(box, c.steps, c.input);
  box.append(element("p", "Output: " + form(c.output), "form"));
  box.append(rawDetails(c));
  return box;
}
function appendTrace(box, trace, input) {
  const steps = Array.isArray(trace) ? trace : (trace?.steps ?? []);
  let current = input,
    unchanged = 0;
  steps.forEach((s) => {
    const output = s.output ?? s.after;
    if (JSON.stringify(current) !== JSON.stringify(output))
      box.append(
        traceLine(
          current,
          output,
          s.law_id ?? s.rule_id ?? s.id ?? "Rule pass",
        ),
      );
    else unchanged++;
    current = output;
  });
  if (unchanged)
    box.append(
      element(
        "p",
        `${unchanged} unchanged rule passes; all passes are retained in the certificate below.`,
        "footnote",
      ),
    );
}
function historyView(h, r) {
  const details = element("details", null, "history-details");
  details.dataset.history = h.id;
  details.append(
    element(
      "summary",
      analysisName(h.analysis_id) + " · predictions & derivation",
    ),
  );
  details.addEventListener("toggle", () => {
    if (!details.open || details.dataset.loaded) return;
    details.dataset.loaded = "true";
    const table = element("table", null, "prediction-table");
    table.append(
      append(
        element("thead"),
        append(
          element("tr"),
          ...["Daughter form", "Predicted", "Required"].map((x) =>
            element("th", x),
          ),
        ),
      ),
    );
    const body = element("tbody");
    r.axes.forEach((axis, i) =>
      body.append(
        append(
          element("tr"),
          element("td", axisName(axis.id)),
          element("td", form(h.predictions[i]), "form"),
          element(
            "td",
            r.selected.includes(axis.id)
              ? "✓ " +
                  form(
                    h.observations?.[i]?.form ??
                      h.observations?.[i] ??
                      axis.expected,
                  )
              : "Unconstrained",
          ),
        ),
      ),
    );
    table.append(body);
    details.append(append(element("div", null, "table-wrap"), table));
    const traces = element("div", null, "derivations");
    h.certificates.forEach((c, i) =>
      traces.append(certificateView(c, axisName(r.axes[i].id))),
    );
    append(
      details,
      element("p", h.analysis_id, "analysis-id"),
      traces,
      element("p", h.source_scope, "footnote"),
    );
  });
  return details;
}
function renderEvidence(r) {
  const box = $("results"),
    a = r.analysis,
    groups = reconstructionGroups(r);
  box.replaceChildren();
  const by = new Map(r.histories.map((h) => [h.id, h]));
  const summary = element("div", null, "result-summary");
  summary.dataset.forms = groups.length;
  [
    [
      groups.length,
      groups.length === 1
        ? "allowed reconstruction"
        : "allowed reconstructions",
    ],
    [a.survivors.length, "compatible form–analysis combinations"],
    [r.histories.length, "combinations checked"],
  ].forEach(([n, label]) =>
    summary.append(
      append(
        element("div", null, "metric"),
        element("strong", n),
        element("span", label),
      ),
    ),
  );
  // A successful API result exhausts the underlying candidate space. The matrix's
  // `complete` field additionally covers conflict diagnosis, a separate search.
  summary.append(
    element(
      "p",
      "✓ All allowed forms in this finite search space are listed.",
      "completion",
    ),
  );
  box.append(summary);
  box.append(
    element(
      "p",
      r.selected.length
        ? "Must match: " +
            r.selected
              .map((id) => {
                const axis = state.current.axes.find((a) => a.id === id);
                return axisName(id) + " = " + form(axis.expected);
              })
              .join("; ") +
            "."
        : "No daughter forms are required. The list contains the entire chosen candidate space.",
      "result-query",
    ),
  );
  if (!groups.length) {
    box.append(heading("No reconstruction matches these constraints", ""));
    box.append(
      element(
        "p",
        "Try allowing another analysis or unchecking a required daughter form. Each conflict below identifies constraints that cannot hold together within this search space.",
      ),
    );
    const list = element("ul", null, "conflict-list");
    a.minimal_conflicts.forEach((core) => {
      const row = element("li");
      row.append(
        element("span", core.map((i) => axisName(r.axes[i].id)).join(" + ")),
      );
      const actions = element("div", null, "selection-actions");
      core.forEach((i) => {
        const id = r.axes[i].id,
          button = element("button", "Uncheck " + axisName(id), "quiet");
        button.type = "button";
        button.addEventListener("click", () => {
          const input = [
            ...document.querySelectorAll('input[name="observation"]'),
          ].find((x) => x.value === id);
          input.checked = false;
          markChanged();
          $("run").focus();
        });
        actions.append(button);
      });
      append(
        row,
        element(
          "small",
          "Minimal conflict: removing any one of these forms makes this subset satisfiable.",
        ),
        actions,
      );
      list.append(row);
    });
    box.append(list);
    if (!a.conflicts_complete)
      box.append(
        element(
          "p",
          "Conflict diagnosis is incomplete: " +
            a.subsets_examined +
            " of " +
            a.subset_space +
            " subsets examined. Increase the diagnostic budget to find all minimal conflicts. The empty reconstruction result above is complete.",
          "source-note incomplete",
        ),
      );
  } else {
    box.append(
      heading(
        "Allowed reconstructions",
        "Open a form to see which analyses allow it",
      ),
    );
    groups.forEach((histories) => {
      const d = element("details", null, "candidate"),
        modelCount = new Set(histories.map((h) => h.analysis_id)).size;
      append(
        d,
        append(
          element("summary"),
          element("span", "*" + form(histories[0].protoform), "proto"),
          element(
            "span",
            modelCount +
              " allowed " +
              (modelCount === 1 ? "analysis" : "analyses"),
            "candidate-id",
          ),
        ),
      );
      d.addEventListener("toggle", () => {
        if (!d.open || d.dataset.loaded) return;
        d.dataset.loaded = "true";
        histories.forEach((h) => d.append(historyView(h, r)));
      });
      box.append(d);
    });
    const diagnostics = element("details", null, "diagnostics");
    diagnostics.append(
      element(
        "summary",
        "Compare predictions & find useful additional evidence",
      ),
    );
    diagnostics.append(
      heading(
        "Analyses with the same selected predictions",
        a.equivalence_classes.length + " groups",
      ),
    );
    a.equivalence_classes.forEach((group, i) => {
      diagnostics.append(
        append(
          element("div", null, "equivalence-row"),
          element(
            "b",
            `Group ${i + 1} · ${group.histories.length} form–analysis combinations`,
          ),
          element(
            "div",
            group.histories
              .map(
                (id) =>
                  "*" +
                  form(by.get(id).protoform) +
                  " [" +
                  analysisName(by.get(id).analysis_id) +
                  "]",
              )
              .join("; "),
          ),
        ),
      );
    });
    diagnostics.append(
      heading(
        "What else would distinguish these reconstructions?",
        "Unchecked forms & unobserved forms",
      ),
    );
    const probes = [...a.probes].sort(
      (l, r) => r.distinguished_pairs - l.distinguished_pairs,
    );
    if (!probes.length)
      diagnostics.append(
        element(
          "p",
          "All available daughter forms are required. Uncheck one to compare its predictions.",
          "footnote",
        ),
      );
    probes.forEach((p) => {
      const d = element("details", null, "probe");
      d.dataset.axis = r.axes[p.axis].id;
      append(
        d,
        append(
          element("summary"),
          element("span", axisName(r.axes[p.axis].id)),
          element("small", p.distinguished_pairs + " pairs distinguished"),
        ),
      );
      p.partitions.forEach((part) =>
        d.append(
          append(
            element("div", null, "partition"),
            element("span", part.prediction.map(predicted).join(" · "), "form"),
            element(
              "span",
              part.histories
                .map(
                  (id) =>
                    "*" +
                    form(by.get(id).protoform) +
                    " [" +
                    analysisName(by.get(id).analysis_id) +
                    "]",
                )
                .join("; "),
            ),
          ),
        ),
      );
      if (!p.discriminating)
        d.append(
          element(
            "p",
            "This form would not distinguish the surviving combinations.",
            "footnote",
          ),
        );
      diagnostics.append(d);
    });
    diagnostics.append(
      element(
        "p",
        "These comparisons preserve analysis identities. Pair counts are not probabilities or evidence weights.",
        "footnote",
      ),
    );
    box.append(diagnostics);
  }
  box.append(
    rawDetails(
      {
        axes: r.axes,
        selected: r.selected,
        matrix: r.matrix,
        analysis: r.analysis,
      },
      "Inspect the checked evidence matrix & completeness record",
    ),
  );
}

function loadChronology(data) {
  state.chronologyRevision++;
  state.chronologyResult = null;
  state.chronology = data;
  $("chronology-title").textContent = data.description ? data.id : "Chronology";
  $("chronology-description").textContent = data.description;
  $("precedence").replaceChildren(element("legend", "Earlier → later"));
  for (const earlier of data.blocks)
    for (const later of data.blocks) {
      if (earlier.id === later.id) continue;
      const edge = JSON.stringify({ earlier: earlier.id, later: later.id });
      const row = checkRow(
        "precedence",
        edge,
        earlier.label + " → " + later.label,
        "",
        data.constraints.some(
          (c) => c.earlier === earlier.id && c.later === later.id,
        ),
      );
      $("precedence").append(row);
    }
  document.querySelectorAll('input[name="precedence"]').forEach((x) =>
    x.addEventListener("change", () => {
      state.chronologyRevision++;
      $("export-chronology").disabled = true;
      $("chronology-results").replaceChildren();
      state.chronologyResult = null;
      status(
        "chronology-status",
        "Precedences changed. Enumerate again to update the orders.",
      );
    }),
  );
  $("chronology-subtitle").textContent =
    data.source_kind + " · " + data.source_ref;
}
async function runChronology() {
  const revision = state.chronologyRevision;
  const request = state.chronology;
  state.chronologyResult = null;
  $("export-chronology").disabled = true;
  $("run-chronology").disabled = true;
  $("chronology-results").setAttribute("aria-busy", "true");
  status(
    "chronology-status",
    "Enumerating every permitted order and deriving its outputs…",
  );
  const constraints = chosen("precedence").map(JSON.parse);
  try {
    const data = await api("/api/run", {
      kind: "chronology",
      request,
      constraints,
    });
    if (revision !== state.chronologyRevision) return;
    state.chronologyResult = data;
    const r = data.result;
    $("chronology-results").replaceChildren();
    $("export-chronology").disabled = false;
    const box = $("chronology-results");
    box.append(
      heading(
        `${r.orders.length} permitted orders`,
        `${r.orders.filter((o) => o.agrees_with_observations).length} match all observations`,
      ),
    );
    if (r.cyclic)
      box.append(
        element(
          "p",
          "The precedence constraints contain a cycle. No order satisfies them.",
          "source-note",
        ),
      );
    r.orders.forEach((o) => {
      const d = element("details", null, "order");
      append(
        d,
        append(
          element("summary"),
          element("span", o.order.join(" → ")),
          element(
            "span",
            o.agrees_with_observations ? "matches" : "mismatch",
            "tag",
          ),
        ),
      );
      o.probes.forEach((p, i) =>
        d.append(certificateView(p, request.probes[i].id)),
      );
      box.append(d);
    });
    box.append(
      element(
        "p",
        r.scope +
          ". Matching these probes establishes agreement within this control, not a full historical chronology.",
        "footnote",
      ),
    );
    status(
      "chronology-status",
      "Complete enumeration checked against the independent interpreter.",
    );
  } catch (e) {
    if (revision === state.chronologyRevision) {
      $("chronology-results").replaceChildren(
        element("p", e.message, "source-note"),
      );
      status("chronology-status", e.message, true);
    }
  } finally {
    $("run-chronology").disabled = false;
    $("chronology-results").setAttribute("aria-busy", "false");
  }
}

async function loadMaterials(reset = false) {
  if (reset) {
    state.page = 0;
    state.materialQuery = {
      dataset: $("source").value,
      q: $("material-query").value,
      language: $("material-language").value,
      concept: $("material-concept").value,
      set: $("material-set").value,
    };
  }
  const query = new URLSearchParams({
    ...state.materialQuery,
    offset: state.page * 25,
    limit: 25,
  });
  const key = query.toString();
  state.materialPending = key;
  $("material-results").setAttribute("aria-busy", "true");
  status("material-status", "Searching retained source rows…");
  $("previous").disabled = true;
  $("next").disabled = true;
  try {
    const r = await api("/api/materials?" + key);
    if (state.materialPending !== key) return;
    const table = element("table", null, "material-table");
    const head = element("thead"),
      tr = element("tr");
    [
      "Form & source record",
      "Language / variety",
      "Meaning",
      "Source ID",
    ].forEach((x) => tr.append(element("th", x)));
    head.append(tr);
    table.append(head);
    const body = element("tbody");
    r.records.forEach((record) => {
      const s = record.source_row,
        row = element("tr"),
        cell = element("td"),
        d = element("details", null, "source-record");
      const display =
        s.Form ||
        s.Value ||
        s.form ||
        s.source_form ||
        s.raw_form ||
        s.transcription ||
        record.source_reconstruction ||
        record.id;
      append(
        d,
        element("summary", display),
        element(
          "p",
          record.representation_note ||
            "Source-qualified transcription. Inspect the original extraction and its scope below.",
          "footnote",
        ),
      );
      if (record.dataset === "vanbik2009")
        d.append(
          link(
            "Open numbered entry in VanBik ↗",
            "/sources/vanbik2009.pdf#page=" + s.source_locator.pdf_page,
          ),
        );
      else
        d.append(
          link(
            "Retained forms table ↗",
            "https://github.com/zengrf/lean-historical-linguistics/blob/main/data/upstream/" +
              record.dataset +
              "/cldf/forms.csv",
          ),
        );
      d.append(element("pre", JSON.stringify(record, null, 2)));
      cell.append(d);
      append(
        row,
        cell,
        element(
          "td",
          record.language?.Name ||
            s.source_alias ||
            s.doculect_id ||
            s.Language_ID ||
            "—",
        ),
        element(
          "td",
          record.concept?.Name || s.source_gloss || s.gloss || s.meaning || "—",
        ),
        element("td", record.id),
      );
      body.append(row);
    });
    table.append(body);
    $("material-results").replaceChildren(
      append(element("div", null, "table-wrap"), table),
    );
    if (!r.total)
      $("material-results").append(
        element(
          "p",
          "No retained source record matches these filters.",
          "footnote",
        ),
      );
    status(
      "material-status",
      `${r.total.toLocaleString()} matching source records · showing ${r.returned ? r.offset + 1 : 0}–${r.offset + r.returned}`,
    );
    $("page-number").textContent =
      `Page ${state.page + 1} of ${Math.max(1, Math.ceil(r.total / 25))}`;
    $("previous").disabled = state.page === 0;
    $("next").disabled = !r.has_more;
  } catch (e) {
    if (state.materialPending === key) {
      status("material-status", e.message, true);
      $("material-results").replaceChildren();
    }
  } finally {
    if (state.materialPending === key)
      $("material-results").setAttribute("aria-busy", "false");
  }
}
async function importFile(file, kind, chronology = false) {
  if (!file) return;
  if (file.size > 2_000_000) throw new Error("JSON input exceeds 2 MB.");
  const request = (await api("/api/import", { text: await file.text() }))
    .request;
  if (chronology) {
    if (!Array.isArray(request.blocks) || !Array.isArray(request.constraints))
      throw new Error("Expected a chronology specification.");
    loadChronology(request);
    $("chronology-results").replaceChildren();
    $("export-chronology").disabled = true;
    status(
      "chronology-status",
      "Imported. Enumerate to validate this specification.",
    );
    return;
  }
  if (!Array.isArray(request.analyses) || !request.analyses.length)
    throw new Error("Expected a specification with whole analyses.");
  const first = request.analyses[0];
  const raw = kind === "paradigm" ? first.cells : first.observations;
  if (!Array.isArray(raw))
    throw new Error(
      "The selected import kind does not match the specification.",
    );
  markChanged();
  const axes = raw.map((x, i) => ({
    id: x.id ?? x.doculect_id,
    expected: kind === "paradigm" ? x.expected : x.form,
    source_ref: x.source_ref,
    observed: request.analyses.every(
      (a) =>
        (kind === "paradigm"
          ? a.cells[i]?.expected
          : a.observations[i]?.form) != null,
    ),
  }));
  $("collection").querySelector('option[value="imported"]')?.remove();
  const imported = element("option", "Imported finite specification");
  imported.value = "imported";
  imported.disabled = true;
  $("collection").append(imported);
  $("collection").value = "imported";
  $("case-search").value = "";
  $("case-search").disabled = true;
  $("case-search-status").textContent = "Imported specification";
  $("case").disabled = false;
  $("case").replaceChildren(element("option", request.id));
  showCase({
    kind,
    imported: true,
    title: request.id,
    subtitle: "Imported finite specification",
    request,
    description: request.source_scope || request.description,
    axes,
    defaults: axes.filter((a) => a.observed).map((a) => a.id),
    hypotheses: request.analyses.map((a) => ({
      id: a.id,
      label: a.description,
    })),
  });
  status("import-status", file.name + " · validated when enumerated");
  status(
    "run-status",
    "Imported. Enumerate to validate and execute this specification.",
  );
}

$("collection").addEventListener("change", () => {
  $("case-search").value = "";
  $("case-search").disabled = false;
  fillCases();
});
$("case-search").addEventListener("input", fillCases);
$("max-length").addEventListener("input", markChanged);
$("reset-constraints").addEventListener("click", () => {
  if (!state.current) return;
  markChanged();
  showCase(state.current);
  status("run-status", "Default constraints restored. Ready to enumerate.");
});
for (const [id, value] of [
  ["observations-all", true],
  ["observations-none", false],
])
  $(id).addEventListener("click", () => {
    document
      .querySelectorAll('input[name="observation"]:not(:disabled)')
      .forEach((x) => (x.checked = value));
    markChanged();
  });
$("case").addEventListener("change", loadCase);
$("subset-budget").addEventListener("change", markChanged);
$("run").addEventListener("click", runEvidence);
$("run-chronology").addEventListener("click", runChronology);
$("export").addEventListener("click", () =>
  download("reconstruction-result.json", state.result),
);
$("export-chronology").addEventListener("click", () =>
  download("chronology-result.json", state.chronologyResult),
);
$("download-input").addEventListener(
  "click",
  () =>
    state.current &&
    download(state.current.request.id + ".json", state.current.request),
);
$("download-chronology").addEventListener("click", () =>
  download("chronology-specification.json", {
    ...state.chronology,
    constraints: chosen("precedence").map(JSON.parse),
  }),
);
$("import-input").addEventListener("change", (e) =>
  importFile(e.target.files[0], $("import-kind").value).catch((e) =>
    status("import-status", e.message, true),
  ),
);
$("import-chronology").addEventListener("change", (e) =>
  importFile(e.target.files[0], "chronology", true).catch((e) =>
    status("chronology-status", e.message, true),
  ),
);
$("material-form").addEventListener("submit", (e) => {
  e.preventDefault();
  loadMaterials(true);
});
$("previous").addEventListener("click", () => {
  state.page--;
  loadMaterials();
});
$("next").addEventListener("click", () => {
  state.page++;
  loadMaterials();
});

async function start() {
  try {
    state.catalogue = await api("/api/catalogue");
    $("collection").replaceChildren();
    [
      ["worked", "Worked examples · stems, tone & evidence"],
      ...state.catalogue.pools.map((p) => [p.id, p.label + " · source pools"]),
    ].forEach(([value, label]) => {
      const o = element("option", label);
      o.value = value;
      $("collection").append(o);
    });
    const coverage = state.catalogue.coverage.datasets;
    [
      ["iecor", "IE-CoR forms"],
      ["sagartst", "Sagart et al. forms"],
      ["hillburmish", "Burmish forms"],
      ["vanbik2009", "VanBik reflex records"],
    ].forEach(([id, label]) =>
      $("coverage").append(
        append(
          element("div"),
          element(
            "strong",
            (
              coverage[id].forms ?? coverage[id].reflex_records
            ).toLocaleString(),
          ),
          element("span", label),
        ),
      ),
    );
    fillCases();
    const c = await api("/api/case?key=chronology");
    loadChronology(c.request);
    $("chronology-title").textContent = c.title;
    $("chronology-subtitle").textContent = c.subtitle;
  } catch (e) {
    status("run-status", e.message, true);
    $("study-title").textContent = "The catalogue is unavailable";
    $("run").disabled = true;
  }
}
start();
