# Human grading

`labels/` is tracked: it holds the judge's label rows exported per dimension
(`judge-D1.jsonl` ...) and the human label files exported from the grading tools
(`labels-<rater>-<rubric hash>.jsonl`, renamed per dimension when saved here). Every row's
`item_id` is a deterministic pool key, so the rows join back to their run and index however many
times the pool is rebuilt.

`tools/` is generated and ignored: the HTML grading tools and their items file are rebuilt from
the pool with one command.
