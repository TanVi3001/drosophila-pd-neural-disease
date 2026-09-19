# Bridge ID-scope contract

The LIF-to-FlyGym bridge treats a neuron ID as a typed identifier, not as a
numeric value that may be silently reformatted.

Each future bridge run should declare the same `id_namespace`, `dataset_id`
(when applicable), and complete `neuron_ids` inventory in both the reference
and condition run manifests. The reviewed annotation CSV must carry matching
`id_namespace`/`dataset_id` columns. Annotation IDs and observed spike IDs
outside the inventory are errors.

A neuron that is present in the inventory but has no spike row remains a valid
silent readout and is included in the denominator using the manifest's
declared `trial_count`. This is different from an ID that is absent from the
inventory, which is rejected.

Older manifests without an inventory are still readable for migration, but
the bridge records `id_scope_not_declared`, returns a readout-gap status, and
must not be presented as a fully scoped ranking input. No namespace mapping is
inferred automatically.
