# Official API description: arch.bootstrap.StationaryBootstrap.bootstrap (arch 8.0.0)

From the installed docstring, unchanged; sections other than the signature, summary and parameters are omitted.

```text
arch.bootstrap.StationaryBootstrap.bootstrap(self, reps: int) -> collections.abc.Generator[tuple[tuple[typing.Union[numpy.ndarray, pandas.DataFrame, pandas.Series], ...], dict[str, typing.Union[numpy.ndarray, pandas.DataFrame, pandas.Series]]], None, None]

Iterator for use when bootstrapping

Parameters
----------
reps : int
    Number of bootstrap replications

Returns
-------
generator
    Generator to iterate over in bootstrap calculations
```
