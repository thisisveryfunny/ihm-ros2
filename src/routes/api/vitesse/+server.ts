import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { db } from '$lib/server/db';
import { vitesse } from '$lib/server/db/schema';
import { desc } from 'drizzle-orm';

export const GET: RequestHandler = async () => {
	const rows = await db.select().from(vitesse).orderBy(desc(vitesse.createdAt));
	return json(rows);
};

export const POST: RequestHandler = async ({ request }) => {
	const { speed } = await request.json();
	const [row] = await db.insert(vitesse).values({ speed }).returning();
	return json(row, { status: 201 });
};
