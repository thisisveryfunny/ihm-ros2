/**
 * Client-side types for the remote control WebSocket protocol.
 * Mirrors the server-side types in $lib/server/ws/protocol.ts
 * (which cannot be imported from client code).
 */

export type Direction = 'front' | 'back' | 'left' | 'right' | 'stop';

export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'error';

export type ClientMessage =
	| { type: 'command'; direction: Direction }
	| { type: 'ping' };

export type ServerMessage =
	| { type: 'command'; direction: Direction }
	| { type: 'status'; connectedRobots: number }
	| { type: 'pong' }
	| { type: 'error'; message: string };

const VALID_DIRECTIONS: ReadonlySet<string> = new Set(['front', 'back', 'left', 'right', 'stop']);

/** Validates and parses an incoming server message. Returns null if invalid. */
export function parseServerMessage(raw: string): ServerMessage | null {
	try {
		const msg = JSON.parse(raw);
		if (msg.type === 'pong') return msg;
		if (msg.type === 'status' && typeof msg.connectedRobots === 'number') return msg;
		if (msg.type === 'error' && typeof msg.message === 'string') return msg;
		if (msg.type === 'command' && VALID_DIRECTIONS.has(msg.direction)) return msg;
		return null;
	} catch {
		return null;
	}
}
