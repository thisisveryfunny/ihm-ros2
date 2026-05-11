import { handler } from './build/handler.js';
import { createServer } from 'node:http';
import { WebSocketServer, WebSocket } from 'ws';

const VALID_DIRECTIONS = ['front', 'back', 'left', 'right', 'stop'];
const VALID_SPEED_MODES = ['lent', 'normal', 'rapide'];
const VALID_CAMERA_DIRECTIONS = ['up', 'down', 'left', 'right', 'stop'];

function parseMessage(raw) {
	try {
		const msg = JSON.parse(raw);
		if (msg.type === 'ping') return msg;
		if (msg.type === 'command' && VALID_DIRECTIONS.includes(msg.direction)) {
			return {
				type: 'command',
				direction: msg.direction,
				speedMode: VALID_SPEED_MODES.includes(msg.speedMode) ? msg.speedMode : 'lent'
			};
		}
		if (msg.type === 'webrtc-offer' && typeof msg.sdp === 'string') return msg;
		if (msg.type === 'webrtc-answer' && typeof msg.sdp === 'string') return msg;
		if (msg.type === 'webrtc-ice' && typeof msg.candidate === 'string') return msg;
		if (msg.type === 'collision-alert' && typeof msg.distance === 'number' && typeof msg.blocked === 'boolean') return msg;
		if (msg.type === 'sign-detected' && (msg.sign === null || typeof msg.sign === 'string')) return msg;
		return null;
	} catch {
		return null;
	}
}

function parseCameraMessage(raw) {
	try {
		const msg = JSON.parse(raw);
		if (msg.type === 'ping') return { type: 'ping' };
		if (msg.type === 'camera' && VALID_CAMERA_DIRECTIONS.includes(msg.direction)) {
			return { type: 'camera', direction: msg.direction };
		}
		return null;
	} catch {
		return null;
	}
}

const server = createServer(handler);
const wss = new WebSocketServer({ noServer: true });
const cameraWss = new WebSocketServer({ noServer: true });

const robots = new Set();
const controllers = new Set();
const cameraRobots = new Set();
const cameraControllers = new Set();

server.on('upgrade', (req, socket, head) => {
	const { pathname } = new URL(req.url ?? '/', `http://${req.headers.host}`);
	if (pathname === '/ws') {
		wss.handleUpgrade(req, socket, head, (ws) => {
			wss.emit('connection', ws, req);
		});
		return;
	}
	if (pathname === '/ws/camera') {
		cameraWss.handleUpgrade(req, socket, head, (ws) => {
			cameraWss.emit('connection', ws, req);
		});
		return;
	}
	socket.destroy();
});

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

	const isRobot = role === 'robot';

	ws.on('message', (data) => {
		const msg = parseMessage(data.toString());
		if (!msg) {
			ws.send(JSON.stringify({ type: 'error', message: 'Invalid message' }));
			return;
		}
		if (msg.type === 'ping') {
			ws.send(JSON.stringify({ type: 'pong' }));
			return;
		}
		if (msg.type === 'command') {
			broadcast(robots, {
				type: 'command',
				direction: msg.direction,
				speedMode: msg.speedMode
			});
			return;
		}
		// WebRTC signaling relay
		if (msg.type === 'webrtc-offer' || msg.type === 'webrtc-answer' || msg.type === 'webrtc-ice') {
			broadcast(isRobot ? controllers : robots, msg);
			return;
		}
		// Robot status alerts → controllers
		if (msg.type === 'collision-alert' || msg.type === 'sign-detected') {
			broadcast(controllers, msg);
		}
	});
});

function sendCameraStatus() {
	broadcast(cameraControllers, { type: 'status', connectedRobots: cameraRobots.size });
}

cameraWss.on('connection', (ws, req) => {
	const url = new URL(req.url ?? '/', `http://${req.headers.host}`);
	const role = url.searchParams.get('role');

	if (role === 'robot') {
		cameraRobots.add(ws);
		sendCameraStatus();
		ws.on('close', () => {
			cameraRobots.delete(ws);
			sendCameraStatus();
		});
	} else {
		cameraControllers.add(ws);
		ws.send(JSON.stringify({ type: 'status', connectedRobots: cameraRobots.size }));
		ws.on('close', () => cameraControllers.delete(ws));
	}

	ws.on('message', (data) => {
		const msg = parseCameraMessage(data.toString());
		if (!msg) {
			ws.send(JSON.stringify({ type: 'error', message: 'Invalid message' }));
			return;
		}
		if (msg.type === 'ping') {
			ws.send(JSON.stringify({ type: 'pong' }));
			return;
		}
		if (msg.type === 'camera') {
			broadcast(cameraRobots, { type: 'camera', direction: msg.direction });
		}
	});
});

const port = parseInt(process.env.PORT ?? '3000', 10);
const host = process.env.HOST ?? '0.0.0.0';
server.listen(port, host, () => {
	console.log(`Server with WebSocket listening on ${host}:${port}`);
});
