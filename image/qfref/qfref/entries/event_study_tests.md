# Event study (method): market model, abnormal returns and CAAR, Patell, BMP and Kolari-Pynnonen tests

**If the task text defines the formula, inputs or conventions differently, the task text wins.**

## Setting and assumptions
- N events (firms) i = 1..N. Event time: day 0 = event date, counted in trading days of the data (not calendar days).
  Estimation window $\operatorname{E}_{i}$: L1 days before the event window ($t = \mathrm{T0}+1\ldots \mathrm{T1}$). Event window: L2 days ($t = \mathrm{T1}+1\ldots \mathrm{T2}$), contains day 0.
  The test window [tau1, tau2] lies inside the event window; $L = \mathrm{tau2} - \mathrm{tau1} + 1$ counts both ends.
- Null H0: mean abnormal return is zero on the tested day, or mean CAR over [tau1, tau2] is zero.
- Market model $R_{it} = \alpha _{i} + \beta _{i} R_{mt} + e_{it}$, fitted by OLS on $\operatorname{E}_{i}$ only. The exact small-sample results below need
  iid normal $e_{it}$ and no event effect on the estimation window; the Z statistics are asymptotic (N large).

## Inputs and units
| symbol | meaning | units |
|---|---|---|
| $R_{it}, R_{mt}$ | firm and market returns (simple or log, as the task says; 2% is `0.02`) | per day |
| L1, L2, L | estimation, event and test-window lengths in trading days | days |
| $N$ | number of events with valid data ($N_{t}$ on day t if some are missing) | count |

## Market model and abnormal returns (means and sums over the estimation window E_i)

$$
\begin{gathered}
S_{\mathrm{xx}} = \sum _{\operatorname{E}} (R_{mt} - \bar{R}_{m})^{2},  \beta _{i} = \sum _{\operatorname{E}} (R_{mt} - \bar{R}_{m})(R_{it} - \bar{R}_{i}) / S_{\mathrm{xx}},  \alpha _{i} = \bar{R}_{i} - \beta _{i} \bar{R}_{m} \\
e_{it} = R_{it} - \alpha _{i} - \beta _{i} R_{mt} (t \in  \operatorname{E}),   s_{i}^{2} = \sum _{\operatorname{E}} e_{it}^{2} / (\mathrm{L1} - 2) \\
\mathrm{AR}_{it} = R_{it} - \alpha _{i} - \beta _{i} R_{mt} (\mathrm{event} \;\text{window}\;),   \mathrm{CAR}_{i} = \sum _{t=\mathrm{tau1}}^{\mathrm{tau2}} \mathrm{AR}_{it} \\
\mathrm{AAR}_{t} = (1/N) \sum _{i} \mathrm{AR}_{it},   \mathrm{CAAR} = (1/N) \sum _{i} \mathrm{CAR}_{i}
\end{gathered}
$$

Forecast-error (prediction-error) correction, since $\alpha _{i}$, $\beta _{i}$ are estimates:

$$
C_{it} = 1 + 1/\mathrm{L1} + (R_{mt} - \bar{R}_{m})^{2} / S_{\mathrm{xx}}
$$

$$
\mathrm{SAR}_{it} = \mathrm{AR}_{it} / (s_{i} \sqrt{C_{it}})
$$

Exact $t(\mathrm{L1}-2)$, with variance $(\mathrm{L1}-2)/(\mathrm{L1}-4)$.

$$
\operatorname{Var}(\mathrm{CAR}_{i}) = s_{i}^{2} [ L + L^{2}/\mathrm{L1} + ( \sum _{t=\mathrm{tau1}}^{\mathrm{tau2}} (R_{mt} - \bar{R}_{m}) )^{2} / S_{\mathrm{xx}} ]
$$

$$
\mathrm{SCAR}_{i} = \mathrm{CAR}_{i} / \sqrt{\operatorname{Var}(\mathrm{CAR}_{i})}
$$

