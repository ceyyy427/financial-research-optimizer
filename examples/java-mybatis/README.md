# Java/MyBatis example

This example is a read-only data-access adapter. It demonstrates how to map a canonical financial observation window into Java types before exporting a snapshot for the statistical/deep-learning pipeline.

Files:

- `MarketObservation.java`: point-in-time-safe domain record;
- `MarketObservationMapper.java`: parameterized mapper interface;
- `MarketObservationMapper.xml`: ordered window query and explicit result mapping.

The example intentionally omits database credentials, a production `pom.xml`, and model code. Add those only in the consuming application. After retrieval, save the query/provenance manifest and run the Skill's data audit before fitting any model.
