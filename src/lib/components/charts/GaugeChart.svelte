<script lang="ts">
    /**
     * Battery/percentage gauge chart.
     * Color automatically transitions: red (0-30%) → amber (30-60%) → green (60-100%).
     */
    import EChart from './EChart.svelte';
    import { buildGaugeChartOption } from '$lib/utils/chart-options.js';

    interface Props {
        value: number; // 0–100
        label?: string;
        height?: string;
    }

    let { value, label = 'Batterie', height = '280px' }: Props = $props();

    const chartOption = $derived(buildGaugeChartOption(value, label));
</script>

<EChart option={chartOption} {height} />
