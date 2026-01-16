/**
 * WebSocket Recovery Manager
 * Handles error recovery, reconnection, and state restoration
 */

import { wsClient, ConnectionState } from './client';
import { subscriptionManager, SubscriptionType } from './subscriptions';

/**
 * Recovery State
 */
export type RecoveryState = 'idle' | 'reconnecting' | 'failed';

/**
 * Recovery Configuration
 */
export interface RecoveryConfig {
  maxFailedAttempts?: number;
  failedAttemptResetDelay?: number;
}

/**
 * Recovery Event Callbacks
 */
export interface RecoveryCallbacks {
  onReconnecting?: (attempt: number, delay: number) => void;
  onReconnectSuccess?: () => void;
  onReconnectFailed?: (consecutiveFailures: number) => void;
  onSubscriptionsRestored?: (subscriptions: SubscriptionType[]) => void;
  /** Called after successful reconnection - trigger data refresh */
  onDataRefreshRequested?: () => void | Promise<void>;
}

/**
 * Reconnection State for UI display
 */
export interface ReconnectionState {
  isReconnecting: boolean;
  attempt: number;
  delay: number;
  consecutiveFailures: number;
}

/**
 * Recovery Manager
 * Manages WebSocket error recovery and reconnection with state restoration
 */
class RecoveryManager {
  private recoveryState: RecoveryState = 'idle';
  private consecutiveFailedAttempts: number = 0;
  private lastReconnectAttemptTime: number = 0;
  private pendingSubscriptions: Set<SubscriptionType> = new Set();
  private recoveryCallbacks: Set<RecoveryCallbacks> = new Set();
  private config: Required<RecoveryConfig>;
  private reconnectionState: ReconnectionState = {
    isReconnecting: false,
    attempt: 0,
    delay: 0,
    consecutiveFailures: 0,
  };
  private stateChangeListeners: Set<(state: ReconnectionState) => void> = new Set();
  private failedAttemptResetTimer: ReturnType<typeof setTimeout> | null = null;

  constructor(config?: RecoveryConfig) {
    this.config = {
      maxFailedAttempts: config?.maxFailedAttempts ?? 3,
      failedAttemptResetDelay: config?.failedAttemptResetDelay ?? 60000, // 1 minute
    };

    this.initialize();
  }

  /**
   * Initialize the recovery manager
   */
  private initialize(): void {
    // Listen for connection state changes
    wsClient.onStateChange((state) => {
      this.handleConnectionStateChange(state);
    });
  }

  /**
   * Handle connection state changes
   */
  private handleConnectionStateChange(state: ConnectionState): void {
    const timestamp = new Date().toISOString();

    if (state === 'connected') {
      this.handleReconnectSuccess();
    } else if (state === 'error' || state === 'disconnected') {
      this.handleConnectionLost();
    }
  }

  /**
   * Handle connection loss
   */
  private handleConnectionLost(): void {
    // Save current subscriptions for restoration
    this.pendingSubscriptions = new Set(subscriptionManager.getActiveSubscriptions());

    if (process.env.NODE_ENV === 'development') {
      console.log(
        `[RecoveryManager] Connection lost. Saving ${this.pendingSubscriptions.size} subscriptions for restoration:`,
        Array.from(this.pendingSubscriptions)
      );
    }
  }

  /**
   * Handle successful reconnection
   */
  private handleReconnectSuccess(): void {
    // Reset consecutive failures
    this.consecutiveFailedAttempts = 0;
    this.clearFailedAttemptResetTimer();

    // Update recovery state
    this.setRecoveryState('idle');
    this.updateReconnectionState({
      isReconnecting: false,
      attempt: 0,
      delay: 0,
      consecutiveFailures: 0,
    });

    // Restore subscriptions
    this.restoreSubscriptions();

    // Notify callbacks about successful reconnection
    this.notifyReconnectSuccess();

    // Request data refresh from all registered callbacks
    this.notifyDataRefreshRequested();

    if (process.env.NODE_ENV === 'development') {
      console.log('[RecoveryManager] Reconnection successful');
    }
  }

