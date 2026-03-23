<script lang="ts">
    import { onMount, onDestroy } from 'svelte';
    import { batteryService } from '$lib/services/index.js';
    import { batteryStore } from '$lib/stores/battery.svelte.js';
    import GaugeChart from '$lib/components/charts/GaugeChart.svelte';
    import LineChart from '$lib/components/charts/LineChart.svelte';
    import StatCard from '$lib/components/cards/StatCard.svelte';
    import StatusBadge from '$lib/components/cards/StatusBadge.svelte';
    import { formatVoltage, formatCurrent, formatTemperature, formatPercent, formatDuration } from '$lib/utils/format.js';

    let unsub: (() => void) | undefined;

    onMount(() => {
        unsub = batteryService.onReading((r) => batteryStore.push(r));
        batteryService.start();
    });

    onDestroy(() => {
        unsub?.();
        batteryService.stop();
        batteryStore.reset();
    });

    const hasData = $derived(batteryStore.history.length > 0);

    const percentageSeries = $derived([
        {
            name: 'Charge',
            data: batteryStore.history.map((r) => ({ timestamp: r.timestamp, value: r.percentage })),
            color: '#22c55e',
            unit: '%',
        },
    ]);

    const voltageSeries = $derived([
        {
            name: 'Tension',
            data: batteryStore.history.map((r) => ({ timestamp: r.timestamp, value: r.voltage })),
            color: '#fbbf24',
            unit: 'V',
        },
    ]);

    const batteryVariant = $derived(() => {
        const pct = batteryStore.stats?.current ?? 100;
        if (pct < 20) return 'danger' as const;
        if (pct < 40) return 'warning' as const;
        return 'success' as const;
    });
</script>

<div class="space-y-6">
    <!-- Page header -->
    <div class="flex items-center justify-between">
        <div>
            <h1 class="text-xl font-bold text-slate-100">Batterie</h1>
            <p class="mt-1 text-sm text-slate-500">Niveau de charge et données électriques</p>
        </div>
        {#if batteryStore.current}
            <StatusBadge status={batteryStore.current.status} />
        {/if}
    </div>

    <!-- Main gauge + stats -->
    <div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <!-- Gauge -->
        <div class="rounded-xl border border-surface-700 bg-surface-800 p-6">
            <GaugeChart
                value={batteryStore.current?.percentage ?? 0}
                label="Charge"
                height="320px"
            />
        </div>

        <!-- Key metrics -->
        <div class="grid grid-cols-2 gap-4 content-start">
            <StatCard
                label="Charge"
                value={formatPercent(batteryStore.current?.percentage ?? 0)}
                variant={batteryVariant()}
            >
                {#snippet icon()}
                    <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <rect x="2" y="7" width="18" height="10" rx="2" />
                        <path d="M22 11v2" stroke-width="3" stroke-linecap="round" />
                    </svg>
                {/snippet}
            </StatCard>

            <StatCard
                label="Tension"
                value={formatVoltage(batteryStore.current?.voltage ?? 0)}
                variant="warning"
            >
                {#snippet icon()}
                    <svg class="h-5 w-5 text-warning-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" />
                    </svg>
                {/snippet}
            </StatCard>

            <StatCard
                label="Courant"
                value={formatCurrent(batteryStore.current?.current ?? 0)}
                sublabel={batteryStore.current?.current && batteryStore.current.current > 0 ? 'Charge entrante' : 'Décharge'}
            />

            <StatCard
                label="Température"
                value={formatTemperature(batteryStore.current?.temperature ?? 0)}
                variant={
                    (batteryStore.current?.temperature ?? 0) > 40 ? 'danger' :
                    (batteryStore.current?.temperature ?? 0) > 35 ? 'warning' : 'default'
                }
            >
                {#snippet icon()}
                    <svg class="h-5 w-5 text-slate-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M14 14.76V3.5a2.5 2.5 0 0 0-5 0v11.26a4.5 4.5 0 1 0 5 0z" />
                    </svg>
                {/snippet}
            </StatCard>

            {#if batteryStore.current?.estimatedRemainingMinutes}
                <div class="col-span-2">
                    <StatCard
                        label="Autonomie estimée"
                        value={formatDuration(batteryStore.current.estimatedRemainingMinutes)}
                        sublabel="Basé sur la consommation actuelle"
                        variant="accent"
                    />
                </div>
            {/if}

            {#if batteryStore.stats}
                <div class="col-span-2">
                    <StatCard
                        label="Tendance"
                        value={batteryStore.stats.trend === 'rising' ? '↑ En hausse' : batteryStore.stats.trend === 'falling' ? '↓ En baisse' : '→ Stable'}
                        variant={batteryStore.stats.trend === 'rising' ? 'success' : batteryStore.stats.trend === 'falling' ? 'warning' : 'default'}
                    />
                </div>
            {/if}
        </div>
    </div>

    <!-- Charge history chart -->
    <div class="rounded-xl border border-surface-700 bg-surface-800 p-4">
        <h2 class="mb-4 text-sm font-medium text-slate-300">Historique de charge</h2>
        <LineChart series={percentageSeries} yAxisLabel="%" loading={!hasData} />
    </div>

    <!-- Voltage history chart -->
    <div class="rounded-xl border border-surface-700 bg-surface-800 p-4">
        <h2 class="mb-4 text-sm font-medium text-slate-300">Historique de tension</h2>
        <LineChart series={voltageSeries} yAxisLabel="V" loading={!hasData} />
    </div>
</div>
