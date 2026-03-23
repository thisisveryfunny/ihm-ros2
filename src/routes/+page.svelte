<script lang="ts">
    import { onMount, onDestroy } from 'svelte';
    import { speedService, imuService, batteryService } from '$lib/services/index.js';
    import { speedStore } from '$lib/stores/speed.svelte.js';
    import { imuStore } from '$lib/stores/imu.svelte.js';
    import { batteryStore } from '$lib/stores/battery.svelte.js';
    import StatCard from '$lib/components/cards/StatCard.svelte';
    import StatusBadge from '$lib/components/cards/StatusBadge.svelte';
    import { formatSpeed, formatPercent, formatVoltage, formatAngleDeg } from '$lib/utils/format.js';

    const unsubs: Array<() => void> = [];

    onMount(() => {
        unsubs.push(speedService.onReading((r) => speedStore.push(r)));
        unsubs.push(imuService.onReading((r) => imuStore.push(r)));
        unsubs.push(batteryService.onReading((r) => batteryStore.push(r)));
        speedService.start();
        imuService.start();
        batteryService.start();
    });

    onDestroy(() => {
        unsubs.forEach((fn) => fn());
        speedService.stop();
        imuService.stop();
        batteryService.stop();
    });

    const currentTime = $derived(
        speedStore.current ? new Date(speedStore.current.timestamp).toLocaleTimeString() : '--:--:--'
    );
</script>