  /**
   * Restore subscriptions after reconnect
   */
  private restoreSubscriptions(): void {
    if (this.pendingSubscriptions.size === 0) {
      if (process.env.NODE_ENV === 'development') {
        console.log('[RecoveryManager] No subscriptions to restore');
      }
      return;
    }

    const subscriptions = Array.from(this.pendingSubscriptions);

    try {
      // Wait a brief moment for the connection to stabilize
      setTimeout(() => {
        subscriptions.forEach((type) => {
          try {
            subscriptionManager.subscribe(type);
          } catch (error) {
            console.error(`[RecoveryManager] Failed to restore subscription to ${type}:`, error);
          }
        });

        // Clear pending subscriptions after restoration attempt
        this.pendingSubscriptions.clear();

        if (process.env.NODE_ENV === 'development') {
          console.log(`[RecoveryManager] Restored ${subscriptions.length} subscriptions:`, subscriptions);
        }

        // Notify callbacks
        this.notifySubscriptionsRestored(subscriptions);
      }, 100);
    } catch (error) {
      console.error('[RecoveryManager] Error restoring subscriptions:', error);
    }
  }

  /**
   * Handle reconnection failure
   * Called when the WebSocket client exhausts reconnect attempts
   * Public method to be called by WSClient
   */
  handleReconnectionFailure(): void {
    const now = Date.now();

    // Increment consecutive failures counter
    this.consecutiveFailedAttempts++;
    this.lastReconnectAttemptTime = now;

    // Update reconnection state
    this.updateReconnectionState({
      isReconnecting: false,
      consecutiveFailures: this.consecutiveFailedAttempts,
    });

    if (process.env.NODE_ENV === 'development') {
      console.error(
        `[RecoveryManager] Reconnection failed. Consecutive failures: ${this.consecutiveFailedAttempts}`
      );
    }

    // Check if we've exceeded max failed attempts
    if (this.consecutiveFailedAttempts >= this.config.maxFailedAttempts) {
      this.setRecoveryState('failed');

      // Notify callbacks about consecutive failures
      this.notifyReconnectFailed(this.consecutiveFailedAttempts);

      if (process.env.NODE_ENV === 'development') {
        console.error(
          `[RecoveryManager] Max consecutive failed attempts (${this.config.maxFailedAttempts}) reached`
        );
      }
    } else {
      // Set up reset timer for consecutive failures
      this.scheduleFailedAttemptReset();
    }
  }

  /**
   * Schedule reset of consecutive failure counter
   * Resets after configured delay if no further failures occur
   */
  private scheduleFailedAttemptReset(): void {
    this.clearFailedAttemptResetTimer();

    this.failedAttemptResetTimer = setTimeout(() => {
      if (process.env.NODE_ENV === 'development') {
        console.log('[RecoveryManager] Resetting consecutive failure counter');
      }
      this.consecutiveFailedAttempts = 0;
      this.updateReconnectionState({
        consecutiveFailures: 0,
      });
    }, this.config.failedAttemptResetDelay);
  }

  /**
   * Clear the failed attempt reset timer
   */
  private clearFailedAttemptResetTimer(): void {
    if (this.failedAttemptResetTimer !== null) {
      clearTimeout(this.failedAttemptResetTimer);
      this.failedAttemptResetTimer = null;
    }
  }

  /**
   * Start reconnection process
   * Called when a reconnection attempt is scheduled
   * Public method to be called by WSClient
   */
  startReconnection(attempt: number, delay: number): void {
    this.setRecoveryState('reconnecting');

    // Update reconnection state
    this.updateReconnectionState({
      isReconnecting: true,
      attempt,
      delay,
      consecutiveFailures: this.consecutiveFailedAttempts,
    });

    // Notify callbacks
    this.notifyReconnecting(attempt, delay);

    if (process.env.NODE_ENV === 'development') {
      console.log(
        `[RecoveryManager] Reconnecting... Attempt ${attempt}, delay: ${delay}ms`
      );
    }
  }

  /**
   * Update recovery state
   */
  private setRecoveryState(state: RecoveryState): void {
    if (this.recoveryState !== state) {
      this.recoveryState = state;

      if (process.env.NODE_ENV === 'development') {
        console.log(`[RecoveryManager] Recovery state: ${this.recoveryState}`);
      }
    }
  }

  /**
   * Update reconnection state and notify listeners
   */
  private updateReconnectionState(updates: Partial<ReconnectionState>): void {
    this.reconnectionState = {
      ...this.reconnectionState,
      ...updates,
    };

    // Notify all listeners
    this.stateChangeListeners.forEach((listener) => {
      try {
        listener(this.reconnectionState);
      } catch (error) {
        console.error('[RecoveryManager] Error in state change listener:', error);
      }
    });
  }

  /**
   * Notify callbacks about reconnection start
   */
  private notifyReconnecting(attempt: number, delay: number): void {
    this.recoveryCallbacks.forEach((callbacks) => {
      if (callbacks.onReconnecting) {
        try {
          callbacks.onReconnecting(attempt, delay);
        } catch (error) {
          console.error('[RecoveryManager] Error in onReconnecting callback:', error);
        }
      }
    });
  }

