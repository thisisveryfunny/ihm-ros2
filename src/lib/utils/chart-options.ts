/**
 * Pure functions that build ECharts option objects.
 * Keeping these outside .svelte files makes them unit-testable and keeps components thin.
 */

import type { TimePoint } from '$lib/types/ros.js';
import type { EChartsOption } from 'echarts';

export interface LineSeriesConfig {
	name: string;
	data: TimePoint[];
	color?: string;
	unit?: string;
}

const CHART_COLORS = [
	'#818cf8', // indigo-400
	'#34d399', // emerald-400
	'#fb923c', // orange-400
	'#f472b6', // pink-400
	'#38bdf8', // sky-400
	'#a78bfa' // violet-400
];

function toEChartsData(points: TimePoint[]): [number, number][] {
	return points.map((p) => [p.timestamp, p.value]);
}

export function buildLineChartOption(
	series: LineSeriesConfig[],
	title?: string,
	yAxisLabel?: string
): EChartsOption {
	return {
		backgroundColor: 'transparent',
		animation: true,
		animationDuration: 300,
		grid: { left: 60, right: 20, top: title ? 50 : 20, bottom: 50 },
		title: title
			? {
					text: title,
					textStyle: { color: '#94a3b8', fontSize: 13, fontWeight: 'normal' },
					left: 0,
					top: 8
				}
			: undefined,
		tooltip: {
			trigger: 'axis',
			backgroundColor: '#1a1a25',
			borderColor: '#374151',
			textStyle: { color: '#e2e8f0' },
			formatter: (params: unknown) => {
				const items = params as Array<{ seriesName: string; value: [number, number] }>;
				if (!items?.length) return '';
				const time = new Date(items[0].value[0]).toLocaleTimeString();
				const lines = items.map((item) => {
					const seriesCfg = series.find((s) => s.name === item.seriesName);
					const unit = seriesCfg?.unit ?? '';
					return `<div>${item.seriesName}: <b>${item.value[1].toFixed(3)}</b> ${unit}</div>`;
				});
				return `<div style="font-size:12px"><div style="color:#64748b">${time}</div>${lines.join('')}</div>`;
			}
		},
		legend:
			series.length > 1
				? {
						data: series.map((s) => s.name),
						textStyle: { color: '#94a3b8', fontSize: 11 },
						top: title ? 28 : 4
					}
				: undefined,
		xAxis: {
			type: 'time',
			axisLine: { lineStyle: { color: '#334155' } },
			axisLabel: {
				color: '#64748b',
				fontSize: 10,
				formatter: (value: number) => new Date(value).toLocaleTimeString()
			},
			splitLine: { show: false }
		},
		yAxis: {
			type: 'value',
			name: yAxisLabel,
			nameTextStyle: { color: '#64748b', fontSize: 11 },
			axisLine: { show: false },
			axisTick: { show: false },
			axisLabel: { color: '#64748b', fontSize: 10 },
			splitLine: { lineStyle: { color: '#1e293b', type: 'dashed' } }
		},
		series: series.map((s, i) => ({
			name: s.name,
			type: 'line',
			data: toEChartsData(s.data),
			smooth: true,
			symbol: 'none',
			lineStyle: { width: 2, color: s.color ?? CHART_COLORS[i % CHART_COLORS.length] },
			itemStyle: { color: s.color ?? CHART_COLORS[i % CHART_COLORS.length] },
			areaStyle: {
				color: {
					type: 'linear',
					x: 0,
					y: 0,
					x2: 0,
					y2: 1,
					colorStops: [
						{ offset: 0, color: (s.color ?? CHART_COLORS[i % CHART_COLORS.length]) + '33' },
						{ offset: 1, color: 'transparent' }
					]
				}
			}
		}))
	};
}

export function buildGaugeChartOption(value: number, label: string): EChartsOption {
	const clampedValue = Math.max(0, Math.min(100, value));

	let color: string;
	if (clampedValue >= 60) color = '#22c55e';
	else if (clampedValue >= 30) color = '#f59e0b';
	else color = '#ef4444';

	return {
		backgroundColor: 'transparent',
		series: [
			{
				type: 'gauge',
				startAngle: 200,
				endAngle: -20,
				min: 0,
				max: 100,
				splitNumber: 5,
				radius: '88%',
				center: ['50%', '58%'],
				axisLine: {
					lineStyle: {
						width: 18,
						color: [
							[0.3, '#ef4444'],
							[0.6, '#f59e0b'],
							[1, '#22c55e']
						]
					}
				},
				pointer: {
					icon: 'path://M12.8,0.7l12.3,33.8h-24.6z',
					length: '52%',
					width: 10,
					offsetCenter: [0, '-60%'],
					itemStyle: { color: 'auto' }
				},
				axisTick: { distance: -22, length: 6, lineStyle: { color: '#fff', width: 1 } },
				splitLine: {
					distance: -28,
					length: 14,
					lineStyle: { color: '#fff', width: 2 }
				},
				axisLabel: {
					color: '#94a3b8',
					fontSize: 11,
					distance: -50,
					formatter: (val: number) => `${val}%`
				},
				anchor: {
					show: true,
					showAbove: false,
					size: 20,
					itemStyle: { borderWidth: 8, borderColor: color, color: '#1a1a25' }
				},
				title: {
					show: true,
					offsetCenter: [0, '42%'],
					fontSize: 13,
					color: '#94a3b8'
				},
				detail: {
					valueAnimation: true,
					fontSize: 36,
					fontWeight: 'bold',
					offsetCenter: [0, '25%'],
					formatter: (val: number) => `${Math.round(val)}%`,
					color
				},
				data: [{ value: clampedValue, name: label }]
			}
		]
	};
}
