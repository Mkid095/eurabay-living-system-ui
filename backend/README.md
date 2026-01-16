# EURABAY Living System - Backend API Server

FastAPI-based backend server for the EURABAY Living autonomous trading system.

## Prerequisites

- Python 3.11 or higher
- pip (Python package installer)
- Git

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd eurabay-living-system-ui/backend
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate

# On Linux/Mac:
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your configuration
nano .env
```

## Project Structure

```
backend/
├── alembic/              # Database migrations
├── app/
│   ├── api/             # API routers (REST and WebSocket)
│   ├── core/            # Configuration and logging
│   ├── models/          # Database models and Pydantic schemas
│   ├── services/        # Business logic services
│   ├── tests/           # Unit tests
│   ├── utils/           # Utility functions
│   └── main.py          # Application entry point
├── data/                # Data storage
├── database/            # SQLite database files
├── logs/                # Application logs
├── tests/               # Integration tests
├── trading/             # Trading system modules
├── requirements.txt     # Python dependencies
├── .env.example         # Example environment configuration
├── .gitignore          # Git ignore rules
└── README.md           # This file
```

## Running the Server

### Development Mode

```bash
# Activate virtual environment first
# On Windows:
venv\Scripts\activate

# On Linux/Mac:
source venv/bin/activate

# Run the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Using Start Scripts

```bash
# On Linux/Mac:
./start.sh

# On Windows:
start.bat
```

## API Documentation

Once the server is running, access the interactive API documentation at:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Health Check

```bash
curl http://localhost:8000/api/health
```

## Environment Variables

See `.env.example` for all available configuration options. Key variables include:

- `SERVER_HOST`: Server host (default: 0.0.0.0)
- `SERVER_PORT`: Server port (default: 8000)
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)
- `DATABASE_URL`: Database connection string
- `MT5_LOGIN`: MetaTrader 5 account login
- `MT5_PASSWORD`: MetaTrader 5 account password
- `MT5_SERVER`: MetaTrader 5 server address

## Logging

Logs are stored in the `logs/` directory:

- `info.log`: General information logs
- `error.log`: Error logs
- `trading.log`: Trading-specific logs

Logs are rotated daily and compressed after 7 days.

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_specific.py
```

## Database Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

## Troubleshooting

### Virtual Environment Issues

If the virtual environment doesn't activate:

```bash
# Delete and recreate
rm -rf venv
python -m venv venv
```

### Import Errors

Ensure you've activated the virtual environment and installed dependencies:

```bash
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### Port Already in Use

Change the port in `.env` or run:

```bash
# Find process using port 8000
lsof -i :8000  # Linux/Mac
netstat -ano | findstr :8000  # Windows

# Kill the process
kill -9 <PID>  # Linux/Mac
taskkill /PID <PID> /F  # Windows
```

## Development Workflow

1. Make changes to code
2. Run tests: `pytest`
3. Check code style: `flake8 app/`
4. Format code: `black app/`
5. Type check: `mypy app/`
6. Commit changes

## Support

For issues and questions, please refer to the main project documentation.
