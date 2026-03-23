<script lang="ts">
    /**
     * Displays X, Y, Z axis values side by side.
     * Used for acceleration, gyroscope, and orientation data.
     */

    interface Props {
        label: string;
        x: number;
        y: number;
        z: number;
        unit: string;
        formatter?: (n: number) => string;
    }

    const defaultFormatter = (n: number) => n.toFixed(3);

    let { label, x, y, z, unit, formatter = defaultFormatter }: Props = $props();

    const axes = $derived([
        { axis: 'X', value: x, color: 'text-danger-400', bg: 'bg-danger-500/10' },
        { axis: 'Y', value: y, color: 'text-success-400', bg: 'bg-success-500/10' },
        { axis: 'Z', value: z, color: 'text-accent-400', bg: 'bg-accent-500/10' },
    ]);
</script>

<div class="rounded-xl border border-surface-700 bg-surface-800 p-4">
    <p class="mb-3 text-xs font-medium uppercase tracking-wider text-slate-500">{label}</p>
    <div class="grid grid-cols-3 gap-2">
        {#each axes as { axis, value, color, bg }}
            <div class="rounded-lg {bg} px-3 py-2.5 text-center">
                <p class="text-xs font-bold {color}">{axis}</p>
                <p class="mt-1 text-sm font-semibold tabular-nums text-slate-100">{formatter(value)}</p>
                <p class="mt-0.5 text-xs text-slate-500">{unit}</p>
            </div>
        {/each}
    </div>
</div>
