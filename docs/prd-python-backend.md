# EURABAY Living System - Python Backend

**Branch:** `backend/python-trading-system`

## Description

Complete Python backend implementation for autonomous trading system with MT5 integration, AI decision engine, memory system, and risk management for volatility indices trading (V10, V25, V50, V75, V100).

## User Stories

### US-001: Set up FastAPI server foundation
**Priority:** 1
**Maven Steps:** 1, 2

As a developer, I need to set up a FastAPI server with async support, CORS, WebSocket, and proper project structure so that the backend can serve the frontend and handle real-time trading operations.

**Acceptance Criteria:**
- Create backend/ directory with Python project structure
- Initialize FastAPI application with async support
- Configure CORS middleware for Next.js frontend
- Set up WebSocket endpoint for real-time data streaming
- Create requirements.txt with all dependencies
- Set up .env file for configuration
- Add health check endpoint
- Add structured logging with loguru
- Create Docker configuration (optional)
- Verify server starts and responds to requests

**Notes:** Foundation for all backend work

---

### US-002: Implement SQLite database schema and models
**Priority:** 1
**Maven Steps:** 1, 5

As a system, I need a SQLite database with proper schema to store trades, performance metrics, configurations, and model metadata on local disk.

**Acceptance Criteria:**
- Create database/ directory for SQLite files
- Design schema with tables: trades, performance_metrics, models, configurations, market_data
- Implement SQLAlchemy async models for all tables
- Create database initialization script
- Add migration system (alembic)
- Create database service class with connection pooling
- Implement CRUD operations for all models
- Add indexing on frequently queried columns
- Add data validation with Pydantic
- Test database operations

**Notes:** Local disk storage - no remote database needed

---

### US-003: Implement MT5 connection service
**Priority:** 1
**Maven Steps:** 1, 7

As a trading system, I need to connect to MetaTrader 5 terminal to fetch real-time data, place orders, and manage positions.

**Acceptance Criteria:**
- Install MetaTrader5 Python library
- Create MT5Service class with connection management
- Implement initialize() with login credentials
- Implement reconnect() logic with retry mechanism
- Add connection state monitoring
- Implement get_price() for current quotes
- Implement get_historical_data() for OHLCV data
- Implement place_order() with error handling
- Implement get_positions() for active trades
- Implement get_account_info() for balance/equity
- Add comprehensive error handling for MT5 failures
- Add logging for all MT5 operations
- Test connection to live MT5 terminal

**Notes:** MT5 terminal must be running and Algo Trading enabled

---

### US-004: Implement data ingestion service
**Priority:** 2
**Maven Steps:** 1, 7

As a system, I need to continuously ingest market data from MT5 for all volatility indices (V10, V25, V50, V75, V100) and store it efficiently.

**Acceptance Criteria:**
- Create DataIngestionService class
- Implement async data fetching loop for all symbols
- Store OHLCV data in Parquet format for efficiency
- Store tick data in SQLite for recent data
- Implement data deduplication
- Add data quality checks
- Create data retention policy (keep 90 days)
- Implement backfill for missing historical data
- Add monitoring for data quality issues
- Test data ingestion for all 5 volatility indices

**Notes:** Use Parquet for time-series, SQLite for structured data

---

### US-005: Implement feature engineering module
**Priority:** 2
**Maven Steps:** 1, 5

As an AI system, I need to transform raw market data into meaningful features for machine learning predictions.

**Acceptance Criteria:**
- Create FeatureEngineering class
- Implement price-based features (returns, log returns)
- Implement volatility features (ATR, std dev, Parkinson estimator)
- Implement momentum features (RSI, MACD, Stochastic)
- Implement trend features (SMA, EMA, ADX)
- Implement lag features (1, 2, 3, 5, 10 periods)
- Implement rolling statistics (mean, std, min, max)
- Implement z-score features
- Implement Bollinger Band features
- Add feature caching to avoid recomputation
- Handle missing data gracefully
- Test feature generation on historical data

**Notes:** Use ta-lib and pandas-ta libraries

---

### US-006: Implement ML model training pipeline
**Priority:** 2
**Maven Steps:** 1, 5

As an AI system, I need to train machine learning models on historical data to generate trading signals.

