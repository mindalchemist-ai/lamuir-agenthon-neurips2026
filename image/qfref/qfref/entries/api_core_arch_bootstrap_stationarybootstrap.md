# Official API description: arch.bootstrap.StationaryBootstrap (arch 8.0.0)

From the installed docstring, unchanged; sections other than the signature, summary and parameters are omitted.

```text
arch.bootstrap.StationaryBootstrap(block_size: int, *args: Union[numpy.ndarray, pandas.DataFrame, pandas.Series], seed: int | numpy.random._generator.Generator | numpy.random.mtrand.RandomState | None = None, **kwargs: Union[numpy.ndarray, pandas.DataFrame, pandas.Series]) -> None

Politis and Romano (1994) bootstrap with expon distributed block sizes

Parameters
----------
block_size : int
    Average size of block to use
args
    Positional arguments to bootstrap
seed : {Generator, RandomState, int}, optional
    Seed to use to ensure reproducable results. If an int, passes the
    value to value to ``np.random.default_rng``. If None, a fresh
    Generator is constructed with system-provided entropy.
kwargs
    Keyword arguments to bootstrap

Attributes
----------
data : tuple
    Two-element tuple with the pos_data in the first position and kw_data
    in the second (pos_data, kw_data)
pos_data : tuple
    Tuple containing the positional arguments (in the order entered)
kw_data : dict
    Dictionary containing the keyword arguments
```
