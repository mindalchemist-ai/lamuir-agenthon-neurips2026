# Corrado (1989) generalised rank test (method): the cross-event rank statistic for event studies

Purpose: a nonparametric test of abnormal returns on an event day or over an event window, built from ranks.

Before ranking: relative event days (-5 ... +5) are labels, not array positions. When the estimation residuals and the
event-window abnormal returns are joined into one array, map each relative day to its position explicitly; a negative
relative day used as a NumPy index reads from the end of the array.

```python
joined = np.concatenate([est_resid, event_ar])          # estimation window first, then the event window
pos = {d: len(est_resid) + k for k, d in enumerate(event_days)}   # event_days in window order, e.g. range(-5, 6)
assert joined[pos[0]] == event_ar[list(event_days).index(0)]      # day 0 reads the event-day abnormal return
```

How to compute

Ranks. For each event i, put its estimation-window residuals and its event-window abnormal returns into one array of T_i values and rank them jointly (1 = smallest, ties get the average rank). Turn each rank into a centred score:

```text
d_it = rank_it / (T_i + 1) - 0.5
```

Scaling. There are two forms; they give different numbers. Pick the one that matches how the task describes the normalisation:

| form | when the task describes | daily statistic Z_t |
|---|---|---|
| event-level | each event normalised by the dispersion of its own scores, or a statistic built event by event and then combined | s_i = sqrt(mean of d_it^2 over all T_i days of event i); Z_t = sqrt(N_t) * mean over events of (d_it / s_i) |
| pooled-day | the dispersion over time of the daily average score across events | D_t = mean over events of d_it; S = sqrt(mean of D_t^2 over all pooled days); Z_t = D_t / S |

If the wording settles neither, state which form was used.

Window statistic, both forms: Z_window = (sum of Z_t over the window days) / sqrt(number of window days).

Easy to get wrong

- Every dispersion (s_i or S) is taken over all pooled days of the event, estimation window plus event window, never over the event window alone.
- Rank within each event's own pooled array, never across events and never within the event window only.
- Keep the numerator and the denominator from the same form.
- Divisors are plain means (population form), not n - 1.

Check before writing the output: compute both forms from your own d matrix, print them, and confirm the value you write equals one of them.

Relative event days are labels, not positions. In each pooled array (estimation days first, then the event window)
relative day `day` sits at position `n_est + (day - first_day)`, where `first_day` is the first label of the event
window (for a window -m..+m it is -m). Indexing with `n_est + day` reads the wrong day whenever the window starts
before day 0.

```python
def corrado_both(d, est_len, first_day, day):  # d: per-event score arrays; est_len: estimation lengths; first_day: first event-window label
    import numpy as np
    pos = [n + (day - first_day) for n in est_len]
    ev = np.array([di[p] for di, p in zip(d, pos)])
    s = np.array([np.sqrt(np.mean(np.asarray(di) ** 2)) for di in d])
    event_level = np.sqrt(len(d)) * np.mean(ev / s)
    D = np.mean(np.vstack(d), axis=0)          # needs equal T_i; pooled-day form
    pooled_day = D[pos[0]] / np.sqrt(np.mean(D ** 2))
    return event_level, pooled_day
```

Sources: Corrado (1989), Journal of Financial Economics 23(2); Corrado and Zivney (1992), Journal of Financial and Quantitative Analysis 27(3).

Reminder: Corrado dispersions (s_i or S) use all pooled days, estimation plus event window, never the event window alone.
Reminder: pick the event-level or pooled-day form from the task's wording, keep numerator and denominator from that form, and print both forms once to check.
