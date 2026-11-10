# Factor models and regressions: conventions and self-checks

Use this when a task regresses returns on factors or characteristics (time series or cross section), compresses features with PCA, or scores forecasts with an IC. Each rule names the quantity, shows code, and gives an assert.

## 1. Training windows and time labels
A forecast made at row t may use only rows before t for fitting. With a RangeIndex, `.iloc[a:b]` excludes b but `.loc[a:b]` includes b, so `.loc[t-W:t]` holds W+1 rows and leaks row t.
```python
tr = df.iloc[t - W:t]
assert len(tr) == W and tr.index.max() < df.index[t]
```
"Mean of the previous N values": `s.rolling(N, min_periods=N).mean().shift(1)`. Rows before N values exist are undefined: keep them NaN and do not rank or trade on them; `fillna(0)` turns "no signal" into a tradable value.

## 2. One regression per model
Models with different regressor sets (nested or not) are separate fits, each on the rows complete for its own regressors and target. Coefficients of a larger model are not those of a smaller one.
```python
for name, cols in models.items():
    sub = d.dropna(subset=[target] + cols)
    fit = sm.OLS(sub[target], sm.add_constant(sub[cols])).fit()
```
An out-of-sample forecast is intercept plus every slope times its regressor, controls included, standardized as in the fit.

## 3. Counting periods
"Start after the n-th month" can count calendar periods of the sample (periods with no estimate still count) or estimated periods only. They differ when early periods are skipped; compute the start date under the reading the wording supports and assert it.

## 4. PCA orientation
Fit scaler and PCA on the training block only. An eigenvector's sign is arbitrary: decide the sign once from the training scores and multiply both training and new scores by the same s.
```python
pc_tr = pca.transform(sc.transform(Xtr))[:, 0]; pc_t = pca.transform(sc.transform(xt))[0, 0]
s = 1.0 if np.corrcoef(pc_tr, ref_tr)[0, 1] >= 0 else -1.0
pc_tr, pc_t = s * pc_tr, s * pc_t
```
Flipping `components_` and also negating the score flips twice.

## 5. HAC (Newey-West) and GRS
Bartlett weights 1 - l/(L+1), autocovariances divided by T. statsmodels `fit(cov_type="HAC", cov_kwds={"maxlags": L})` matches this; `use_correction=True` multiplies the covariance by T/(T-k). GRS has two consistent forms: (T-N-K)/N with residual covariance /T, or (T/N)(T-N-K)/(T-K-1) with residual covariance /(T-K-1); factor covariance /T in both. Mixing pairs changes the statistic.

## 6. IC, turnover, annualization
Spearman IC = Pearson correlation of ranks; undefined (NaN) when either side is constant. Per-period cross-sectional IC averaged over time differs from one pooled correlation. Turnover and cost reported for a period refer to the executed weights; assert `cost == rate * sum|w_final - w_prev|`. When a neutralizing projection is re-applied to a blend of old and new weights, two supports are possible: every name the blend holds (old names kept) or only this period's selected names (old names dropped); check which one lets the names the text says may carry over keep weight. Annualized return can be arithmetic (mean x P) or geometric ((prod(1+r))^(P/n) - 1); state which.

## 7. Task wording -> API arguments
| call | argument and effect | wording it usually matches |
|---|---|---|
| `Series.std`/`np.std` | `ddof=0` population (numpy, StandardScaler), `ddof=1` sample (pandas) | "population" / "sample", "z-score" |
| `sm.OLS` | no intercept unless `sm.add_constant(X, has_constant="add")` | "with an intercept/constant" |
| `.fit(cov_type="HAC")` | `maxlags=L`; `use_correction`; `use_t` normal vs t p-values | "Newey-West, L lags", "small-sample" |
| `np.linalg.lstsq` | `rcond=None` machine-precision cutoff; minimum-norm on rank deficiency | "least squares", "pseudo-inverse" |
| `rolling` | `min_periods` (default = window); window includes current row unless `closed="left"` (same as `.shift(1)`) | "trailing N" vs "previous N" |
| `pct_change` / `shift` | first row NaN; `shift(-1)` = next-period value | "forward return", "drop first row" |
| `PCA` | centers, never scales; `whiten=False`; sign arbitrary; `random_state` only for randomized solvers | "z-normalize then PCA" |
| `np.median`/`np.percentile`/`quantile` | linear interpolation default | "median", "1st/99th percentile" |
| `np.random.default_rng(s)` vs `np.random.seed(s)` | different streams (PCG64 Generator vs legacy MT19937); the draw order also changes the numbers | the task names the generator; when it only says "use seed s", no reading is standard: numpy recommends the Generator API (`default_rng`) for new code, while code written with the legacy API seeds `np.random.seed(s)`; when a result sits on a discrete step the choice decides it, so say which one is used and keep one generator for every draw |
| `to_csv` | index written as unnamed column unless `index=False`; name it with `rename_axis(name).reset_index()` | first column named in the spec |

Read every written CSV back and assert its header equals the specified column list.

## Sources
Cochrane, *Asset Pricing* (rev. 2005), ch. 12.1 (GRS, time-series regressions) and 12.3 (Fama-MacBeth); Fama & MacBeth (1973) JPE 81(3); Newey & West (1987) Econometrica 55(3); Gibbons, Ross & Shanken (1989) Econometrica 57(5), sec. 2; Grinold & Kahn, *Active Portfolio Management* (2000), ch. 6 (IC); Jolliffe, *Principal Component Analysis* (2002), ch. 2-3; statsmodels 0.15 `RegressionResults.get_robustcov_results`; pandas 3.0 `DataFrame.loc`, `rolling`, `to_csv`; scikit-learn 1.9 `PCA`, `StandardScaler`; NumPy 2.5 `random.default_rng`, `linalg.lstsq`.
