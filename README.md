# ProofPilot

**Move the shipment. Never the payment.**

ProofPilot is a verifiable supplier-master change control system designed to defeat payment-diversion attacks and indirect prompt injection. Rather than allowing an autonomous agent to execute direct mutations, ProofPilot confines operations to an inviolable chain:

$$\text{Contract} \longrightarrow \text{Decision} \longrightarrow \text{Bounded Write} \longrightarrow \text{Independent Read-back} \longrightarrow \text{Inspectable Evidence}$$

All demo endpoints, data, and suppliers are fictional. Designed for controlled demonstration and safety evaluation.

---

## Repository Layout

```
proofpilot/
├── proofpilot/                     # Runnable implementation, web portal, and tests
│   ├── portal/                     # Server, workflow contracts, policy gates, executor, UI
│   ├── evaluation/                 # Test runner, matched scenario comparisons, E2E benchmarks
│   ├── demo/                       # Scripted UI rehearsal runner and submission runbook
│   ├── product/                    # Product reset, competitive notes, and validation hypotheses
│   ├── reports/                    # Pre-generated evaluation reports, metrics, and rehearsal recordings
│   ├── tests/                      # Automated test suite (60+ unit and integration tests)
│   ├── Makefile                    # Target automation (test, run, reset, evaluate, rehearse)
│   ├── README.md                   # Detailed implementation documentation
│   └── requirements.txt            # Python dependencies (Playwright, Pillow)
└── proofpilot-spec/                # Architecture specifications and discovery documents
    ├── ProofPilot_Master_Specification.md  # Complete 45KB master system specification
    └── Factory_Replay_Discovery_Brief.md   # Companion discovery concept for industrial safety
```

---

## Core Security & Architecture Principles

1. **Deterministic Task Contracts (`portal/workflow.py`)**  
   Approved CSV instructions are transformed into cryptographically hashed contracts binding the request ID, supplier name, supplier ID, and target value. Ambiguous entities (e.g., duplicate supplier legal names) strictly require human resolution with an expiring TTL; automated resolution is prohibited.

2. **Server-Enforced Capability Boundary (`portal/server.py`, `portal/executor.py`)**  
   Browser agents cannot write directly to the database. Mutations require short-lived, HMAC-signed capability tokens binding run ID, supplier ID, record version, and target value. Forbidden fields (such as `bank_account` or `tax_id`) are rejected atomically (HTTP 403) before any write occurs.

3. **Dual-Protocol Meta Computer-Use Loop (`portal/meta_agent.py`)**  
   Supports Meta `muse-wonder-1.0` via the Responses API. The system attempts the documented `computer_call` batched tool first; when unsupported on the provider key, it falls back seamlessly to **vision + function calling** (`propose_action` tool with strict whitelisted actions). Every trace discloses whether real model inference, mock, or scripted execution took place.

4. **OS Sandbox Isolation (`portal/sandbox.py`)**  
   Under Linux, the browser worker executes inside unprivileged Bubblewrap (`bwrap`) containers using isolated user, network, PID, IPC, and mount namespaces with `--clearenv` to guarantee the model API key never leaks to the execution environment.

5. **Independent Read-Back Verifier (`portal/proof.py`)**  
   Commits are held in a `WRITTEN_UNVERIFIED` state until a separate read-only principal (`verifier` identity) independently polls the live API over HTTP, confirms value parity, version increment, and verifies SHA-256 hashes of restricted fields remain unchanged.

6. **Exportable Evidence Packages**  
   Every completed run generates downloadable JSON, HTML, and ZIP bundles containing DOM action traces, screenshots, request tokens, and cryptographic verification receipts.

---

## Quickstart

### Prerequisites
- Python 3.10+
- Playwright Chromium (`python3 -m playwright install chromium`)
- Bubblewrap (`bwrap`) for Linux sandbox isolation (optional on macOS)

### Running Locally

```bash
cd proofpilot

# Install dependencies
python3 -m pip install -r requirements.txt
python3 -m playwright install chromium

# Run the test suite
make test

# Run end-to-end evaluation and generate reports
make evaluate

# Run demo UI rehearsals
make rehearse

# Start the interactive workspace portal
make run
# Open http://127.0.0.1:8000/workspace
```

---

## Detailed Documentation

- [Implementation README](proofpilot/README.md)
- [Master System Specification](proofpilot-spec/ProofPilot_Master_Specification.md)
- [Demo & Submission Runbook](proofpilot/demo/DEMO_AND_SUBMISSION_RUNBOOK.md)
- [Product Reset & Strategy](proofpilot/product/PRODUCT_RESET.md)
