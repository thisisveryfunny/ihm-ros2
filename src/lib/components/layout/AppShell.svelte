<script lang="ts">
    import Sidebar from './Sidebar.svelte';

    interface Props {
        children: import('svelte').Snippet;
    }

    let { children }: Props = $props();

    let collapsed = $state(false);
</script>

<div class="flex h-screen overflow-hidden bg-surface-950">
    <Sidebar {collapsed} onToggle={() => (collapsed = !collapsed)} />

    <main class="flex-1 overflow-y-auto">
        <div class="min-h-full p-6">
            {@render children()}
        </div>
    </main>
</div>
