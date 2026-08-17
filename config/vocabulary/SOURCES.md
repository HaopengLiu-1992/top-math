# Vocabulary Catalog Sources

The checked-in catalog is `academic_word_bank_10000.json`, version
`g5-g8-2026.08`. It is a local selection catalog, not a copy of a commercial
publisher's grade-level list.

## Research basis

- The Common Core language standards require students in Grades 5-8 to acquire
  general academic and domain-specific words, rather than prescribing one
  universal list. See [Grade 5 L.5.6](https://www.thecorestandards.org/ELA-Literacy/L/5/6/)
  and the [full ELA standards](https://corestandards.org/wp-content/uploads/2023/09/ELA_Standards1.pdf).
- The Middle School Vocabulary Lists (MSVL) research separates English,
  mathematics, science, health, and social studies vocabulary for Grades 6-8.
  It is used here as a design reference for subject layering, not copied into
  the product because its [site terms](https://www.eapfoundation.com/terms/)
  restrict reuse for commercial products. See the [MSVL research page](https://www.eapfoundation.com/vocab/other/msvl/index.php?list=math&sort=none).
- The catalog uses the `wordfreq` frequency database to rank common English
  words and Princeton WordNet 3.0 to provide local English definitions.

## Build inputs

- `curated_math_science_core`: 275 local teaching entries retained in their
  existing order and category labels.
- [`wordfreq==3.1.1`](https://github.com/rspeer/wordfreq): frequency ranking
  for the general reading pool. Review the package and bundled-data licenses
  before redistributing a modified catalog commercially.
- [Princeton WordNet 3.0](https://wordnetcode.princeton.edu/3.0/): English
  definition source for generated catalog entries. The WordNet license allows
  commercial use with the required copyright and license notice.

The build-time dependencies are listed in
`requirements-vocabulary-build.txt`. The running app does not need them; it
loads the generated JSON and index only. To rebuild the files, install those
dependencies, download the WordNet corpora (`wordnet` and `omw-1.4`), and run:

```bash
python scripts/build_vocabulary_catalog.py
```

The generated entries include `grade_min`, `grade_max`, `category`, frequency
metadata, and definition provenance. Grade bands are an explicit frequency
heuristic with a domain overlay, not a claim that every US school district
teaches the word in exactly that grade.