Exact $t(\mathrm{L1}-2)$. The equivalent matrix expression is $\operatorname{Var}(\mathrm{CAR}_i)=s_i^2 1'(I+X^{*}(X'X)^{-1}(X^{*})')1$, with $X$ and $X^{*}$ the $[1,R_m]$ regressor matrices of E and of the window.

## Patell (1976) Z

$$
\begin{gathered}
Z_{\operatorname{P}} = \sum _{i} X_{i} / \sqrt{\sum _{i} (\mathrm{L1}_{i} - 2)/(\mathrm{L1}_{i} - 4)}        \mathrm{reference} N(0,1); \mathrm{needs} \mathrm{L1}_{i} > 4 \\
\mathrm{equal} \mathrm{L1}:  Z_{\operatorname{P}} = \sqrt{N (\mathrm{L1} - 4)/(\mathrm{L1} - 2)} \cdot  \operatorname{mean}_{i} X_{i}
\end{gathered}
$$

Single day: $X_{i} = \mathrm{SAR}_{\mathrm{i0}}$. Window: $X_{i} = \mathrm{SCAR}_{i}$(version a), or $X_{i} = \mathrm{CSAR}_{i} = \sum _{t=\mathrm{tau1}}^{\mathrm{tau2}} \mathrm{SAR}_{it} / \sqrt{L}$(version b).

Which window version: version (b) standardizes every event day by its own forecast-error variance, $\mathrm{SAR}_{it} = \mathrm{AR}_{it} / (s_{i}\sqrt{C_{it}})$ with a day-specific $C_{it}$, and then sums. When a task defines the standardized residual through a per-day correction $C_{i,t}$ (one value per event day), it specifies version (b); version (a) uses one window-level variance of the CAR and has no per-day $C_{i,t}$. The two give different numbers. BMP and the Kolari-Pynnönen adjustment are then applied to the same $X_{i}$.


## Boehmer-Musumeci-Poulsen (1991) standardized cross-sectional test

$$
t_{\mathrm{BMP}} = \sqrt{N} \cdot  \mathrm{Xbar} / S_{X},   \mathrm{Xbar} = (1/N) \sum _{i} X_{i},   S_{X} = \sqrt{\sum _{i} (X_{i} - \mathrm{Xbar})^{2} / (N - 1)}
$$

$X_{i} = \mathrm{SAR}_{\mathrm{i0}}$ for a single day. For a window, $X_{i}$ is the same window statistic chosen for the Patell test above: $\mathrm{CSAR}_{i} = \sum_{t} \mathrm{SAR}_{it} / \sqrt{L}$ (version b) when the task standardizes each event day with its own correction $C_{it}$, or $\mathrm{SCAR}_{i} = \mathrm{CAR}_{i} / \sqrt{\operatorname{Var}(\mathrm{CAR}_{i})}$ (version a) when it standardizes the window CAR by one window-level variance; the Kolari–Pynnönen adjustment multiplies this same BMP t. Reference t(N-1) (N(0,1) for large N). Robust to event-induced variance.

## Kolari-Pynnonen (2010) adjustment for cross-sectional correlation (clustered event dates)
$\bar{r}$ is the average over the $N(N-1)/2$ pairs $i < j$ of $\mathrm{corr}(e_{i}., e_{j}.)$, the Pearson correlation of the two firms' estimation-window residuals over their common calendar dates (diagonal 1's excluded).
Same reference as BMP:

$$
t_{\mathrm{KP}} = t_{\mathrm{BMP}} \cdot  \sqrt{(1 - \bar{r}) / (1 + (N - 1) \bar{r})}
$$

Adjusted Patell: software implementations multiply $Z_{\operatorname{P}}$ by the same factor; the variance of $Z_{\operatorname{P}}$ under equicorrelation
gives $Z_{\operatorname{P}}$ / $\sqrt{1 + (N - 1) \bar{r}}$. They differ by $\sqrt{1 - \bar{r}}$; use the one the task names.

## Corrado rank test
See the separate entry corrado_rank_test.

