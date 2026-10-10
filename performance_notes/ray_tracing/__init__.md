# harness_designer/ray_tracing/__init__.py

## Whole file — package exports
Re-exports the public names. Importing this package imports `bvh_processor`, which imports the compiled `bvh_fast` module. On a machine where `bvh_fast` has not been built, the package fails to import (`ModuleNotFoundError: No module named 'bvh_fast'`). The review therefore cannot import the ray-tracing package here. Build the extension to run the import check.
