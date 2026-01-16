/**
 * WebSocket Subscription Manager
 * Manages data stream subscriptions for real-time updates
 */

import { wsClient } from './client';

/**
 * Subscription Types
 * Defines all available data stream subscriptions
 */
export enum SubscriptionType {
  TRADES = 'trades',
  EVOLUTION = 'evolution',
  MARKETS = 'markets',
  SYSTEM_STATUS = 'system_status',
  PERFORMANCE = 'performance',
  MT5 = 'mt5',
}

/**
 * Subscribe Message sent to server
 */
interface SubscribeMessage {
  type: 'subscribe';
  subscription: SubscriptionType;
  timestamp: number;
}

/**
 * Unsubscribe Message sent to server
 */
interface UnsubscribeMessage {
  type: 'unsubscribe';
  subscription: SubscriptionType;
  timestamp: number;
}

/**
 * Subscription Manager
 * Manages active WebSocket data stream subscriptions
 */
class SubscriptionManager {
  private activeSubscriptions: Set<SubscriptionType> = new Set();
  private isInitialized: boolean = false;

  /**
   * Initialize the subscription manager
   * Must be called before using the manager
   */
  initialize(): void {
    if (this.isInitialized) {
      return;
    }

    // Clear all subscriptions when disconnected
    wsClient.onStateChange((state) => {
      if (state === 'disconnected' || state === 'error') {
        // Clear active subscriptions on disconnect
        this.activeSubscriptions.clear();
      }
    });

    this.isInitialized = true;

    if (process.env.NODE_ENV === 'development') {
      console.log('[SubscriptionManager] Initialized');
    }
  }

  /**
   * Subscribe to a data stream
   * @param type - The subscription type to subscribe to
   */
  subscribe(type: SubscriptionType): void {
    this.initialize();

    // Check if already subscribed to avoid duplicates
    if (this.activeSubscriptions.has(type)) {
      if (process.env.NODE_ENV === 'development') {
        console.log(`[SubscriptionManager] Already subscribed to: ${type}`);
      }
      return;
    }

    try {
      // Send subscribe message to server
      const message: SubscribeMessage = {
        type: 'subscribe',
        subscription: type,
        timestamp: Date.now(),
      };

      wsClient.emit('subscribe', message);

      // Track the subscription
      this.activeSubscriptions.add(type);

      if (process.env.NODE_ENV === 'development') {
        console.log(`[SubscriptionManager] Subscribed to: ${type}`);
      }
    } catch (error) {
      if (process.env.NODE_ENV === 'development') {
        console.error(`[SubscriptionManager] Failed to subscribe to ${type}:`, error);
      }
      throw error;
    }
  }

  /**
   * Unsubscribe from a data stream
   * @param type - The subscription type to unsubscribe from
   */
  unsubscribe(type: SubscriptionType): void {
    this.initialize();

    // Check if actually subscribed
    if (!this.activeSubscriptions.has(type)) {
      if (process.env.NODE_ENV === 'development') {
        console.log(`[SubscriptionManager] Not subscribed to: ${type}`);
      }
      return;
    }

    try {
      // Send unsubscribe message to server
      const message: UnsubscribeMessage = {
        type: 'unsubscribe',
        subscription: type,
        timestamp: Date.now(),
      };

      wsClient.emit('unsubscribe', message);

      // Remove from active subscriptions
      this.activeSubscriptions.delete(type);

      if (process.env.NODE_ENV === 'development') {
        console.log(`[SubscriptionManager] Unsubscribed from: ${type}`);
      }
    } catch (error) {
      if (process.env.NODE_ENV === 'development') {
        console.error(`[SubscriptionManager] Failed to unsubscribe from ${type}:`, error);
      }
      throw error;
    }
  }

  /**
   * Unsubscribe from all active data streams
   */
  unsubscribeAll(): void {
    this.initialize();

    if (this.activeSubscriptions.size === 0) {
      if (process.env.NODE_ENV === 'development') {
        console.log('[SubscriptionManager] No active subscriptions to clear');
      }
      return;
    }

    const subscriptions = Array.from(this.activeSubscriptions);

    try {
      // Send unsubscribe message for each subscription
      subscriptions.forEach((type) => {
        const message: UnsubscribeMessage = {
          type: 'unsubscribe',
          subscription: type,
          timestamp: Date.now(),
        };

        try {
          wsClient.emit('unsubscribe', message);
        } catch (error) {
          if (process.env.NODE_ENV === 'development') {
            console.error(`[SubscriptionManager] Failed to unsubscribe from ${type}:`, error);
          }
        }
      });

      // Clear all subscriptions
      this.activeSubscriptions.clear();

      if (process.env.NODE_ENV === 'development') {
        console.log(`[SubscriptionManager] Unsubscribed from all (${subscriptions.length} subscriptions)`);
      }
    } catch (error) {
      if (process.env.NODE_ENV === 'development') {
        console.error('[SubscriptionManager] Failed to unsubscribe from all:', error);
      }
      throw error;
    }
  }

  /**
   * Check if currently subscribed to a specific data stream
   * @param type - The subscription type to check
   * @returns True if subscribed, false otherwise
   */
  isSubscribed(type: SubscriptionType): boolean {
    return this.activeSubscriptions.has(type);
  }

  /**
   * Get all active subscriptions
   * @returns Array of active subscription types
   */
  getActiveSubscriptions(): SubscriptionType[] {
    return Array.from(this.activeSubscriptions);
  }

  /**
   * Get the count of active subscriptions
   * @returns Number of active subscriptions
   */
  getSubscriptionCount(): number {
    return this.activeSubscriptions.size;
  }
}

/**
 * Export singleton instance
 */
export const subscriptionManager = new SubscriptionManager();
