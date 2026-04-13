<script lang="ts">
import { onMount, onDestroy } from "svelte";

let video: HTMLVideoElement;
let pc: RTCPeerConnection;

const SERVER = import.meta.env.VITE_CAMERA_HOST ?? location.hostname;

async function start() {

    pc = new RTCPeerConnection();

    // IMPORTANT: request video
    pc.addTransceiver("video", { direction: "recvonly" });

    pc.ontrack = (event) => {
        video.srcObject = event.streams[0];
    };

    const offer = await pc.createOffer();
    await pc.setLocalDescription(offer);

    const response = await fetch(`http://${SERVER}:8889/robot/whep`, {
        method: "POST",
        headers: {
            "Content-Type": "application/sdp"
        },
        body: offer.sdp
    });

    const answer = await response.text();

    await pc.setRemoteDescription({
        type: "answer",
        sdp: answer
    });
}

onMount(start);

onDestroy(() => {
    pc?.close();
});
</script>

<video
bind:this={video}
autoplay
playsinline
muted
class="w-full h-full object-cover"
/>