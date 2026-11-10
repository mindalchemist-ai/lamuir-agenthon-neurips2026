# Gaussian hidden regimes: filtering, smoothing and estimation

Use this reference when an observed return series is modeled by a latent Markov state with Gaussian emissions. It separates real-time state probabilities from retrospective classifications and from portfolio allocation conditional on those states.

## A verified minimal implementation (one series, K Gaussian states)

Scaled forward-backward and one Baum-Welch update per iteration; shapes are in the comments. Initial values, tolerance, iteration cap and stopping rule come from the task; this function only takes them. Checked on simulated two-regime data: the log-likelihood never decreases and the states are recovered. The scaling already keeps it numerically stable, so copy the function as written; rewriting it in log space is not needed and is a common source of wrong updates. Two choices are the task's, not the function's: whether the initial distribution pi is re-estimated (`update_pi=True`, gamma[0], standard Baum-Welch) or held (`update_pi=False`) only when the task says pi is fixed or not re-estimated, or ties it to each new A as its stationary distribution. A starting pi given in the inputs, whatever it is called, is an initial value, and standard Baum-Welch re-estimates it. The stopping rule is also the task's.

```python
from scipy.stats import norm
def baum_welch(x, mu, sigma, A, pi, tol, max_iter, update_pi=True):
    x = np.asarray(x, float)                                              # (T,)
    mu, sigma, A, pi = (np.asarray(v, float) for v in (mu, sigma, A, pi))  # (K,), (K,), (K, K) rows sum to 1, (K,)
    T, K = len(x), len(mu); loglik = []
    for it in range(1, max_iter + 1):
        B = norm.pdf(x[:, None], mu[None, :], sigma[None, :])             # (T, K) emission densities
        alpha = np.empty((T, K)); c = np.empty(T)                         # scaled forward, scale factors
        alpha[0] = pi * B[0]; c[0] = alpha[0].sum(); alpha[0] /= c[0]
        for t in range(1, T):
            alpha[t] = (alpha[t - 1] @ A) * B[t]; c[t] = alpha[t].sum(); alpha[t] /= c[t]
        beta = np.ones((T, K))                                            # scaled backward
        for t in range(T - 2, -1, -1):
            beta[t] = (A @ (B[t + 1] * beta[t + 1])) / c[t + 1]
        gamma = alpha * beta; gamma /= gamma.sum(1, keepdims=True)        # (T, K) smoothed state probabilities
        xi = alpha[:-1, :, None] * A[None] * (B[1:] * beta[1:])[:, None, :] / c[1:, None, None]   # (T-1, K, K)
        loglik.append(np.log(c).sum())                                    # log-likelihood of the parameters used in this pass
        mu_new = gamma.T @ x / gamma.sum(0)
        sigma = np.sqrt((gamma * (x[:, None] - mu_new[None]) ** 2).sum(0) / gamma.sum(0))   # uses the new means
        A = xi.sum(0) / xi.sum((0, 2))[:, None]
        pi = gamma[0] if update_pi else pi                                # re-estimated, or held as the task says
        done = np.max(np.abs(mu_new - mu)) < tol                          # replace with the task's stopping rule
        mu = mu_new
        if done:
            break
    return dict(mu=mu, sigma=sigma, A=A, pi=pi, gamma=gamma, loglik=np.array(loglik), n_iter=it)
```

Checks before using the fit:

```python
assert (np.diff(fit["loglik"]) > -1e-8).all()                             # EM never lowers the likelihood; a drop means a bug
assert np.ptp(fit["mu"]) > 0 or np.ptp(fit["sigma"]) > 0                  # states that became identical carry no regime information
assert fit["n_iter"] >= 1 and np.allclose(fit["A"].sum(1), 1)
never_top = ~(fit["gamma"].argmax(1)[:, None] == np.arange(len(fit["mu"]))).any(0)
print("states never most likely on any day:", np.flatnonzero(never_top))  # a rare state can be legitimate; check the update before calling it a collapse
```

