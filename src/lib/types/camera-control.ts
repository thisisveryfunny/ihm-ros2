/**
 * Client-side types for the dedicated camera servo WebSocket protocol.
 * Mirrors the server-side types in $lib/server/ws/camera-protocol.ts
 * (which cannot be imported from client code).
 */

import type { ConnectionStatus } from './remote-control.js';

export type { ConnectionStatus };

export type CameraDirection = 'up' | 'down' | 'left' | 'right' | 'stop';

export type CameraClientMessage =
	| { type: 'camera'; direction: CameraDirection }
	| { type: 'ping' };

export type CameraServerMessage =
	| { type: 'camera'; direction: CameraDirection }
	| { type: 'status'; connectedRobots: number }
	| { type: 'pong' }
	| { type: 'error'; message: string };

const VALID_CAMERA_DIRECTIONS: ReadonlySet<string> = new Set([
	'up',
	'down',
	'left',
	'right',
	'stop'
]);

/** Validates and parses an incoming camera server message. Returns null if invalid. */
export function parseCameraServerMessage(raw: string): CameraServerMessage | null {
	try {
		const msg = JSON.parse(raw);
		if (msg.type === 'pong') return msg;
		if (msg.type === 'status' && typeof msg.connectedRobots === 'number') return msg;
		if (msg.type === 'error' && typeof msg.message === 'string') return msg;
		if (msg.type === 'camera' && VALID_CAMERA_DIRECTIONS.has(msg.direction)) return msg;
		return null;
	} catch {
		return null;
	}
}
