<script lang="ts">
    /**
     * Base ECharts wrapper component.
     * Handles all lifecycle: init, reactive updates via $effect, resize, and dispose.
     * Use LineChart.svelte or GaugeChart.svelte instead of using this directly.
     */
    import { onMount, onDestroy } from 'svelte';
    import * as echarts from 'echarts';
    import type { EChartsOption } from 'echarts';

    interface Props {
        option: EChartsOption;
        height?: string;
        loading?: boolean;
    }

    let { option, height = '300px', loading = false }: Props = $props();

    let container: HTMLDivElement;
    let chart: echarts.ECharts | undefined;

    onMount(() => {
        chart = echarts.init(container, 'dark', { renderer: 'canvas' });

        const ro = new ResizeObserver(() => {
            chart?.resize();
        });
        ro.observe(container);

        onDestroy(() => {
            ro.disconnect();
            chart?.dispose();
        });
    });

    // Reactively update chart when option changes
    $effect(() => {
        if (chart) {
            chart.setOption(option, { notMerge: false, lazyUpdate: false });
        }
    });

    // Show/hide loading overlay
    $effect(() => {
        if (!chart) return;
        if (loading) {
            chart.showLoading('default', {
                text: 'Chargement…',
                color: '#818cf8',
                textColor: '#94a3b8',
                maskColor: 'rgba(10, 10, 15, 0.8)',
            });
        } else {
            chart.hideLoading();
        }
    });
</script>

<div bind:this={container} style="height: {height}; width: 100%;"></div>
