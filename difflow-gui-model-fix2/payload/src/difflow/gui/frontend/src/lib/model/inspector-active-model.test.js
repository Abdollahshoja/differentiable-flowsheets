import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync, writeFileSync, mkdtempSync, rmSync } from 'node:fs'
import { join } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'
import { compile } from 'svelte/compiler'
import { render } from 'svelte/server'

test('a built Flash displays its actual model card, without being pending', async () => {
  const lib = fileURLToPath(new URL('../', import.meta.url))
  const temp = mkdtempSync(join(lib, '.model-render-'))
  try {
    for (const name of ['ActiveModel', 'Inspector']) {
      const source = readFileSync(join(lib, `${name}.svelte`), 'utf8')
      let code = compile(source, { generate: 'server', filename: `${name}.svelte` }).js.code
      code = code.replaceAll("from './", "from '../")
      code = code.replace("'../ActiveModel.svelte'", "'./ActiveModel.mjs'")
      writeFileSync(join(temp, `${name}.mjs`), code)
    }
    const { default: Inspector } = await import(pathToFileURL(join(temp, 'Inspector.mjs')))
    for (const model of ['Raoult', 'NRTL', 'PengRobinson']) {
      const html = render(Inspector, { props: {
        node: { id: 'flash', type: 'unit', data: { operation: 'Flash', label: 'flash' } },
        unit: { name: 'flash', params: {}, inlets: ['feed'], outlets: ['liquid', 'vapor'],
          runtime_model: { model, calculation: 'TP flash', liquid: 'test liquid',
            vapor: 'test vapor', property_package: 'IdealThermo', species: ['water', 'ethanol'],
            method: 'test method', parameters: {}, equations: [], assumptions: [] } },
        spec: { name: 'Flash', parameters: [], call_parameters: [] },
        pending: null,
      } }).body
      assert.match(html, /Active equilibrium model/)
      assert.ok(html.includes(model), `missing active model ${model}`)
      assert.match(html, /test liquid/)
      assert.match(html, /test vapor/)
    }
  } finally {
    rmSync(temp, { recursive: true, force: true })
  }
})
