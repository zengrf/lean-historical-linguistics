"use strict";

(() => {
  let pageRevision = 0;
  let spec = null,
    result = null,
    revision = 0,
    tableDirty = false,
    lastPage = null;
  const showWord = (w) => (w.length ? "*" + w.join("") : "∅");
  const shortCount = (s) =>
    s.length > 45 ? `${s.slice(0, 12)}… (${s.length} digits)` : s;
  function invalidate() {
    revision++;
    result = null;
    lastPage = null;
    $("lex-results").hidden = true;
    $("lex-export").disabled = true;
    status(
      "lex-status",
      "Constraints changed. Run the search to check them together.",
    );
  }
  function modelOptions() {
    $("lex-models").replaceChildren(
      ...spec.analyses.map((a) =>
        checkRow("lex-model", a.id, a.id, a.description),
      ),
    );
    $("lex-model-edit").value = JSON.stringify(spec.analyses, null, 2);
  }
  function loadSpec(next, tsv) {
    spec = next;
    invalidate();
    tableDirty = false;
    modelOptions();
    $("lex-languages").replaceChildren(
      ...spec.languages.map((l) => checkRow("lex-language", l.id, l.label)),
    );
    $("lex-description").textContent = spec.description;
    $("lex-inventory").value = spec.proto_inventory.join(" ");
    $("lex-min").value = spec.min_length;
    $("lex-max").value = spec.max_length;
    $("lex-shapes").value = JSON.stringify(spec.phonotactics);
    $("lex-table").value = tsv;
    $("lex-row-count").textContent =
      `${spec.entries.length.toLocaleString()} cognate sets`;
    status(
      "lex-status",
      "Ready. Select the models and daughter languages, then enumerate.",
    );
  }
  async function example() {
    const rev = ++revision;
    $("lex-run").disabled = true;
    try {
      const data = await api(
        "/api/lexicon/example?key=" +
          encodeURIComponent($("lex-example").value),
      );
      if (rev !== revision) return;
      const key = $("lex-example").value;
      $("lex-example").replaceChildren(
        ...Object.entries(data.examples).map(([id, label]) => {
          const o = element("option", label);
          o.value = id;
          return o;
        }),
      );
      $("lex-example").value = key;
      loadSpec(data.request, data.tsv);
    } catch (e) {
      status("lex-status", e.message, true);
    } finally {
      $("lex-run").disabled = false;
    }
  }
  function settings() {
    if (!spec) throw new Error("Load a request first");
    const next = structuredClone(spec);
    next.proto_inventory = $("lex-inventory")
      .value.trim()
      .split(/\s+/u)
      .filter(Boolean);
    next.min_length = Number($("lex-min").value);
    next.max_length = Number($("lex-max").value);
    next.phonotactics = JSON.parse($("lex-shapes").value);
    return next;
  }
  async function input() {
    let next = settings();
    if (tableDirty) {
      next = (
        await api("/api/lexicon/table", {
          request: next,
          tsv: $("lex-table").value,
          source_ref: $("lex-source").value,
        })
      ).request;
    }
    return next;
  }
  function selectOption(value, label) {
    const option = element("option", label);
    option.value = value;
    return option;
  }
  function summary() {
    const s = result.summary;
    $("lex-results").hidden = false;
    $("lex-total").textContent =
      `${shortCount(s.lexicon_count)} allowed protolexicons`;
    $("lex-total").title = s.lexicon_count;
    $("lex-scope").textContent =
      `Complete search checked by Lean. ${result.request.entries.length.toLocaleString()} cognate sets; ${s.nodes.toLocaleString()} graph states. Counts distinguish global models, even when they predict the same forms.`;
    $("lex-model-summary").replaceChildren(
      ...s.models.map((m) => {
        const card = element("div", null, "lex-model-card");
        const blocked = m.entries.filter((e) => e.count === "0");
        append(
          card,
          element("b", m.analysis_id),
          element(
            "p",
            `${shortCount(m.lexicon_count)} protolexicons · ${m.mode === "compiled" ? "compiled sound laws" : "reference interpreter"}`,
          ),
        );
        if (blocked.length)
          card.append(
            element(
              "p",
              `No full lexicon: ${blocked.length} row(s) have no allowed form (${blocked
                .slice(0, 10)
                .map((e) => e.entry_id)
                .join(", ")}${blocked.length > 10 ? ", …" : ""}).`,
              "source-note",
            ),
          );
        return card;
      }),
    );
    $("lex-result-model").replaceChildren(
      ...s.models.map((m) =>
        selectOption(
          m.analysis_id,
          `${m.analysis_id} · ${shortCount(m.lexicon_count)}`,
        ),
      ),
    );
    const viable = s.models.find((m) => m.lexicon_count !== "0");
    if (viable) $("lex-result-model").value = viable.analysis_id;
    $("lex-entry").replaceChildren(
      ...result.request.entries.map((e) =>
        selectOption(e.id, `${e.meaning} · ${e.id}`),
      ),
    );
    $("lex-offset").value = "0";
    $("lex-export").disabled = false;
  }
  function derivation(item) {
    const d = element("details", null, "lex-derivation");
    append(
      d,
      element(
        "summary",
        `${showWord(item.proposal.word)} · checked daughter derivations`,
      ),
    );
    item.certificates.forEach((c, i) => {
      const language = result.request.languages[i];
      const block = element("details");
      const output = c.output.join("") || "∅";
      block.append(element("summary", `${language.label}: ${output}`));
      const steps = element("ol");
      c.steps.forEach((s) =>
        steps.append(
          element("li", `${s.rule_id}: ${s.output.join("") || "∅"}`),
        ),
      );
      if (!c.steps.length)
        block.append(element("p", "Identity: the form is unchanged."));
      block.append(steps, rawDetails(c));
      d.append(block);
    });
    return d;
  }
  async function browse() {
    if (!result) return;
    const pageRev = ++pageRevision;
    const rev = revision,
      token = result.token;
    const isWords = $("lex-view").value === "words";
    $("lex-entry").disabled = !isWords;
    $("lex-go").disabled = true;
    $("lex-candidates").replaceChildren();
    status("lex-page-status", "Checking the displayed derivations…");
    try {
      const data = await api("/api/lexicon/page", {
        token,
        analysis_id: $("lex-result-model").value,
        entry_id: isWords ? $("lex-entry").value : null,
        offset: $("lex-offset").value,
        limit: isWords ? 20 : 1,
      });
      if (
        rev !== revision ||
        pageRev !== pageRevision ||
        result?.token !== token
      )
        return;
      lastPage = data;
      const model = result.summary.models.find(
        (m) => m.analysis_id === $("lex-result-model").value,
      );
      status(
        "lex-page-status",
        `${shortCount(data.count)} ${isWords ? "protoforms for this row" : "whole protolexicons"}. Showing ${data.items.length} from index ${data.offset}.` +
          (isWords && model.lexicon_count === "0"
            ? " This model cannot reconstruct the whole lexicon because another row has no allowed form."
            : ""),
      );
      if (isWords)
        $("lex-candidates").replaceChildren(...data.items.map(derivation));
      else
        $("lex-candidates").replaceChildren(
          ...data.items.map((item) => {
            const section = element("section", null, "lex-whole");
            section.append(
              element("h4", `${item.analysis_id} · lexicon ${item.index}`),
            );
            const table = element("table");
            const head = element("tr");
            head.append(
              element("th", "Cognate set"),
              element("th", "Protoform"),
            );
            table.append(head);
            item.words.forEach((w) => {
              const tr = element("tr");
              tr.append(
                element("td", w.entry_id),
                element("td", showWord(w.word)),
              );
              table.append(tr);
            });
            section.append(
              table,
              rawDetails(
                item.derivations,
                "Checked derivations for every word",
              ),
            );
            return section;
          }),
        );
      if (!data.items.length)
        $("lex-candidates").append(
          element(
            "p",
            data.count === "0"
              ? "No reconstructions satisfy these constraints."
              : "This index is beyond the last reconstruction.",
          ),
        );
      $("lex-previous").disabled = BigInt(data.offset) === 0n;
      $("lex-next").disabled = !data.has_more;
    } catch (e) {
      status("lex-page-status", e.message, true);
    } finally {
      $("lex-go").disabled = false;
    }
  }
  $("lex-run").addEventListener("click", async () => {
    invalidate();
    const rev = revision;
    $("lex-run").disabled = true;
    $("lex-results").setAttribute("aria-busy", "true");
    status(
      "lex-status",
      "Generating the inverse languages and checking completeness in Lean…",
    );
    try {
      const request = await input();
      if (rev !== revision) return;
      const data = await api("/api/lexicon/run", {
        request,
        analyses: chosen("lex-model"),
        languages: chosen("lex-language"),
        node_budget: Number($("lex-budget").value),
        time_limit: Number($("lex-seconds").value),
      });
      if (rev !== revision) return;
      if (!data.summary?.complete)
        throw new Error(
          data.error ||
            "Incomplete search; no completeness claim is available.",
        );
      result = data;
      summary();
      status(
        "lex-status",
        "Complete. Every allowed protoform is represented in the checked search graph.",
      );
      await browse();
    } catch (e) {
      if (rev === revision) status("lex-status", e.message, true);
    } finally {
      $("lex-run").disabled = false;
      $("lex-results").setAttribute("aria-busy", "false");
    }
  });
  $("lex-example").addEventListener("change", example);
  $("lex-table").addEventListener("input", () => {
    tableDirty = true;
    invalidate();
  });
  [
    "lex-models",
    "lex-languages",
    "lex-inventory",
    "lex-min",
    "lex-max",
    "lex-shapes",
    "lex-budget",
    "lex-seconds",
    "lex-source",
  ].forEach((id) => $(id).addEventListener("input", invalidate));
  $("lex-model-edit").addEventListener("input", () => {
    invalidate();
    status("lex-status", "Apply model edits before running the search.");
    $("lex-run").disabled = true;
  });
  $("lex-apply-models").addEventListener("click", () => {
    try {
      const models = JSON.parse($("lex-model-edit").value);
      if (!Array.isArray(models))
        throw new Error("Expected an array of models");
      spec.analyses = models;
      modelOptions();
      invalidate();
      $("lex-run").disabled = false;
    } catch (e) {
      status("lex-status", e.message, true);
    }
  });
  $("lex-tsv-import").addEventListener("change", async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    $("lex-table").value = await file.text();
    tableDirty = true;
    invalidate();
  });
  $("lex-import").addEventListener("change", async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    try {
      const imported = (
        await api("/api/lexicon/import", { text: await file.text() })
      ).request;
      const escape = (value) =>
        /[\t\r\n"]/.test(value)
          ? '"' + value.replaceAll('"', '""') + '"'
          : value;
      const lines = [
        ["id", "meaning", ...imported.languages.map((l) => l.id)],
        ...imported.entries.map((e) => [
          e.id,
          e.meaning,
          ...e.reflexes.map((r) =>
            r.form === null
              ? ""
              : r.form.length
                ? r.form.map((s) => s ?? "?").join(" ")
                : "∅",
          ),
        ]),
      ];
      const tsv =
        lines.map((row) => row.map(escape).join("\t")).join("\n") + "\n";
      const validated = await api("/api/lexicon/table", {
        request: imported,
        tsv,
        source_ref: "user:import-validation",
      });
      // Keep imported per-cell provenance; the table round trip is validation only.
      if (!validated.request) throw new Error("Invalid reflex table");
      loadSpec(imported, tsv);
    } catch (e) {
      status("lex-status", e.message, true);
    }
  });
  ["lex-result-model", "lex-view", "lex-entry"].forEach((id) =>
    $(id).addEventListener("change", () => {
      $("lex-offset").value = "0";
      browse();
    }),
  );
  $("lex-go").addEventListener("click", browse);
  $("lex-previous").addEventListener("click", () => {
    if (!lastPage) return;
    const n =
      BigInt(lastPage.offset) - BigInt(lastPage.kind === "words" ? 20 : 1);
    $("lex-offset").value = String(n < 0n ? 0n : n);
    browse();
  });
  $("lex-next").addEventListener("click", () => {
    if (!lastPage) return;
    $("lex-offset").value = String(
      BigInt(lastPage.offset) + BigInt(lastPage.items.length),
    );
    browse();
  });
  $("lex-download-input").addEventListener("click", async () => {
    try {
      download("reflex-request.json", await input());
    } catch (e) {
      status("lex-status", e.message, true);
    }
  });
  $("lex-export").addEventListener("click", async () => {
    if (!result) return;
    try {
      download(
        "checked-protolexicons.json",
        await api("/api/lexicon/export", { token: result.token }),
      );
    } catch (e) {
      status("lex-status", e.message, true);
    }
  });
  example();
})();
