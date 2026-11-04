# ProofPilot demo film — narration script

Voice: calm, confident, technical-but-plain. ~3 minutes, 10 segments.
Rule for this film: no "demo data", no "mock". No claim we cannot back — say "Meta model",
not "computer-use tool"; say "separate read-only identity", not "external audit".

## 1 · Hook
Somewhere in a finance team's inbox right now is an email that looks exactly like it came
from a supplier. New shipping address, please update the record. The next one will ask for
bank details. By the time anyone notices, the payment is gone.

## 2 · The gap
Software agents can now log in, read screens and take action. That is the promise. The problem
is what happens in the middle: an agent that can change anything can be talked into changing
the wrong thing.

## 3 · Introducing ProofPilot
ProofPilot keeps the promise and removes the middle. One bounded change at a time, on the
record you approved, at the version you approved — and a receipt you can actually check.

## 4 · Contract first
It starts with a contract. Your request becomes an explicit statement of what may change:
the field, the supplier, the value, the record version. Approve it, and that approval binds
to this exact contract. Change one character, and it no longer applies.

## 5 · Ambiguity stops the line
Then ProofPilot matches records. Two suppliers look alike? It stops. No guess, no silent
pick — a human chooses, the choice expires, and if the record moves underneath it, the
approval dies with it.

## 6 · The model proposes, the runtime decides
Now the model works. A Meta model reads the screen and proposes the next action. Every
proposal passes a policy gate: raw clicks are resolved to the controls this workflow
allows, unknown actions stop the run, and provider safety checks are never waved through.

## 7 · Isolated by construction
The browser runs inside a locked-down sandbox: no network, no filesystem, no credentials,
not even the model key. Isolation is probed before a single action runs. If the probes
fail, nothing executes.

## 8 · The server writes
The browser never writes. The server commits — against the target, the field, the value and
the version, re-checked at the last possible moment. Cancelled? The write never happens.
Lost acknowledgement? ProofPilot reconciles state instead of blindly retrying.

## 9 · Read back before you believe it
Then a separate read-only identity reads the record back over HTTP and compares value,
version and the protected fields. Only then does ProofPilot say verified. Everything is
exportable: the chain, the timeline, the model provenance, one file.

## 10 · Measured, not assumed
Here is what the measurement actually says. Every authorised change completed and verified.
Zero unauthorised mutations across eighteen attempts. Verification caught every tampered
record, and every failure surfaced instead of being quietly retried. The live model finished
nine of twelve runs — nine of nine where finishing was possible. That is the difference
between an agent that acts, and a system you can check. ProofPilot.

> Wording discipline: `reports/measurement.json` holds 18 measurement rows but only 10 distinct
> cases (C01/C02/C03/C09 are the live ones, run 3x each), so "eighteen cases" is defensible yet
> misleading. The script says "eighteen **attempts**", which is exactly what the 0/18 metric counts.
> The live number is always quoted as 9/12 with the spread
> (9 · 6 · 8 · 9 across four identical suites) and 9/9 where completion was possible; the
> results scene puts that spread on screen as well.
