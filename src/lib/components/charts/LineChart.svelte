<script lang="ts">
    /**
     * Typed line chart for time-series robot data.
     * Builds ECharts options from typed props via pure buildLineChartOption().
     */
    import EChart from './EChart.svelte';
    import { buildLineChartOption, type LineSeriesConfig } from '$lib/utils/chart-options.js';

    interface Props {
        series: LineSeriesConfig[];
        title?: string;
        yAxisLabel?: string;
        height?: string;
        loading?: boolean;
    }

    let { series, title, yAxisLabel, height = '280px', loading = false }: Props = $props();

    const chartOption = $derived(buildLineChartOption(series, title, yAxisLabel));
</script>

<EChart option={chartOption} {height} {loading} />
