<script>
  let { model, busy = false, onapply = async () => ({}) } = $props()
  let choice = $state('Raoult')
  let a = $state('')
  let b = $state('')
  let alpha = $state('')
  let kij = $state('')
  let error = $state('')
  const text = (value) => value == null ? '' : JSON.stringify(value)
  $effect(() => {
    choice = model.model
    a = text(model.parameters?.a)
    b = text(model.parameters?.b)
    alpha = text(model.parameters?.alpha)
    kij = text(model.parameters?.k_ij ?? model.species.map(() => model.species.map(() => 0)))
    error = ''
  })
  function loadExample() {
    a = text(model.nrtl_example.a)
    b = text(model.nrtl_example.b)
    alpha = text(model.nrtl_example.alpha)
    error = ''
  }
  async function apply() {
    error = ''
    let config = { model: choice }
    try {
      if (choice === 'NRTL') {
        config = { ...config, a: JSON.parse(a), b: JSON.parse(b), alpha: JSON.parse(alpha) }
      } else if (choice === 'PengRobinson' || choice === 'SRK') {
        config.k_ij = JSON.parse(kij)
      }
    } catch {
      error = 'Enter valid JSON matrices, for example [[0,0.3],[0.3,0]].'
      return
    }
    const answer = await onapply(config)
    if (answer?.ok === false) error = answer.error
  }
</script>

<fieldset disabled={busy}>
  <legend>Equilibrium model selection</legend>
  <label>Model
    <select value={choice} onchange={(e) => { choice = e.currentTarget.value; error = '' }}>
      <option value="Raoult">Raoult — ideal liquid and vapor</option>
      <option value="NRTL">NRTL — nonideal liquid, ideal vapor</option>
      <option value="PengRobinson">Peng–Robinson — EOS</option>
      <option value="SRK">Soave–Redlich–Kwong — EOS</option>
    </select>
  </label>
  <p>Matrix row/column order: {model.species.join(', ')}</p>
  {#if choice === 'NRTL'}
    <p>tau = a + b/T. a and alpha are dimensionless; b is in K.</p>
    {#if model.nrtl_example}
      <button type="button" onclick={loadExample}>Load water/ethanol example parameters</button>
      <p>Example source: repository test_flash_azeotrope.py. Verify against experimental data before research use.</p>
    {/if}
    <label>a matrix<textarea rows="2" bind:value={a} placeholder="[[0,...],[...,0]]"></textarea></label>
    <label>b matrix (K)<textarea rows="2" bind:value={b}></textarea></label>
    <label>alpha matrix<textarea rows="2" bind:value={alpha}></textarea></label>
  {:else if choice === 'PengRobinson' || choice === 'SRK'}
    <label>k_ij matrix<textarea rows="2" bind:value={kij}></textarea></label>
    <p>Zero binary interactions are an assumption. Enter symmetric fitted values when available. Critical properties come from the species database.</p>
  {/if}
  <button type="button" onclick={apply}>Apply model</button>
  <p>Then press Solve. Applying clears previous results. The model and parameter values are saved with the flowsheet.</p>
  {#if error}<p role="alert">{error}</p>{/if}
</fieldset>

<style>
  fieldset { min-width: 0; border: 1px solid var(--line, #aaa); border-radius: 5px; margin: .6rem 0; padding: .65rem; }
  legend { font-size: .85rem; font-weight: 600; }
  label { display: block; font-size: .78rem; margin: .45rem 0; }
  select, textarea { display: block; box-sizing: border-box; width: 100%; margin-top: .3rem; font-size: .78rem; }
  textarea { resize: vertical; font-family: monospace; }
  p { font-size: .75rem; overflow-wrap: anywhere; }
  [role=alert] { color: #b42318; }
</style>
