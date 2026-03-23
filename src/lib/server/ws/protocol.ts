export type Direction = 'front' | 'back' | 'left' | 'right' | 'stop';

export type ClientMessage = { type: 'command'; direction: Direction } | { type: 'ping' };

export type ServerMessage =
	| { type: 'command'; direction: Direction }
	| { type: 'status'; connectedRobots: number }
	| { type: 'pong' }
	| { type: 'error'; message: string };

const VALID_DIRECTIONS: Direction[] = ['front', 'back', 'left', 'right', 'stop'];

/** Validates and parses an incoming JSON string into a ClientMessage. Returns null if invalid. */
export function parseClientMessage(raw: string): ClientMessage | null {
	try {
		const msg = JSON.parse(raw);
		if (msg.type === 'ping') return msg;
		if (msg.type === 'command' && VALID_DIRECTIONS.includes(msg.direction)) {
			return msg;
		}
		return null;
	} catch {
		return null;
	}
}
