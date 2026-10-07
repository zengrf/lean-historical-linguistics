/* Private research workspace. Project text is always inserted as text, never HTML. */
(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const copy = (value) => structuredClone(value);
  const app = {
    project: null,
    doc: null,
    dirty: false,
    token: "",
    edits: 0,
    selected: new Set(),
    hypotheses: new Set(),
    daughters: new Set(),
    undo: [],
    redo: [],
    gridPage: 0,
    job: null,
    result: null,
    page: null,
    saving: null,
    reading: null,
  };
  const formText = (form) =>
    form === null
      ? ""
      : form.length
        ? form.map((s) => (s === null ? "?" : s)).join(" ")
        : "∅";
  const key = (entry, language) => JSON.stringify([entry, language]);
  const spec = () => app.doc.request;
  const el = (tag, text, attrs = {}) => {
    const node = document.createElement(tag);
    if (text !== null && text !== undefined) node.textContent = text;
    for (const [name, value] of Object.entries(attrs))
      node.setAttribute(name, value);
    return node;
  };
  const option = (value, label) => el("option", label, { value });
  const readableDate = (stamp) => new Date(stamp).toLocaleString();
  const countText = (count) =>
    String(count).length <= 24
      ? String(count)
      : `${String(count).slice(0, 12)}… (${String(count).length} digits; exact count in download)`;
  function tell(message, error = false) {
    $("ws-message").textContent = message;
    $("ws-message").classList.toggle("error", error);
    const dialog = document.querySelector("dialog[open]");
    if (dialog) {
      let status = dialog.querySelector(".dialog-status");
      if (!status) {
        status = el("p", "", { role: "status", class: "dialog-status" });
        dialog.append(status);
      }
      status.textContent = message;
    }
  }
  function action(fn) {
    return async (event) => {
      event?.preventDefault();
      try {
        await fn(event);
      } catch (error) {
        tell(error.message, true);
      }
    };
  }
  const on = (id, event, fn) => $(id).addEventListener(event, action(fn));
  const button = (text, fn, attrs = {}) => {
    const node = el("button", text, { type: "button", ...attrs });
    node.addEventListener("click", action(fn));
    return node;
  };
  async function api(path, body) {
    const response = await fetch(
      "/api/workspace/" + path,
      body === undefined
        ? {}
        : {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "X-Workspace-Token": app.token,
            },
            body: JSON.stringify(body),
          },
    );
    const result = await response.json();
    if (!response.ok)
      throw new Error(result.error || `Request failed (${response.status})`);
    return result;
  }
  function parseForm(text) {
    const tokens = text.trim().split(/\s+/u).filter(Boolean);
    if (!tokens.length) return null;
    if (tokens.length === 1 && tokens[0] === "∅") return [];
    if (tokens.includes("∅"))
      throw new Error(
        "∅ must occupy the whole cell. Use ? for one unknown segment.",
      );
    return tokens.map((s) => (s === "?" ? null : s));
  }
  function validateAlignment(text, form) {
    if (!text.trim()) return;
    const tokens = text
      .trim()
      .split(/\s+/u)
      .filter((s) => s !== "-")
      .map((s) => (s === "?" ? null : s));
    if (form === null || JSON.stringify(tokens) !== JSON.stringify(form))
      throw new Error(
        "Removing alignment gaps must recover the comparison segments exactly.",
      );
  }
  function needProject() {
    if (!app.doc) throw new Error("Create or import a project first.");
  }
  const snapshot = () => ({ doc: copy(app.doc), title: app.title });
  function saveState() {
    $("ws-save-state").textContent = !app.project
      ? "No project loaded"
      : app.dirty
        ? "Unsaved changes · draft in this browser"
        : `Saved revision ${app.project.revision}`;
    $("ws-undo").disabled = !app.undo.length;
    $("ws-redo").disabled = !app.redo.length;
    $("ws-selected-count").textContent =
      `${app.selected.size} cognate sets selected from the wordlist.`;
    if (app.job && app.result)
      $("ws-result-provenance").textContent =
        `Checked revision ${app.job.revision} · ${app.job.settings.entries.length} sets · daughters ${app.job.settings.languages.join(", ")}. ${app.job.revision !== app.project.revision || app.dirty ? "The project has unsaved edits or a newer revision. " : ""}New selections apply to the next run. The certificate retains the exact input and engine hash.`;
  }
  const draftKey = (id) => "comparative-draft-" + id;
  function retainDraft() {
    if (!app.project || !app.dirty) return;
    try {
      localStorage.setItem(
        draftKey(app.project.id),
        JSON.stringify({ revision: app.project.revision, ...snapshot() }),
      );
    } catch (_) {
      $("ws-save-state").textContent =
        "Unsaved · browser draft storage is full";
      tell(
        "The browser could not retain this draft. Save a revision or download the complete project before leaving.",
        true,
      );
    }
  }
  function edit(change) {
    needProject();
    app.undo.push(snapshot());
    while (
      app.undo.length > 1 &&
      (app.undo.length > 30 || JSON.stringify(app.undo).length > 16_000_000)
    )
      app.undo.shift();
    app.redo = [];
    change();
    app.dirty = true;
    app.edits++;
    saveState();
    retainDraft();
  }
  function restoreSnapshot(value) {
    app.doc = copy(value.doc);
    app.title = value.title;
    $("ws-title").value = value.title;
    app.dirty = true;
    app.edits++;
    render();
    retainDraft();
  }
  function safeSwitch() {
    return (
      !app.dirty ||
      window.confirm(
        "This project has unsaved edits. Its browser draft will be retained. Switch projects?",
      )
    );
  }
  async function projects() {
    const result = await api("projects");
    $("ws-project").replaceChildren(
      option("", "Choose a project"),
      ...result.projects.map((p) => option(p.id, p.title)),
    );
    $("ws-project").value = app.project?.id || "";
    return result.projects;
  }
  async function loadProject(project) {
    app.project = project;
    app.title = project.title;
    app.doc = copy(project.document);
    app.dirty = false;
    app.edits++;
    app.undo = [];
    app.redo = [];
    app.job = null;
    app.result = null;
    app.resultRequest = null;
    app.page = null;
    app.gridPage = 0;
    app.selected = new Set(spec().entries.map((r) => r.id));
    app.hypotheses = new Set(spec().analyses.map((m) => m.id));
    app.daughters = new Set(spec().languages.map((l) => l.id));
    $("ws-title").value = project.title;
    $("ws-filter").value = "";
    $("ws-result").hidden = true;
    $("ws-no-results").hidden = false;
    $("ws-jobs").replaceChildren();
    $("ws-correspondence-output").replaceChildren();
    render();
    await projects();
    await refreshJobs();
    let draft;
    try {
      draft = JSON.parse(localStorage.getItem(draftKey(project.id)));
    } catch (_) {
      draft = null;
    }
    app.recovery = draft;
    $("ws-recovery").hidden = !draft;
    if (draft)
      $("ws-recovery").querySelector("span").textContent =
        `A browser draft based on revision ${draft.revision} is available. The saved project is at revision ${project.revision}.`;
    tell(`Opened “${project.title}”, revision ${project.revision}.`);
  }
  async function saveProject() {
    needProject();
    if (!document.querySelector("dialog[open]")) document.activeElement?.blur();
    if (document.querySelector('#ws-grid [aria-invalid="true"]'))
      throw new Error(
        "Correct the invalid comparison cell before saving; its previous value remains in the draft.",
      );
    if (app.saving) return app.saving;
    if (!app.dirty) return app.project;
    const id = app.project.id,
      edits = app.edits;
    app.saving = (async () => {
      const saved = await api("save", {
        id,
        revision: app.project.revision,
        title: $("ws-title").value,
        document: copy(app.doc),
        message: "Saved wordlist, readings and reconstruction assumptions",
      });
      if (app.project.id === id) {
        app.project = saved;
        if (app.edits === edits) {
          app.dirty = false;
          localStorage.removeItem(draftKey(id));
        } else retainDraft();
        saveState();
        await projects();
        tell(`Saved revision ${saved.revision}.`);
      }
      return saved;
    })();
    try {
      return await app.saving;
    } finally {
      app.saving = null;
    }
  }
  function view(name, focus = false) {
    for (const tab of document.querySelectorAll("[data-view]")) {
      const active = tab.dataset.view === name;
      tab.setAttribute("aria-selected", String(active));
      tab.tabIndex = active ? 0 : -1;
      $("ws-" + tab.dataset.view).hidden = !active;
      if (active && focus) tab.focus();
    }
    if (name === "history" && app.project)
      refreshHistory().catch((error) => tell(error.message, true));
  }
  function render() {
    if (!app.doc) return;
    $("ws-description").textContent = spec().description;
    $("ws-counts").textContent =
      `${spec().entries.length} cognate sets · ${spec().languages.length} varieties`;
    $("ws-notes").value = app.doc.project_notes;
    renderGrid();
    renderRules();
    renderConstraints();
    saveState();
  }
  function renderGrid() {
    const head = el("tr");
    head.append(
      el("th", "Select"),
      el("th", "Set"),
      el("th", "Gloss / concept"),
    );
    for (const lang of spec().languages) {
      const th = el("th");
      th.append(button(lang.label, () => openLanguage(lang.id)));
      head.append(th);
    }
    $("ws-grid").tHead.replaceChildren(head);
    const term = $("ws-filter").value.toLocaleLowerCase();
    const rows = spec().entries.filter((r) =>
      [r.id, r.meaning, ...r.reflexes.map((x) => formText(x.form))]
        .join(" ")
        .toLocaleLowerCase()
        .includes(term),
    );
    app.gridPage = Math.max(
      0,
      Math.min(app.gridPage, Math.ceil(rows.length / 50) - 1),
    );
    const body = $("ws-grid").tBodies[0];
    body.replaceChildren();
    for (const [rowNumber, row] of rows
      .slice(app.gridPage * 50, app.gridPage * 50 + 50)
      .entries()) {
      const tr = el("tr", null, { "data-entry": row.id });
      const select = el("input", null, {
        type: "checkbox",
        "aria-label": `Select ${row.meaning}`,
      });
      select.checked = app.selected.has(row.id);
      select.addEventListener("change", () => {
        select.checked ? app.selected.add(row.id) : app.selected.delete(row.id);
        saveState();
      });
      const td = el("td");
      td.append(select);
      tr.append(td);
      const id = el("td", null, { class: "set-id" });
      id.append(button(row.id, () => openRow(row.id)));
      tr.append(id);
      const gloss = el("td", row.meaning, { class: "gloss" });
      tr.append(gloss);
      for (const [column, language] of spec().languages.entries()) {
        const reflex = row.reflexes.find((r) => r.language_id === language.id);
        if (!reflex) continue;
        const cell = el("td"),
          group = el("div", null, {
            class: "form-cell" + (reflex.form === null ? " missing" : ""),
          });
        const input = el("input", null, {
          type: "text",
          spellcheck: "false",
          "aria-label": `${row.meaning}, ${language.label}`,
          "data-grid-row": rowNumber,
          "data-grid-column": column,
        });
        input.value = formText(reflex.form);
        input.placeholder = "—";
        input.addEventListener(
          "change",
          action(() => {
            let value;
            try {
              value = parseForm(input.value);
            } catch (error) {
              input.setAttribute("aria-invalid", "true");
              input.setCustomValidity(error.message);
              throw error;
            }
            input.removeAttribute("aria-invalid");
            input.setCustomValidity("");
            edit(() => {
              reflex.form = value;
              const note = app.doc.annotations[key(row.id, language.id)];
              if (note?.alignment) {
                note.note =
                  (note.note || "") +
                  `\nPrevious alignment before segment edit: ${note.alignment}`;
                note.alignment = "";
              }
            });
            group.classList.toggle("missing", value === null);
          }),
        );
        input.addEventListener("keydown", (event) => {
          if (event.key === "Escape") {
            input.value = formText(reflex.form);
            input.removeAttribute("aria-invalid");
            input.setCustomValidity("");
            input.blur();
          }
          const movement =
            event.key === "Enter"
              ? [event.shiftKey ? -1 : 1, 0]
              : event.ctrlKey
                ? {
                    ArrowDown: [1, 0],
                    ArrowUp: [-1, 0],
                    ArrowLeft: [0, -1],
                    ArrowRight: [0, 1],
                  }[event.key]
                : null;
          if (movement) {
            event.preventDefault();
            const next = document.querySelector(
              `[data-grid-row="${rowNumber + movement[0]}"][data-grid-column="${column + movement[1]}"]`,
            );
            if (next) next.focus();
            else input.blur();
          }
        });
        group.append(
          input,
          button("⋯", () => openReading(row.id, language.id), {
            "aria-label": `Reading and sources: ${row.meaning}, ${language.label}`,
          }),
        );
        cell.append(group);
        tr.append(cell);
      }
      body.append(tr);
    }
    $("ws-grid-status").textContent = rows.length
      ? `${app.gridPage * 50 + 1}–${Math.min(rows.length, app.gridPage * 50 + 50)} of ${rows.length} matching sets`
      : "No matching cognate sets";
    $("ws-grid-prev").disabled = app.gridPage === 0;
    $("ws-grid-next").disabled = (app.gridPage + 1) * 50 >= rows.length;
  }
  const classText = (values) =>
    values.length === 1 ? values[0] : `[${values.join(" ")}]`;
  function formatRule(r) {
    const side = (tests) =>
      tests
        .map((t) => (t === "*" ? "." : t === "+" ? "+" : classText(t)))
        .join(" ");
    let text = `${classText(r.target)} > ${r.replacement ?? "∅"}`;
    if (r.left.length || r.right.length || r.left_edge || r.right_edge)
      text += ` / ${(r.left_edge ? "# " : "") + side([...r.left].reverse())} _ ${side(r.right) + (r.right_edge ? " #" : "")}`;
    return (
      text.trim() +
      (r.direction === "right-to-left" ? "; rtl" : "") +
      (r.mode === "feeding" ? "; feeding" : "")
    );
  }
  const selectedModel = () =>
    spec().analyses.find((m) => m.id === $("ws-rule-model").value);
  const selectedBranch = () =>
    selectedModel()?.branches.find(
      (b) => b.language_id === $("ws-rule-language").value,
    );
  function fillSelect(id, choices, old = $(id).value) {
    $(id).replaceChildren(...choices);
    if ([...$(id).options].some((o) => o.value === old)) $(id).value = old;
  }
  function renderRules() {
    fillSelect(
      "ws-rule-model",
      spec().analyses.map((m) => option(m.id, m.id)),
    );
    fillSelect(
      "ws-rule-language",
      spec().languages.map((l) => option(l.id, l.label)),
    );
    $("ws-classes").value = app.doc.classes;
    showRules();
  }
  function showRules() {
    const model = selectedModel(),
      branch = selectedBranch();
    $("ws-model-description").value = model?.description || "";
    $("ws-model-source").value = model?.source_ref || "";
    const draft =
      app.doc.annotations._rule_drafts?.[key(model?.id, branch?.language_id)];
    $("ws-rule-text").value =
      draft ??
      (branch?.package.laws.map((law) => formatRule(law.rule)).join("\n") ||
        "");
    $("ws-rule-status").textContent =
      draft === undefined ? "" : "Draft · apply before enumeration";
  }
  function checklist(id, values, selected) {
    $(id).replaceChildren(
      ...values.map(([value, title]) => {
        const label = el("label", null, { class: "check-option" });
        const input = el("input", null, { type: "checkbox", value });
        input.checked = selected.has(value);
        input.addEventListener("change", () =>
          input.checked ? selected.add(value) : selected.delete(value),
        );
        label.append(input, el("span", title));
        return label;
      }),
    );
  }
  function renderConstraints() {
    checklist(
      "ws-hypotheses",
      spec().analyses.map((m) => [m.id, `${m.id} · ${m.description}`]),
      app.hypotheses,
    );
    checklist(
      "ws-daughters",
      spec().languages.map((l) => [l.id, l.label]),
      app.daughters,
    );
    const draft = app.doc.annotations._constraint_draft;
    $("ws-alphabet").value =
      draft?.alphabet ?? spec().proto_inventory.join(" ");
    $("ws-min").value = draft?.minimum ?? spec().min_length;
    $("ws-max").value = draft?.maximum ?? spec().max_length;
    $("ws-shapes").value =
      draft?.shapes ??
      (spec()
        .phonotactics?.map((shape) =>
          shape.length ? shape.map(classText).join(" ") : "∅",
        )
        .join(" | ") ||
        "");
  }
  function openReading(entryId, languageId) {
    const row = spec().entries.find((r) => r.id === entryId),
      reflex = row.reflexes.find((r) => r.language_id === languageId);
    const note = copy(app.doc.annotations[key(entryId, languageId)] || {});
    app.reading = {
      entryId,
      languageId,
      note,
      alternatives: note.alternatives || [],
    };
    $("ws-reading-title").textContent =
      `${row.meaning} · ${spec().languages.find((l) => l.id === languageId).label}`;
    readingFields({ ...note, form: reflex.form, source: reflex.source_ref });
    $("ws-segment-options").replaceChildren();
    renderAlternatives();
    openDialog("ws-reading-dialog");
  }
  function readingFields(reading) {
    for (const field of [
      "original",
      "source",
      "witness",
      "locator",
      "certainty",
      "alignment",
      "note",
    ])
      $("ws-reading-" + field).value =
        reading[field] || (field === "certainty" ? "unassessed" : "");
    $("ws-reading-form").value = formText(reading.form ?? null);
  }
  function readFields() {
    const reading = { form: parseForm($("ws-reading-form").value) };
    for (const field of [
      "original",
      "source",
      "witness",
      "locator",
      "certainty",
      "alignment",
      "note",
    ])
      reading[field] = $("ws-reading-" + field).value;
    validateAlignment(reading.alignment, reading.form);
    if (!reading.source.trim())
      throw new Error("Record a source reference for the selected reading.");
    return reading;
  }
  function renderAlternatives() {
    $("ws-alternatives").replaceChildren(
      ...app.reading.alternatives.map((reading, index) => {
        const box = el("div", null, { class: "alternative-reading" });
        for (const [field, label] of [
          ["original", "Reading as printed"],
          ["form", "Comparison segments"],
          ["source", "Source reference"],
          ["witness", "Witness / edition"],
          ["locator", "Locator"],
          ["note", "Editorial note"],
        ]) {
          const wrap = el("label", label),
            input = el("input", null, {
              "aria-label": `Alternative ${index + 1}: ${label}`,
            });
          input.value =
            field === "form"
              ? formText(reading.form ?? null)
              : reading[field] || "";
          input.addEventListener(
            "change",
            action(() => {
              reading[field] =
                field === "form" ? parseForm(input.value) : input.value;
            }),
          );
          wrap.append(input);
          box.append(wrap);
        }
        box.append(
          button("Use for comparison", () => {
            const previous = readFields();
            readingFields(reading);
            app.reading.alternatives[index] = previous;
            renderAlternatives();
          }),
          button("Remove alternative", () => {
            app.reading.alternatives.splice(index, 1);
            renderAlternatives();
          }),
        );
        return box;
      }),
    );
  }
  function openDialog(id) {
    $(id).querySelector(".dialog-status")?.remove();
    $(id).showModal();
  }
  function openRow(id = null) {
    app.rowId = id;
    const row = spec().entries.find((r) => r.id === id);
    $("ws-row-meaning").value = row?.meaning || "";
    $("ws-row-reference").value =
      id && app.doc.annotations._references?.[id]
        ? formText(app.doc.annotations._references[id])
        : "";
    $("ws-row-split").value = app.doc.annotations._splits?.[id] || "unassigned";
    openDialog("ws-row-dialog");
  }
  function openLanguage(id = null) {
    app.languageId = id;
    $("ws-language-name").value =
      spec().languages.find((l) => l.id === id)?.label || "";
    $("ws-language-note").value = app.doc.annotations._languages?.[id] || "";
    openDialog("ws-language-dialog");
  }
  const newId = (prefix) => prefix + "-" + crypto.randomUUID().slice(0, 8);
  function emptyPackage(id) {
    return {
      id,
      version: "1.0.0",
      description: "Working branch: enter justified sound changes",
      initial_stage: "stem",
      final_stage: "stem",
      inventory: [...spec().proto_inventory],
      laws: [],
    };
  }
  async function refreshJobs() {
    if (!app.project) return;
    const projectId = app.project.id,
      data = await api("jobs?id=" + projectId);
    if (app.project.id !== projectId) return;
    $("ws-jobs").replaceChildren(
      ...data.jobs.map((job) => {
        const row = el("div", null, {
          class: "analysis-job",
          "data-job": job.id,
        });
        const label = el(
          "span",
          `Revision ${job.revision} · ${readableDate(job.created)}`,
        );
        label.append(
          el(
            "small",
            `${job.settings.entries.length} sets · ${job.settings.analyses.length} hypotheses${job.error ? " · " + job.error : ""}`,
          ),
        );
        row.append(label, el("span", job.status, { class: "job-status" }));
        if (["running", "queued"].includes(job.status))
          row.append(
            button("Cancel", async () => {
              await api("cancel", { id: job.id });
              await refreshJobs();
            }),
          );
        if (job.status === "complete")
          row.append(button("Open result", () => openResult(job)));
        return row;
      }),
    );
    if (!data.jobs.length)
      $("ws-jobs").append(
        el("p", "No analyses saved for this project yet.", { class: "help" }),
      );
    if (
      app.awaiting &&
      data.jobs.some(
        (j) =>
          j.id === app.awaiting && !["queued", "running"].includes(j.status),
      )
    ) {
      const finished = data.jobs.find((j) => j.id === app.awaiting);
      app.awaiting = null;
      if (finished.status === "complete") await openResult(finished);
      else tell(`Analysis ${finished.status}: ${finished.error}`, true);
    }
  }
  async function openResult(job) {
    const projectId = app.project.id;
    const requestId = Symbol();
    app.resultRequest = requestId;
    const result = await api("result?id=" + job.id);
    if (app.project.id !== projectId || app.resultRequest !== requestId) return;
    app.job = job;
    app.result = result;
    app.page = null;
    $("ws-result").hidden = false;
    $("ws-no-results").hidden = true;
    $("ws-result-provenance").textContent =
      `Checked analysis of revision ${job.revision}. ${job.revision !== app.project.revision || app.dirty ? "The current draft or revision differs from these results. " : ""}The certificate records the exact input and engine hash.`;
    $("ws-result-total").textContent =
      `${countText(result.summary.lexicon_count)} allowed whole-wordlist reconstructions (hypothesis counted separately)`;
    $("ws-model-outcomes").replaceChildren(
      ...result.summary.models.map((model) => {
        const box = el("div", null, { class: "model-outcome" });
        box.append(
          el("strong", model.analysis_id),
          el(
            "p",
            `${countText(model.lexicon_count)} complete wordlists; ${model.entries.filter((r) => r.count === "0").length} incompatible cognate sets.`,
          ),
        );
        if (model.lexicon_count === "0")
          box.append(
            el(
              "p",
              "Incompatible sets: " +
                model.entries
                  .filter((r) => r.count === "0")
                  .map((r) => r.entry_id)
                  .join(", "),
            ),
          );
        return box;
      }),
    );
    fillSelect(
      "ws-result-model",
      result.summary.models.map((m) => option(m.analysis_id, m.analysis_id)),
    );
    fillSelect(
      "ws-result-entry",
      result.request.entries.map((r) => option(r.id, `${r.id} · ${r.meaning}`)),
    );
    $("ws-result-number").value = "1";
    saveState();
    view("results");
    await showPage();
    const evaluation = await api("evaluation?id=" + job.id);
    if (app.job?.id !== job.id) return;
    $("ws-evaluation").replaceChildren();
    if (evaluation.totals.length) {
      $("ws-evaluation").append(
        el("h3", "Reference-form evaluation"),
        el("p", evaluation.protocol, { class: "help" }),
      );
      $("ws-evaluation").append(
        simpleTable(
          [
            "Hypothesis",
            "Partition",
            "References",
            "In scope",
            "Recovered",
            "Unique reference",
          ],
          evaluation.totals.map((r) => [
            r.analysis_id,
            r.partition,
            r.references,
            r.in_scope,
            r.recovered,
            r.unique_reference,
          ]),
        ),
      );
    }
  }
  function simpleTable(headings, rows) {
    const table = el("table", null, { class: "simple-table" }),
      head = el("thead"),
      header = el("tr"),
      body = el("tbody");
    header.append(...headings.map((text) => el("th", text, { scope: "col" })));
    head.append(header);
    for (const values of rows) {
      const row = el("tr");
      row.append(...values.map((text) => el("td", String(text))));
      body.append(row);
    }
    table.append(head, body);
    return table;
  }
  function derivation(item) {
    const request = app.result.request,
      proposal = item.proposal;
    const box = el("details", null, { class: "candidate" });
    box.append(
      el(
        "summary",
        `*${formText(proposal.word)} · ${request.entries.find((r) => r.id === proposal.entry_id)?.meaning || proposal.entry_id}`,
      ),
    );
    const model = request.analyses.find((m) => m.id === proposal.analysis_id);
    for (const [i, certificate] of item.certificates.entries()) {
      const branch = model.branches[i],
        language = request.languages.find((l) => l.id === branch.language_id);
      const detail = el("details");
      detail.append(el("summary", language.label + " · checked derivation"));
      const traces = certificate.steps || certificate.traces || [];
      detail.append(
        el(
          "p",
          `*${formText(certificate.input)} → ${formText(certificate.output)}`,
        ),
      );
      if (traces.length)
        detail.append(
          simpleTable(
            ["Sound change", "Input", "Output"],
            traces.map((step, n) => [
              formatRule(branch.package.laws[n].rule),
              formText(n ? traces[n - 1].output : certificate.input),
              formText(step.output),
            ]),
          ),
        );
      else if (branch.package.laws.length)
        detail.append(
          el(
            "p",
            branch.package.laws.map((law) => formatRule(law.rule)).join("; "),
          ),
        );
      box.append(detail);
    }
    return box;
  }
  async function showPage(offset = null) {
    if (!app.job) return;
    const startText = $("ws-result-number").value.trim();
    if (!/^[1-9][0-9]*$/u.test(startText) || startText.length > 200000)
      throw new Error("Enter a positive whole reconstruction number.");
    const start = offset ?? (BigInt(startText) - 1n).toString();
    const words = $("ws-result-view").value === "words";
    $("ws-result-entry").disabled = !words;
    $("ws-page-status").textContent = "Checking the displayed derivations…";
    const jobId = app.job.id,
      pageId = Symbol();
    app.pageRequest = pageId;
    const data = await api("page", {
      id: jobId,
      analysis_id: $("ws-result-model").value,
      entry_id: words ? $("ws-result-entry").value : null,
      offset: start,
      limit: words ? 20 : 1,
    });
    if (app.pageRequest !== pageId || app.job?.id !== jobId) return;
    app.page = data;
    $("ws-result-number").value = (BigInt(data.offset) + 1n).toString();
    $("ws-page-status").textContent = data.items.length
      ? `Showing ${countText(BigInt(data.offset) + 1n)}–${countText(BigInt(data.offset) + BigInt(data.items.length))} of ${countText(data.count)}. Every displayed form passed native forward checking.`
      : data.count === "0"
        ? "No reconstruction satisfies these assumptions for this selection."
        : `No item at this position. This selection has ${countText(data.count)} reconstructions.`;
    $("ws-candidates").replaceChildren();
    if (
      words &&
      data.count !== "0" &&
      app.result.summary.models.find(
        (m) => m.analysis_id === $("ws-result-model").value,
      )?.lexicon_count === "0"
    )
      $("ws-page-status").textContent +=
        " These local protoforms cannot form a complete wordlist under this hypothesis because another selected cognate set is incompatible.";
    for (const item of data.items) {
      if (data.kind === "words") $("ws-candidates").append(derivation(item));
      else {
        const section = el("section");
        section.append(el("h3", `Wordlist ${BigInt(item.index) + 1n}`));
        section.append(...item.derivations.map(derivation));
        $("ws-candidates").append(section);
      }
    }
    $("ws-result-prev").disabled = BigInt(data.offset) === 0n;
    $("ws-result-next").disabled = !data.has_more;
  }
  async function refreshHistory() {
    if (!app.project) return;
    const id = app.project.id,
      data = await api("history?id=" + id);
    if (app.project.id !== id) return;
    $("ws-history-list").replaceChildren(
      ...data.revisions.map((revision) => {
        const row = el("div", null, { class: "revision" }),
          label = el(
            "p",
            `Revision ${revision.revision} · ${revision.message}`,
          );
        label.append(el("br"), el("small", readableDate(revision.created)));
        row.append(label);
        if (revision.revision !== app.project.revision)
          row.append(
            button("Restore as new revision", async () => {
              if (app.dirty) await saveProject();
              await loadProject(
                await api("restore", {
                  id,
                  revision: app.project.revision,
                  restore_revision: revision.revision,
                }),
              );
              await refreshHistory();
            }),
          );
        return row;
      }),
    );
  }
  function downloadBlob(blob, name) {
    const url = URL.createObjectURL(blob),
      link = el("a", "", { href: url, download: name });
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 30000);
  }
  async function download(path, name) {
    const response = await fetch("/api/workspace/" + path);
    if (!response.ok)
      throw new Error((await response.json()).error || "Export failed");
    downloadBlob(await response.blob(), name);
  }
  // Project and editing commands.
  on("ws-new", "click", () => openDialog("ws-create-dialog"));
  on("ws-import", "click", () => openDialog("ws-import-dialog"));
  on("ws-create", "click", async () => {
    if (!safeSwitch()) return;
    const example = await api(
      "example?key=" + encodeURIComponent($("ws-new-example").value),
    );
    const project = await api("create", {
      title: $("ws-new-title").value,
      document: example.document,
    });
    $("ws-create-dialog").close();
    await loadProject(project);
    view("wordlist");
  });
  on("ws-project", "change", async () => {
    const id = $("ws-project").value;
    if (!id || !safeSwitch()) {
      $("ws-project").value = app.project?.id || "";
      return;
    }
    retainDraft();
    await loadProject(await api("project?id=" + id));
  });
  on("ws-save", "click", saveProject);
  on("ws-title", "change", () =>
    edit(() => {
      app.title = $("ws-title").value;
    }),
  );
  on("ws-notes", "change", () =>
    edit(() => {
      app.doc.project_notes = $("ws-notes").value;
    }),
  );
  on("ws-undo", "click", () => {
    if (app.undo.length) {
      app.redo.push(snapshot());
      restoreSnapshot(app.undo.pop());
    }
  });
  on("ws-redo", "click", () => {
    if (app.redo.length) {
      app.undo.push(snapshot());
      restoreSnapshot(app.redo.pop());
    }
  });
  on("ws-recover", "click", () => {
    if (!app.recovery) return;
    if (app.recovery.revision !== app.project.revision)
      throw new Error(
        "This draft is based on an older revision. Download the draft below, then import it as a separate project to compare changes.",
      );
    restoreSnapshot(app.recovery);
    $("ws-recovery").hidden = true;
    tell("Recovered the browser draft. Save it to create a durable revision.");
  });
  $("ws-recovery").append(
    button("Download draft", () => {
      if (app.recovery)
        downloadBlob(
          new Blob([JSON.stringify(app.recovery.doc, null, 2)], {
            type: "application/json",
          }),
          "recovered-project.json",
        );
    }),
  );
  on("ws-discard-draft", "click", () => {
    localStorage.removeItem(draftKey(app.project.id));
    app.recovery = null;
    $("ws-recovery").hidden = true;
  });
  on("ws-filter", "input", () => {
    needProject();
    app.gridPage = 0;
    renderGrid();
  });
  on("ws-grid-prev", "click", () => {
    app.gridPage--;
    renderGrid();
  });
  on("ws-grid-next", "click", () => {
    app.gridPage++;
    renderGrid();
  });
  on("ws-select-all", "click", () => {
    needProject();
    app.selected = new Set(spec().entries.map((r) => r.id));
    renderGrid();
    saveState();
  });
  on("ws-select-none", "click", () => {
    app.selected.clear();
    if (app.doc) renderGrid();
    saveState();
  });
  on("ws-add-row", "click", () => {
    needProject();
    openRow();
  });
  on("ws-add-language", "click", () => {
    needProject();
    openLanguage();
  });
  on("ws-save-row", "click", () => {
    const meaning = $("ws-row-meaning").value.trim(),
      reference = parseForm($("ws-row-reference").value);
    if (!meaning) throw new Error("Enter a gloss or concept.");
    if (reference?.some((s) => s === null))
      throw new Error(
        "A reference reconstruction must specify known segments.",
      );
    edit(() => {
      let row = spec().entries.find((r) => r.id === app.rowId);
      if (!row) {
        row = {
          id: newId("set"),
          meaning,
          reflexes: spec().languages.map((l) => ({
            language_id: l.id,
            form: null,
            source_ref: "user:unassessed",
          })),
        };
        spec().entries.push(row);
        app.selected.add(row.id);
      }
      row.meaning = meaning;
      app.doc.annotations._references ||= {};
      app.doc.annotations._splits ||= {};
      if (reference !== null)
        app.doc.annotations._references[row.id] = reference;
      else delete app.doc.annotations._references[row.id];
      app.doc.annotations._splits[row.id] = $("ws-row-split").value;
    });
    $("ws-row-dialog").close();
    render();
  });
  on("ws-save-language", "click", () => {
    const name = $("ws-language-name").value.trim();
    if (!name) throw new Error("Enter a variety name.");
    edit(() => {
      let language = spec().languages.find((l) => l.id === app.languageId);
      if (!language) {
        language = { id: newId("variety"), label: name };
        spec().languages.push(language);
        app.daughters.add(language.id);
        for (const row of spec().entries)
          row.reflexes.push({
            language_id: language.id,
            form: null,
            source_ref: "user:unassessed",
          });
        for (const model of spec().analyses)
          model.branches.push({
            language_id: language.id,
            package: emptyPackage(model.id + "-" + language.id),
          });
      }
      language.label = name;
      app.doc.annotations._languages ||= {};
      app.doc.annotations._languages[language.id] = $("ws-language-note").value;
    });
    $("ws-language-dialog").close();
    render();
  });
  on("ws-save-reading", "click", () => {
    const reading = readFields(),
      { entryId, languageId } = app.reading;
    for (const alternative of app.reading.alternatives)
      validateAlignment(alternative.alignment || "", alternative.form ?? null);
    edit(() => {
      const reflex = spec()
        .entries.find((r) => r.id === entryId)
        .reflexes.find((r) => r.language_id === languageId);
      reflex.form = reading.form;
      reflex.source_ref = reading.source;
      app.doc.annotations[key(entryId, languageId)] = {
        ...app.reading.note,
        ...reading,
        alternatives: copy(app.reading.alternatives),
      };
    });
    $("ws-reading-dialog").close();
    renderGrid();
  });
  on("ws-add-reading", "click", () => {
    app.reading.alternatives.push({
      original: "",
      form: null,
      source: "",
      certainty: "unassessed",
    });
    renderAlternatives();
  });
  on("ws-suggest-segments", "click", async () => {
    const inventory = [
      ...new Set(
        spec().analyses.flatMap((m) =>
          m.branches.flatMap((b) => b.package.inventory),
        ),
      ),
    ];
    const result = await api("segment", {
      value: $("ws-reading-original").value,
      inventory,
    });
    $("ws-segment-options").replaceChildren(
      el(
        "p",
        result.options.length
          ? `${result.unique ? "One segmentation" : "Alternative segmentations"}${result.truncated ? " (first 16 shown)" : ""}. Select explicitly.`
          : "The supplied inventory cannot segment this exact reading. Enter a transcription without changing the source reading.",
      ),
    );
    for (const form of result.options)
      $("ws-segment-options").append(
        button(formText(form), () => {
          $("ws-reading-form").value = formText(form);
        }),
      );
  });
  on("ws-do-import", "click", async () => {
    if (!safeSwitch()) return;
    const file = $("ws-import-file").files[0],
      format = $("ws-import-format").value;
    let text = $("ws-import-text").value;
    if (file) {
      if (file.size > 11_000_000)
        throw new Error("Select a file smaller than 11 MB for browser import.");
      if (format === "cldf")
        text = await new Promise((resolve, reject) => {
          const reader = new FileReader();
          reader.onload = () => resolve(reader.result.split(",")[1]);
          reader.onerror = reject;
          reader.readAsDataURL(file);
        });
      else text = await file.text();
    }
    if (format === "cldf" && !file) throw new Error("Choose a CLDF ZIP file.");
    const imported = await api("import", {
      format,
      text,
      title: $("ws-import-title").value,
      source: $("ws-import-source").value,
    });
    const project = await api("create", {
      title: $("ws-import-title").value,
      document: imported.document,
    });
    $("ws-import-dialog").close();
    await loadProject(project);
    view("wordlist");
    tell("Imported the wordlist. " + imported.warnings.join(" "));
  });
  on("ws-export", "click", async () => {
    needProject();
    const format = $("ws-export-format").value;
    if (format === "project") {
      downloadBlob(
        new Blob([JSON.stringify(app.doc, null, 2) + "\n"], {
          type: "application/json",
        }),
        "comparative-project.json",
      );
      return;
    }
    const saved = await saveProject();
    await download(
      `export?format=${format}&id=${saved.id}`,
      `comparative-${format}.${format === "cldf" ? "zip" : format === "tei" ? "xml" : "tsv"}`,
    );
  });
  on("ws-rule-model", "change", showRules);
  on("ws-rule-language", "change", showRules);
  on("ws-model-description", "change", () =>
    edit(() => {
      selectedModel().description = $("ws-model-description").value;
    }),
  );
  on("ws-model-source", "change", () =>
    edit(() => {
      selectedModel().source_ref = $("ws-model-source").value;
    }),
  );
  on("ws-classes", "change", () =>
    edit(() => {
      app.doc.classes = $("ws-classes").value;
    }),
  );
  on("ws-rule-text", "input", () =>
    edit(() => {
      app.doc.annotations._rule_drafts ||= {};
      app.doc.annotations._rule_drafts[
        key(selectedModel().id, selectedBranch().language_id)
      ] = $("ws-rule-text").value;
      $("ws-rule-status").textContent = "Draft · apply before enumeration";
    }),
  );
  on("ws-apply-rules", "click", async () => {
    const id = app.project.id,
      edits = app.edits;
    const result = await api("notation", {
      request: spec(),
      analysis_id: selectedModel().id,
      language_id: selectedBranch().language_id,
      rules: $("ws-rule-text").value,
      classes: $("ws-classes").value,
      direction: "left-to-right",
      mode: "simultaneous",
    });
    if (app.project.id !== id || app.edits !== edits)
      throw new Error(
        "The draft changed while the rules were checked. Apply again to use the latest text.",
      );
    const draftId = key(selectedModel().id, selectedBranch().language_id);
    edit(() => {
      app.doc.request = result.request;
      app.doc.classes = $("ws-classes").value;
      if (app.doc.annotations._rule_drafts)
        delete app.doc.annotations._rule_drafts[draftId];
    });
    showRules();
    $("ws-rule-status").textContent = "Applied to the current draft";
    renderConstraints();
  });
  on("ws-duplicate-model", "click", () => {
    const model = copy(selectedModel());
    model.id = newId(model.id);
    model.description = "Alternative account: " + model.description;
    edit(() => {
      spec().analyses.push(model);
      app.hypotheses.add(model.id);
    });
    renderRules();
    $("ws-rule-model").value = model.id;
    showRules();
    renderConstraints();
  });
  for (const id of ["ws-alphabet", "ws-min", "ws-max", "ws-shapes"])
    on(id, "input", () =>
      edit(() => {
        app.doc.annotations._constraint_draft = {
          alphabet: $("ws-alphabet").value,
          minimum: $("ws-min").value,
          maximum: $("ws-max").value,
          shapes: $("ws-shapes").value,
        };
      }),
    );
  on("ws-apply-constraints", "click", async () => {
    const minimum = Number($("ws-min").value),
      maximum = Number($("ws-max").value),
      alphabet = $("ws-alphabet").value.trim().split(/\s+/u).filter(Boolean);
    if (
      !Number.isInteger(minimum) ||
      !Number.isInteger(maximum) ||
      minimum < 0 ||
      maximum < minimum ||
      maximum > 64
    )
      throw new Error(
        "Choose integer length bounds from 0 to 64, with maximum at least minimum.",
      );
    if (
      !alphabet.length ||
      alphabet.length > 64 ||
      new Set(alphabet).size !== alphabet.length
    )
      throw new Error("Choose 1–64 distinct proto-segments.");
    const id = app.project.id,
      edits = app.edits,
      result = await api("shapes", {
        text: $("ws-shapes").value,
        classes: app.doc.classes,
      });
    if (app.project.id !== id || app.edits !== edits)
      throw new Error(
        "The draft changed while shapes were parsed. Apply again.",
      );
    edit(() => {
      Object.assign(spec(), {
        min_length: minimum,
        max_length: maximum,
        proto_inventory: alphabet,
        phonotactics: result.phonotactics,
      });
      delete app.doc.annotations._constraint_draft;
      for (const m of spec().analyses)
        for (const b of m.branches)
          b.package.inventory = [
            ...new Set([...b.package.inventory, ...alphabet]),
          ];
    });
    renderConstraints();
    tell("Alphabet, length bounds and word shapes applied to the draft.");
  });
  on("ws-run", "click", async () => {
    needProject();
    if (
      Object.keys(app.doc.annotations._rule_drafts || {}).length ||
      app.doc.annotations._constraint_draft
    )
      throw new Error(
        "Apply the draft sound changes and reconstruction constraints before enumeration.",
      );
    if (!app.hypotheses.size || !app.daughters.size || !app.selected.size)
      throw new Error(
        "Select at least one hypothesis, daughter variety and cognate set.",
      );
    $("ws-run").disabled = true;
    try {
      const settings = {
        analyses: [...app.hypotheses],
        languages: [...app.daughters],
        entries: [...app.selected],
        node_budget: Number($("ws-nodes").value),
        time_limit: Number($("ws-seconds").value),
      };
      const saved = await saveProject(),
        job = await api("run", {
          id: saved.id,
          revision: saved.revision,
          settings,
        });
      app.awaiting = job.id;
      await refreshJobs();
      tell(
        `Analysis queued from saved revision ${saved.revision}. You can continue editing.`,
      );
    } finally {
      $("ws-run").disabled = false;
    }
  });
  on("ws-refresh-jobs", "click", refreshJobs);
  on("ws-show-result", "click", () => showPage());
  for (const id of ["ws-result-model", "ws-result-view", "ws-result-entry"])
    on(id, "change", async () => {
      $("ws-result-number").value = "1";
      await showPage();
    });
  on("ws-result-prev", "click", () =>
    showPage(
      (BigInt(app.page.offset) > 20n && app.page.kind === "words"
        ? BigInt(app.page.offset) - 20n
        : app.page.kind === "lexicons" && BigInt(app.page.offset) > 0n
          ? BigInt(app.page.offset) - 1n
          : 0n
      ).toString(),
    ),
  );
  on("ws-result-next", "click", () =>
    showPage(
      (BigInt(app.page.offset) + BigInt(app.page.items.length)).toString(),
    ),
  );
  on("ws-download-result", "click", () =>
    download(
      "export?format=result&id=" + app.job.id,
      "checked-reconstructions.json",
    ),
  );
  on("ws-refresh-history", "click", refreshHistory);
  on("ws-backup", "click", async () => {
    if (app.dirty) await saveProject();
    await download("backup", "comparative-workspace.zip");
    tell(
      "Downloaded a workspace backup. Restore into a new directory with workspace_backup.py restore.",
    );
  });
  on("ws-correspondences", "click", async () => {
    needProject();
    const result = await api("correspondences", { document: app.doc });
    $("ws-correspondence-output").replaceChildren(
      el(
        "p",
        `${result.columns.length} distinct supplied correspondence columns; ${result.skipped.length} sets lack two alignments of equal length.`,
      ),
    );
    if (result.columns.length)
      $("ws-correspondence-output").append(
        simpleTable(
          [...spec().languages.map((l) => l.label), "Occurrences"],
          result.columns.map((r) => [...r.segments, r.count]),
        ),
      );
  });
  for (const tab of document.querySelectorAll("[data-view]")) {
    tab.addEventListener("click", () => view(tab.dataset.view));
    tab.addEventListener("keydown", (event) => {
      const tabs = [...document.querySelectorAll("[data-view]")],
        index = tabs.indexOf(tab);
      const next =
        event.key === "ArrowRight"
          ? (index + 1) % tabs.length
          : event.key === "ArrowLeft"
            ? (index + tabs.length - 1) % tabs.length
            : event.key === "Home"
              ? 0
              : event.key === "End"
                ? tabs.length - 1
                : null;
      if (next !== null) {
        event.preventDefault();
        view(tabs[next].dataset.view, true);
      }
    });
  }
  document.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s") {
      event.preventDefault();
      if (document.querySelector("dialog[open]")) {
        tell("Keep the dialog's edits before saving the project.");
        return;
      }
      if (app.project)
        saveProject().catch((error) => tell(error.message, true));
    }
  });
  window.addEventListener("beforeunload", (event) => {
    if (app.dirty) {
      retainDraft();
      event.preventDefault();
      event.returnValue = "";
    }
  });
  for (const input of document.querySelectorAll("input[name=theme]"))
    input.addEventListener("change", () => {
      document.documentElement.dataset.time = input.value;
      try {
        localStorage.setItem("comparative-theme", input.value);
      } catch (_) {
        /* appearance remains usable without storage */
      }
    });
  async function start() {
    const session = await api("session");
    app.token = session.token;
    $("ws-engine-status").textContent = session.checker_ready
      ? "Lean checker available · private local workspace"
      : "Build the Lean checker before running analyses";
    $("ws-workspace-location").textContent =
      "Saved on this computer: " + session.workspace;
    $("ws-new-example").replaceChildren(
      ...Object.entries(session.examples).map(([id, title]) =>
        option(id, title),
      ),
    );
    $("ws-new-example").value = "merger";
    try {
      const theme = localStorage.getItem("comparative-theme");
      const input = document.querySelector(
        `input[name=theme][value="${["day", "dusk", "night"].includes(theme) ? theme : "day"}"]`,
      );
      input.checked = true;
      document.documentElement.dataset.time = input.value;
    } catch (_) {
      /* default day */
    }
    const available = await projects();
    if (available.length)
      await loadProject(await api("project?id=" + available[0].id));
    else {
      tell(
        "Create a project from an example, or import a wordlist with explicit cognate sets.",
      );
      openDialog("ws-create-dialog");
    }
    setInterval(() => {
      if (app.project && !document.hidden)
        refreshJobs().catch((error) => tell(error.message, true));
    }, 2500);
  }
  start().catch((error) => tell(error.message, true));
})();
