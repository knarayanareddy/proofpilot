# Factory Replay: Independent Discovery Brief

**Status:** Research and discovery concept—not part of the ProofPilot demo build  
**Version:** 1.0 · 4 November 2026  
**Companion:** `ProofPilot_Master_Specification.md`

## 1. Concept

Factory Replay is an evidence-linked investigation workspace for industrial near misses. A safety investigator supplies a video clip and relevant site procedure; the system proposes a timeline with references to source frames, potential hypotheses, missing evidence and clear uncertainty. A human investigator reviews and corrects the output before any report is exported.

**Product positioning:** investigation assistance, not fault determination, real-time safety control, employee surveillance, or automated compliance certification.

## 2. Initial use case

A forklift and pedestrian appear near an intersection in a controlled or consented warehouse recording. The investigator needs to reconstruct what is visible and determine what other evidence should be collected.

**Inputs:** video, incident timestamp, site procedure; optionally camera map and equipment records.  
**Outputs:** timestamped observations, object-track overlays, procedure citations, alternative hypotheses, missing-evidence list and human-reviewed report.

**Example:** “A forklift and a pedestrian appear near the same intersection. Actual separation and the operator’s field of view cannot be established from this uncalibrated camera.”

## 3. User and problem hypotheses

- **Primary user:** workplace safety investigator.
- **Potential buyer:** warehouse or industrial site safety leadership.
- **Affected stakeholders:** workers, worker representatives, privacy officers, site managers and insurers.
- **Hypothesis:** assembling relevant evidence and documenting uncertainty takes time; investigators may value a reviewable evidence timeline. This is unvalidated until interviews and user testing.

### Discovery questions
1. How are near misses identified and reported today?
2. Which footage, logs and procedures are actually available?
3. What creates the most investigation delay?
4. What evidence would a safety professional trust or reject?
5. What worker privacy protections and consultation are required?
6. Who decides whether the product can be piloted and where data may be processed?
7. What outcomes matter more than detection accuracy—time, completeness, learning, or something else?

## 4. Candidate MVP

1. Upload a single synthetic/consented clip and a sample procedure PDF.
2. Select an approximate event window.
3. Use Muse to propose candidate timestamped observations.
4. Use SAM 3.1 to highlight and track a forklift and person across a selected clip.
5. Link each observation to its clip and classify it as observed, inferred, unknown, document-derived or reviewer-authored.
6. Retrieve relevant procedure passages with page references.
7. Present at least two possible explanations and explicitly list evidence gaps.
8. Let the investigator edit, reject and approve claims.
9. Export a report with evidence and limitations.

### Explicit exclusions
No face recognition; identity or emotion inference; individual productivity scoring; fault assignment; automatic disciplinary recommendations; real-time alerts or control; numerical distance/speed from uncalibrated footage; declarations of legal compliance.

## 5. Technical concept

```text
Video + procedure + optional site map
        ↓
Secure ingestion + timestamp indexing
        ↓
SAM 3.1 object masks/tracks + Muse video observations
        ↓
Evidence-linked timeline and cited procedure passages
        ↓
Hypotheses + missing evidence + human correction
        ↓
Reviewed report
```

SAM produces masks/tracks, not collision-risk or causal conclusions. Muse may generate candidate descriptions but must not be the sole authority for factual or safety claims. Validate all model output against source evidence and human review. Meta documentation: https://dev.meta.ai/docs/media-segmentation and https://dev.meta.ai/docs/models.

## 6. Evidence and safety requirements

- Each factual observation links to a time range and clip/frame; procedure references include document/page.
- Label uncertain interpretation as inference, not fact; require explicit unknowns.
- Do not estimate physical distance or speed without calibrated geometry, validated measurement pipeline and error bounds.
- Record who edited and approved a report; preserve original evidence separately from generated text.
- Use synthetic or properly authorized data; minimize personal data and retention.
- Consult affected workers and privacy/legal experts before any workplace pilot. Assess GDPR, local labor rules and applicable AI Act classification for the actual use; do not assume a safety purpose automatically makes monitoring lawful.

## 7. Research and datasets

- NVIDIA synthetic warehouse scenes include forklift–human near-miss scenarios and multi-view synthetic clips: https://huggingface.co/datasets/nvidia/PhysicalAI-WorldModel-Synthetic-Warehouse-Operations-Scenes. Check license, data size, permitted use, and sampling. Synthetic performance does not establish real-site performance.
- Published workplace safety behavior dataset: https://www.sciencedirect.com/science/article/pii/S235234092400756X. Check terms, labels and fit.
- Examine competitors and existing safety workflows before claiming novelty. The candidate differentiation is evidence provenance, uncertainty, competing hypotheses and human review—not merely detecting forklift proximity.

## 8. Evaluation proposal

Create annotated, consented or synthetic clips with event and non-event cases. Split by scene/camera/site when real data is available; avoid near-identical clips across train/test.

| Metric | Definition |
|---|---|
| Event retrieval recall | Relevant annotated events surfaced / total annotated relevant events |
| False alerts | Non-events surfaced per reviewed camera-hour; report dataset context |
| Temporal localization | Difference between predicted and annotated time ranges |
| Claim support | Reviewer-supported factual claims / all factual claims |
| Unsupported causal claims | Unsubstantiated causal claims / all reports |
| Review time | Investigator time with and without tool, under comparable tasks |
| Human correction | Rate and type of edits; disagreement among reviewers |

Show sample sizes, annotation procedure, failure cases, camera conditions and privacy constraints. Do not extrapolate synthetic metrics to deployment.

## 9. Discovery phases and definitions of done

### A. Stakeholder research
- [ ] Interview safety investigators and affected stakeholders, with consent.
- [ ] Document current workflow, pain points and unacceptable uses.
- [ ] Identify a domain adviser and potential lawful data sources.
- [ ] Document hypotheses rather than assert customer demand.

### B. Feasibility prototype
- [ ] Process one permitted clip and one sample procedure.
- [ ] Display timestamped candidate observations with evidence links.
- [ ] Track at least the relevant objects using SAM 3.1; disclose misses.
- [ ] Explicitly show unknown physical distances and occluded viewpoints.
- [ ] Human can edit and reject claims.

### C. Evaluation
- [ ] Build a small, documented event/non-event set with expert annotation.
- [ ] Measure retrieval, claim support, false positives and review effort.
- [ ] Report failures, data limitations and sample sizes.
- [ ] Complete privacy and worker-impact assessment for intended data use.

### D. Pilot decision
- [ ] Safety partner confirms a concrete use case and acceptable controls.
- [ ] Legal/privacy review and worker consultation are complete where required.
- [ ] Pilot is human-reviewed only, has defined access/retention and stop conditions.
- [ ] No claims of live safety protection or incident reduction without evidence.

## 10. Relationship to ProofPilot

Factory Replay is a separate product, dataset, user group and validation effort. It may eventually reuse generic evidence-store, claim-linking, timeline and review components, but this is not a dependency of the ProofPilot hackathon demo. Do not conflate security of a digital agent with reliability of physical-world incident analysis.
