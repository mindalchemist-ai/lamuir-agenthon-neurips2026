# Official API description: scipy.stats.rv_continuous.fit (scipy 1.18.1)

From the installed docstring, unchanged; sections other than the signature, summary and parameters are omitted.

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
```
