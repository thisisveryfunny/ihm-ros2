/**
 * Immutable fixed-size ring buffer utility.
 * Always returns a new array — never mutates the input.
 */

export function addToRingBuffer<T>(buffer: readonly T[], item: T, maxLength: number): T[] {
    if (buffer.length < maxLength) {
        return [...buffer, item];
    }
    return [...buffer.slice(1), item];
}

export function createRingBuffer<T>(maxLength: number): T[] {
    return [];
}
