<script>
  let { model, heading = 'Active equilibrium model' } = $props()
</script>

<section aria-label={heading}>
  <h3>{heading}: {model.model}</h3>
  <dl>
    <dt>Calculation</dt><dd>{model.calculation}</dd>
    <dt>Liquid</dt><dd>{model.liquid}</dd>
    <dt>Vapor</dt><dd>{model.vapor}</dd>
    <dt>Property package</dt><dd>{model.property_package}</dd>
    <dt>Species order</dt><dd>{model.species.join(', ')}</dd>
    <dt>Numerical method</dt><dd>{model.method}</dd>
  </dl>
  {#if model.note}<p>{model.note}</p>{/if}
  {#if Object.keys(model.parameters ?? {}).length}
    <details>
      <summary>Interaction parameters used</summary>
      <pre>{JSON.stringify(model.parameters, null, 2)}</pre>
    </details>
  {/if}
</section>

<style>
  section { border: 1px solid var(--line, #aaa); border-radius: 5px; padding: .65rem; margin: .6rem 0; }
  h3 { margin: 0 0 .5rem; font-size: .85rem; }
  dl { display: grid; grid-template-columns: auto 1fr; gap: .3rem .6rem; margin: 0; font-size: .78rem; }
  dt { font-weight: 600; }
  dd { margin: 0; overflow-wrap: anywhere; }
  p, details { font-size: .76rem; margin: .5rem 0 0; }
  pre { overflow: auto; max-height: 12rem; }
</style>
