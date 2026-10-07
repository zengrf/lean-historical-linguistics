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
    document.documentElement.dataset.theme = radio.value;
    try {
      localStorage.setItem("comparative-theme", radio.value);
    } catch {}
  }),
);
try {
  const theme = localStorage.getItem("comparative-theme");
  if (["day", "dusk", "night"].includes(theme)) {
    document.documentElement.dataset.theme = theme;
    document.querySelector(`input[name="theme"][value="${theme}"]`).checked =
      true;
  }
} catch {}

function markChanged() {
  state.revision++;
  $("export").disabled = true;
  if (state.result) {
    status(
      "run-status",
      "Selections changed. Enumerate again to update the result.",
    );
    $("results").replaceChildren(
      append(
        element("div", null, "empty-state"),
        element("h3", "Ready for another comparison"),
        element(
          "p",
          "The observations or hypotheses have changed. Enumerate again to see the new result.",
        ),
      ),
    );
    state.result = null;
  }
}
function fillCases() {
  const collection = $("collection").value;
  $("case").replaceChildren();
  let options;
  if (collection === "worked")
    options = state.catalogue.examples
      .filter((x) => x.kind !== "chronology")
      .map((x) => [x.key, x.title]);
  else {
    const queries = state.catalogue.pools.find(
      (p) => p.id === collection,
    ).queries;
    options = [
      ...new Set(
        queries.filter((q) => q.scope === "all-groups").map((q) => q.case),
      ),
    ].map((c) => [c, c]);
  }
  options.forEach(([value, label]) => {
    const o = element("option", label);
    o.value = value;
    $("case").append(o);
  });
  loadCase();
}
async function loadCase() {
  markChanged();
  const revision = state.revision;
  $("run").disabled = true;
  status("run-status", "Loading the declared models…");
  try {
    const params = new URLSearchParams(
      $("collection").value === "worked"
        ? { key: $("case").value }
        : { dataset: $("collection").value, case: $("case").value },
    );
    const data = await api("/api/case?" + params);
    if (revision !== state.revision) return;
    showCase(data);
    status("run-status", "Ready. All displayed assumptions are explicit.");
  } catch (e) {
    status("run-status", e.message, true);
  } finally {
    if (revision === state.revision) $("run").disabled = false;
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
  data.hypotheses.forEach((h) =>
    $("hypothesis-options").append(checkRow("hypothesis", h.id, h.id, h.label)),
  );
  data.axes.forEach((a) => {
    const row = checkRow(
      "observation",
      a.id,
      a.id,
      form(a.expected),
      data.defaults?.includes(a.id) ?? a.observed,
      !a.observed,
    );
    row.querySelector("small")?.classList.add("observation-form");
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
}
function activeBody() {
  const c = state.current;
  if (!c) throw new Error("Choose a case first.");
  const hypotheses = chosen("hypothesis");
  if (!hypotheses.length)
    throw new Error("Select at least one whole hypothesis.");
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
        ? "Enumeration checked. Inspect or export the complete result."
        : "Conflict enumeration is incomplete. Increase the subset budget to exhaust it.",
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
    $("run").disabled = false;
    $("results").setAttribute("aria-busy", "false");
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
function renderEvidence(r) {
  const box = $("results");
  box.replaceChildren();
  const a = r.analysis;
  const by = new Map(r.histories.map((h) => [h.id, h]));
  const summary = element("div", null, "result-summary");
  [
    [a.survivors.length, "surviving histories"],
    [a.equivalence_classes.length, "prediction classes"],
    [r.histories.length, "declared histories"],
  ].forEach(([n, label]) =>
    summary.append(
      append(
        element("div", null, "metric"),
        element("strong", n),
        element("span", label),
      ),
    ),
  );
  summary.append(
    element(
      "p",
      r.complete
        ? "✓ Complete within the declared finite space"
        : "Partial conflict search · completion not established",
      "completion" + (r.complete ? "" : " incomplete"),
    ),
  );
  box.append(summary);
  if (!a.survivors.length) {
    box.append(
      heading(
        "Minimal conflicting evidence",
        `${a.subsets_examined} / ${a.subset_space} subsets examined`,
      ),
    );
    box.append(
      element(
        "p",
        "No declared history satisfies all selected observations. Each set below is inconsistent; deleting any one of its observations makes that set satisfiable.",
        "footnote",
      ),
    );
    const list = element("ul", null, "conflict-list");
    a.minimal_conflicts.forEach((core) =>
      list.append(
        append(
          element("li"),
          element("span", core.map((i) => r.axes[i].label).join(" + ")),
          element(
            "small",
            "Minimal by inclusion within the selected hypothesis and candidate space",
          ),
        ),
      ),
    );
    box.append(list);
    if (!a.conflicts_complete)
      box.append(
        element(
          "p",
          "The subset budget was exhausted. This list may omit other minimal conflicts.",
          "source-note",
        ),
      );
  } else {
    box.append(
      heading(
        "Surviving reconstructions",
        "Open a history to inspect its derivations",
      ),
    );
    a.survivors.forEach((id) => {
      const h = by.get(id),
        d = element("details", null, "candidate");
      d.dataset.history = id;
      append(
        d,
        append(
          element("summary"),
          element("span", "*" + form(h.protoform), "proto"),
          element("span", h.analysis_id, "candidate-id"),
        ),
      );
      d.addEventListener("toggle", () => {
        if (!d.open || d.dataset.loaded) return;
        d.dataset.loaded = "true";
        const traces = element("div", null, "derivations");
        h.certificates.forEach((c, i) =>
          traces.append(certificateView(c, r.axes[i].label)),
        );
        traces.append(element("p", h.source_scope, "footnote"));
        d.append(traces);
      });
      box.append(d);
    });
    box.append(
      heading(
        "Observational equivalence",
        "Hypothesis identities are retained",
      ),
    );
    a.equivalence_classes.forEach((group, i) => {
      const row = element("div", null, "equivalence-row");
      append(
        row,
        element("b", `Class ${i + 1} · ${group.histories.length} histories`),
        element(
          "div",
          group.histories
            .map(
              (id) =>
                "*" +
                form(by.get(id).protoform) +
                " [" +
                by.get(id).analysis_id +
                "]",
            )
            .join("; "),
        ),
      );
      row.append(
        element(
          "div",
          r.selected.length
            ? "Same prediction on: " + r.selected.join(", ")
            : "No observations selected: all declared histories are equivalent on the empty observation set.",
        ),
      );
      box.append(row);
    });
    box.append(
      heading(
        "Discriminating predictions",
        "Withheld observations & unobserved probes",
      ),
    );
    const probes = [...a.probes].sort(
      (l, r) => r.distinguished_pairs - l.distinguished_pairs,
    );
    if (!probes.length)
      box.append(
        element(
          "p",
          "All available observations are selected. Withhold one to examine its predicted outcomes.",
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
          element("span", r.axes[p.axis].label),
          element(
            "small",
            p.distinguished_pairs + " history pairs distinguished",
          ),
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
                    by.get(id).analysis_id +
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
            "This observation would not distinguish the surviving histories.",
            "footnote",
          ),
        );
      box.append(d);
    });
    box.append(
      element(
        "p",
        "Pair counts compare the declared histories. They are not probabilities, evidence weights or a measure of historical plausibility.",
        "footnote",
      ),
    );
  }
  box.append(
    rawDetails(
      {
        axes: r.axes,
        selected: r.selected,
        matrix: r.matrix,
        analysis: r.analysis,
      },
      "Evidence matrix & completeness record",
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

$("collection").addEventListener("change", fillCases);
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
