# Knowledge contribution contract

Knowledge is a typed, source-backed learning object, not an unreviewed prose
dump. A contribution must include:

- stable concept id, title, domain, and content type (`Concept`, `Definition`,
  `Theorem`, `Equation`, `Derivation`, `Proof`, `Assumption`, `Prerequisite`,
  `Example`, `CodeExample`, `FinancialInterpretation`, `QuantApplication`,
  `StrategyApplication`, `Misconception`, `Exercise`, or `SourceReference`);
- prerequisites and an explicit learning path position;
- intuition, formal statement, equations/derivation or proof when applicable;
- runnable, deterministic code examples with expected output when applicable;
- financial interpretation and quant/strategy application boundaries;
- common misconceptions and a correction;
- authoritative source references, retrieval/capture date, rights basis, and
  a reviewer.

AI may help draft or test an entry, but an unreviewed AI output must never be
merged as authoritative knowledge. Avoid unsupported claims, invented sources,
false precision, and promises of alpha. Run the knowledge schema validator and
the focused tests before opening a pull request.
