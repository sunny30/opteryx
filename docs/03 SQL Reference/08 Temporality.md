# SQL Temporality

Partition schemes that supports temporal queries allow you to view data from a different time by using a `FOR` clause in the SQL statement. `FOR` clauses state the date, or date range, a query should retrieve results for.

If not temporal clause is provided, `FOR TODAY` is assumed.

Where multiple dates are provided, they have an implicit `UNION` applied to them.

## Valid Clauses

Clause             | Description                           | Example
------------------ | ------------------------------------- | ---------------------------
`FOR 'date'`       | Data as at a specific date            | `FOR DATE '2022-09-16'`
`FOR DATES BETWEEN 'date' AND 'date'` | Data between two specific dates | `FOR BETWEEN DATES '2000-01-01' AND '2000-12-31'`  

Date values in `FOR` clauses must either be in 'YYYY-MM-DD' format or a recognised date placeholder:

- `TODAY`
- `YESTERDAY`

for example: `FOR DATES BETWEEN '2000-01-01' AND TODAY`

## Limitations

- `FOR` clauses cannot contain comments or reference column values or aliases
- Dates can not include times and must be in the format 'YYYY-MM-DD'
- The default partition scheme does not support Temporal queries