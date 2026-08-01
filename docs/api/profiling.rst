Profiling — Domain Layer
========================

Location: ``ds_data_miner.profiling``

The profiling domain layer contains all statistical computation.  It depends
**only** on ``numpy``, ``scipy``, and ``ds_data_miner.core`` — never on
``pandas`` or ``matplotlib``.

BaseProfiler
------------

.. autoclass:: ds_data_miner.profiling.base.BaseProfiler
   :members:
   :show-inheritance:

NumericProfiler
---------------

.. autoclass:: ds_data_miner.profiling.numeric.NumericProfiler
   :members:
   :show-inheritance:

CategoricalProfiler
-------------------

.. autoclass:: ds_data_miner.profiling.categorical.CategoricalProfiler
   :members:
   :show-inheritance:

DatetimeProfiler
----------------

.. autoclass:: ds_data_miner.profiling.datetime.DatetimeProfiler
   :members:
   :show-inheritance:

DistributionTester
------------------

.. autoclass:: ds_data_miner.profiling.distribution_test.DistributionTester
   :members:
   :show-inheritance:

ProfilingEngine
---------------

.. autoclass:: ds_data_miner.profiling.engine.ProfilingEngine
   :members:
   :show-inheritance:
