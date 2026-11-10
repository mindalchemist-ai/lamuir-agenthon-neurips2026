# Official API description: numpy.random.default_rng (numpy 2.5.3)

From the installed docstring, unchanged; sections other than the signature, summary, parameters and notes are omitted.

```text
numpy.random.default_rng(seed=None)

default_rng(seed=None)

Construct a new Generator with the default BitGenerator (PCG64).

Parameters
----------
seed : {None, int, array_like[ints], SeedSequence, BitGenerator, Generator, RandomState}, optional
    A seed to initialize the `BitGenerator`. If None, then fresh,
    unpredictable entropy will be pulled from the OS. If an ``int`` or
    ``array_like[ints]`` is passed, then all values must be non-negative and will be
    passed to `SeedSequence` to derive the initial `BitGenerator` state. One may also
    pass in a `SeedSequence` instance.
    Additionally, when passed a `BitGenerator`, it will be wrapped by
    `Generator`. If passed a `Generator`, it will be returned unaltered.
    When passed a legacy `RandomState` instance it will be coerced to a `Generator`.

Returns
-------
Generator
    The initialized generator object.

Notes
-----
If ``seed`` is not a `BitGenerator` or a `Generator`, a new `BitGenerator`
is instantiated. This function does not manage a default global instance.

See :ref:`seeding_and_entropy` for more information about seeding.
```
