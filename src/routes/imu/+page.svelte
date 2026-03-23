<script lang="ts">
    import { onMount, onDestroy } from 'svelte';
    import { imuService } from '$lib/services/index.js';
    import { imuStore } from '$lib/stores/imu.svelte.js';
    import LineChart from '$lib/components/charts/LineChart.svelte';
    import Vector3Card from '$lib/components/cards/Vector3Card.svelte';
    import { formatAcceleration, formatAngularRate, formatAngleDeg } from '$lib/utils/format.js';

    let unsub: (() => void) | undefined;

    onMount(() => {
        unsub = imuService.onReading((r) => imuStore.push(r));
        imuService.start();
    });

    onDestroy(() => {
        unsub?.();
        imuService.stop();
        imuStore.reset();
    });

    const hasData = $derived(imuStore.history.length > 0);

    // Acceleration series (x, y, z)
    const accelSeries = $derived([
        {
            name: 'Acc X',
            data: imuStore.history.map((r) => ({ timestamp: r.timestamp, value: r.acceleration.x })),
            color: '#f87171',
            unit: 'm/s²',
        },
        {
            name: 'Acc Y',
            data: imuStore.history.map((r) => ({ timestamp: r.timestamp, value: r.acceleration.y })),
            color: '#4ade80',
            unit: 'm/s²',
        },
        {
            name: 'Acc Z',
            data: imuStore.history.map((r) => ({ timestamp: r.timestamp, value: r.acceleration.z })),
            color: '#818cf8',
            unit: 'm/s²',
        },
    ]);

    // Gyroscope series
    const gyroSeries = $derived([
        {
            name: 'Gyro X',
            data: imuStore.history.map((r) => ({ timestamp: r.timestamp, value: r.gyroscope.x })),
            color: '#f87171',
            unit: 'rad/s',
        },
        {
            name: 'Gyro Y',
            data: imuStore.history.map((r) => ({ timestamp: r.timestamp, value: r.gyroscope.y })),
            color: '#4ade80',
            unit: 'rad/s',
        },
        {
            name: 'Gyro Z',
            data: imuStore.history.map((r) => ({ timestamp: r.timestamp, value: r.gyroscope.z })),
            color: '#818cf8',
            unit: 'rad/s',
        },
    ]);

    // Orientation series
    const orientSeries = $derived([
        {
            name: 'Roulis (Roll)',
            data: imuStore.history.map((r) => ({ timestamp: r.timestamp, value: (r.orientation.roll * 180) / Math.PI })),
            color: '#f87171',
            unit: '°',
        },
        {
            name: 'Tangage (Pitch)',
            data: imuStore.history.map((r) => ({ timestamp: r.timestamp, value: (r.orientation.pitch * 180) / Math.PI })),
            color: '#4ade80',
            unit: '°',
        },
        {
            name: 'Lacet (Yaw)',
            data: imuStore.history.map((r) => ({ timestamp: r.timestamp, value: (r.orientation.yaw * 180) / Math.PI })),
            color: '#818cf8',
            unit: '°',
        },
    ]);
</script>

<div class="space-y-8">
    <!-- Page header -->
    <div>
        <h1 class="text-xl font-bold text-slate-100">Centrale Inertielle (IMU)</h1>
        <p class="mt-1 text-sm text-slate-500">Accélération, gyroscope et orientation en temps réel</p>
    </div>

    <!-- Acceleration section -->
    <section class="space-y-4">
        <h2 class="flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-slate-400">
            <span class="h-3 w-3 rounded-full bg-danger-500"></span>
            Accélération
        </h2>

        {#if imuStore.current}
            <Vector3Card
                label="Accélération (m/s²)"
                x={imuStore.current.acceleration.x}
                y={imuStore.current.acceleration.y}
                z={imuStore.current.acceleration.z}
                unit="m/s²"
                formatter={formatAcceleration}
            />
        {/if}

        <div class="rounded-xl border border-surface-700 bg-surface-800 p-4">
            <LineChart series={accelSeries} yAxisLabel="m/s²" loading={!hasData} />
        </div>
    </section>

    <!-- Gyroscope section -->
    <section class="space-y-4">
        <h2 class="flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-slate-400">
            <span class="h-3 w-3 rounded-full bg-success-500"></span>
            Gyroscope
        </h2>

        {#if imuStore.current}
            <Vector3Card
                label="Gyroscope (rad/s)"
                x={imuStore.current.gyroscope.x}
                y={imuStore.current.gyroscope.y}
                z={imuStore.current.gyroscope.z}
                unit="rad/s"
                formatter={formatAngularRate}
            />
        {/if}

        <div class="rounded-xl border border-surface-700 bg-surface-800 p-4">
            <LineChart series={gyroSeries} yAxisLabel="rad/s" loading={!hasData} />
        </div>
    </section>

    <!-- Orientation section -->
    <section class="space-y-4">
        <h2 class="flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-slate-400">
            <span class="h-3 w-3 rounded-full bg-accent-500"></span>
            Orientation (Euler)
        </h2>

        {#if imuStore.current}
            <Vector3Card
                label="Orientation (degrés)"
                x={imuStore.current.orientation.roll}
                y={imuStore.current.orientation.pitch}
                z={imuStore.current.orientation.yaw}
                unit="°"
                formatter={formatAngleDeg}
            />
        {/if}

        <div class="rounded-xl border border-surface-700 bg-surface-800 p-4">
            <LineChart series={orientSeries} yAxisLabel="°" loading={!hasData} />
        </div>

        <!-- Quaternion display -->
        {#if imuStore.current}
            <div class="rounded-xl border border-surface-700 bg-surface-800 p-4">
                <p class="mb-3 text-xs font-medium uppercase tracking-wider text-slate-500">Quaternion (w, x, y, z)</p>
                <div class="grid grid-cols-4 gap-2">
                    {#each [
                        { label: 'W', value: imuStore.current.orientationQuaternion.w },
                        { label: 'X', value: imuStore.current.orientationQuaternion.x },
                        { label: 'Y', value: imuStore.current.orientationQuaternion.y },
                        { label: 'Z', value: imuStore.current.orientationQuaternion.z },
                    ] as q}
                        <div class="rounded-lg bg-surface-700/50 px-3 py-2 text-center">
                            <p class="text-xs font-bold text-slate-400">{q.label}</p>
                            <p class="mt-1 text-sm font-semibold tabular-nums text-slate-200">{q.value.toFixed(4)}</p>
                        </div>
                    {/each}
                </div>
            </div>
        {/if}
    </section>
</div>
