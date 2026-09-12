import { coverageWorkflow } from './workflow.mjs';

const args = process.argv.slice(2);
if (args.length > 1 || (args.length === 1 && args[0] !== '--live')) {
  console.error('Usage: node run.mjs [--live]');
  process.exitCode = 2;
} else {
  try {
    const run = await coverageWorkflow.createRun();
    const result = await run.start({ inputData: { live: args[0] === '--live' } });
    if (result.status !== 'success') throw new Error('Workflow failed');
    console.log(JSON.stringify(result.result, null, 2));
    if (['error', 'incomplete_response'].includes(result.result.status)) process.exitCode = 1;
  } catch {
    console.error('Coverage workflow failed. No raw error details are logged.');
    process.exitCode = 1;
  }
}
