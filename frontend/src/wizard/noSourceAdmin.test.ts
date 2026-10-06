import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';
import { WIZARD_STEPS } from './wizard';

function collect(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const full = join(dir, name);
    if (statSync(full).isDirectory()) return collect(full);
    return /\.(ts|tsx)$/.test(name) && !/\.test\./.test(name) ? [full] : [];
  });
}

describe('public frontend', () => {
  it('does not expose source administration', () => {
    const forbidden = ['/api/sources', '/api/connectors', 'knowledge/connectors', 'import-url', 'import-file', 'icadb'];
    for (const file of collect(join(process.cwd(), 'src'))) {
      const text = readFileSync(file, 'utf8');
      for (const token of forbidden) expect(text.includes(token), `${file} ${token}`).toBe(false);
    }
  });

  it('does not require a user source selection step', () => {
    expect((WIZARD_STEPS as string[]).includes('sources')).toBe(false);
    expect(WIZARD_STEPS[0]).toBe('project');
  });
});