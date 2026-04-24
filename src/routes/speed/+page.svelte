<script lang="ts">
    import { onMount, onDestroy } from 'svelte';
    import { speedService } from '$lib/services/index.js';
    import { speedStore } from '$lib/stores/speed.svelte.js';
    import LineChart from '$lib/components/charts/LineChart.svelte';
    import StatCard from '$lib/components/cards/StatCard.svelte';
    import { formatSpeed } from '$lib/utils/format.js';

    let unsub: (() => void) | undefined;

    onMount(() => {
        unsub = speedService.onReading((r) => speedStore.push(r));
        speedService.start();
    });

    onDestroy(() => {
        unsub?.();
        speedService.stop();
        speedStore.reset();
    });

    const speedSeries = $derived([
        {
            name: 'Vitesse linéaire',
            data: speedStore.history.map((r) => ({ timestamp: r.timestamp, value: r.magnitude })),
            color: '#818cf8',
            unit: 'm/s',
        },
    ]);

    const hasData = $derived(speedStore.history.length > 0);
</script>

<div class="space-y-6">
    <!-- Page header -->
    <div>
        <h1 class="text-xl font-bold text-slate-100">Vitesse du Robot</h1>
        <p class="mt-1 text-sm text-slate-500">Données de vitesse linéaire en temps réel</p>
    </div>

    <!-- Stats row -->
    <div class="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard
            label="Vitesse actuelle"
            value={formatSpeed(speedStore.stats.current)}
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

        <StatCard
            label="Vitesse max"
            value={formatSpeed(speedStore.stats.max)}
            variant="danger"
        >
            {#snippet icon()}
                <svg class="h-5 w-5 text-danger-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="18 15 12 9 6 15" />
                </svg>
            {/snippet}
        </StatCard>

        <StatCard
            label="Vitesse min"
            value={formatSpeed(speedStore.stats.min)}
        >
            {#snippet icon()}
                <svg class="h-5 w-5 text-slate-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="6 9 12 15 18 9" />
                </svg>
            {/snippet}
        </StatCard>

        <StatCard
            label="Vitesse moyenne"
            value={formatSpeed(speedStore.stats.average)}
            variant="success"
        >
            {#snippet icon()}
                <svg class="h-5 w-5 text-success-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <line x1="5" y1="12" x2="19" y2="12" />
                    <line x1="5" y1="8" x2="14" y2="8" />
                    <line x1="5" y1="16" x2="14" y2="16" />
                </svg>
            {/snippet}
        </StatCard>
    </div>

    <!-- Linear speed components -->
    {#if speedStore.current}
        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <StatCard
                label="Composante X"
                value={formatSpeed(speedStore.current.linearX)}
                sublabel="Direction avant/arrière"
            />
        </div>
    {/if}

    <!-- Speed over time chart -->
    <div class="rounded-xl border border-surface-700 bg-surface-800 p-4">
        <h2 class="mb-4 text-sm font-medium text-slate-300">Vitesse linéaire dans le temps</h2>
        <LineChart series={speedSeries} yAxisLabel="m/s" loading={!hasData} />
    </div>
</div>