<div class="space-y-6">
    <!-- Page header -->
    <div class="flex items-center justify-between">
        <div>
            <h1 class="text-xl font-bold text-slate-100">Vue d'ensemble</h1>
            <p class="mt-1 text-sm text-slate-500">Yahboom Raspberry Pi 5 — ROS2 Robot Car</p>
        </div>
        <div class="flex items-center gap-3">
            <StatusBadge status="connected" label="Données simulées" />
            <span class="font-mono text-xs text-slate-500">{currentTime}</span>
        </div>
    </div>

    <!-- System overview cards -->
    <div class="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <a href="/speed" class="group block transition-transform hover:-translate-y-0.5">
            <StatCard
                label="Vitesse actuelle"
                value={formatSpeed(speedStore.stats.current)}
                sublabel="→ Voir détails"
                variant="accent"
            >
                {#snippet icon()}
                    <svg class="h-5 w-5 text-accent-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M12 2a10 10 0 1 0 10 10" />
                        <path d="M12 12 L18 6" />
                        <circle cx="12" cy="12" r="2" fill="currentColor" />
                    </svg>
                {/snippet}
            </StatCard>
        </a>

        <a href="/battery" class="group block transition-transform hover:-translate-y-0.5">
            <StatCard
                label="Batterie"
                value={formatPercent(batteryStore.current?.percentage ?? 0)}
                sublabel={batteryStore.current?.status ?? 'inconnu'}
                variant={
                    (batteryStore.current?.percentage ?? 100) < 20 ? 'danger' :
                    (batteryStore.current?.percentage ?? 100) < 40 ? 'warning' : 'success'
                }
            >
                {#snippet icon()}
                    <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <rect x="2" y="7" width="18" height="10" rx="2" />
                        <path d="M22 11v2" stroke-width="3" stroke-linecap="round" />
                    </svg>
                {/snippet}
            </StatCard>
        </a>

        <a href="/imu" class="group block transition-transform hover:-translate-y-0.5">
            <StatCard
                label="Tangage (Pitch)"
                value={formatAngleDeg(imuStore.current?.orientation.pitch ?? 0)}
                sublabel="→ Voir IMU"
            >
                {#snippet icon()}
                    <svg class="h-5 w-5 text-slate-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="3" />
                        <path d="M12 2v4M12 18v4M2 12h4M18 12h4" />
                    </svg>
                {/snippet}
            </StatCard>
        </a>

        <a href="/imu" class="group block transition-transform hover:-translate-y-0.5">
            <StatCard
                label="Roulis (Roll)"
                value={formatAngleDeg(imuStore.current?.orientation.roll ?? 0)}
                sublabel="→ Voir IMU"
            >
                {#snippet icon()}
                    <svg class="h-5 w-5 text-slate-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
                        <circle cx="12" cy="12" r="3" />
                    </svg>
                {/snippet}
            </StatCard>
        </a>
    </div>

    <!-- Quick nav cards -->
    <div class="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <a href="/speed" class="rounded-xl border border-surface-700 bg-surface-800 p-5 transition-all hover:border-accent-500/50 hover:bg-surface-700">
            <div class="mb-3 flex h-10 w-10 items-center justify-center rounded-lg bg-accent-500/15">
                <svg class="h-6 w-6 text-accent-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M12 2a10 10 0 1 0 10 10" />
                    <path d="M12 12 L18 6" />
                    <circle cx="12" cy="12" r="2" fill="currentColor" />
                </svg>
            </div>
            <h3 class="font-semibold text-slate-100">Vitesse</h3>
            <p class="mt-1 text-sm text-slate-500">Vitesse linéaire et angulaire en temps réel avec historique</p>
            <div class="mt-3 flex items-center gap-1 text-xs font-medium text-accent-400">
                <span>Voir la page</span>
                <svg class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
            </div>
        </a>

        <a href="/imu" class="rounded-xl border border-surface-700 bg-surface-800 p-5 transition-all hover:border-success-500/50 hover:bg-surface-700">
            <div class="mb-3 flex h-10 w-10 items-center justify-center rounded-lg bg-success-500/15">
                <svg class="h-6 w-6 text-success-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="3" />
                    <path d="M12 2v4M12 18v4M2 12h4M18 12h4" />
                    <path d="M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
                </svg>
            </div>
            <h3 class="font-semibold text-slate-100">Centrale Inertielle</h3>
            <p class="mt-1 text-sm text-slate-500">Accélération, gyroscope et orientation (roulis, tangage, lacet)</p>
            <div class="mt-3 flex items-center gap-1 text-xs font-medium text-success-400">
                <span>Voir la page</span>
                <svg class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
            </div>
        </a>

        <a href="/battery" class="rounded-xl border border-surface-700 bg-surface-800 p-5 transition-all hover:border-warning-500/50 hover:bg-surface-700">
            <div class="mb-3 flex h-10 w-10 items-center justify-center rounded-lg bg-warning-500/15">
                <svg class="h-6 w-6 text-warning-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <rect x="2" y="7" width="18" height="10" rx="2" />
                    <path d="M22 11v2" stroke-width="3" stroke-linecap="round" />
                    <rect x="5" y="10" width="5" height="4" rx="0.5" fill="currentColor" stroke="none" />
                </svg>
            </div>
            <h3 class="font-semibold text-slate-100">Batterie</h3>
            <p class="mt-1 text-sm text-slate-500">Niveau de charge, tension, courant et autonomie estimée</p>
            <div class="mt-3 flex items-center gap-1 text-xs font-medium text-warning-400">
                <span>Voir la page</span>
                <svg class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
            </div>
        </a>
    </div>

    <!-- Tech info banner -->
    <div class="rounded-xl border border-ros-orange/20 bg-ros-orange/5 p-4">
        <div class="flex items-start gap-3">
            <svg class="mt-0.5 h-5 w-5 shrink-0 text-ros-orange" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            <div>
                <p class="text-sm font-medium text-ros-orange">Mode simulation</p>
                <p class="mt-1 text-xs text-slate-500">
                    Les données sont générées localement. Pour connecter le robot réel, implémentez
                    <code class="rounded bg-surface-700 px-1 py-0.5 font-mono text-slate-300">ROS2SpeedService</code>,
                    <code class="rounded bg-surface-700 px-1 py-0.5 font-mono text-slate-300">ROS2ImuService</code> et
                    <code class="rounded bg-surface-700 px-1 py-0.5 font-mono text-slate-300">ROS2BatteryService</code>
                    dans <code class="rounded bg-surface-700 px-1 py-0.5 font-mono text-slate-300">src/lib/services/ros2/</code>.
                </p>
            </div>
        </div>
    </div>
</div>
