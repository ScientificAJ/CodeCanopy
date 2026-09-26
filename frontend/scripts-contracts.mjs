import { compile } from 'json-schema-to-typescript'
import { readFile, writeFile } from 'node:fs/promises'
for (const [source, target] of [['prd.schema.json','prd.generated.ts'],['structure-1.1.schema.json','structure.generated.ts']]) {
  const schema = JSON.parse(await readFile(new URL('../contracts/' + source, import.meta.url)))
  const output = await compile(schema, 'CodeCanopyContract', {unreachableDefinitions:true, bannerComment:'/* Generated from contracts/' + source + '. Run npm run contracts; do not edit. */'})
  await writeFile(new URL('./src/types/v1/' + target, import.meta.url),output)
}
