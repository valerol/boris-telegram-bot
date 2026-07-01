# Native BOIS Core storage

This directory stores native BOIS Core packages without flattening, rewriting, translating, or deleting package files.

Structure:

- `active` - symlink to the active package under `versions/<version>` after a successful import.
- `versions/` - immutable imported native core packages.
- `staging/` - temporary extraction area for manual imports.
- `backups/` - reserved for explicit backup artifacts.
- `registry.json` - active version and import metadata.

Manual commands:

```bash
python scripts/import_core.py /path/to/BOIS_Core.zip
python scripts/show_core.py
python scripts/rollback_core.py
```
