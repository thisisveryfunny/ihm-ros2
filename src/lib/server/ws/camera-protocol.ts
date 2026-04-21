/**
 * Protocol for the dedicated camera servo WebSocket (`/ws/camera`).
 * Independent from the movement protocol so the two control planes
 * can evolve separately.
 */

export type CameraDirection = 'up' | 'down' | 'left' | 'right' | 'stop';

export type CameraClientMessage =
	| { type: 'camera'; direction: CameraDirection }
	| { type: 'ping' };

export type CameraServerMessage =
	| { type: 'camera'; direction: CameraDirection }
	| { type: 'status'; connectedRobots: number }
	| { type: 'pong' }
	| { type: 'error'; message: string };

const VALID_CAMERA_DIRECTIONS: CameraDirection[] = ['up', 'down', 'left', 'right', 'stop'];

/** Validates and parses an incoming JSON string into a CameraClientMessage. Returns null if invalid. */
export function parseCameraClientMessage(raw: string): CameraClientMessage | null {
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
