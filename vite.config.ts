import tailwindcss from '@tailwindcss/vite';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';
import type { Plugin } from 'vite';
import { attachWebSocketServer } from './src/lib/server/ws/index.js';

function webSocketPlugin(): Plugin {
	return {
		name: 'websocket',
		configureServer(server) {
			if (server.httpServer) {
				attachWebSocketServer(server.httpServer);
			}
		}
	};
}

export default defineConfig({ plugins: [tailwindcss(), sveltekit(), webSocketPlugin()] });
