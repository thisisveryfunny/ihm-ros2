import { Router } from 'express';
import { db } from '../db/index.js';
import { vitesse } from '../db/schema.js';
import { desc } from 'drizzle-orm';

const router = Router();

router.get('/', async (_req, res) => {
	const rows = await db.select().from(vitesse).orderBy(desc(vitesse.createdAt));
	res.json(rows);
});

router.post('/', async (req, res) => {
	const { speed } = req.body;
	const [row] = await db.insert(vitesse).values({ speed }).returning();
	res.status(201).json(row);
});

export default router;
