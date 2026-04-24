import { WebSocketServer, WebSocket } from 'ws';
import type { Server } from 'node:http';
import { parseClientMessage, type ServerMessage } from './protocol.js';

const HEARTBEAT_INTERVAL_MS = 30_000;

export function attachWebSocketServer(server: Server): WebSocketServer {
	const wss = new WebSocketServer({ noServer: true });

	server.on('upgrade', (req, socket, head) => {
		const { pathname } = new URL(req.url ?? '/', `http://${req.headers.host}`);
		if (pathname === '/ws') {
			wss.handleUpgrade(req, socket, head, (ws) => {
				wss.emit('connection', ws, req);
			});
		}
	});

	const robots = new Set<WebSocket>();
	const controllers = new Set<WebSocket>();

	function broadcast(targets: Set<WebSocket>, msg: ServerMessage) {
		const payload = JSON.stringify(msg);
		for (const ws of targets) {
			if (ws.readyState === WebSocket.OPEN) ws.send(payload);
		}
	}

	function sendStatusToControllers() {
		broadcast(controllers, { type: 'status', connectedRobots: robots.size });
	}

	wss.on('connection', (ws, req) => {
		const url = new URL(req.url ?? '/', `http://${req.headers.host}`);
		const role = url.searchParams.get('role');

		if (role === 'robot') {
			robots.add(ws);
			sendStatusToControllers();
			ws.on('close', () => {
				robots.delete(ws);
				sendStatusToControllers();
			});
		} else {
			controllers.add(ws);
			ws.send(JSON.stringify({ type: 'status', connectedRobots: robots.size }));
			ws.on('close', () => controllers.delete(ws));
		}

		const isRobot = role === 'robot';

		ws.on('message', (data) => {
			const msg = parseClientMessage(data.toString());
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
			if (msg.type === 'webrtc-offer') {
				broadcast(isRobot ? controllers : robots, msg);
				return;
			}
			if (msg.type === 'webrtc-answer') {
				broadcast(isRobot ? controllers : robots, msg);
				return;
			}
			if (msg.type === 'webrtc-ice') {
				broadcast(isRobot ? controllers : robots, msg);
				return;
			}
			// Robot status alerts → broadcast to controllers
			if (msg.type === 'collision-alert' || msg.type === 'sign-detected') {
				broadcast(controllers, msg);
			}
		});
	});

	// Heartbeat to detect dead connections
	const interval = setInterval(() => {
		for (const ws of wss.clients) {
			if ((ws as any).__alive === false) {
				ws.terminate();
				continue;
			}
			(ws as any).__alive = false;
			ws.ping();
		}
	}, HEARTBEAT_INTERVAL_MS);

	wss.on('connection', (ws) => {
		(ws as any).__alive = true;
		ws.on('pong', () => {
			(ws as any).__alive = true;
		});
	});

	wss.on('close', () => clearInterval(interval));

	return wss;
}
