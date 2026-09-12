import { createStep, createWorkflow } from '@mastra/core/workflows';
import { z } from 'zod';
import { gateSummary, privateSummary } from './coverage.mjs';

const inputSchema = z.object({ live: z.boolean().default(false) });
const summarySchema = z.object({
  status: z.enum(['observed', 'empty', 'error', 'incomplete_response']),
  synthetic: z.boolean(),
  scope: z.literal('soccer_epl'),
  groups: z.array(z.object({ bookmaker: z.string(), complete: z.number().int().nonnegative(), incomplete: z.number().int().nonnegative() })),
  missingRequestedBooks: z.array(z.string()),
  groupsWithoutH2h: z.number().int().nonnegative(),
  skippedDerivedGroups: z.number().int().nonnegative(),
});
const outputSchema = summarySchema.extend({
  decision: z.enum(['stop', 'review_incomplete_groups', 'supplied_shapes_complete']),
  complete: z.number().int().nonnegative(),
  incomplete: z.number().int().nonnegative(),
  shapeCheckPassed: z.boolean(),
});

const inspect = createStep({
  id: 'inspect-private-moneyline', inputSchema, outputSchema: summarySchema, retries: 0,
  execute: async ({ inputData }) => privateSummary(inputData.live),
});
const gate = createStep({
  id: 'gate-incomplete-moneylines', inputSchema: summarySchema, outputSchema, retries: 0,
  execute: async ({ inputData }) => gateSummary(inputData),
});

export const coverageWorkflow = createWorkflow({
  id: 'private-soccer-moneyline-coverage', inputSchema, outputSchema,
  options: { shouldPersistSnapshot: () => false },
}).then(inspect).then(gate).commit();
