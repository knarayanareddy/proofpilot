# ProofPilot demo and submission runbook

**Version:** 2.0 (product reset) · 4 November 2026
**Demo:** one fictional case — approved shipping change, separate unauthorized bank-field request.

## 1. The claim we can defend

> ProofPilot runs a bounded supplier change: the contract fixes what may change, the runtime filters
> every action the model proposes, an isolated browser performs only whitelisted interactions, the
> server commits the write, and a **separate read-only principal** reads the portal back before
> anything is shown as verified. Evidence is exportable and mode-labelled.

What it is **not**, and we say so out loud:

* Not an external audit. The verifier reads the same demo portal under a second identity.
* Not prompt-injection immunity. Denied batches and safety-check stops are policy outcomes.
* Not bank-account verification, payment fraud detection or an out-of-band callback.
* Not production software: demo endpoints are unauthenticated and fixtures are fictional.
* Without `MODEL_API_KEY`, not a Meta demo at all — the UI says "Mock fallback · no key".

## 2. Setup

Linux with Python 3.10+, Playwright Chromium and its OS libraries, and Bubblewrap (`bwrap`) with
unprivileged user/network namespaces for the isolated modes.

```sh
cd proofpilot
python3 -m pip install -r requirements.txt
python3 -m playwright install chromium
# If required on Linux: python3 -m playwright install-deps chromium
# Install Bubblewrap with the distribution package manager.
make test && make evaluate && make rehearse
```

Enable real Meta runs either with `export MODEL_API_KEY` before starting the server, or through the
**Model access** panel in the workspace sidebar (writes `.model_api_key`, mode 0600, shows only a
SHA-256 fingerprint). The badge turns green, the Meta button becomes the primary action, and traces
record the real provider request IDs, tokens and protocol. A per-process call cap is enforced
(`PROOFPILOT_MAX_META_CALLS`). Never paste a key into chat or a public preview: anyone holding the
preview link can run tasks and spend the credit, so keep it private, set provider-side limits, and
remove the key when you are done.

**Say this out loud during the demo.** The documented computer-use tool is *not enabled for this
key*: the provider rejects `{"type":"computer"}`, so the loop falls back to **vision + function
calling** — the model sees real screenshots and calls `propose_action` with one whitelisted action
per turn. The provenance panel shows `protocol: vision_function_tool` and a `protocol_fallback`
event. That is still real Meta inference driving the isolated browser, but it is not the
computer-use tool, and claiming otherwise would be wrong.

## 3. Pre-flight

- [ ] `make test` passes (62 tests) with no skips you cannot explain.
- [ ] `make evaluate` produced current reports; read the measurement section and the partial rows.
- [ ] `make rehearse` passes 3/3 in the environment you will present from.
- [ ] Decide the mode: with a key → real Meta path; without → scripted/mock, labelled as such.
- [ ] If recording, name the file honestly: `meta_run.webm` or `mock_fallback.webm`.
- [ ] Reset fixtures (`make reset`) so the demo starts from the known state.
- [ ] Confirm no real customer data, secrets or browser credentials are in the demo or evidence.
- [ ] Recheck event rules, deadlines and eligibility with the organizers.

## 4. Live script (~3 minutes, one page, no tab switching)

**A. The case (15s).** Open `/workspace`. "An AP clerk has an approved request to move a supplier's
shipping address. The request that must never succeed is a bank change."

**B. Try the boundary (25s).** Click **Run bank-change probe**. It sends a request that changes
shipping *and* bank at once: HTTP 403, bank/shipping/version unchanged. Say plainly: this is a
direct request from the page, not a model action — it shows the server-enforced field boundary.

**C. Contract and approval (30s).** Create the task from the fixture CSV. Show the three rows: one
unambiguous, one ambiguous supplier, one whose page content is untrusted. Approve the exact hash.
"Approval is a local demo action, not authenticated identity verification."

**D. Ambiguity (20s).** Start matching. Row 2 pauses with two candidates. Do not select it — the
mixed outcome is part of the story. Point out that matching itself writes nothing.

**E. Execution (40s).** On row 1, click the primary action:
*With a key:* **Run with Meta computer-use** — screenshots go to the model, it returns batched
actions, the runtime resolves coordinates and filters them.
*Without:* the button is disabled and the reason is on screen; use **Run deterministic mock**.
Then open the **Model provenance** panel: model, endpoint, provider request IDs, turns, what was
allowed, what was denied, the stop reason, and the sandbox probe results.

**F. Read-back (25s).** Click **Verify portal read-back**. Show `VERIFIED` only when the read-back
succeeded, and say it is a separate read-only principal against the same demo portal, at this
instant in time.

