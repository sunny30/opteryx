# Query Optimization

## 1. Avoid `SELECT *`

Selecting only the fields you need to be returned improves query performance by reducing the amount of data that is processed internally.

A principle the Query Optimizer uses is to eliminate rows and columns to process as early as possible, `SELECT *` removes the option to remove columns from the data being processed.

## 2. Prune Early

Where available, use temporal filters (`FOR DATE`) to limit the date range over will limit the number of partitions that need need to be read.

Not reading the record is faster than reading and working out if it needs to be filtered out of the result set.

## 3. GROUP BY

**strings**
Grouping by string columns is slower than grouping by numeric columns, if you have an option of grouping by a username or a numeric user id, prefer the user id.

**cardinality**
Grouping by columns with high cardinality (mostly unique) is much slower than grouping where there is a lot of duplication in the groups.
