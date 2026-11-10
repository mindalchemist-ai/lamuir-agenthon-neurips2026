# Credit portfolio loss by Monte Carlo under factor copulas

The task description inside <task_instructions> takes priority over this card: where it gives a different formula, input or convention, follow the task description.

## Topic: Latent-factor default model

**Purpose:** Simulate correlated defaults through sector or market factors.

**When to use:** Defaults must be correlated through common factors. For a large uniform portfolio the one-factor closed form is an approximation, not the simulated result.

**How to implement:** Asset return $A_i=\sqrt{\rho_i}\,M_{s(i)}+\sqrt{1-\rho_i}\,\varepsilon_i$ with $M$ correlated normal factors (Cholesky factor of the correlation matrix) and $\varepsilon_i$ independent. Obligor $i$ defaults when $A_i<d_i$, where $d_i$ is the quantile of the PD under the copula's marginal.

**Limitations and cautions:**

1. Write the simulation once as a function of its varying inputs (parameters, distribution family, seed); every variant calls it.
2. Simulated frequencies carry sampling error; compare them with the PDs only within that error.

**Double check:**

1. The simulated default frequency of each obligor is close to its PD, and the mean simulated loss is close to the analytical mean, checked before any risk measure is reported.

## Topic: Student-t copula

**Purpose:** Add tail dependence beyond the Gaussian copula.

**When to use:** The task asks for tail dependence beyond the Gaussian copula. Compare it with the Gaussian case on the same PDs.

**How to implement:** One mixing variable $W=\chi^2_\nu/\nu$ per scenario divides every factor and every idiosyncratic shock by $\sqrt W$. The threshold is the Student-t quantile $t_\nu^{-1}(\mathrm{PD}_i)$.

**Limitations and cautions:**

1. Call the same simulation function as the Gaussian case with the copula family as an argument; do not copy it.
2. The normal quantile as threshold changes the marginal PDs.

**Double check:**

1. The simulated default frequency of each obligor is still close to its PD.
2. After writing, read the table back: each summary figure must equal the aggregate of its detail table, and the header must equal the task's column list character by character.

## Topic: VaR, CVaR and Euler allocation

**Purpose:** Summarise the simulated loss distribution and attribute the loss to obligors or groups.

**When to use:** VaR and CVaR describe the simulated loss distribution. Euler allocation attributes the loss; when the total comes from simulation, use the simulated scenarios, not a closed-form allocation.

**How to implement:** Loss per scenario is the sum of $\mathrm{EAD}_i\cdot\mathrm{LGD}_i$ over defaulted obligors. $\mathrm{VaR}_\alpha$ is the empirical quantile and $\mathrm{CVaR}_\alpha$ the mean loss over scenarios with loss at or above it. With the tail scenarios fixed, the contribution of obligor $i$ is the mean of its own loss over those scenarios.

**Limitations and cautions:**

1. Take the tail scenarios once and use the same set for every obligor.
2. A contribution that must add up to a simulated total is computed from the same simulated scenarios; a closed-form approximation does not add up to a simulated sum.

**Double check:**

1. Contributions add up to $\mathrm{CVaR}_\alpha$ at the same level, group totals add up to the portfolio total, and $\mathrm{CVaR}_\alpha\ge\mathrm{VaR}_\alpha$ at every level.
2. After writing, read the table back: each summary figure must equal the aggregate of its detail table, and the header must equal the task's column list character by character.

## Topic: Stress variants

**Purpose:** Measure how the loss changes when named obligors or sectors behave differently in stress.

**When to use:** The task names obligors or sectors with stressed parameters. Compare the stressed run with the base run under the same seed.

**How to implement:** Raise the asset correlation, capped below 1, and replace the base recovery by the stressed one for the same obligors.

**Limitations and cautions:**

1. Reuse the base simulation function with the stressed inputs.
2. Where a quantile of the PD enters a formula, leave out obligors with PD equal to 0.

**Double check:**

1. Only the stressed inputs differ from the base run; the seed is the same.
2. After writing, read the table back: each summary figure must equal the aggregate of its detail table, and the header must equal the task's column list character by character.
