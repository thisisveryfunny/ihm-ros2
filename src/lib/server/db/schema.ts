import { pgTable, serial, real, timestamp } from 'drizzle-orm/pg-core';

export const batterie = pgTable('batterie', {
	id: serial('id').primaryKey(),
	percentage: real('percentage').notNull(),
	createdAt: timestamp('created_at', { withTimezone: true }).notNull().defaultNow()
});

export const vitesse = pgTable('vitesse', {
	id: serial('id').primaryKey(),
	speed: real('speed').notNull(),
	createdAt: timestamp('created_at', { withTimezone: true }).notNull().defaultNow()
});

export const imu = pgTable('imu', {
	id: serial('id').primaryKey(),
	accelX: real('accel_x').notNull(),
	accelY: real('accel_y').notNull(),
	accelZ: real('accel_z').notNull(),
	gyroX: real('gyro_x').notNull(),
	gyroY: real('gyro_y').notNull(),
	gyroZ: real('gyro_z').notNull(),
	magX: real('mag_x').notNull(),
	magY: real('mag_y').notNull(),
	magZ: real('mag_z').notNull(),
	createdAt: timestamp('created_at', { withTimezone: true }).notNull().defaultNow()
});
