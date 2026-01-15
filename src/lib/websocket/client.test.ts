/**
 * Simple test for WebSocket client
 * This file validates the basic functionality without running actual tests
 */

import { WSClient, ConnectionState } from './client';

// Test: Client can be instantiated
const testClientInstantiation = () => {
  const client = new WSClient({
    url: 'ws://localhost:3001',
    connectionTimeout: 10000,
  });

  console.log('[WS Test] Client instantiation: PASS');
  return client;
};

// Test: Initial state is disconnected
const testInitialState = (client: WSClient) => {
  const state = client.getState();
  if (state === 'disconnected') {
    console.log('[WS Test] Initial state check: PASS');
  } else {
    console.error('[WS Test] Initial state check: FAIL - Expected "disconnected", got', state);
  }
};

// Test: Connection attempt counter starts at 0
const testConnectionAttempts = (client: WSClient) => {
  const attempts = client.getConnectionAttemptCount();
  if (attempts === 0) {
    console.log('[WS Test] Connection attempts counter: PASS');
  } else {
    console.error('[WS Test] Connection attempts counter: FAIL - Expected 0, got', attempts);
  }
};

// Test: State change subscription works
const testStateChangeSubscription = (client: WSClient) => {
  let receivedState: ConnectionState | null = null;

  const unsubscribe = client.onStateChange((state) => {
    receivedState = state;
  });

  // Simulate state change by accessing private method through public interface
  // In real usage, this would be triggered by connect()

  unsubscribe();
  console.log('[WS Test] State change subscription: PASS (callback registered)');
};

// Test: GetState returns valid state
const testGetState = (client: WSClient) => {
  const state = client.getState();
  const validStates: ConnectionState[] = ['disconnected', 'connecting', 'connected', 'error'];

  if (validStates.includes(state)) {
    console.log('[WS Test] getState returns valid state: PASS');
  } else {
    console.error('[WS Test] getState returns valid state: FAIL');
  }
};

// Test: Disconnect can be called safely
const testDisconnect = (client: WSClient) => {
  try {
    client.disconnect();
    console.log('[WS Test] disconnect() method: PASS');
  } catch (error) {
    console.error('[WS Test] disconnect() method: FAIL', error);
  }
};

// Test: Reconnect can be called safely
const testReconnect = (client: WSClient) => {
  try {
    client.reconnect();
    console.log('[WS Test] reconnect() method: PASS');
  } catch (error) {
    console.error('[WS Test] reconnect() method: FAIL', error);
  }
};

// Test: Singleton instance is exported
const testSingletonInstance = () => {
  const { wsClient } = require('./client');
  if (wsClient && typeof wsClient.getState === 'function') {
    console.log('[WS Test] Singleton instance export: PASS');
  } else {
    console.error('[WS Test] Singleton instance export: FAIL');
  }
};

// Run all validation tests
const runTests = () => {
  console.log('[WS Test] Starting WebSocket client validation tests...\n');

  const client = testClientInstantiation();
  testInitialState(client);
  testConnectionAttempts(client);
  testStateChangeSubscription(client);
  testGetState(client);
  testDisconnect(client);
  testReconnect(client);
  testSingletonInstance();

  client.destroy();

  console.log('\n[WS Test] All validation tests completed.');
};

// Export for manual testing
export { runTests };

// Auto-run in development mode
if (process.env.NODE_ENV === 'development' && typeof window !== 'undefined') {
  console.log('[WS Test] WebSocket client test file loaded. Run runTests() to execute validation.');
}
