<script lang="ts">
    type Variant = 'default' | 'success' | 'warning' | 'danger' | 'accent';

    interface Props {
        label: string;
        value: string;
        sublabel?: string;
        variant?: Variant;
        icon?: import('svelte').Snippet;
    }

    let { label, value, sublabel, variant = 'default', icon }: Props = $props();

    const variantClasses: Record<Variant, string> = {
        default: 'text-slate-100',
        success: 'text-success-400',
        warning: 'text-warning-400',
        danger: 'text-danger-400',
        accent: 'text-accent-400',
    };

    const iconBgClasses: Record<Variant, string> = {
        default: 'bg-slate-700/50',
        success: 'bg-success-500/15',
        warning: 'bg-warning-500/15',
        danger: 'bg-danger-500/15',
        accent: 'bg-accent-500/15',
    };
</script>

<div class="rounded-xl border border-surface-700 bg-surface-800 p-4 transition-colors hover:border-surface-600">
    <div class="flex items-start justify-between gap-3">
        <div class="min-w-0 flex-1">
            <p class="truncate text-xs font-medium uppercase tracking-wider text-slate-500">{label}</p>
            <p class="mt-1.5 text-2xl font-bold tabular-nums {variantClasses[variant]}">{value}</p>
            {#if sublabel}
                <p class="mt-1 truncate text-xs text-slate-500">{sublabel}</p>
            {/if}
        </div>
        {#if icon}
            <div class="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg {iconBgClasses[variant]}">
                {@render icon()}
            </div>
        {/if}
    </div>
</div>
