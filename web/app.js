/* AGORA's page. No framework and no build step: the whole thing is one file of
   plain DOM, because the interesting part is the core, not the client.

   The playground runs entirely here. A rule that comes back from the solver is a
   complete outcome table over its electorate, so stress-testing it is a lookup,
   not another round trip, and nothing on this page can drift from what was proved. */

const NAMES = "ABCDEFGH";
const $ = (id) => document.getElementById(id);

const state = {
  mode: "scf",
  voters: 2,
  candidates: 3,
  library: [],
  sizes: [],
  picked: new Set(),
  custom: [],        // accepted proposals the user added
  proposal: null,    // the one currently on screen, accepted or not
  result: null,
};

// -- plumbing ---------------------------------------------------------------

const esc = (s) =>
  String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

async function api(path, body) {
  const opts = body
    ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }
    : {};
  const reply = await fetch(path, opts);
  const data = await reply.json().catch(() => ({ error: "the server said something unreadable" }));
  if (!reply.ok) throw new Error(data.error || `request failed (${reply.status})`);
  return data;
}

// -- the question -----------------------------------------------------------

function renderSizes() {
  $("size").innerHTML = state.sizes
    .map((s) => {
      const on = s.voters === state.voters && s.candidates === state.candidates;
      return `<option value="${s.voters},${s.candidates}"${on ? " selected" : ""}>` +
        `${s.voters} voters, ${s.candidates} candidates &mdash; ${esc(s.note)}</option>`;
    })
    .join("");
}

function renderAxioms() {
  const rows = state.library.map((a) => {
    const usable = a.modes.includes(state.mode);
    const on = usable && state.picked.has(a.name);
    return `<button class="axiom${usable ? "" : " off"}" data-axiom="${esc(a.name)}"
        aria-pressed="${on}"${usable ? "" : " disabled aria-disabled=\"true\""}>
      <span class="tick">${on ? "&#10003;" : ""}</span>
      <span><span class="nm">${esc(a.name)}</span>
        <span class="gl">${esc(usable ? a.english : `only defined for a rule that ${a.modes.includes("scf") ? "elects one winner" : "produces a ranking"}`)}</span>
      </span></button>`;
  });
  const mine = state.custom.map((c, i) => {
    const on = state.picked.has(c.name);
    return `<button class="axiom" data-custom="${i}" aria-pressed="${on}">
      <span class="tick">${on ? "&#10003;" : ""}</span>
      <span><span class="nm">${esc(c.name)}</span> <span class="custom-tag">yours</span>
        <span class="gl">${esc(c.english)}</span>
        <span class="gl mono">${esc(c.formula)}</span>
      </span></button>`;
  });
  $("axioms").innerHTML = mine.concat(rows).join("");
}

function setMode(mode) {
  state.mode = mode;
  for (const b of $("mode").children) b.setAttribute("aria-pressed", String(b.dataset.mode === mode));
  // A custom axiom is formalised for one kind of rule, so switching kinds drops it.
  state.custom = state.custom.filter((c) => c.mode === mode);
  for (const a of state.library) {
    if (!a.modes.includes(mode)) state.picked.delete(a.name);
  }
  for (const name of [...state.picked]) {
    const known = state.library.some((a) => a.name === name) || state.custom.some((c) => c.name === name);
    if (!known) state.picked.delete(name);
  }
  renderAxioms();
}

// -- minting ----------------------------------------------------------------

async function mint() {
  const chosen = [
    ...state.library.filter((a) => state.picked.has(a.name)).map((a) => a.name),
    ...state.custom.filter((c) => state.picked.has(c.name))
      .map((c) => ({ name: c.name, english: c.english, formula: c.formula })),
  ];
  if (!chosen.length) return fail("Pick at least one property first.");
  fail("");
  $("mint").disabled = true;
  $("mint").innerHTML = '<span class="spinner"></span> deriving';
  $("stage").innerHTML = `<div class="empty"><div class="mark"><span class="spinner"></span></div>
    <div>Searching every profile of this electorate.</div></div>`;
  try {
    state.result = await api("/api/derive", {
      mode: state.mode, voters: state.voters, candidates: state.candidates, axioms: chosen,
    });
    renderResult();
  } catch (e) {
    fail(e.message);
    $("stage").innerHTML = `<div class="empty"><div class="mark">&#9671;</div><div>${esc(e.message)}</div></div>`;
  } finally {
    $("mint").disabled = false;
    $("mint").textContent = "Mint";
  }
}

