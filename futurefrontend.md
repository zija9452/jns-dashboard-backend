# Frontend Integration with Better Auth Documentation

## Overview
This document provides comprehensive guidance for integrating Better Auth with your Next.js 16 frontend to work seamlessly with your existing Python/FastAPI backend.

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────────┐
│   Next.js 16    │    │  Better Auth     │    │  Python/FastAPI     │
│   Frontend      │    │  (Node.js)       │    │   Backend           │
│                 │    │                  │    │                     │
│ - Better Auth   │◄──►│ - Handles auth   │    │ - Business Logic    │
│ - Next.js Auth  │    │ - User mgmt      │    │ - API endpoints     │
│ - UI/UX         │    │ - JWT tokens     │    │ - Data validation   │
└─────────────────┘    └──────────────────┘    └─────────────────────┘
                            │
                            ▼
                       ┌─────────────┐
                       │   Neon DB   │
                       │ (PostgreSQL)│
                       │ - Users     │
                       │ - Sessions  │
                       │ - Accounts  │
                       └─────────────┘
```

## Prerequisites

- Your Python/FastAPI backend is running (port 8000)
- Database is accessible (Neon PostgreSQL)
- Redis is running for token management

## Installation Steps

### 1. Create Next.js Application
```bash
npx create-next-app@latest regal-pos-frontend
cd regal-pos-frontend
npm install better-auth @better-auth/postgres-adapter drizzle-orm @neondatabase/serverless
```

### 2. Environment Variables
Create `.env.local` in your Next.js project:
```env
NEON_DATABASE_URL=your_neon_database_url
NEXT_PUBLIC_BETTER_AUTH_URL=http://localhost:3000
```

## Configuration

### 1. Better Auth Configuration
Create `lib/auth.ts`:
```typescript
import { betterAuth } from "better-auth";
import { postgresAdapter } from "@better-auth/postgres-adapter";
import { drizzle } from "drizzle-orm/neon-serverless";
import { Pool } from "@neondatabase/serverless";

const pool = new Pool({
  connectionString: process.env.NEON_DATABASE_URL!
});
const db = drizzle(pool);

export const auth = betterAuth({
  database: postgresAdapter(db, {
    provider: "pg",
  }),
  emailAndPassword: {
    enabled: true,
    requireEmailVerification: false,
  },
  socialProviders: {
    // Add social providers if needed
  },
  session: {
    expiresIn: 7 * 24 * 60 * 60, // 7 days
    slidingExpiration: true,
  },
});
```

### 2. Next.js Middleware
Create `middleware.ts`:
```typescript
import { auth } from "@/auth";
import { betterFetch } from "@better-fetch/fetch";

export const { middleware, matcher } = auth;

export default middleware;
```

### 3. API Routes
Create `app/api/auth/[...nextauth]/route.ts`:
```typescript
import { auth } from "@/auth";
import { handleAuth } from "next-auth/handlers";

export const GET = handleAuth(auth);
export const POST = handleAuth(auth);
```

## Frontend Components

### 1. Authentication Component
Create `components/AuthProvider.tsx`:
```typescript
"use client";
import { SessionProvider } from "better-auth/react";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  return (
    <SessionProvider>
      {children}
    </SessionProvider>
  );
}
```

### 2. Login Component
Create `components/LoginButton.tsx`:
```typescript
"use client";
import { useSession, signIn, signOut } from "better-auth/react";

export function LoginButton() {
  const { data: session, status } = useSession();

  if (status === "loading") {
    return <div>Loading...</div>;
  }

  if (session) {
    return (
      <div>
        <span>Welcome {session.user.email}</span>
        <button onClick={() => signOut()}>
          Sign out
        </button>
      </div>
    );
  }

  return (
    <button onClick={() => signIn()}>
      Sign in
    </button>
  );
}
```

### 3. API Integration Component
Create `lib/api.ts`:
```typescript
import { useSession } from "better-auth/react";