A collapse to identical states usually comes from an update that mixes shapes (gamma summed over the wrong axis, x broadcast as (K, T)); fix the update rather than reporting the collapsed fit or an iteration count of 0.

## Shared Foundations

Map the task's notation, time frequency, emission model and transition orientation explicitly. Initialization, permitted parameter constraints and stopping criteria may be specified separately. A state index has no intrinsic economic meaning.

Let $y_{t}$ be a scalar observation, $s_{t}$ a hidden state in $\{1,\ldots ,K\}, \pi _{j}=\operatorname{P}(s_{1}=j)$, and $\operatorname{P}_{ij}=\operatorname{P}(s_{t+1}=j\vert s_{t}=i)$. Rows of P sum to one. Conditional on the hidden states, observations are independent. State j has mean $\mu _{j}$ and strictly positive variance $v_{j}$.

The Gaussian observation density in state j is:

$$
b_{j}(y) = \exp (-(y-\mu _{j})^{2}/(2\cdot v_{j}))/\sqrt{2\cdot \pi \cdot v_{j}}
$$

These are densities, not probabilities of observing an exact real number. Their values can exceed one.

## Filtered probabilities and likelihood

Let $f_{t}(j)=\operatorname{P}(s_{t}=j\vert y_{1},\ldots ,y_{t})$. Before the first observation, the predicted probabilities equal $\pi$; at later dates the Markov transition propagates the preceding filtered distribution.

$$
\begin{gathered}
p_{1}(j) = \pi _{j} \\
p_{t}(j) = \sum _{i} f_{t-1}(i)\cdot \operatorname{P}_{ij},  t\ge 2
\end{gathered}
$$

The predictive density $c_{t}$ normalizes the filter.

$$
\begin{gathered}
c_{t} = \sum _{j} p_{t}(j)\cdot b_{j}(y_{t}) \\
f_{t}(j) = p_{t}(j)\cdot b_{j}(y_{t})/c_{t}
\end{gathered}
$$

The log likelihood of T observations is:

$$
\mathrm{logL} = \sum _{t=1}^{T} \ln (c_{t})
$$

For extreme observations, log densities and log-sum-exp express the same identities without multiplying tiny probabilities. With $P_{ij}$ the probability of moving from state i to state j (rows sum to one), the one-step prediction is $p_{t}(j)=\sum_i f_{t-1}(i)P_{ij}$, that is `f_prev @ P`, or in logs `logsumexp(log_f_prev[:, None] + np.log(P), axis=0)`. Using `P.T` or summing over the wrong axis swaps the roles of the states. That error leaves every row sum intact, so check the column sums of ξ against $\gamma_{t+1}$ as well (below). A zero computed normalizer can be numerical underflow; a genuinely zero predictive density is a model-support failure.

## Smoothed probabilities

Smoothing conditions on the entire observed sample, including observations after t. Define a scaled backward quantity $B_{T}(j)=1$. Its recursion uses the same forward normalizers $c_{t}$.

$$
B_{t}(i) = \sum _{j} \operatorname{P}_{ij}\cdot b_{j}(y_{t+1})\cdot B_{t+1}(j)/c_{t+1}
$$

The smoothed state probability is:

$$
\gamma _{t}(j) = f_{t}(j)\cdot B_{t}(j)
$$

The smoothed joint probability for two adjacent states is:

$$
\xi _{t}(i,j) = f_{t}(i)\cdot \operatorname{P}_{ij}\cdot b_{j}(y_{t+1})\cdot B_{t+1}(j)/c_{t+1}
$$

In exact arithmetic $\gamma$ sums to one, $\xi$ sums to one, its row sums equal $\gamma _{t}$, and its column sums equal $\gamma_{t+1}$. These are useful checks on time indexing and transition orientation.

## Gaussian Baum–Welch updates

These are unconstrained maximum-likelihood M-step identities for one sequence, using probabilities from the preceding parameter values. Fixed parameters, priors or imposed variance floors define different updates.

