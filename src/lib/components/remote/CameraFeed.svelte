<script lang="ts">
import { onMount, onDestroy } from "svelte";

interface Props {
    onready?: () => void;
}

let { onready }: Props = $props();

let video: HTMLVideoElement;
let pc: RTCPeerConnection;
let error = $state(false);

async function start() {
    const SERVER = import.meta.env.VITE_CAMERA_HOST ?? location.hostname;

    pc = new RTCPeerConnection();

    pc.addTransceiver("video", { direction: "recvonly" });

    pc.ontrack = (event) => {
        video.srcObject = event.streams[0];
    };

    try {
        const offer = await pc.createOffer();
        await pc.setLocalDescription(offer);

        const response = await fetch(`http://${SERVER}:8889/robot/whep`, {
            method: "POST",
            headers: {
                "Content-Type": "application/sdp"
            },
            body: offer.sdp
        });

        if (!response.ok) {
            error = true;
            return;
        }

        const answer = await response.text();

        await pc.setRemoteDescription({
            type: "answer",
            sdp: answer
        });
    } catch {
        error = true;
    }
}

function handlePlaying() {
    onready?.();
}

onMount(start);

onDestroy(() => {
    pc?.close();
});
</script>

<video
    bind:this={video}
    onplaying={handlePlaying}
    autoplay
    playsinline
    muted
    class="w-full h-full object-cover"
></video>
