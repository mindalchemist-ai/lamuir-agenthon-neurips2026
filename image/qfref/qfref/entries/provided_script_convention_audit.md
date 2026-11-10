# Debugging a provided pricing script against a convention contract

The task description inside <task_instructions>, and any conventions file it names, take priority over this card: where they state a different rule, follow them.

Use when a task gives a script that "runs but produces wrong outputs" together with a conventions file or a list of conventions in the task text. Audit explicit conventions alongside implementation correctness; do not assume either is already correct.

## Rule that is easy to miss

A value reported "from the perspective of" a party named in the inputs (pay or receive, long or short, buyer or seller) takes its sign from that input field. Find every place the script fixes such a sign in code, replace it with a branch on the input field, and after the final run print the input field next to the sign of each reported value.

## Algorithm: convention audit before editing

```text
1  contract <- every convention the task text and the conventions file state, one line each:
       instrument / leg, day count, payment frequency, schedule direction and roll, discount curve,
       projection curve, interpolation and extrapolation, compounding, sign or direction rule, build order
2  for each function in the script:
       list every day-count call, frequency or step, curve object used for discounting, curve used for
       forwards, interpolation call, and sign choice, with its line number
3  table <- one row per item:
       contract source | instrument / leg | function and line | actual behavior | required behavior | status
       status is match, mismatch, or unresolved (contract unclear: do not guess); check each leg separately,
       even when two legs share a helper name or a similar line
4  print the table; every mismatch row is a bug to fix, including rows in helper functions that look correct
       for another reason (for example a leg discounted on the right curve but accrued with the wrong day count)
5  edit ONE writable working copy cumulatively: never restart from the original file after fixes were made;
       scope each replacement to the intended function or leg, check that it matched the expected number of
       times, and print the resulting diff
6  compile and run the final edited file; check the outputs from that run in the required directory.
       A successful edit message or an output written by an earlier version is not evidence of a fix
7  verify: every input instrument reprices to its quote; a reprice that matches does NOT prove the
       conventions, because a bootstrap and a repricer that share the same wrong helper still agree
```

## Checks after the fix

1. The audit table has no mismatch row left, and each fixed line is printed with its new value from the final file.
2. Instruments reprice to their quotes within the stated tolerance.
3. One hand calculation for a single cash flow per leg (accrual fraction, discount factor, forward) matches the script.
4. Build order: a curve used for discounting inside another curve's bootstrap is built first.
5. Direction: values reported "from the perspective of" a party use that party's sign.

## Common mistakes

- Checking which curve a function uses and not which day count it uses, or the reverse.
- Trusting a helper because its name matches the leg (an `annuity` helper can still accrue with the float-leg day count).
- Stopping after the repricing check passes.
