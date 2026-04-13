import { Router } from 'express';
import { db } from '../db/index.js';
import { batterie } from '../db/schema.js';
import { desc } from 'drizzle-orm';

const router = Router();

router.get('/', async (_req, res) => {
	const rows = await db.select().from(batterie).orderBy(desc(batterie.createdAt));
	res.json(rows);
});

router.post('/', async (req, res) => {
	const { percentage } = req.body;
	const [row] = await db.insert(batterie).values({ percentage }).returning();
	res.status(201).json(row);
});

export default router;
