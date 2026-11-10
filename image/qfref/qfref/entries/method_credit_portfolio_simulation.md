# Method: portfolio credit loss by Monte Carlo rating migration (CreditMetrics, one-factor Gaussian copula)

The task description inside <task_instructions> takes priority over this card: where it gives a different formula, input, setting or convention, follow the task description.

Read the topics relevant to the task; a task usually needs several of them.

## Topic 1: Rating thresholds from a transition row

**Purpose:** Turn one row of migration probabilities into standard normal band edges for the latent variable.

**When to use:** Correlated rating migrations or defaults of a bond portfolio are simulated from a rating transition matrix with a one-factor Gaussian copula.

**Constraints:**

1. Ratings are ordered from best to worst with Default last, as in a transition matrix row.
2. Lay the bands in the direction the task describes (default in the lowest band or in the highest band); both give the same migration probabilities, but the same random draws give different paths.

**How to implement:**

Step 1: Normalize the row of the bond's initial rating so it sums to one.

Step 2: Cumulative probability from the worst rating upwards: for each rating $k$, $c_k=P(\text{new rating is }k\text{ or worse})$, computed by a reversed cumulative sum (`np.cumsum` on the reversed row).

Step 3: Band edges (default in the lowest band): $e_k=N^{-1}(c_k)$ for the boundaries between consecutive ratings (`scipy.stats.norm.ppf`, with the probabilities clipped to $[0,1]$); the edges are descending.

Step 4: Mapping: the new rating index (0 = best) of a latent value $Z$ is the number of edges that $Z$ falls below.

**Double check:**

1. Over many simulations, the frequency of each new rating for a bond is close to its transition row.

## Topic 2: Simulating correlated migrations

**Purpose:** Draw the systematic factor and idiosyncratic shocks and map every bond to a new rating.

**When to use:** After Topic 1, for every simulation and bond.

**Constraints:**

1. Use the random generator, draw order and array shapes the task names; when it gives only a seed, state the choice. Each choice is a valid sample, but the estimates differ by sampling noise.

**How to implement:**

Step 1: Choose the generator and order: `np.random.seed(seed)` with the legacy global functions, or `rng = np.random.default_rng(seed)`; the factor for all simulations first and then the shock matrix, or both per simulation; the shock matrix shaped (simulations, bonds) or transposed.

Step 2: Latent values for all simulations and bonds at once (matrix form, factor broadcast across bonds):

$$Z_{s,j}=\sqrt\rho\,M_s+\sqrt{1-\rho}\,\varepsilon_{s,j}$$

Step 3: New ratings: compare each bond's column of $Z$ with that bond's edges (broadcast the edges against the column and count, `(Z[:, j, None] < edges[None, :]).sum(axis=1)`); loop over bonds only, never over simulations.

Step 4: Loss per bond and simulation, by the loss definition the task uses:

1. Default mode: only defaults lose, $(1-R)\cdot\text{face}$.
2. Mark-to-market: every migration revalues the bond with the forward value for its new rating, so downgrades also lose. Use it when the task supplies forward values or spread curves by rating.

Step 5: Portfolio loss per simulation: the sum over bonds.

**Double check:**

1. For each group of bonds with the same initial rating, the simulated default frequency over all bond-simulation pairs is close to the default probability in the transition row; in default mode, one bond's mean loss equals $(1-R)\cdot\text{face}$ times that frequency.

## Topic 3: VaR and ES of the simulated loss

**Purpose:** Report quantile-based risk measures of a discrete loss distribution.

**When to use:** Loss quantiles and expected shortfall of the simulated portfolio loss.

**Constraints:**

1. Average the losses at or above the VaR to get ES, unless the task writes a strict inequality or the word "strictly"; "beyond VaR" and "exceeding VaR" are not such a request. Use the Acerbi-Tasche weighted tail mean when the task asks for the coherent or integrated-quantile form.

**How to implement:**

Step 1: VaR with the quantile method the task names: `np.quantile(L, level, method=...)` with linear interpolation (the numpy default), `"lower"`, `"higher"` or `"inverted_cdf"`; otherwise the library default, stated.

Step 2: ES: the mean of $L$ over the simulations with $L\ge\mathrm{VaR}$.

Step 3: Print the probability mass exactly at the VaR, and the strict mean ($L>\mathrm{VaR}$) as a diagnostic only.

**Limitations and cautions:**

1. With defaults only, losses take few values and ties at the VaR carry probability, so the readings can differ by one loss step.

**Double check:**

1. ES is at least the VaR.

## Topic 4: Losses by category and migration rates

**Purpose:** Break the loss down by category (initial rating, sector, region) and report migration frequencies.

**When to use:** The task asks for a loss table by category or for upgrade, downgrade and default rates.

**Constraints:**

1. A loss table broken down by category, in the same unit as the portfolio loss, reports each category's contribution: the category total, averaged over simulations, so that the rows add up to the portfolio mean loss. Divide by the number of bonds only when the wording asks for a per-bond, per-obligor or average-bond figure; an input stated per bond (a notional, a recovery amount) does not ask for it.

**How to implement:**

Step 1: For each category, sum the loss over its bonds in each simulation, then average over simulations.

Step 2: One bond's mean loss, when asked: the category total divided by its number of bonds.

Step 3: Migration rates over all bond-simulation pairs: the share that moved up the rating scale (upgrade), moved down without defaulting (downgrade), and defaulted.

**Double check:**

1. The category rows add up to the portfolio mean loss; if not, a per-bond figure was reported where a total was meant.
