<script lang="ts">
	import { onMount, onDestroy } from 'svelte';

	let videoElement: HTMLVideoElement;
	let pc: RTCPeerConnection | null = null;

	const SERVER = "localhost"; // change this
	const STREAM = "webrtc://" + SERVER + "/live/robot";

	async function startStream() {
		pc = new RTCPeerConnection();

		pc.ontrack = (event) => {
			videoElement.srcObject = event.streams[0];
		};

		const offer = await pc.createOffer({
			offerToReceiveAudio: false,
			offerToReceiveVideo: true
		});

		await pc.setLocalDescription(offer);

		const response = await fetch(`http://${SERVER}:1985/rtc/v1/play/`, {
			method: "POST",
			headers: {
				"Content-Type": "application/json"
			},
			body: JSON.stringify({
				api: `http://${SERVER}:1985/rtc/v1/play/`,
				streamurl: STREAM,
				sdp: offer.sdp
			})
		});

		const data = await response.json();

		await pc.setRemoteDescription({
			type: "answer",
			sdp: data.sdp
		});
	}

	onMount(() => {
		startStream();
	});

	onDestroy(() => {
		if (pc) {
			pc.close();
			pc = null;
		}
	});
</script>

<div class="w-full h-full rounded-xl overflow-hidden bg-black">
	<video
		bind:this={videoElement}
		autoplay
		playsinline
		muted
		class="w-full h-full object-cover"
	/>
</div>