# EURABAY Living System UI

A modern Next.js dashboard for the EURABAY Living System - an automated trading system with evolution-based strategy optimization.

## Tech Stack

- **Next.js 15** - React framework with App Router
- **TypeScript** - Type-safe development
- **Tailwind CSS** - Utility-first styling
- **shadcn/ui** - High-quality React components
- **Recharts** - Data visualization charts
- **Drizzle ORM** - Database toolkit with libSQL
- **Zod** - Runtime type validation

## Prerequisites

- Node.js 18+ and npm/yarn/pnpm
- Python backend server (optional, for development)

## Getting Started

### 1. Installation

Install dependencies:

```bash
npm install
# or
yarn install
# or
pnpm install
```

### 2. Environment Configuration

Copy the environment template and configure your variables:

```bash
cp .env.local.example .env.local
```

Edit `.env.local` and configure the following variables:

#### Required Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `NEXT_PUBLIC_APP_URL` | Frontend application URL | `http://localhost:3000` |
| `NEXT_PUBLIC_API_URL` | Backend API base URL | `http://localhost:8000/api` |
| `NEXT_PUBLIC_WS_URL` | WebSocket URL for real-time updates | `ws://localhost:8000/ws` |
| `NEXT_PUBLIC_API_TIMEOUT` | API request timeout (ms) | `30000` |

#### Optional Environment Variables (Production)

| Variable | Description |
|----------|-------------|
| `TURSO_DATABASE_URL` | Turso database URL for production |
| `TURSO_AUTH_TOKEN` | Turso authentication token |

### 3. Run Development Server

Start the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

## Development Workflow

### Type Checking

Run TypeScript type checking:

```bash
npm run typecheck
```

### Linting

Run ESLint to check code quality:

```bash
npm run lint
```

### Database Management

Generate database migrations:

```bash
npm run db:generate
```

Push schema changes to database:

```bash
npm run db:push
```

Open Drizzle Studio (database GUI):

```bash
npm run db:studio
```

Seed database with sample data:

```bash
npm run db:seed
```

## Project Structure

```
src/
├── app/                    # Next.js App Router pages
├── components/             # React components
│   ├── dashboard/          # Dashboard-specific components
│   └── ui/                 # shadcn/ui components
├── hooks/                  # Custom React hooks
├── lib/                    # Utilities and core logic
│   ├── api/                # API client and endpoints
│   ├── db/                 # Database configuration and repositories
│   └── websocket/          # WebSocket client
└── types/                  # TypeScript type definitions
```

## API Integration

The frontend connects to a Python FastAPI backend for:

- Real-time trading data
- Evolution system metrics
- Market data via Deriv.com
- MT5 integration for order execution

### API Client

The API client (`src/lib/api/client.ts) provides:

- Automatic auth token injection
- Request/response interceptors
- Retry logic with exponential backoff
- Type-safe requests

### WebSocket Connection

Real-time updates are handled through WebSocket:

- Trade status updates
- Evolution events
- Market price changes
- System status changes

## Building for Production

Create an optimized production build:

```bash
npm run build
```

Start the production server:

```bash
npm start
```

## Deploy on Vercel

The easiest way to deploy is using [Vercel](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme).

Check out the [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.

## License

This project is proprietary software.