function fail(message) {
  const box = $("ask-error");
  box.textContent = message;
  box.hidden = !message;
}

function footer(r) {
  const checked = r.verified
    ? " Every rule shown was re-checked against its properties without the solver."
    : "";
  return `Searched all ${r.profiles.toLocaleString()} profiles of this electorate, ` +
    `${r.variables.toLocaleString()} variables, in ${r.elapsed.toFixed(2)}s.${checked}`;
}

function gloss(r, name) {
  return (r.glosses && r.glosses[name]) || "";
}

function renderResult() {
  const r = state.result;
  const stage = $("stage");
  stage.dataset.status = r.status;
  if (r.status === "sat") stage.innerHTML = satView(r);
  else if (r.status === "unsat") stage.innerHTML = unsatView(r);
  else stage.innerHTML = unknownView(r);
  stage.append($("tpl-honest").content.cloneNode(true));
  if (r.status === "sat") wirePlayground();
  stage.scrollTop = 0;
}

function askedList(r) {
  return `<div class="rows pair">` + r.axioms.map((n) =>
    `<div class="row"><span class="k">${esc(n)}</span><span class="v faint">${esc(gloss(r, n))}</span></div>`
  ).join("") + `</div>`;
}

function satView(r) {
  const kind = r.mode === "scf" ? "elects one winner" : "produces a ranking";
  const rows = Object.entries(r.rule.table);
  const preview = rows.slice(0, 8).map(([p, o]) =>
    `<div class="row"><span class="k">${esc(p)}</span><span class="v">${esc(o)}</span></div>`).join("");
  return `
  <div class="enter">
    <div class="verdict"><span class="glyph">&#9679;</span>
      <h3>A rule exists.</h3></div>
    <p class="muted">Over ${r.voters} voters and ${r.candidates} candidates, a rule that ${kind}
      and has every property you asked for. ${ruleName(r)}</p>
  </div>
  <div class="card enter"><h2>What you asked for</h2>${askedList(r)}</div>
  <div class="card enter"><h2>Try it on an election</h2><div id="playground"></div></div>
  <div class="card enter"><h2>The rule, in full &mdash; ${rows.length} profiles</h2>
    <div class="rows">${preview}</div>
    ${rows.length > 8 ? `<p class="faint" style="margin:10px 0 0;font-size:12px">
      ${rows.length - 8} more, all decided. Every one of them is in the table the playground above reads from.</p>` : ""}
  </div>
  <p class="faint" style="font-size:12px">${esc(footer(r))}</p>`;
}

function ruleName(r) {
  const named = `It is <strong>${esc(r.rule_name)}</strong>.`;
  const unnamed = `It is not a rule anyone has written down: ` +
    `<strong>${esc(String(r.rule_name).replace("no textbook match: ", ""))}</strong>.`;
  return { true: named, false: unnamed }[r.rule_named];
}

function unsatView(r) {
  const core = r.core || [];
  const dropped = r.axioms.filter((a) => !core.includes(a));
  const blame = core.map((n) =>
    `<div><span class="name">${esc(n)}</span> <span class="gloss">${esc(gloss(r, n))}</span></div>`).join("");
  const without = core.map((n) =>
    `<span class="drop">without ${esc(n)}</span><span class="mono">${esc(r.witnesses[n] || "a rule exists")}</span>`).join("");
  return `
  <div class="enter">
    <div class="verdict"><span class="glyph">&#9632;</span><h3>No rule can exist.</h3></div>
    <p class="muted">Over ${r.voters} voters and ${r.candidates} candidates, nothing that
      ${r.mode === "scf" ? "elects one winner" : "produces a ranking"} satisfies all of these at once.</p>
  </div>
  <div class="card enter"><h2>The properties to blame</h2>
    <div class="blame">${blame}</div>
    ${dropped.length ? `<p class="notice">You asked for ${r.axioms.length}. The ${core.length} above
      rule it out on their own, so ${esc(dropped.join(", "))} never came into it.</p>` : ""}
  </div>
  <div class="card enter"><h2>None of them is spare</h2>
    ${r.core_minimal
      ? `<p class="muted" style="margin-top:0">Give up any single one and a rule appears. That is what
           makes this a proof rather than a complaint: each line below is a rule the solver produced
           and then re-checked against the properties that remain.</p>
         <div class="without">${without}</div>`
      : `<p class="muted" style="margin-top:0">Minimisation did not finish inside the budget, so this set is
           known to be unsatisfiable but is not known to be minimal: some of it may be spare.</p>`}
  </div>
  <details class="card enter"><summary class="faint" style="cursor:pointer;font-size:12px">The machine's own words</summary>
    <pre class="raw" style="margin-top:12px">${esc(r.text)}</pre></details>
  <p class="faint" style="font-size:12px">${esc(footer(r))}</p>`;
}

function unknownView(r) {
  return `
  <div class="enter"><div class="verdict"><span class="glyph">&#9633;</span><h3>Undecided.</h3></div>
    <p class="muted">Nothing is claimed either way at this size.</p></div>
  <div class="card enter"><pre class="raw">${esc(r.text)}</pre></div>`;
}

// -- the playground ---------------------------------------------------------

// Every ballot of the electorate already appears in the rule's own table keys,
// so there is nothing to enumerate here.
function ballotOptions() {
  const first = Object.keys(state.result.rule.table).map((k) => k.split(" | ")[0].slice(4));
  return [...new Set(first)];
}

function profileKey(ballots) {
  return ballots.map((b, i) => `v${i + 1}: ${b}`).join(" | ");
}

function wirePlayground() {
  const r = state.result;
  const options = ballotOptions();
  const box = $("playground");
  box.innerHTML = `
    <div class="ballots">${Array.from({ length: r.voters }, (_, i) => `
      <div class="ballot"><label for="b${i}">v${i + 1}</label>
        <select id="b${i}">${options.map((o, k) =>
          `<option${k === (i % options.length) ? " selected" : ""}>${o}</option>`).join("")}</select>
      </div>`).join("")}</div>
    <div style="display:flex;gap:8px;margin-bottom:14px">
      <button class="small" id="shuffle">Random election</button>
      <button class="small" id="worst">Find a disagreement</button>
    </div>
    <div id="verdict-out"></div>`;
  for (let i = 0; i < r.voters; i++) $("b" + i).onchange = runPlayground;
  $("shuffle").onclick = () => {
    for (let i = 0; i < r.voters; i++) $("b" + i).selectedIndex = Math.floor(Math.random() * options.length);
    runPlayground();
  };
  $("worst").onclick = findDisagreement;
  runPlayground();
}

function currentBallots() {
  return Array.from({ length: state.result.voters }, (_, i) => $("b" + i).value);
}

function scores(ballots, candidates) {
  const cands = [...NAMES.slice(0, candidates)];
  const rank = (b) => b.split(" > ");
  const plurality = {}, borda = {}, beats = {};
  for (const c of cands) { plurality[c] = 0; borda[c] = 0; beats[c] = 0; }
  for (const b of ballots) {
    const order = rank(b);
    plurality[order[0]]++;
    order.forEach((c, k) => (borda[c] += candidates - 1 - k));
  }
  for (const a of cands) for (const b of cands) {
    if (a === b) continue;
    const wins = ballots.filter((x) => x.split(" > ").indexOf(a) < x.split(" > ").indexOf(b)).length;
    if (2 * wins > ballots.length) beats[a]++;
  }
  const best = (t) => cands.slice().sort((x, y) => t[y] - t[x] || (x < y ? -1 : 1));
  const condorcet = cands.find((c) => beats[c] === candidates - 1);
  return { plurality: best(plurality), borda: best(borda), condorcet };
}

function runPlayground() {
  const r = state.result;
  const ballots = currentBallots();
  const outcome = r.rule.table[profileKey(ballots)];
  const s = scores(ballots, r.candidates);
  const mine = r.mode === "scf" ? outcome : outcome.split(" > ")[0];
  const agrees = [
    ["plurality", s.plurality[0]],
    ["borda", s.borda[0]],
    ["condorcet winner", s.condorcet || "none"],
  ];
  $("verdict-out").innerHTML = `
    <div class="outcome"><span class="faint">your rule ${r.mode === "scf" ? "elects" : "ranks"}</span>
      <span class="big">${esc(outcome)}</span>
      ${agrees.every(([, v]) => v === mine || v === "none")
        ? `<span class="agree">&#10003; agrees with all three</span>`
        : `<span class="agree">&#9679; differs from ${esc(agrees.filter(([, v]) => v !== mine && v !== "none").map(([k]) => k).join(", "))}</span>`}
    </div>
    <div class="compare">${agrees.map(([k, v]) =>
      `<div><span class="cl">${esc(k)}</span><span class="cv">${esc(v)}</span></div>`).join("")}</div>`;
}

function findDisagreement() {
  const r = state.result;
  const options = ballotOptions();
  for (const key of Object.keys(r.rule.table)) {
    const ballots = key.split(" | ").map((s) => s.split(": ")[1]);
    const outcome = r.rule.table[key];
    const mine = r.mode === "scf" ? outcome : outcome.split(" > ")[0];
    const s = scores(ballots, r.candidates);
    if (s.plurality[0] !== mine || (s.condorcet && s.condorcet !== mine)) {
      ballots.forEach((b, i) => ($("b" + i).selectedIndex = options.indexOf(b)));
      return runPlayground();
    }
  }
  $("verdict-out").insertAdjacentHTML("beforeend",
    `<p class="faint" style="font-size:12px;margin-bottom:0">No profile of this electorate where the rule
     parts company with plurality or the Condorcet winner. It agrees with them everywhere.</p>`);
}

// -- free-form entry --------------------------------------------------------

async function formalize() {
  const text = $("invent").value.trim();
  if (!text) return;
  const button = $("formalize");
  button.disabled = true;
  button.innerHTML = '<span class="spinner"></span> formalising';
  $("formalize-out").innerHTML = "";
  try {
    state.proposal = await api("/api/formalize", { text, mode: state.mode });
    renderProposal();
  } catch (e) {
    $("formalize-out").innerHTML = `<p class="err">${esc(e.message)}</p>`;
  } finally {
    button.disabled = false;
    button.textContent = "Formalise it";
  }
}

async function recheck() {
  const formula = $("edit-formula").value.trim();
  const button = $("recheck");
  button.disabled = true;
  button.innerHTML = '<span class="spinner"></span> checking';
  try {
    state.proposal = await api("/api/vet", {
      formula, mode: state.mode,
      name: state.proposal?.name, english: state.proposal?.english,
    });
    renderProposal();
  } catch (e) {
    $("formalize-out").innerHTML = `<p class="err">${esc(e.message)}</p>`;
  }
}

const VERDICT = {
  true: { glyph: "&#9679;", head: "The checker accepts it." },
  false: { glyph: "&#9632;", head: "The checker will not take it." },
};
const MARK = { true: "&#10003;", false: "&#10007;" };
const CLS = { true: "pass", false: "fail" };
const HOLDS = { true: "&#10003; holds", false: "&#10007; fails" };
const TONE = { true: "yes", false: "no" };
const STATUS = { true: "sat", false: "unsat" };

function renderProposal() {
  const p = state.proposal;
  const v = VERDICT[p.accepted];

  // A rejected earlier draft is just a failed gate with a longer note, so the
  // whole history and the current run render as one ladder rather than two.
  const ladder = [
    // The same objection three times is noise. The full text is on the live
    // attempt below; the history keeps the first sentence of each.
    ...p.attempts.map((a) => ({
      passed: false, step: "rejected",
      note: `<span class="mono">${esc(a.formula)}</span><br>${esc(a.why.split(". ")[0])}`,
    })),
    ...p.gates.map((g) => ({ ...g, note: esc(g.note) })),
  ].map((g) => `<div class="gate ${CLS[g.passed]}"><span class="mark">${MARK[g.passed]}</span>
      <span class="step">${esc(g.step)}</span><span class="note">${g.note}</span></div>`).join("");

  const sections = [
    [p.english, `<p class="muted" style="margin-top:0">${esc(p.english)}</p>`],
    [!p.accepted, `<p class="notice">${esc(p.why)}</p>`],
    [p.accepted, `<button class="small" id="adopt">Add to the list</button>`],
    [p.behaviour.length, `<div class="card enter"><h2>What it does to rules we can name</h2>
      <div class="behaviour">${p.behaviour.map((b) =>
        `<span class="rn">${esc(b.rule)}</span><span class="rv ${TONE[b.holds]}">${HOLDS[b.holds]}</span>`
      ).join("")}</div>
      <p class="faint" style="font-size:12px;margin-bottom:0">The gates prove it is well formed,
      satisfiable, and not a tautology. They cannot prove it means what you said. This table is the part
      that can: if a rule you would call fair fails here, or one you would not call fair passes, the
      formalisation is not what you meant. Edit it above and check again.</p></div>`],
  ].map(([on, html]) => (on ? html : ""));
  const [english, notice, adoptButton, behaviourCard] = sections;

  const stage = $("stage");
  stage.dataset.status = STATUS[p.accepted];
  stage.innerHTML = `
    <div class="enter">
      <div class="verdict"><span class="glyph">${v.glyph}</span><h3>${v.head}</h3></div>
      <p class="muted">You wrote: &ldquo;${esc(p.text)}&rdquo;</p>
    </div>
    <div class="card enter">
      <h2>The formalisation &mdash; drafted by ${esc(p.backend)}, decided here</h2>
      ${english}
      <textarea class="formula" id="edit-formula" spellcheck="false">${esc(p.formula)}</textarea>
      <div style="display:flex;gap:8px;margin-top:8px;flex-wrap:wrap">
        <button class="small" id="recheck">Check again</button>${adoptButton}
      </div>
      ${notice}
      <h2 style="margin-top:18px">Gates</h2>${ladder}
    </div>
    ${behaviourCard}`;
  stage.append($("tpl-honest").content.cloneNode(true));
  stage.scrollTop = 0;
  $("recheck").onclick = recheck;
  document.getElementById("adopt")?.addEventListener("click", adopt);
}

function adopt() {
  const p = state.proposal;
  const name = state.custom.some((c) => c.name === p.name) || state.library.some((a) => a.name === p.name)
    ? `${p.name}_${state.custom.length + 1}` : p.name;
  state.custom.push({ name, english: p.english || p.text, formula: p.formula, mode: state.mode });
  state.picked.add(name);
  state.proposal = null;
  $("invent").value = "";
  renderAxioms();
  const stage = $("stage");
  delete stage.dataset.status;
  stage.innerHTML = `<div class="empty"><div class="mark">&#9671;</div>
    <div><span class="mono">${esc(name)}</span> is in the list now, and ticked.</div>
    <div class="faint" style="font-size:12px">Add the library properties you want beside it, then mint.</div></div>`;
}

// -- boot -------------------------------------------------------------------

async function boot() {
  const [cat, model] = await Promise.all([api("/api/axioms"), api("/api/health")]);
  state.library = cat.axioms;
  state.sizes = cat.sizes;
  renderSizes();
  renderAxioms();

  $("model-state").innerHTML = model.backend
    ? `<span class="chip">${esc(model.backend)}</span>
       <span class="chip">${model.grammar ? "grammar-constrained" : "json schema only"}</span>
       <span class="chip">local, offline</span>`
    : `<span class="chip">no local model: free-form entry is off</span>`;
  if (!model.backend) $("formalize").disabled = true;

  $("mode").onclick = (e) => { const b = e.target.closest("button"); if (b) setMode(b.dataset.mode); };
  $("size").onchange = (e) => {
    const [v, c] = e.target.value.split(",").map(Number);
    state.voters = v; state.candidates = c;
  };
  $("axioms").onclick = (e) => {
    const b = e.target.closest(".axiom");
    if (!b || b.disabled) return;
    const name = b.dataset.axiom ?? state.custom[Number(b.dataset.custom)].name;
    state.picked.has(name) ? state.picked.delete(name) : state.picked.add(name);
    renderAxioms();
  };
  $("mint").onclick = mint;
  $("formalize").onclick = formalize;
  $("invent").onkeydown = (e) => { if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) formalize(); };
}

boot();
