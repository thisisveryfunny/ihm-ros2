/**
 * Client-side types for the remote control WebSocket protocol.
 * Mirrors the server-side types in $lib/server/ws/protocol.ts
 * (which cannot be imported from client code).
 */

export type Direction = 'front' | 'back' | 'left' | 'right' | 'stop';
export type SpeedMode = 'lent' | 'normal' | 'rapide';

export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'error';

export type ClientMessage =
	| { type: 'command'; direction: Direction; speedMode: SpeedMode }
	| { type: 'ping' };

export type ServerMessage =
	| { type: 'command'; direction: Direction; speedMode: SpeedMode }
	| { type: 'status'; connectedRobots: number }
	| { type: 'pong' }
	| { type: 'error'; message: string }
	| { type: 'collision-alert'; distance: number; blocked: boolean };

const VALID_DIRECTIONS: ReadonlySet<string> = new Set(['front', 'back', 'left', 'right', 'stop']);
const VALID_SPEED_MODES: ReadonlySet<string> = new Set(['lent', 'normal', 'rapide']);

function parseSpeedMode(value: unknown): SpeedMode {
	return typeof value === 'string' && VALID_SPEED_MODES.has(value) ? (value as SpeedMode) : 'lent';
}

/** Validates and parses an incoming server message. Returns null if invalid. */
export function parseServerMessage(raw: string): ServerMessage | null {
	try {
		const msg = JSON.parse(raw);
		if (msg.type === 'pong') return msg;
		if (msg.type === 'status' && typeof msg.connectedRobots === 'number') return msg;
		if (msg.type === 'error' && typeof msg.message === 'string') return msg;
		if (msg.type === 'command' && VALID_DIRECTIONS.has(msg.direction)) {
			return {
				type: 'command',
				direction: msg.direction,
				speedMode: parseSpeedMode(msg.speedMode)
			};
		}
		if (
			msg.type === 'collision-alert' &&
			typeof msg.distance === 'number' &&
			typeof msg.blocked === 'boolean'
		) {
			return { type: 'collision-alert', distance: msg.distance, blocked: msg.blocked };
		}
		return null;
	} catch {
		return null;
	}
}