**Acceptance Criteria:**
- Create ModelTrainer class
- Implement TimeSeriesSplit for cross-validation
- Train XGBoost classifier for buy/sell/wait signals
- Implement feature importance analysis
- Save trained models with joblib
- Log training metrics (accuracy, precision, recall, F1)
- Implement backtesting framework
- Calculate Sharpe ratio, max drawdown, win rate
- Generate training reports
- Add model versioning
- Test training on 60+ days of historical data

**Notes:** Use XGBoost for baseline, target 65-70% win rate

---

### US-007: Implement ML model inference service
**Priority:** 2
**Maven Steps:** 1, 5

As a trading system, I need to use trained models to generate real-time trading signals with confidence scores.

**Acceptance Criteria:**
- Create ModelInferenceService class
- Load trained models from disk
- Implement predict() method returning signal + confidence
- Implement batch prediction for multiple symbols
- Add model performance monitoring
- Implement model fallback on errors
- Log all predictions for audit trail
- Add prediction caching (1 second TTL)
- Test inference speed (< 100ms per prediction)
- Validate predictions on hold-out test set

**Notes:** Must be fast for real-time trading

---

### US-008: Implement signal generation system
**Priority:** 3
**Maven Steps:** 1, 5

As a trading system, I need to combine ML predictions with technical analysis to generate final trading signals.

**Acceptance Criteria:**
- Create SignalGenerator class
- Implement signal aggregation (ML + technical)
- Implement confidence scoring
- Add signal filtering (minimum confidence threshold)
- Implement signal cooldown (avoid overtrading)
- Add market regime detection (trending/ranging)
- Implement strategy switching based on regime
- Generate structured signal object (symbol, direction, confidence, reasons)
- Log all generated signals
- Test signal generation on historical data

**Notes:** Combine ML with technical analysis for robustness

---

### US-009: Implement risk management system
**Priority:** 1
**Maven Steps:** 1, 5

As a trading system, I need to calculate position sizes, stop losses, and take profits to manage risk properly.

**Acceptance Criteria:**
- Create RiskManager class
- Implement fixed percentage risk (1-2% per trade)
- Implement ATR-based stop loss calculation
- Implement Kelly Criterion position sizing
- Implement volatility-based position sizing
- Add risk-reward ratio validation (min 1.5:1)
- Implement trailing stop loss
- Implement time-based exit (max trade duration)
- Implement maximum daily loss limit
- Implement position correlation check
- Implement maximum concurrent positions limit
- Add comprehensive risk logging
- Test risk calculations on historical trades

**Notes:** Never risk more than 2% per trade

---

### US-010: Implement order execution service
**Priority:** 2
**Maven Steps:** 1, 7

As a trading system, I need to execute trades through MT5 when signals are generated and risk is validated.

**Acceptance Criteria:**
- Create OrderExecutionService class
- Implement order placement with retry logic
- Implement order validation before submission
- Add order status tracking
- Implement order modification (stop loss / take profit)
- Implement position closing logic
- Add comprehensive error handling
- Implement order queue for multiple symbols
- Add order execution logging
- Implement emergency stop functionality
- Test order execution with paper trading

**Notes:** Must handle MT5 connection failures gracefully

---

### US-011: Implement trade management system
**Priority:** 2
**Maven Steps:** 1, 7

As a trading system, I need to monitor open positions, update stop losses, and manage trade lifecycle.

**Acceptance Criteria:**
- Create TradeManager class
- Implement open position monitoring loop
- Implement trailing stop loss updates
- Implement partial profit taking
- Implement position scaling in/out
- Add trade state management (pending, open, closed)
- Implement trade expiry logic
- Add manual override capability
- Generate trade lifecycle events
- Log all trade management actions
- Test trade management on historical data

**Notes:** Active management required for volatility indices

---

### US-012: Implement performance tracking system
**Priority:** 2
**Maven Steps:** 1, 5

As a trader, I need to track performance metrics, win rate, profit factor, and drawdown to evaluate system performance.

