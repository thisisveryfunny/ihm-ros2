export type Direction = 'front' | 'back' | 'left' | 'right' | 'stop';

export type ClientMessage =
	| { type: 'command'; direction: Direction }
	| { type: 'ping' }
	| { type: 'webrtc-offer'; sdp: string }
	| { type: 'webrtc-answer'; sdp: string }
	| {
			type: 'webrtc-ice';
			candidate: string;
			sdpMid: string | null;
			sdpMLineIndex: number | null;
	  }
	| { type: 'collision-alert'; distance: number; blocked: boolean }
	| { type: 'sign-detected'; sign: string | null };

export type ServerMessage =
	| { type: 'command'; direction: Direction }
	| { type: 'status'; connectedRobots: number }
	| { type: 'pong' }
	| { type: 'error'; message: string }
	| { type: 'webrtc-offer'; sdp: string }
	| { type: 'webrtc-answer'; sdp: string }
	| {
			type: 'webrtc-ice';
			candidate: string;
			sdpMid: string | null;
			sdpMLineIndex: number | null;
	  }
	| { type: 'collision-alert'; distance: number; blocked: boolean }
	| { type: 'sign-detected'; sign: string | null };

const VALID_DIRECTIONS: Direction[] = ['front', 'back', 'left', 'right', 'stop'];

/** Validates and parses an incoming JSON string into a ClientMessage. Returns null if invalid. */
export function parseClientMessage(raw: string): ClientMessage | null {
	try {
		const msg = JSON.parse(raw);
		if (msg.type === 'ping') return msg;
		if (msg.type === 'command' && VALID_DIRECTIONS.includes(msg.direction)) {
			return msg;
		}
		if (msg.type === 'webrtc-offer' && typeof msg.sdp === 'string') {
			return { type: 'webrtc-offer', sdp: msg.sdp };
		}
		if (msg.type === 'webrtc-answer' && typeof msg.sdp === 'string') {
			return { type: 'webrtc-answer', sdp: msg.sdp };
		}
		if (msg.type === 'webrtc-ice' && typeof msg.candidate === 'string') {
			return {
				type: 'webrtc-ice',
				candidate: msg.candidate,
				sdpMid: msg.sdpMid ?? null,
				sdpMLineIndex: msg.sdpMLineIndex ?? null
			};
		}
		if (
			msg.type === 'collision-alert' &&
			typeof msg.distance === 'number' &&
			typeof msg.blocked === 'boolean'
		) {
			return { type: 'collision-alert', distance: msg.distance, blocked: msg.blocked };
		}
		if (msg.type === 'sign-detected') {
			const sign = msg.sign;
			if (sign === null || ['stop', 'up', 'down', 'left', 'right'].includes(sign)) {
				return { type: 'sign-detected', sign };
			}
		}
		return null;
	} catch {
		return null;
	}
}
