import { useState, useEffect } from 'react';

/**
 * A hook that provides a debounced version of a value
 * @param value The value to debounce
 * @param delay The delay in milliseconds
 * @returns The debounced value
 */
export function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    // Update debounced value after delay
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    // Cancel the timeout if value changes or component unmounts
    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
}

/**
 * A hook that provides a debounced callback function
 * @param callback The function to debounce
 * @param delay The delay in milliseconds
 * @returns A tuple containing the debounced function and a function to cancel the debounce
 */
export function useDebouncedCallback<T extends (...args: any[]) => any>(
  callback: T,
  delay: number
): [(...args: Parameters<T>) => void, () => void] {
  const [timeoutId, setTimeoutId] = useState<NodeJS.Timeout | null>(null);

  const debouncedFn = (...args: Parameters<T>) => {
    if (timeoutId) {
      clearTimeout(timeoutId);
    }

    const id = setTimeout(() => {
      callback(...args);
      setTimeoutId(null);
    }, delay);

    setTimeoutId(id);
  };

  const cancelDebounce = () => {
    if (timeoutId) {
      clearTimeout(timeoutId);
      setTimeoutId(null);
    }
  };

  // Clean up on unmount
  useEffect(() => {
    return () => {
      if (timeoutId) {
        clearTimeout(timeoutId);
      }
    };
  }, [timeoutId]);

  return [debouncedFn, cancelDebounce];
}