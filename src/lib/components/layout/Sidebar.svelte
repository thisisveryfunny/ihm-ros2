<script lang="ts">
    import SidebarLink from './SidebarLink.svelte';

    interface Props {
        collapsed?: boolean;
        onToggle?: () => void;
    }

    let { collapsed = false, onToggle }: Props = $props();
</script>

<aside
    class="flex h-screen flex-col border-r border-surface-700 bg-surface-900 transition-all duration-300
        {collapsed ? 'w-16' : 'w-60'}"
>
    <!-- Header -->
    <div class="flex h-16 items-center gap-3 border-b border-surface-700 px-4">
        <div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-ros-orange/15">
            <!-- Robot icon -->
            <svg class="h-5 w-5 text-ros-orange" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="11" width="18" height="10" rx="2" />
                <path d="M9 11V7a3 3 0 0 1 6 0v4" />
                <circle cx="9" cy="16" r="1" fill="currentColor" />
                <circle cx="15" cy="16" r="1" fill="currentColor" />
            </svg>
        </div>
        {#if !collapsed}
            <div class="min-w-0">
                <p class="truncate text-sm font-semibold text-slate-100">ROS2 Dashboard</p>
                <p class="truncate text-xs text-slate-500">Yahboom Robot Car</p>
            </div>
        {/if}
    </div>

    <!-- Navigation -->
    <nav class="flex-1 space-y-1 overflow-y-auto p-3">
        <SidebarLink href="/" label="Vue d'ensemble" {collapsed}>
            {#snippet icon()}
                <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <rect x="3" y="3" width="7" height="7" rx="1" />
                    <rect x="14" y="3" width="7" height="7" rx="1" />
                    <rect x="3" y="14" width="7" height="7" rx="1" />
                    <rect x="14" y="14" width="7" height="7" rx="1" />
                </svg>
            {/snippet}
        </SidebarLink>

        <SidebarLink href="/speed" label="Vitesse" {collapsed}>
            {#snippet icon()}
                <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M12 2a10 10 0 1 0 10 10" />
                    <path d="M12 12 L18 6" />
                    <circle cx="12" cy="12" r="2" fill="currentColor" />
                    <path d="M12 6v2M6.3 17.7l1.4-1.4M4 12H6" />
                </svg>
            {/snippet}
        </SidebarLink>

        <SidebarLink href="/imu" label="Inertiel (IMU)" {collapsed}>
            {#snippet icon()}
                <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="3" />
                    <path d="M12 2v4M12 18v4M2 12h4M18 12h4" />
                    <path d="M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
                </svg>
            {/snippet}
        </SidebarLink>

        <SidebarLink href="/battery" label="Batterie" {collapsed}>
            {#snippet icon()}
                <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <rect x="2" y="7" width="18" height="10" rx="2" />
                    <path d="M22 11v2" stroke-width="3" stroke-linecap="round" />
                    <rect x="5" y="10" width="5" height="4" rx="0.5" fill="currentColor" stroke="none" />
                </svg>
            {/snippet}
        </SidebarLink>
    </nav>

    <!-- Footer toggle -->
    <div class="border-t border-surface-700 p-3">
        <button
            onclick={onToggle}
            class="flex w-full items-center justify-center rounded-lg px-3 py-2 text-slate-500 transition-colors hover:bg-surface-700 hover:text-slate-300"
            title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
            <svg
                class="h-4 w-4 transition-transform duration-300 {collapsed ? 'rotate-180' : ''}"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
            >
                <path d="M15 18l-6-6 6-6" />
            </svg>
            {#if !collapsed}
                <span class="ml-2 text-xs">Réduire</span>
            {/if}
        </button>

        <!-- Connection status -->
        <div class="mt-2 flex items-center gap-2 px-3 py-1">
            <span class="h-2 w-2 animate-pulse rounded-full bg-success-500"></span>
            {#if !collapsed}
                <span class="text-xs text-slate-500">Données simulées</span>
            {/if}
        </div>
    </div>
</aside>
