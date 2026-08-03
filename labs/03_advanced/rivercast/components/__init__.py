"""RiverCast pipeline components (PLAN.md Phase 8).

Each subpackage (``fetch``, ``validate``, ``transform``, ``train``,
``evaluate``, ``register``, ``promote``, ``forecast``, ``monitor``,
``deploy``) exposes one ``component.py`` with a plain ``run()`` function and
a thin CLI ``main()``. See ``components/common.py`` for the shared result
envelope and object-store helpers, and ``docs/pipeline_components.md`` for
the full component contract and image mapping.
"""