**G. Failure (20s).** Run row 3 (untrusted content, simulated 503). It stays `FAILED`. "A failure is
a result here, not a bug we hide."

**H. Evidence (25s).** Show the **source-to-outcome chain**: source contract → selected target →
model/run → write → read-back, with pending links labelled pending. Open the evidence report and
the ZIP. Close on limitations: point-in-time, same-system verifier, CSV bytes not retained.

## 5. Fallbacks

| Situation | Do | Do not |
|---|---|---|
| No `MODEL_API_KEY` | Use mock/scripted; the badge and trace record the mode | Call any run "Meta-driven" |
| Provider error / timeout | Show `STOPPED` with the recorded reason and reconcile attempts | Retry blindly or present partial output as success |
| Verification unavailable | Show `EXECUTED_UNVERIFIED` and explain | Manufacture a green result |
| Bubblewrap/Chromium missing | Say isolation is unavailable and stop execution | Fall back to the unsandboxed path while claiming isolation |
| Recording fails | Debug with the failure screenshot; re-run | Show a stale or partial recording as a pass |

## 5b. The film (inside the running portal)

The portal serves the demo film, so it is reachable from the preview itself:

| Route | What it is |
|---|---|
| `/film` | Full-page player (3:03, 1920×1080, narrated) |
| `/film.mp4` | The MP4; supports HTTP Range, so seeking works. `?download=1` forces a save dialog |
| `/film-poster.jpg` | Poster frame used by both players |
| `/film-contact-sheet.jpg` | 12 frames from the film, for a quick skim or a static slide |

The task workspace (`/workspace`) embeds the player in a **Product film · 3:03** panel just below the
hero, and both `/` and `/workspace` carry a **Demo film ↗** link in the header. The file is served
from `video/out/proofpilot-demo.mp4` — re-render it and the portal picks it up on the next request,
no restart needed:

```bash
cd video && npx remotion render src/index.js ProofPilot out/proofpilot-demo.mp4 --concurrency=2
```

Wording note, because it is easy to get wrong: `reports/measurement.json` holds **18 measurement
rows**, but they are **10 distinct cases** — C01, C02, C03 and C09 are the live ones and are run three
times each. So "eighteen cases" is defensible and still misleading. The film says "eighteen
**attempts**" for the 0/18 unauthorized-mutation denominator, which is exactly what that metric counts.
Keep it that way if the script changes.

## 6. Numbers to quote (regenerate before presenting)

`make evaluate` prints the live measurement. Quote numerator and denominator together, always state
the model mode and protocol printed next to them, and regenerate on the day you present. The most
recent live run reported:

```
Authorized task success 7/7 · unauthorized mutations 0/18 · verification TP 7 TN 3 FP 0 FN 0
Failures correctly surfaced 11/11 · live completion 9/12 (9/9 excluding the 503 fixture row)
LIVE_META · vision_function_tool
```

Quote the live-completion spread when asked "how often does it work": across four identical suites
the score was 9/12, 6/12, 8/12 and 9/12, and the shortfalls were always the model replying in prose
instead of calling the tool — never an unauthorized write. Bounded retry prompts recovered most of
them. Eighteen measurement rows — ten distinct cases, with the four live ones repeated three times each — on one model version on one day are not a statistical estimate.

## 7. Open gates before a full Meta-focused submission

- [x] Live Meta runs completed: real provider calls, real traces, real read-back, repeat runs and
      provider request IDs recorded in `reports/measurement.json`.
- [ ] Ask Meta to enable the computer-use tool for this key, then re-run the same suite on the
      documented `computer_call` protocol and publish both protocol results side by side.
- [ ] Increase live-case repetitions and report the spread; investigate the ~25% of runs where the
      model answers in prose instead of calling the tool (prompt shape, `previous_response_id`
      chaining, or a stricter tool_choice if the provider adds support).
- [ ] Capture a real end-to-end Meta trace and a real recording; keep the mock recording as the
      labelled fallback only.
- [ ] Validate the provider protocol against the live API (request shape, `computer_call_output`,
      `previous_response_id`, safety-check fields) — today it is written to the documentation.
- [ ] Evaluate real-model behaviour on unauthorized action attempts and untrusted page content,
      reported separately from the deterministic probes.
- [ ] Remaining engineering gaps: process-kill recovery, stale `PREPARED` attempt cleanup, richer
      network/redirect coverage, real portal UI integration instead of a rendered fixture.
- [ ] Product validation: interviews with AP/supplier-master operators and a hands-on comparison to
      browser-agent audit trails and supplier fraud products (see `product/PRODUCT_RESET.md`).
- [ ] Confirm submission format, eligibility of pre-existing work, and the judging rubric with the
      organizers.
