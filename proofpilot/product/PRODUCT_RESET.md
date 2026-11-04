# Product reset: supplier changes with a verifiable boundary

Status: **hypothesis with a working prototype.** Everything below about value and differentiation is
unvalidated unless marked otherwise. Last updated 4 November 2026.

## 1. The use case

An accounts-payable or supplier-master specialist receives a request to change a supplier's shipping
address. The change is legitimate, small and frequent. The catastrophic version of the same task is a
bank-account change triggered by a compromised email or an injected instruction on a page the agent
reads.

The wedge is narrow on purpose: prove that one bounded change happened, on the right record, at the
right version, and that nothing else moved — then show the receipt.

## 2. What is built now

* **Contract**: CSV → fixed-template contract with a hash; approval binds to the hash and row hashes.
* **Decision**: ambiguous suppliers pause for a human; selections expire in five minutes and
  invalidate when the target version changes. Matching writes nothing.
* **Execution**: three modes, recorded per trace — real Meta model, deterministic mock, and
  scripted browser (see README). The real path attempts the documented Responses API computer-use
  loop (screenshot in, batched `computer_call` out, `computer_call_output` back in) and falls back
  to **vision + function calling** when the provider rejects the computer tool for the key, which
  is what `muse-wonder-1.0` on this account does today. Both are real Meta inference over real
  screenshots; the trace records which ran.
* **Enforcement**: coordinates resolved to whitelisted elements; unknown or out-of-bounds actions
  stop the run; provider safety checks are never auto-acknowledged; the write is committed by the
  server against target, field, value, version and approval, re-checked immediately before commit.
* **Isolation**: Bubblewrap namespaces, `--clearenv`, read-only system mounts, no workspace, no
  `MODEL_API_KEY`, probed before any action. The scripted path has no OS isolation and says so.
* **Read-back**: a separate read-only principal reads the same portal over HTTP and compares value,
  version and restricted-field hashes. `VERIFIED` only on a successful read-back.
* **Evidence**: chain view, provenance panel, timeline, JSON/HTML/ZIP export with mode labels,
  provider request IDs and explicit omissions.
* **Measurement**: ten end-to-end cases with numerators and denominators (see README §What is
  measured).

## 3. Competitive reality (desk research, 4 November 2026)

Claims below are vendor claims, not independent evaluations, and no hands-on comparison has been run.

* **Skyvern** advertises screenshots, recordings, structured logs and workflows for browser agents:
  https://www.skyvern.com/blog/browser-automation-security-best-practices/ — audit trails alone are
  therefore not novel.
* **UiPath** positions governance and monitoring across agents and automation:
  https://www.uipath.com/agentic-automation/agent-orchestrator
* **Browser Use** provides general browser-agent infrastructure:
  https://github.com/browser-use/browser-use
* **Trustpair** markets supplier bank-account validation and payment-fraud prevention:
  https://trustpair.com/ — ProofPilot does **not** verify account ownership.
* **FBI** guidance on business email compromise recommends verifying account or payment-procedure
  changes through independently obtained contact information:
  https://www.fbi.gov/how-we-can-help-you/scams-and-safety/common-scams-and-crimes/business-email-compromise

**The honest differentiation claim**: not "audit logs", but a workflow-specific
contract → decision → bounded write → independent read-back chain, where the intervention and the
mode that produced each trace are visible in the same UI. Whether that matters enough to switch to
is unknown.

## 4. What is explicitly not claimed

* No validation that this wedge is a real priority for AP teams. No user interviews were run.
* No hands-on competitor evaluation; the comparison above is desk research.
* No bank-account ownership verification, payment processing, or out-of-band callback.
* No external audit: the verifier shares the demo portal's underlying system.
* No model-robustness claim: without a live key, provider responses are scripted fixtures.
* No production identity, secret management, tamper-proof storage or compliance posture.

## 5. Evaluation plan (definitions before numbers)

Report numerator and denominator, and never merge modes:

* **Authorized task success** — approved value written and independently read back `VERIFIED`.
* **Unauthorized mutations** — restricted-field changes; or any change in blocked, cancelled or
  unknown-state cases.
* **Verification correctness** — true/false positives and negatives, including a negative control
  where the record is tampered with after the write.
* **Human intervention** — required decisions (contract approval, ambiguous selection) versus
  unnecessary ones.
* **Failure handling** — blocked, cancelled, unknown, 503 and verification failures surfaced rather
  than retried blindly or counted as success.

Predefined held-out cases: stale record version, ambiguous supplier, simulated 503, untrusted page
content, forbidden fields, malformed provider responses, cancellation, lost acknowledgement.
Deterministic probes are reported separately from model-driven attempts; mock is never combined with
real Meta in one success rate.

## 6. Next validation steps, in order

1. ~~Run the ten cases with a live key; publish live-model numbers separately, with repeat runs.~~
   **Done 4 Nov 2026** — 18 cases, 12 live-model runs: 7/7 authorized success, 0/18 unauthorized
   mutations, verification TP 7 · TN 3 · FP 0 · FN 0, 11/11 failures surfaced, 9/12 runs committed
   a write (9/9 excluding the intentional 503 fixture row). Four identical suites scored 9/12,
   6/12, 8/12 and 9/12: the variance is real, and every shortfall was the model answering in prose
   rather than calling the tool — never an unauthorized write.
1a. Ask Meta to enable the computer-use tool for this key and re-measure on the documented protocol.
2. Five conversations with AP / supplier-master operators: does the read-back receipt change what
   they do today, and what would they pay for?
3. Hands-on comparison against one browser-agent product with audit trails and one supplier-fraud
   product, testing the same three scenarios.
4. Decide whether the wedge is defensible or whether the real value is the enforcement layer, and
   re-scope accordingly.
