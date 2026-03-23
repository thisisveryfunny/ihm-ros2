import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { db } from '$lib/server/db';
import { imu } from '$lib/server/db/schema';
import { desc } from 'drizzle-orm';

export const GET: RequestHandler = async () => {
	const rows = await db.select().from(imu).orderBy(desc(imu.createdAt));
	return json(rows);
};

export const POST: RequestHandler = async ({ request }) => {
	const { accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z, mag_x, mag_y, mag_z } =
		await request.json();

	const [row] = await db
		.insert(imu)
		.values({
			accelX: accel_x,
			accelY: accel_y,
			accelZ: accel_z,
			gyroX: gyro_x,
			gyroY: gyro_y,
			gyroZ: gyro_z,
			magX: mag_x,
			magY: mag_y,
			magZ: mag_z
		})
		.returning();

	return json(row, { status: 201 });
};
