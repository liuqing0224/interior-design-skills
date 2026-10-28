// Compatibility entry point. The maintained builder ships inside interior-cost.
// export_budget.py needs only Python + openpyxl, so this wrapper just forwards.
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const result=spawnSync(process.env.INTERIOR_PYTHON || 'python3',[path.join(root,'skills/interior-cost/scripts/export_budget.py'),...process.argv.slice(2)],{stdio:'inherit'});
process.exit(result.status ?? 1);
