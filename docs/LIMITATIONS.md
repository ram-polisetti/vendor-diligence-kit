# Limitations

1. **Structural lineage, not content audit.** The kit verifies that each vendor
   claim *links to a readable document*, not that the document's contents
   substantiate the claim. A vendor can link a real PDF full of nonsense and
   score full lineage points. Reading the documents is still a human job.
2. **Behavioral fairness probes are proxies.** The kit cannot see the vendor's
   real decision logs, so it probes with synthetic group-varying prompts. This
   measures the delivered system's behavior on the probes, not its behavior on
   the deployer's actual caseload.
3. **The citation-faithfulness judge is a word-overlap heuristic.**
   Paraphrased hallucinations that reuse the source's vocabulary can pass
   rag-redteam's check. Treat a pass as weak evidence, a fail as strong.
4. **Use-case tags are heuristic.** `derive_use_case_tags()` is a keyword
   mapper onto ai-act-checker's tag vocabulary; unusual phrasings can miss the
   right Annex III area. The deployer must confirm the tags.
5. **The AI Act mapping is not legal advice.** See the checker's disclaimer;
   verify against the official Act text and qualified counsel.
6. **Refusals are counted as evidence gaps.** A vendor that refuses to answer
   screening-style probes looks "untestable" rather than "safe" in the
   fairness dimension. The report says so explicitly.
7. **Scores are not comparable across runs** unless the same sibling SHAs,
   battery version, and target contract were used — all recorded in the report.
8. **The registry mapping is lossy by design.** The registry allows only
   `approved`/`rejected`; a `conditional` recommendation becomes a qualified
   approval with conditions in the rationale. Read the rationale, not just the
   decision.