**Acceptance Criteria:**
- Create PerformanceTracker class
- Calculate real-time win rate
- Calculate profit factor
- Calculate Sharpe ratio
- Calculate maximum drawdown
- Calculate average win/loss
- Implement equity curve calculation
- Generate daily/weekly/monthly reports
- Store performance metrics in database
- Add performance alerting (degradation detection)
- Create performance dashboard API endpoints
- Test calculations on historical trade data

**Notes:** Track everything - data is gold

---

### US-013: Implement pattern recognition system
**Priority:** 3
**Maven Steps:** 1, 5

As an AI system, I need to recognize recurring price patterns and market regimes to adapt trading strategies.

**Acceptance Criteria:**
- Create PatternRecognition class
- Implement price pattern detection (support/resistance, double top/bottom)
- Implement candlestick pattern recognition
- Implement regime detection (bull/bear/ranging)
- Implement volatility regime detection (low/medium/high)
- Implement pattern clustering with KMeans
- Store detected patterns in database
- Implement pattern matching for current conditions
- Generate pattern-based signals
- Log all detected patterns
- Test pattern recognition on historical data

**Notes:** Use for strategy adaptation

---

### US-014: Implement genetic algorithm optimizer
**Priority:** 3
**Maven Steps:** 1, 5

As an evolving system, I need to optimize trading strategy parameters using genetic algorithms to improve performance over time.

**Acceptance Criteria:**
- Create GeneticOptimizer class
- Define strategy parameters as genes (RSI period, MACD settings, ATR multiplier)
- Implement fitness function (Sharpe ratio + win rate)
- Implement selection (tournament selection)
- Implement crossover (single-point crossover)
- Implement mutation (Gaussian mutation)
- Implement elitism (keep best performers)
- Run evolution for 50+ generations
- Track evolution progress
- Save best parameters to database
- Implement parameter validation
- Test optimization on historical data

**Notes:** Use DEAP library for genetic algorithms

---

### US-015: Implement continuous learning system
**Priority:** 3
**Maven Steps:** 1, 5

As a learning system, I need to continuously retrain models with new data and adapt to changing market conditions.

**Acceptance Criteria:**
- Create ContinuousLearning class
- Implement retraining trigger logic (performance degradation + minimum trades)
- Implement incremental learning (update model with new data)
- Implement model versioning and rollback
- A/B test new models before deployment
- Implement model performance comparison
- Add learning rate scheduling
- Implement concept drift detection
- Log all learning events
- Schedule automatic retraining (weekly)
- Test continuous learning on simulated data

**Notes:** Critical for long-term success

---

### US-016: Implement trading loop orchestration
**Priority:** 2
**Maven Steps:** 1, 7

As a trading system, I need to orchestrate the entire trading loop from data ingestion to order execution.

**Acceptance Criteria:**
- Create TradingLoop class
- Implement async trading loop (runs every 1 second)
- Orchestrate: data fetch → features → prediction → signal → risk → execution
- Implement error handling for each step
- Add circuit breaker for critical failures
- Implement loop state management (running/paused/stopped)
- Add loop monitoring and health checks
- Implement loop recovery from errors
- Add comprehensive logging
- Implement loop performance metrics
- Test trading loop end-to-end with paper trading

**Notes:** Heart of the trading system

---

### US-017: Implement WebSocket real-time streaming
**Priority:** 2
**Maven Steps:** 1, 9

As a frontend, I need to receive real-time updates on prices, signals, trades, and performance via WebSocket.

**Acceptance Criteria:**
- Create WebSocket manager class
- Implement /ws/stream endpoint for real-time data
- Stream price updates for all volatility indices
- Stream new trading signals
- Stream trade execution events
- Stream position updates
- Stream performance metrics
- Implement connection management (connect/disconnect/reconnect)
- Add authentication for WebSocket connections
- Implement heartbeat/ping-pong
- Add rate limiting
- Test WebSocket with multiple concurrent connections

**Notes:** Matches frontend WebSocket client

---

### US-018: Implement REST API endpoints
**Priority:** 2
**Maven Steps:** 1, 7

As a frontend, I need REST API endpoints to fetch data, control the system, and retrieve historical information.

