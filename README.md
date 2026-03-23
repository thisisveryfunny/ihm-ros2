# IHM ROS2

SvelteKit dashboard for a ROS2 robot. Stores and serves telemetry data (battery, speed, IMU) via a PostgreSQL database.

## Prerequisites

- Node.js
- Docker & Docker Compose

## Database Setup

1. Start PostgreSQL:

```sh
npm run db:start
```

This runs `db/docker-compose.yml` which starts a Postgres 16 container and executes `db/init.sql` to create the tables.

2. Create a `.env` file at the project root:

```
DATABASE_URL=postgresql://ros2:ros2@localhost:5432/ros2
```

3. (Optional) Push the Drizzle schema to verify sync:

```sh
npm run db:push
```

## Developing

```sh
npm install
npm run dev
```

## API Endpoints

### `POST /api/batterie`

Store a battery reading.

```json
{ "percentage": 85.5 }
```

### `GET /api/batterie`

Returns all battery readings, newest first.

### `POST /api/vitesse`

Store a speed reading.

```json
{ "speed": 1.23 }
```

### `GET /api/vitesse`

Returns all speed readings, newest first.

### `POST /api/imu`

Store an IMU reading (accelerometer in m/s², gyroscope in rad/s, magnetometer in µT).

```json
{
  "accel_x": 0.1, "accel_y": 0.2, "accel_z": 9.8,
  "gyro_x": 0.01, "gyro_y": -0.02, "gyro_z": 0.0,
  "mag_x": 25.0, "mag_y": -10.5, "mag_z": 40.0
}
```

### `GET /api/imu`

Returns all IMU readings, newest first.

All POST endpoints return the created row with a `201` status. All responses include an auto-generated `id` and `createdAt` timestamp.

## Building

```sh
npm run build
```

Preview the production build with `npm run preview`.
