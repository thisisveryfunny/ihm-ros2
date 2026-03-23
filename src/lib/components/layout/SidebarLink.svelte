<script lang="ts">
    import { page } from '$app/stores';

    interface Props {
        href: string;
        label: string;
        icon: import('svelte').Snippet;
        collapsed?: boolean;
    }

    let { href, label, icon, collapsed = false }: Props = $props();

    const isActive = $derived($page.url.pathname === href || $page.url.pathname.startsWith(href + '/'));
</script>

<a
    {href}
    class="group flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-150
        {isActive
        ? 'bg-accent-500/15 text-accent-400'
        : 'text-slate-400 hover:bg-surface-700 hover:text-slate-100'}"
    title={collapsed ? label : undefined}
>
    <span class="shrink-0 {isActive ? 'text-accent-400' : 'text-slate-500 group-hover:text-slate-300'}">
        {@render icon()}
    </span>
    {#if !collapsed}
        <span class="truncate">{label}</span>
    {/if}
    {#if isActive && !collapsed}
        <span class="ml-auto h-1.5 w-1.5 rounded-full bg-accent-400"></span>
    {/if}
</a>
