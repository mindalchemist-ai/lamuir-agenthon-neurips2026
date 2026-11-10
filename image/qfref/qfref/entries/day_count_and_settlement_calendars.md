# Day-count fractions, accrual dates and settlement calendars

Use explicit contract conventions. A year fraction, a business-day adjustment and a cashflow's payment entitlement are separate definitions. Currency names alone do not select a calendar or day-count variant. Dates below are ordered start $a\le b$ and end $b$; the discussion concerns date-only accrual, not intraday timestamps. When both endpoints carry a time of day, the ACT/365 numerator is the elapsed time in days, `total_seconds()/86400`, not the whole-day count `.days`.

**Before computing accruals or discount factors in two currencies:** each currency's leg, deposit rate and curve uses that currency's own day-count basis (the trade or quote conventions name it, for example ACT/360 for one currency and ACT/365F for another). One shared year fraction for both legs is a common error that the totals do not reveal. Write one year-fraction function per currency and check that the two give different values for the same dates whenever the bases differ:

```python
from datetime import date
def yf(a, b, basis):
    return (b - a).days / {"ACT/360": 360, "ACT/365F": 365}[basis]
basis = {"CCY1": "ACT/360", "CCY2": "ACT/365F"}         # from the task's conventions
a, b = date(2024, 1, 15), date(2024, 2, 15)
t1, t2 = yf(a, b, basis["CCY1"]), yf(a, b, basis["CCY2"])
assert basis["CCY1"] == basis["CCY2"] or not np.isclose(t1, t2)   # a 1M fraction differs between ACT/360 and ACT/365F
```

## Actual day counts

Let $D(a,b)$ be the integer calendar-day difference. Actual/360 and Actual/365 Fixed use:

$$
\tau_{360}(a,b)=\frac{D(a,b)}{360},\qquad
\tau_{365F}(a,b)=\frac{D(a,b)}{365}.
$$

Leap days belong in the numerator; Actual/365 Fixed does not replace its denominator by 366. Actual/Actual is another family requiring its own definition. Counting business days is not a substitute for actual calendar-day accrual. The ordinary date difference excludes the start and includes the end; reversing the inclusion convention without changing a count can obscure endpoint errors.

## A specified 30/360 US convention

For year, month and day components $(Y_i,M_i,D_i)$, replace the day components by $D_i^*$ using the stated variant. The accrual is:

$$
\tau_{30/360}=\frac{360(Y_2-Y_1)+30(M_2-M_1)+D_2^*-D_1^*}{360}.
$$

For the `Thirty360::USA` implementation cited below, apply these adjustments in order: if the start is February's last day, set its day to 30 and also set the end day to 30 when it too is February's last day; next change an end day of 31 to 30 when the adjusted start day is at least 30; finally change a start day of 31 to 30. Both common and leap-year February endpoints need this test.

This is not a license to use one formula for every label containing 30/360. Bond Basis omits February rules; European 30E/360 clips each 31 independently. Other variants can depend on the termination date. Use the declared variant and applicable market specification rather than silently exchanging them.

As synthetic arithmetic checks, January 31 to February 28 in a non-leap year has a 28/360 US fraction under that variant; February 28 to March 31 has 30/360. A year beginning and ending at February month-end can have actual-day count different from its 30/360 numerator.

## Business-day calendars and date rolls

A calendar decides whether a date is open, including its holiday set and weekend definition. Following moves a closed date to the next open date. Modified Following instead uses the preceding open date if Following would cross the original calendar month. This is different from adding a fixed number of calendar days.

Where settlement requires both markets to be open, the joint business-day indicator is:

$$
I_{\mathrm{joint}}(d)=I_1(d)I_2(d).
$$

The joint holiday set is therefore the union, not the intersection. Some products use other joint-calendar rules; the contract governs. Adding a positive business-day lag counts eligible following business days without counting the start. A zero lag still needs a declared adjustment convention if the start is closed.

Calendar-month advancement precedes any specified business-day roll. Month-end preservation, clamping a nonexistent day and holiday adjustment are distinct rules. Advancing from the original schedule anchor and repeatedly advancing the previous adjusted date can produce different schedules. Under ordinary calendar clamping, a synthetic leap-year January 31 plus one month is February 29; another month from that clamped date is March 29, whereas two months from the original anchor reaches March 31. An explicit end-of-month schedule is a different rule.

## Accrual versus payment

For fixed notional $N$, annual simple coupon rate $r$ and contractual accrual $\tau$, the coupon is:

$$
C=Nr\tau.
$$

For a coupon period with stated full coupon $C$, an elapsed/full-period fraction convention gives accrued interest:

$$
\mathrm{AI}=C\frac{\tau_{\mathrm{elapsed}}}{\tau_{\mathrm{full}}}.
$$

This equals $Nr\tau_{\mathrm{elapsed}}$ only when the coupon and full-period accrual were defined compatibly. A delayed payment date does not automatically lengthen the interest accrual period. Discounting time can use a different day-count basis from coupon accrual. Stub coupons, ex-coupon entitlement and settlement ownership require their contractual rules.

## Sources and limits

[QuantLib Thirty360 implementation](https://github.com/lballabio/QuantLib/blob/master/ql/time/daycounters/thirty360.cpp) and [variant definitions](https://github.com/lballabio/QuantLib/blob/master/ql/time/daycounters/thirty360.hpp) identify the day adjustments above. [Calendar adjustment implementation](https://github.com/lballabio/QuantLib/blob/master/ql/time/calendar.cpp) and [joint calendar rules](https://github.com/lballabio/QuantLib/blob/master/ql/time/calendars/jointcalendar.hpp) distinguish date rolling and calendar combinations. Formula scaling, synthetic examples and the joint-indicator identity follow by date arithmetic and the stated definitions; no live holiday calendar or transaction-specific settlement date is supplied here.
