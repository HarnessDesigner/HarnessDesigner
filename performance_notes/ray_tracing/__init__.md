# harness_designer/ray_tracing/__init__.py

Re-exports the public names. Importing the package imports `bvh_processor`, which imports the compiled `bvh` extension (`bvh.cp311-win_amd64.pyd` next to the source); on a machine where it is not built the package does not import. Import cost only.