The initial-state distribution and transition probabilities update as:

$$
\begin{gathered}\pi_{\mathrm{new}}(j)=\gamma_1(j)\\ P_{\mathrm{new}}(i,j)=\frac{\sum_{t=1}^{T-1}\xi_t(i,j)}{\sum_{t=1}^{T-1}\gamma_t(i)}\end{gathered}
$$

The mean uses every observation weighted by state occupancy.

$$
\mu_{\mathrm{new}}(j)=\frac{\sum_{t=1}^T\gamma_t(j)y_t}{\sum_{t=1}^T\gamma_t(j)}
$$

The variance is a weighted maximum-likelihood variance about the new mean, without a sample degrees-of-freedom correction.

$$
v_{\mathrm{new}}(j)=\frac{\sum_{t=1}^T\gamma_t(j)(y_t-\mu_{\mathrm{new}}(j))^2}{\sum_{t=1}^T\gamma_t(j)}
$$

Zero occupancy leaves an update undefined. Gaussian likelihoods can become singular as a state's variance collapses. A specified positive floor regularizes this problem but changes the optimization problem. Exact EM is nondecreasing in likelihood, not a guarantee of a global optimum. When the task states a stopping rule → test exactly the quantity it names (only the means, if it names the means) against its tolerance and nothing more → check that the reported iteration count is the first iteration at which that one test passes; adding variance or transition tests changes that count. Without a stated rule, small mean changes alone do not prove transition or variance convergence. Pass the current start distribution, transition matrix, means and standard deviations explicitly into every forward, backward and E-step function: a helper that reads them from an outer scope keeps stale values after a refit.

When the forward-backward pass is written in log space with transition matrix `P[i, j]` = Pr(next state j | current state i) → sum over the previous state i, and check that the posteriors are normalized at every date (a transposed P breaks this):

```python
from scipy.special import logsumexp
logP = np.log(P)
log_alpha[0] = np.log(pi) + log_b[0]
for t in range(1, T):
    log_alpha[t] = log_b[t] + logsumexp(log_alpha[t - 1][:, None] + logP, axis=0)
log_beta[-1] = 0.0
for t in range(T - 2, -1, -1):
    log_beta[t] = logsumexp(logP + (log_b[t + 1] + log_beta[t + 1])[None, :], axis=1)
log_gamma = log_alpha + log_beta
log_gamma -= logsumexp(log_gamma, axis=1, keepdims=True)
assert np.allclose(logsumexp(log_alpha[-1]), logsumexp(log_alpha[0] + log_beta[0]))   # same likelihood both ways
```

## Financial interpretation and checks

State labels may be permuted without changing likelihood. If a state is named by a higher fitted mean, the same permutation applies to $\pi$, both axes of P and all state summaries. A per-date maximum smoothed probability is not the Viterbi most likely whole-state sequence. Naming the states (for example by mean) and classifying a date are separate steps: the current regime is the state whose filtered or smoothed probability at the last date is largest, as the task specifies, and the parameters used afterwards (for example a regime covariance) are those of that state.

An emission variance estimated with $\gamma$ weights is not the same statistic as an asset covariance estimated on hard-classified dates. A univariate market-state model does not by itself determine a multivariate asset covariance. Conditional allocations require a separately defined return/covariance estimator and matching annualization conventions.

Filtered probabilities use observations through their date, but parameters estimated on future data still introduce hindsight. Smoothed probabilities are retrospective even with fixed parameters. With $K=1$ the model reduces to one Gaussian distribution. Equal emissions across states remove the observations' information about the latent states, though the Markov prior still evolves.

## References

[hmmlearn official tutorial](https://hmmlearn.readthedocs.io/en/stable/tutorial.html), model definition, Gaussian emissions, Baum–Welch, decoding and state-label conventions. The normalized forward/backward formulas follow from Bayes' rule; the Gaussian updates follow from maximizing the posterior-weighted complete-data log likelihood. They are independently checked by enumerating finite hidden-state paths, rather than relying on library defaults.
