# V434: verify a focused startup rebuild

Use a private scratch directory outside the Git checkout. Keep retail inputs, traces, registries, and generated C out of Git and public CI.

1. Run V433 on the old registry, whole-image registry, old instrumented shards, and discovery trace. Exit 1 means it identified observed indirect gaps. If requested, its private target list is input for selecting the next AOT functions; it is not permission to dispatch unknown targets at runtime.
2. Generate the expanded focused registry and instrumented shards with the same pinned emitter and original image.
3. Run the rebuild gate:
   
   ```sh
   python audit_focused_rebuild_v434.py \
     --baseline old/recomp.c --rebuilt rebuilt/recomp.c --whole whole/recomp.c \
     --baseline-shards old --rebuilt-shards rebuilt --trace discovery.log
   ```

The gate preserves old registrations, requires every observed missing target, and rejects extra registrations unless an explicit `--max-extra` budget is supplied. All new rows still have to match the whole-image table. Both generated versions are checked for the observed CALL continuations. Only counts are printed. A pass says nothing about an unobserved path or a linked binary.

Then build and run the fixed-route native replay from an input-free working directory, with the interpreter fallback disabled. Use V424 to check constructor return identities against the private retail order. Keep any exploratory returns separate from the verified prefix. V434 does not claim constructor 1089 has returned.
