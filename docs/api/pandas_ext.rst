Pandas Extension — Adapter Layer
================================

Location: ``ds_data_miner.pandas_ext``

The Pandas extension registers the ``df.miner`` accessor on
:class:`pandas.DataFrame`.  Import this module once to activate it.

.. code-block:: python

   import ds_data_miner.pandas_ext  # registers df.miner

MinerAccessor
-------------

.. autoclass:: ds_data_miner.pandas_ext.accessor.MinerAccessor
   :members:
   :show-inheritance:
