import { handler } from './build/handler.js';
import { createServer } from 'node:http';
import { WebSocketServer, WebSocket } from 'ws';

const VALID_DIRECTIONS = ['front', 'back', 'left', 'right', 'stop'];

function parseCommand(raw) {
	try {
		const msg = JSON.parse(raw);
		if (msg.type === 'ping') return msg;
		if (msg.type === 'command' && VALID_DIRECTIONS.includes(msg.direction)) return msg;
		return null;
	} catch {
		return null;
	}
}

const server = createServer(handler);
const wss = new WebSocketServer({ server, path: '/ws' });

const robots = new Set();
const controllers = new Set();

function broadcast(targets, msg) {
	const payload = JSON.stringify(msg);
	for (const ws of targets) {
		if (ws.readyState === WebSocket.OPEN) ws.send(payload);
	}
}

function sendStatus() {
	broadcast(controllers, { type: 'status', connectedRobots: robots.size });
}

wss.on('connection', (ws, req) => {
	const url = new URL(req.url ?? '/', `http://${req.headers.host}`);
	const role = url.searchParams.get('role');

	if (role === 'robot') {
		robots.add(ws);
		sendStatus();
		ws.on('close', () => {
			robots.delete(ws);
			sendStatus();
		});
	} else {
		controllers.add(ws);
		ws.send(JSON.stringify({ type: 'status', connectedRobots: robots.size }));
		ws.on('close', () => controllers.delete(ws));
	}

	ws.on('message', (data) => {
		const msg = parseCommand(data.toString());
		if (!msg) {
			ws.send(JSON.stringify({ type: 'error', message: 'Invalid message' }));
			return;
		}
		if (msg.type === 'ping') {
			ws.send(JSON.stringify({ type: 'pong' }));
			return;
		}
		if (msg.type === 'command') {
			broadcast(robots, { type: 'command', direction: msg.direction });
		}
	});
});

const port = parseInt(process.env.PORT ?? '3000', 10);
const host = process.env.HOST ?? '0.0.0.0';
server.listen(port, host, () => {
	console.log(`Server with WebSocket listening on ${host}:${port}`);
});
