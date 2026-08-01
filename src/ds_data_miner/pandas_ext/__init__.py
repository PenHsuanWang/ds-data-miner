"""
Pandas extension adapter.

Importing this package registers the ``miner`` accessor on
:class:`pandas.DataFrame`.
"""

from ds_data_miner.pandas_ext.accessor import MinerAccessor

__all__ = ["MinerAccessor"]
