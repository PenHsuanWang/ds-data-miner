Export — JSON Serialization
===========================

Location: ``ds_data_miner.export``

The export layer serializes :class:`~ds_data_miner.core.contracts.DatasetReport`
objects to formatted JSON files and auto-generates the corresponding JSON Schema.
It depends only on ``ds_data_miner.core``.

ReportExporter
--------------

.. autoclass:: ds_data_miner.export.serializer.ReportExporter
   :members:
   :show-inheritance:
