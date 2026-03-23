<script lang="ts">
    type Status = 'connected' | 'disconnected' | 'charging' | 'discharging' | 'full' | 'unknown';

    interface Props {
        status: Status;
        label?: string;
    }

    let { status, label }: Props = $props();

    const config: Record<Status, { dot: string; text: string; displayLabel: string }> = {
        connected: { dot: 'bg-success-500 animate-pulse', text: 'text-success-400', displayLabel: 'Connecté' },
        disconnected: { dot: 'bg-danger-500', text: 'text-danger-400', displayLabel: 'Déconnecté' },
        charging: { dot: 'bg-warning-400 animate-pulse', text: 'text-warning-400', displayLabel: 'En charge' },
        discharging: { dot: 'bg-slate-400', text: 'text-slate-400', displayLabel: 'En décharge' },
        full: { dot: 'bg-success-500', text: 'text-success-400', displayLabel: 'Chargé' },
        unknown: { dot: 'bg-slate-600', text: 'text-slate-500', displayLabel: 'Inconnu' },
    };

    const { dot, text, displayLabel } = $derived(config[status] ?? config.unknown);
    const shownLabel = $derived(label ?? displayLabel);
</script>

<div class="inline-flex items-center gap-1.5 rounded-full border border-surface-700 bg-surface-800 px-2.5 py-1">
    <span class="h-2 w-2 rounded-full {dot}"></span>
    <span class="text-xs font-medium {text}">{shownLabel}</span>
</div>
