import 'dotenv/config';
import express from 'express';
import cors from 'cors';
import { createServer } from 'node:http';
import { attachWebSocketServer } from './ws/index.js';
import batterieRouter from './routes/batterie.js';
import vitesseRouter from './routes/vitesse.js';
import imuRouter from './routes/imu.js';

const app = express();

app.use(cors());
app.use(express.json());

app.use('/api/batterie', batterieRouter);
app.use('/api/vitesse', vitesseRouter);
app.use('/api/imu', imuRouter);

app.get('/health', (_req, res) => {
	res.json({ status: 'ok' });
});

const server = createServer(app);

attachWebSocketServer(server);

const port = parseInt(process.env.PORT ?? '3001', 10);
const host = process.env.HOST ?? '0.0.0.0';
server.listen(port, host, () => {
	console.log(`Backend server listening on ${host}:${port}`);
});
