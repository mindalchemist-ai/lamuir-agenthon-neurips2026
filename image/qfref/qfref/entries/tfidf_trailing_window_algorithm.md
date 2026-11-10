# Document frequency for TF-IDF, and pre-event trailing features on the daily series
The task description inside <task_instructions> takes priority over this card: where it gives a different formula, input or convention, follow the task description.

A TF-IDF novelty score compares each document with the documents just before it; its document frequency counts documents, not word occurrences. Pre-event features such as a trailing z-score are computed on the underlying daily series at the event's position, not on the much shorter table of events.

```text
Inputs : documents in time order (token lists after the stated normalization);
         a daily series of valid dates with the values the features need; each event's index in that daily series.
Outputs: document frequencies; per event the trailing features.

1. Document frequency: df[term] = number of documents whose token set contains term
   (count each document once: iterate over set(tokens)). Do not use the total count of the term
   across the corpus (a Counter over all tokens).
2. Trailing feature for an event at daily index e over a window of n valid dates:
   window = daily values at indices max(0, e - n) .. e - 1 (the n valid dates immediately before the event);
   apply the stated statistic (mean, sample std with the stated ddof, z-score of the pre-event value).
   The window counts rows of the daily series, never rows of the event table.
```

Checks:
- `df[term] <= number of documents` for every term; at least one term has total count > df.
- For one event, recompute the trailing window by hand from the daily series and print its first and last date: the last date is the valid date immediately before the event date.
- A pre-event feature built from n daily rows changes when the window length changes even if no event is added.
