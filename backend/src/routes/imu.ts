import { Router } from 'express';
import { db } from '../db/index.js';
import { imu } from '../db/schema.js';
import { desc } from 'drizzle-orm';

const router = Router();

router.get('/', async (_req, res) => {
	const rows = await db.select().from(imu).orderBy(desc(imu.createdAt));
	res.json(rows);
});

router.post('/', async (req, res) => {
	const { accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z } = req.body;

	const [row] = await db
		.insert(imu)
		.values({
			accelX: accel_x,
			accelY: accel_y,
			accelZ: accel_z,
			gyroX: gyro_x,
			gyroY: gyro_y,
			gyroZ: gyro_z
		})
		.returning();

	res.status(201).json(row);
});

export default router;