**Acceptance Criteria:**
- Implement GET /api/health - health check
- Implement GET /api/account - account information
- Implement GET /api/positions - open positions
- Implement GET /api/trades - trade history
- Implement GET /api/performance - performance metrics
- Implement GET /api/signals - recent signals
- Implement GET /api/models - model information
- Implement POST /api/start - start trading loop
- Implement POST /api/stop - stop trading loop
- Implement POST /api/pause - pause trading
- Implement GET /api/config - system configuration
- Implement PUT /api/config - update configuration
- Add request validation with Pydantic
- Add error handling and proper status codes
- Add API documentation (OpenAPI/Swagger)

**Notes:** Matches frontend API client

---

### US-019: Implement configuration management
**Priority:** 3
**Maven Steps:** 1, 5

As a system administrator, I need to manage system configuration including risk parameters, trading symbols, and model settings.

**Acceptance Criteria:**
- Create Configuration class
- Load configuration from .env file
- Store configuration in database for runtime updates
- Implement configuration validation
- Add default values for all settings
- Implement configuration update API
- Add configuration change logging
- Implement configuration versioning
- Add configuration reset to defaults
- Document all configuration options
- Test configuration management

**Notes:** Make system configurable without code changes

---

### US-020: Implement logging and monitoring
**Priority:** 2
**Maven Steps:** 1, 5

As a system operator, I need comprehensive logging and monitoring to track system health and debug issues.

**Acceptance Criteria:**
- Set up structured logging with loguru
- Implement log rotation (daily)
- Add log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Log all trading operations
- Log all system errors with stack traces
- Implement performance monitoring (loop execution time)
- Implement system metrics (CPU, memory, disk usage)
- Add alerting for critical errors
- Implement dashboard for system health
- Store logs in backend/logs/ directory
- Test logging and monitoring

**Notes:** Essential for production system

---

### US-021: Implement error handling and recovery
**Priority:** 1
**Maven Steps:** 1, 10

As a robust system, I need comprehensive error handling and automatic recovery from failures.

**Acceptance Criteria:**
- Implement try-except blocks around all MT5 calls
- Implement MT5 reconnection logic
- Implement database reconnection logic
- Implement model fallback on errors
- Implement circuit breaker for repeated failures
- Add graceful degradation (reduce trading on errors)
- Implement error tracking and counting
- Add error recovery strategies
- Implement system state recovery after crash
- Add comprehensive error logging
- Test error handling scenarios

**Notes:** Critical for 24/7 operation

---

### US-022: Implement backtesting framework
**Priority:** 3
**Maven Steps:** 1, 5

As a developer, I need a backtesting framework to validate strategies and models on historical data before live trading.

**Acceptance Criteria:**
- Create Backtester class
- Implement historical data loading
- Implement signal generation on historical data
- Simulate trade execution with realistic slippage
- Calculate performance metrics (returns, Sharpe, drawdown)
- Generate equity curve
- Generate trade-by-trade analysis
- Implement parameter optimization
- Generate backtesting reports (HTML/PDF)
- Add walk-forward analysis
- Validate backtesting results on out-of-sample data
- Test backtesting on 90+ days of data

**Notes:** Essential for validation

---

### US-023: Implement paper trading mode
**Priority:** 2
**Maven Steps:** 1, 5

As a tester, I need a paper trading mode to validate the system without risking real money.

**Acceptance Criteria:**
- Create PaperTrader class
- Simulate MT5 connection (no real trades)
- Track virtual positions and balances
- Implement virtual order execution
- Track paper trading performance separately
- Add paper trading mode configuration
- Implement paper trading UI indicator
- Compare paper vs live performance
- Run paper trading for minimum 2 weeks before live
- Validate paper trading results match backtests
- Test paper trading mode end-to-end

**Notes:** Must validate system before live trading

---

### US-024: Create backend deployment and startup scripts
**Priority:** 3
**Maven Steps:** 1, 7

As a system administrator, I need scripts to easily start, stop, and manage the backend service.

**Acceptance Criteria:**
- Create start.sh script to launch backend
- Create stop.sh script to gracefully shutdown
- Create restart.sh script for quick restart
- Create status.sh script to check system status
- Create install.sh script for initial setup
- Add virtual environment setup (venv)
- Create requirements.txt with pinned versions
- Add systemd service file (optional)
- Create startup logging
- Add startup health checks
- Document deployment process
- Test all scripts

