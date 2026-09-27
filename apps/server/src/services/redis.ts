/**
 * Optional Redis cache helpers. Empty/unreachable REDIS_URL → no-op.
 */

import { env } from "../config/env";

type RedisLike = {
  get(key: string): Promise<string | null>;
  set(key: string, value: string, mode: string, ttl: number): Promise<unknown>;
  ping(): Promise<string>;
  quit(): Promise<void>;
  on(event: string, cb: (...args: unknown[]) => void): void;
  connect(): Promise<void>;
};

let client: RedisLike | null = null;
let disabled = false;
let connecting: Promise<RedisLike | null> | null = null;
let hits = 0;
let misses = 0;

export function redisConfigured(): boolean {
  return Boolean(env.REDIS_URL?.trim());
}

async function connect(): Promise<RedisLike | null> {
  if (!redisConfigured() || disabled) return null;
  if (client) return client;
  if (connecting) return connecting;

  connecting = (async () => {
    try {
      const Redis = (await import("ioredis")).default;
      const c = new Redis(env.REDIS_URL!, {
        maxRetriesPerRequest: 1,
        enableOfflineQueue: false,
        connectTimeout: 1500,
        lazyConnect: true,
      }) as unknown as RedisLike;

      c.on("error", () => {});

      await c.connect();
      await c.ping();
      client = c;
      return client;
    } catch {
      disabled = true;
      client = null;
      return null;
    } finally {
      connecting = null;
    }
  })();

  return connecting;
}

export async function redisPing(): Promise<boolean> {
  const c = await connect();
  if (!c) return false;
  try {
    return (await c.ping()) === "PONG";
  } catch {
    return false;
  }
}

export async function cacheGet<T = unknown>(key: string): Promise<T | null> {
  const c = await connect();
  if (!c) return null;
  try {
    const raw = await c.get(key);
    if (raw == null) {
      misses += 1;
      return null;
    }
    hits += 1;
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}

export async function cacheSet(key: string, value: unknown, ttlSeconds = 300): Promise<boolean> {
  const c = await connect();
  if (!c) return false;
  try {
    await c.set(key, JSON.stringify(value), "EX", Math.max(1, ttlSeconds));
    return true;
  } catch {
    return false;
  }
}

export function cacheStats(): { hits: number; misses: number } {
  return { hits, misses };
}

export async function closeRedis(): Promise<void> {
  if (client) {
    try {
      await client.quit();
    } catch {
      /* ignore */
    }
  }
  client = null;
  disabled = false;
}

export function _resetRedisForTests(): void {
  client = null;
  disabled = false;
  connecting = null;
  hits = 0;
  misses = 0;
}