  /**
   * Notify callbacks about successful reconnection
   */
  private notifyReconnectSuccess(): void {
    this.recoveryCallbacks.forEach((callbacks) => {
      if (callbacks.onReconnectSuccess) {
        try {
          callbacks.onReconnectSuccess();
        } catch (error) {
          console.error('[RecoveryManager] Error in onReconnectSuccess callback:', error);
        }
      }
    });
  }

  /**
   * Notify callbacks about failed reconnection
   */
  private notifyReconnectFailed(consecutiveFailures: number): void {
    this.recoveryCallbacks.forEach((callbacks) => {
      if (callbacks.onReconnectFailed) {
        try {
          callbacks.onReconnectFailed(consecutiveFailures);
        } catch (error) {
          console.error('[RecoveryManager] Error in onReconnectFailed callback:', error);
        }
      }
    });
  }

  /**
   * Notify callbacks about restored subscriptions
   */
  private notifySubscriptionsRestored(subscriptions: SubscriptionType[]): void {
    this.recoveryCallbacks.forEach((callbacks) => {
      if (callbacks.onSubscriptionsRestored) {
        try {
          callbacks.onSubscriptionsRestored(subscriptions);
        } catch (error) {
          console.error('[RecoveryManager] Error in onSubscriptionsRestored callback:', error);
        }
      }
    });
  }

  /**
   * Notify callbacks to request data refresh
   */
  private async notifyDataRefreshRequested(): Promise<void> {
    const promises: Array<Promise<void>> = [];

    this.recoveryCallbacks.forEach((callbacks) => {
      if (callbacks.onDataRefreshRequested) {
        try {
          const result = callbacks.onDataRefreshRequested();
          // Handle both sync and async callbacks
          if (result instanceof Promise) {
            promises.push(result);
          }
        } catch (error) {
          console.error('[RecoveryManager] Error in onDataRefreshRequested callback:', error);
        }
      }
    });

    // Wait for all async refresh operations to complete
    if (promises.length > 0) {
      try {
        await Promise.allSettled(promises);
        if (process.env.NODE_ENV === 'development') {
          console.log(`[RecoveryManager] Data refresh completed for ${promises.length} callback(s)`);
        }
      } catch (error) {
        console.error('[RecoveryManager] Error during data refresh:', error);
      }
    }
  }

  /**
   * Register recovery callbacks
   */
  registerCallbacks(callbacks: RecoveryCallbacks): () => void {
    this.recoveryCallbacks.add(callbacks);
    return () => this.recoveryCallbacks.delete(callbacks);
  }

  /**
   * Subscribe to reconnection state changes
   */
  onReconnectionStateChange(callback: (state: ReconnectionState) => void): () => void {
    this.stateChangeListeners.add(callback);

    // Immediately call with current state
    callback(this.reconnectionState);

    return () => this.stateChangeListeners.delete(callback);
  }

  /**
   * Get current reconnection state
   */
  getReconnectionState(): ReconnectionState {
    return { ...this.reconnectionState };
  }

  /**
   * Get current recovery state
   */
  getRecoveryState(): RecoveryState {
    return this.recoveryState;
  }

  /**
   * Get consecutive failed attempts count
   */
  getConsecutiveFailedAttempts(): number {
    return this.consecutiveFailedAttempts;
  }

  /**
   * Check if reconnection has failed
   */
  hasReconnectionFailed(): boolean {
    return this.recoveryState === 'failed';
  }

  /**
   * Reset recovery state (e.g., after manual reconnect)
   */
  reset(): void {
    this.consecutiveFailedAttempts = 0;
    this.recoveryState = 'idle';
    this.reconnectionState = {
      isReconnecting: false,
      attempt: 0,
      delay: 0,
      consecutiveFailures: 0,
    };
    this.clearFailedAttemptResetTimer();

    if (process.env.NODE_ENV === 'development') {
      console.log('[RecoveryManager] Recovery state reset');
    }
  }

  /**
   * Cleanup resources
   */
  destroy(): void {
    this.clearFailedAttemptResetTimer();
    this.recoveryCallbacks.clear();
    this.stateChangeListeners.clear();
    this.pendingSubscriptions.clear();
  }
}

/**
 * Create singleton instance
 */
const recoveryManager = new RecoveryManager({
  maxFailedAttempts: 3,
  failedAttemptResetDelay: 60000,
});

export { recoveryManager, RecoveryManager };
export type { ReconnectionState, RecoveryCallbacks, RecoveryConfig };
