# Print format recovery record

This folder preserves the exact Print Format record needed to recover the corrected Sales Order selection.

- `so16-before.json` is the SO16 record deleted during the correction. It can be inserted as a `Print Format` document if SO16 is needed again.
- `so18-restored.json` is the SO18 record restored from the deployment-before snapshot.
- `correction-deploy-result.json` records the production deletion, restoration, source hashes and Bench backup hashes.
- `backup-manifest.json` identifies the complete four-part Bench backup on `qq`; the backup itself stays in the server's private backup directory because it contains production data.

The production snapshot is:
`/home/frappe/frappe-bench/sites/erp.solua.one/private/deployment_snapshots/20261018-print-format-correction-so18-220016`

The full Bench backup prefix is:
`20261018_220016-erp_solua_one-`