export const apiCall = async (endpoint: string, options: RequestInit = {}) => {
  const session = useSession();

  if (!session.data?.accessToken) {
    throw new Error("Not authenticated");
  }

  const response = await fetch(`http://localhost:8000${endpoint}`, {
    ...options,
    headers: {
      ...options.headers,
      'Authorization': `Bearer ${session.data.accessToken}`,
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`API call failed: ${response.statusText}`);
  }

  return response.json();
};

// Specific API calls for your POS system
export const getProduct = async (productId: string) => {
  return apiCall(`/admin/GetProducts/${productId}`);
};

export const getAllProducts = async () => {
  return apiCall('/admin/Viewproduct');
};

export const getMaxProductId = async () => {
  return apiCall('/admin/GetMaxProId');
};

export const getStockDetail = async (productName: string) => {
  return apiCall(`/admin/GetStockDetail?pro_name=${encodeURIComponent(productName)}`);
};

export const addBrand = async (brandName: string) => {
  return apiCall('/admin/brand', {
    method: 'POST',
    body: JSON.stringify({ brand: brandName })
  });
};
```

## Python Backend Updates

### 1. Better Auth Token Validator
Create `src/auth/better_auth_validator.py`:
```python
from fastapi import HTTPException, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
import os
from typing import Dict, Optional

class BetterAuthValidator:
    def __init__(self):
        self.secret = os.getenv("BETTER_AUTH_JWT_SECRET")
        self.algorithm = "HS256"
        self.audience = os.getenv("BETTER_AUTH_AUDIENCE", "your-app")

    def verify_token(self, token: str) -> Dict:
        try:
            payload = jwt.decode(
                token,
                self.secret,
                algorithms=[self.algorithm],
                audience=self.audience
            )
            return payload
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid Better Auth token")

# Security scheme
security = HTTPBearer()

def get_current_user_from_better_auth(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    validator = BetterAuthValidator()
    user_data = validator.verify_token(token)

    # You can extend this to map Better Auth user to your existing user model
    return user_data
```

### 2. Update Protected Endpoints
```python
from fastapi import APIRouter, Depends
from src.auth.better_auth_validator import get_current_user_from_better_auth

router = APIRouter()

@router.get("/products")
async def get_products(current_user = Depends(get_current_user_from_better_auth)):
    # Your existing business logic remains the same
    pass

@router.get("/admin/GetMaxProId")
async def get_max_product_id(current_user = Depends(get_current_user_from_better_auth)):
    # Your existing implementation
    pass
```

## Complete Flow Example

### 1. App Wrapper
Update `app/layout.tsx`:
```tsx
import { AuthProvider } from '@/components/AuthProvider';

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}
```

### 2. Dashboard Component
Create `app/dashboard/page.tsx`:
```tsx
"use client";
import { useSession } from "better-auth/react";
import { useState, useEffect } from "react";
import { getAllProducts, getProduct, getMaxProductId } from "@/lib/api";

export default function Dashboard() {
  const { data: session, status } = useSession();
  const [products, setProducts] = useState([]);
  const [maxProductId, setMaxProductId] = useState(null);

  useEffect(() => {
    if (session?.accessToken) {
      fetchDashboardData();
    }
  }, [session]);

  const fetchDashboardData = async () => {
    try {
      const [allProducts, maxId] = await Promise.all([
        getAllProducts(),
        getMaxProductId()
      ]);
      setProducts(allProducts);
      setMaxProductId(maxId);
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
    }
  };

  if (status === "loading") {
    return <div>Loading...</div>;
  }

  if (!session) {
    return <div>Please sign in to access the dashboard</div>;
  }

  return (
    <div className="dashboard">
      <h1>POS Dashboard</h1>
      <div className="stats">
        <div>Total Products: {products.length}</div>
        <div>Max Product ID: {maxProductId}</div>
      </div>
      <div className="products">
        <h2>Products</h2>
        {products.map((product: any) => (
          <div key={product.pro_id} className="product-card">
            <h3>{product.pro_name}</h3>
            <p>Price: ${product.pro_price}</p>
            <p>Cost: ${product.pro_cost}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
```

## Error Handling

### Frontend Error Handling
```typescript
// lib/errorHandler.ts
export const handleApiError = (error: any) => {
  if (error.status === 401) {
    // Redirect to login
    window.location.href = '/login';
  } else if (error.status === 403) {
    // Show forbidden message
    alert('You do not have permission to access this resource');
  } else {
    // Show generic error
    alert('An error occurred: ' + error.message);
  }
};
```

### Backend Error Handling
Your existing error handling remains the same, but now it will work with Better Auth tokens.

## Security Considerations

1. **JWT Secret Management**: Store Better Auth JWT secret securely in environment variables
2. **HTTPS in Production**: Always use HTTPS for authentication
3. **Token Expiration**: Implement proper token refresh mechanisms
4. **CORS Configuration**: Configure CORS appropriately for your domain

## Deployment

### Environment Variables for Production
```env
# Better Auth Configuration
BETTER_AUTH_JWT_SECRET=your_secure_jwt_secret
BETTER_AUTH_ISSUER=your-domain.com
BETTER_AUTH_AUDIENCE=your-app

# Database
NEON_DATABASE_URL=your_production_neon_url

# Frontend
NEXT_PUBLIC_BETTER_AUTH_URL=https://your-frontend-domain.com
```

### Docker Configuration for Frontend
Create `Dockerfile` for Next.js:
```dockerfile
FROM node:18-alpine

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm install

# Copy source code
COPY . .

# Build the application
RUN npm run build

# Expose port
EXPOSE 3000

# Start the application
CMD ["npm", "start"]
```

## Testing the Integration

### 1. Unit Tests for API Integration
```typescript
// __tests__/api.test.ts
import { apiCall } from '../lib/api';

describe('API Integration', () => {
  test('should make authenticated API calls', async () => {
    // Mock session data
    const mockSession = { accessToken: 'test-token' };

    const result = await apiCall('/admin/GetMaxProId');
    expect(result).toBeDefined();
  });
});
```

### 2. Integration Test Flow
1. Start Python backend: `docker-compose up`
2. Start Next.js frontend: `npm run dev`
3. Register/login via Better Auth
4. Navigate to protected routes
5. Verify API calls work with Better Auth tokens
6. Test CRUD operations

## Troubleshooting

### Common Issues

1. **Token Validation Fails**: Ensure JWT secret matches between Better Auth and Python backend
2. **API Calls Return 401**: Check if Better Auth token is being passed in Authorization header
3. **Database Connection Issues**: Verify Neon database URL and credentials
4. **CORS Errors**: Configure CORS in both Next.js and FastAPI applications

### Debug Steps
1. Verify Better Auth is generating valid JWT tokens
2. Check that Python backend can decode Better Auth tokens
3. Confirm API endpoints are protected with Better Auth validation
4. Test authentication flow step by step

## Best Practices

1. **Keep Backend Logic Separate**: Maintain your Python/FastAPI backend as the source of truth for business logic
2. **Consistent User Experience**: Ensure authentication feels seamless across the application
3. **Error Handling**: Provide clear error messages to users
4. **Performance**: Implement caching where appropriate
5. **Security**: Regularly rotate JWT secrets and monitor authentication logs

## Migration Strategy

### Phase 1: Integration
- Set up Better Auth in Next.js frontend
- Create token validation bridge in Python backend
- Test authentication flow end-to-end

### Phase 2: Feature Migration
- Migrate existing user data to Better Auth format if needed
- Update frontend components to use Better Auth
- Test all CRUD operations with new authentication

### Phase 3: Optimization
- Optimize performance
- Add additional security measures
- Monitor and refine the authentication flow