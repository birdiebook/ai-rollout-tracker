import { bundle } from '$lib/server/bundle';
import { BRANCH_CODES } from '$lib/data';
import { error } from '@sveltejs/kit';
import type { EntryGenerator } from './$types';

export const entries: EntryGenerator = () => BRANCH_CODES.map((id) => ({ id }));

export async function load({ params }) {
  if (!(BRANCH_CODES as readonly string[]).includes(params.id)) error(404, `okänd gren ${params.id}`);
  return { branch: await bundle().branch(params.id) };
}
