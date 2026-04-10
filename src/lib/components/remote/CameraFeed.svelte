<script lang="ts">
import { onMount } from "svelte";

let video: HTMLVideoElement;

onMount(() => {
    const pc = new RTCPeerConnection();

    pc.ontrack = (event) => {
        video.srcObject = event.streams[0];
    };

    fetch("http://localhost:8889/robot/whep", {
        method: "POST"
    })
});
</script>

<video bind:this={video} autoplay playsinline></video>