**Notes:** Make system easy to deploy

---

### US-025: Create backend documentation
**Priority:** 3
**Maven Steps:** 1

As a developer, I need comprehensive documentation for the backend system.

**Acceptance Criteria:**
- Create README.md in backend/ directory
- Document system architecture
- Document installation process
- Document configuration options
- Document API endpoints (OpenAPI/Swagger)
- Document database schema
- Document deployment process
- Add code comments for complex logic
- Create troubleshooting guide
- Document development workflow
- Add examples and usage guides
- Review documentation completeness

**Notes:** Good documentation essential for maintenance

---

## Functional Requirements

- **FR-1:** System must connect to MetaTrader 5 terminal for trading operations
- **FR-2:** System must monitor 5 volatility indices simultaneously (V10, V25, V50, V75, V100)
- **FR-3:** System must generate trading signals autonomously using ML models
- **FR-4:** System must implement proper risk management (max 2% risk per trade)
- **FR-5:** System must use local disk storage (SQLite + Parquet) - no remote databases
- **FR-6:** System must have memory and learning capabilities
- **FR-7:** System must achieve 65-70% win rate target
- **FR-8:** System must provide REST API for frontend communication
- **FR-9:** System must provide WebSocket for real-time updates
- **FR-10:** System must handle errors gracefully and recover automatically
- **FR-11:** System must log all operations for audit trail
- **FR-12:** System must support paper trading mode for validation

## Non-Goals

- No desktop application wrapper in this phase (future goal)
- No remote database or cloud storage (local disk only)
- No cryptocurrency or forex trading (volatility indices only)
- No social trading or copy trading features
- No mobile app in this phase
- No multi-tenancy (single user system)
- No web-based configuration UI (use API/config files)

## Technical Considerations

- Python 3.11+ required for best performance
- FastAPI with async/await for real-time operations
- SQLite for structured data, Parquet for time-series data
- XGBoost for ML baseline, target 65-70% win rate
- MetaTrader5 Python library for terminal integration
- ta-lib or pandas-ta for technical indicators
- DEAP library for genetic algorithm optimization
- System must handle MT5 connection failures gracefully
- All data stored locally on hard disk (backend/data/ directory)
- Logging essential for debugging and audit trails
- Paper trading required before live trading (minimum 2 weeks)

## Success Metrics

- System can connect to MT5 and fetch real-time data
- System can generate and execute trading signals autonomously
- System achieves 65%+ win rate in backtesting
- System achieves 60%+ win rate in paper trading
- System properly manages risk (max 2% per trade)
- System can run 24/7 without crashes
- System has comprehensive logging and monitoring
- System has API documentation (OpenAPI/Swagger)
- System has been validated with 2+ weeks of paper trading
- **Target:** 70% win rate, 1.5+ profit factor, <20% max drawdown

## Tech Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.11+ |
| Framework | FastAPI 0.104+ |
| Database | SQLite (aiosqlite) |
| Data Storage | Parquet files (pyarrow) |
| MT5 Integration | MetaTrader5 5.0.45+ |
| ML Framework | scikit-learn, XGBoost 2.0+ |
| Technical Analysis | ta-lib, pandas-ta |
| Genetic Algorithm | DEAP |
| Async Runtime | uvicorn |
| Logging | loguru |
| Data Processing | pandas, numpy |

## Architecture

**Type:** Python FastAPI Backend
**Storage:** Local disk (SQLite + Parquet)
**Communication:** REST API + WebSocket
**Execution:** Async/await with uvicorn
**MT5 Connection:** Direct via MetaTrader5 library
**Data Flow:** MT5 → Data Ingestion → Features → ML Model → Signal → Risk → Execution → Database

## Timeline

### Phase 1: Foundation (Week 1-2)
FastAPI setup, database, MT5 connection

### Phase 2: ML Pipeline (Week 3-4)
Feature engineering, model training, inference

### Phase 3: Trading Engine (Week 5-6)
Risk management, order execution, trade management

### Phase 4: Intelligence (Week 7-8)
Pattern recognition, genetic algorithm, continuous learning

### Phase 5: Production (Week 9-10)
Error handling, monitoring, paper trading, documentation
