# Official API description: scipy.stats.rv_continuous.fit (scipy 1.18.1)

From the installed docstring, unchanged; sections other than the signature, summary, parameters and notes are omitted.

```text
scipy.stats.rv_continuous.fit(self, data, *args, **kwds)

Return estimates of shape (if applicable), location, and scale
parameters from data. The default estimation method is Maximum
Likelihood Estimation (MLE), but Method of Moments (MM)
is also available.

Starting estimates for the fit are given by input arguments;
for any arguments not provided with starting estimates,
``self._fitstart(data)`` is called to generate such.

One can hold some parameters fixed to specific values by passing in
keyword arguments ``f0``, ``f1``, ..., ``fn`` (for shape parameters)
and ``floc`` and ``fscale`` (for location and scale parameters,
respectively).

Parameters
----------
data : array_like or `CensoredData` instance
    Data to use in estimating the distribution parameters.
arg1, arg2, arg3,... : floats, optional
    Starting value(s) for any shape-characterizing arguments (those not
    provided will be determined by a call to ``_fitstart(data)``).
    No default value.
**kwds : floats, optional
    - `loc`: initial guess of the distribution's location parameter.
    - `scale`: initial guess of the distribution's scale parameter.

    Special keyword arguments are recognized as holding certain
    parameters fixed:

    - f0, ..., fn : hold respective shape parameters fixed.
      Alternatively, shape parameters to fix can be specified by name.
      For example, if ``self.shapes == "a, b"``, ``fa`` and ``fix_a``
      are equivalent to ``f0``, and ``fb`` and ``fix_b`` are
      equivalent to ``f1``.

    - floc : hold location parameter fixed to specified value.

    - fscale : hold scale parameter fixed to specified value.

    - optimizer : The optimizer to use.  The optimizer must take
      ``func`` and starting position as the first two arguments,
      plus ``args`` (for extra arguments to pass to the
      function to be optimized) and ``disp``.
      The ``fit`` method calls the optimizer with ``disp=0`` to suppress output.
      The optimizer must return the estimated parameters.

    - method : The method to use. The default is "MLE" (Maximum
      Likelihood Estimate); "MM" (Method of Moments)
      is also available.

Returns
-------
parameter_tuple : tuple of floats
    Estimates for any shape parameters (if applicable), followed by
    those for location and scale. For most random variables, shape
    statistics will be returned, but there are exceptions (e.g.
    ``norm``).

Notes
-----
With ``method="MLE"`` (default), the fit is computed by minimizing
the negative log-likelihood function. A large, finite penalty
(rather than infinite negative log-likelihood) is applied for
observations beyond the support of the distribution.

With ``method="MM"``, the fit is computed by minimizing the L2 norm
of the relative errors between the first *k* raw (about zero) data
moments and the corresponding distribution moments, where *k* is the
number of non-fixed parameters.
More precisely, the objective function is::

    (((data_moments - dist_moments)
      / np.maximum(np.abs(data_moments), 1e-8))**2).sum()

where the constant ``1e-8`` avoids division by zero in case of
vanishing data moments. Typically, this error norm can be reduced to
zero.
Note that the standard method of moments can produce parameters for
which some data are outside the support of the fitted distribution;
this implementation does nothing to prevent this.

For either method,
the returned answer is not guaranteed to be globally optimal; it
may only be locally optimal, or the optimization may fail altogether.
If the data contain any of ``np.nan``, ``np.inf``, or ``-np.inf``,
the `fit` method will raise a ``RuntimeError``.

When passing a ``CensoredData`` instance to ``data``, the log-likelihood
function is defined as:

.. math::

    l(\pmb{\theta}; k) & = \sum
                            \log(f(k_u; \pmb{\theta}))
                        + \sum
                            \log(F(k_l; \pmb{\theta})) \\
                        & + \sum
                            \log(1 - F(k_r; \pmb{\theta})) \\
                        & + \sum
                            \log(F(k_{\text{high}, i}; \pmb{\theta})
                            - F(k_{\text{low}, i}; \pmb{\theta}))

where :math:`f` and :math:`F` are the pdf and cdf, respectively, of the
function being fitted, :math:`\pmb{\theta}` is the parameter vector,
:math:`u` are the indices of uncensored observations,
:math:`l` are the indices of left-censored observations,
:math:`r` are the indices of right-censored observations,
subscripts "low"/"high" denote endpoints of interval-censored observations, and
:math:`i` are the indices of interval-censored observations.
```
