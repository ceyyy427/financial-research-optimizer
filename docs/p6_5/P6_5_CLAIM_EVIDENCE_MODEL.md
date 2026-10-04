# P6.5 Claim and Evidence Model

## Claim taxonomy

Every important user-facing statement is a typed `Claim`:

| Type | Meaning in the CPI journey | What it cannot imply |
| --- | --- | --- |
| `FACT` | A value/time directly reported by an admitted source | causal meaning or a forecast |
| `INTERPRETATION` | A bounded reading of source facts | that the interpretation is source-reported truth |
| `HYPOTHESIS` | A falsifiable proposed mechanism/test | that it has already been supported |
| `QUANT_FINDING` | A normalized output of the typed P6 experiment | out-of-sample or future performance |
| `UNKNOWN` | A material question not resolved by current evidence | a license to fill the gap with prose |
| `LIMITATION` | A scope, timing, revision, or design constraint | a hidden footnote that can be omitted from UI |

Each claim contains a bounded ID, text, one or more evidence IDs, an
`EvidenceStatus`, optional source fingerprint, verification flag, and explicit
limitations. A claim without evidence is invalid at the product boundary.

## Evidence records and links

`Evidence` records state:

- the evidence ID/type (`TransportCapture`, `OfficialDocument`, `QuantRun`,
  etc.);
- the original source and optional capture;
- a reference (artifact ID, URL, or P6 run ID);
- scope and limitations;
- structured status: `DIRECT_SOURCE`, `DERIVED_FROM_SOURCE`,
  `QUANT_SUPPORTED`, `THEORY_SUPPORTED`, `PARTIALLY_SUPPORTED`, or
  `INSUFFICIENT_EVIDENCE`;
- a source/result fingerprint where one exists.

`ClaimEvidenceLink` is a first-class many-to-many relation. It records support
type, scope, and limitations instead of implying that every linked item proves
the whole sentence. The SQL schema and the in-memory `EvidenceBundle` both
reject unknown evidence IDs.

## Verification boundary

`verified_claim(...)` is the issuer path. It requires non-empty evidence and a
matching source fingerprint, then issues a model-level verification token that
cannot be serialized or supplied as ordinary user data. `TrustedEvidenceRegistry`
and `EvidenceBundle` re-check the relationship before a claim is displayed.
Directly self-setting `source_verified=True`, or supplying a self-consistent
hash without an approved evidence record, must fail or remain unverified. This
prevents provenance from becoming a claim attribute that callers can forge.

The quant path is analogous: the existing P6 gateway returns a successful
`QuantRun`/result fingerprint and limitations; P6.5 wraps that normalized
response as `QUANT_SUPPORTED` evidence. A metric copied from an arbitrary
payload is not quant evidence.

## Show Evidence contract

`EvidenceBundle.show_evidence(claim_id)` returns a bounded projection with:

```text
claim ID/type/text
evidence ID/type/status
publisher source ID and reference
scope and limitations
source fingerprint
```

The SQL repository’s `show_evidence` additionally joins publisher, canonical
URL, capture ID/times, and raw artifact ID. This is the product-facing path for
answering “why should I believe this?” without exposing arbitrary SQL.

## CPI examples

- **FACT:** “BLS `CUUR0000SA0` was [captured value] for 2024-12.” Linked to the
  official release and raw API capture; limitation: the API row has no public
  vintage identifier.
- **INTERPRETATION/THEORY:** “Inflation may affect rate expectations, yields,
  discount rates, and valuation.” Linked to the mechanism map and marked
  `THEORY_SUPPORTED`; it is not a causal event result.
- **QUANT_FINDING:** “The fixed historical experiment produced normalized
  metrics.” Linked to the P6 `QuantRun`; limitations include fixture/sample
  design and no-causality boundary.
- **UNKNOWN:** “The release alone does not determine tomorrow’s equity return.”
  This is an explicit unresolved claim, not an omitted caveat.

## LLM policy

The model may propose candidate claims, concepts, mechanisms, or explanation
structure. It may not persist those proposals as FACT or authoritative source
metadata without evidence resolution and typed validation. Source text and
footnotes are inert data and never instructions.
