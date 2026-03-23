import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { db } from '$lib/server/db';
import { batterie } from '$lib/server/db/schema';
import { desc } from 'drizzle-orm';

export const GET: RequestHandler = async () => {
	const rows = await db.select().from(batterie).orderBy(desc(batterie.createdAt));
	return json(rows);
};

export const POST: RequestHandler = async ({ request }) => {
	const { percentage } = await request.json();
	const [row] = await db.insert(batterie).values({ percentage }).returning();
	return json(row, { status: 201 });
};