## Common variants and mistakes
- Randomization p-values (sign-flip, permutation, bootstrap) count draws whose statistic is at least as extreme as the observed one. The draw that reproduces the observed sample (all signs +1, the identity permutation) gives the observed statistic only up to floating-point round-off, so an exact comparison such as `abs(t_star) >= abs(t_obs)` can drop it or keep it by chance. Compare with a relative tolerance, for example `abs(t_star) >= abs(t_obs) * (1 - 1e-12)`, and check that the reproducing draw is counted.
- $s_{i}^{2}$ divisor: L1 - 2 (market model), L1 - 1 (constant-mean model, where $C_{it} = 1 + 1/\mathrm{L1}$ and
  $\operatorname{Var}(\mathrm{CAR})=s^2(L+L^2/\mathrm{L1})$), L1 (MLE). Market-adjusted model ($\mathrm{AR} = R - R_{m}$): no estimation, $C_{it} = 1$.
- Forecast-error correction omitted ($C_{it} = 1, \operatorname{Var}(\mathrm{CAR}) = L s_{i}^{2}$) is a common simpler variant; it changes the number.
- Patell window version a vs b, and BMP on SCAR vs on CSAR, give different numbers; follow the task's wording.
- BMP compared with t(N-1) vs N(0,1); one-sided vs two-sided p-values; p = 2 * (1 - F(|stat|)) for two-sided.
- Off-by-one windows: (-1, +1) is three days; the estimation window must end before the event window starts.
- Lagged regressors: compute the change series once and shift it by exactly one row; re-deriving lagged differences with nested index offsets shifts twice and can leave the earliest windows empty.
- A lagged fit inside a window (y_t on y_{t-1}, as in an AR(1) of daily changes): take the positions `js` of the window's responses in the full series and pair each with its own previous value, `y = series[js]`, `x = series[js - 1]`, then fit once and reuse the coefficients for the forecast. Cutting the window out first and offsetting it (`w[1:]` against `w[:-1]`) drops the window's first response, whose previous value lies just before the window. If the task requires both values of a pair to lie inside the window, follow the task.
- When a window is stated as the n valid observations before an event → keep the rows where every field the window needs is valid, then take the last n of them before the event (`valid = frame.dropna(subset=needed_fields); window = valid[valid.index < event_date].iloc[-n:]`); n positions of the raw index span invalid rows and give a different window. Check the window length and its first and last dates.

## Applicability and known limits
- Our null simulation (validation.md): all tests are near nominal size with iid normal residuals. Fat-tailed residuals
  make Patell over-reject (about 7% at nominal 5%); BMP and Corrado stay near nominal.
- Event-induced variance (higher variance in the event window): Patell and Corrado over-reject strongly; BMP does not.
- Same event date for all firms with correlated residuals: Patell and BMP over-reject badly even for small rbar;
  KP-adjusted BMP and the variance-algebra adjusted Patell restore the size; Corrado stays close to nominal.
- KP adjustment without clustering adds noise from rbar and slightly over-rejects; compute rbar on overlapping
  calendar dates and adjust only when event windows overlap in calendar time.
- Patell version b over-rejects for long windows (daily SARs share the estimation error); version a is exact.
- The multi-day Corrado statistic under-rejects as L grows (ranks within a firm are dependent).

## Sources
Patell (1976) J. Accounting Research 14(2):246-276; Boehmer, Musumeci & Poulsen (1991) J. Financial Economics
30(2):253-272; Kolari & Pynnonen (2010) Review of Financial Studies 23(11):3996-4025; Corrado (1989) J. Financial
Economics 23(2):385-395; Corrado & Zivney (1992) J. Financial and Quantitative Analysis 27(3):465-478; Cowan (1992)
Review of Quantitative Finance and Accounting 2:343-358; Campbell & Wasley (1993) J. Financial Economics 33(1):73-92;
MacKinlay (1997) J. Economic Literature 35(1):13-39; Campbell, Lo & MacKinlay (1997) The Econometrics of Financial
Markets, Princeton UP, ch. 4.
