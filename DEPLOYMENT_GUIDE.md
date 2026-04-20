# Backend Deployment Guide - Google Cloud & Local

## **Overview**
This guide covers deployment to:
1. **Local (Docker Desktop)** - Development & Testing
2. **Google Cloud Run** - Production (Recommended)
3. **Google Kubernetes Engine (GKE)** - Advanced Production

---

## **Prerequisites**

### **1. Install Required Tools:**
```bash
# Install Docker Desktop
https://www.docker.com/products/docker-desktop

# Install Google Cloud SDK
https://cloud.google.com/sdk/docs/install

# Install gcloud CLI (alternative)
curl https://sdk.cloud.google.com | bash
```

### **2. Google Cloud Setup:**
```bash
# Login to Google Cloud
gcloud auth login

# Set your project ID
export PROJECT_ID="your-project-id"
gcloud config set project $PROJECT_ID

# Enable required APIs
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
gcloud services enable cloudbuild.googleapis.com
```

---

## **Option 1: Google Cloud Run (Recommended for Production)**

### **Step 1: Build & Push to Container Registry**
```bash
cd E:\JnS\backend

# Set project
export PROJECT_ID="your-project-id"
gcloud config set project $PROJECT_ID

# Build and push to Google Container Registry
gcloud builds submit --tag gcr.io/$PROJECT_ID/backend-api:latest
```

### **Step 2: Deploy to Cloud Run**
```bash
# Deploy
gcloud run deploy backend-api \
  --image gcr.io/$PROJECT_ID/backend-api:latest \
  --platform managed \
  --region me-central1 \
  --allow-unauthenticated \
  --set-env-vars ENVIRONMENT=production \
  --set-secrets DATABASE_URL=DATABASE_SECRET:latest \
  --set-secrets JWT_SECRET=JWT_SECRET:latest \
  --memory 512Mi \
  --cpu 1 \
  --concurrency 80 \
  --timeout 300
```

### **Step 3: Add Environment Variables**
```bash
# Update environment variables
gcloud run services update backend-api \
  --set-env-vars CLOUDINARY_CLOUD_NAME=your-cloud-name \
  --set-env-vars CLOUDINARY_API_KEY=your-key \
  --set-env-vars REDIS_URL=redis://your-redis:6379 \
  --region me-central1
```

### **Step 4: Get Service URL**
```bash
gcloud run services describe backend-api \
  --platform managed \
  --region me-central1 \
  --format 'value(status.url)'
```

### **Step 5: View Logs**
```bash
gcloud run logs read backend-api --region me-central1
```

---

-

## **Environment Variables**

### **Required Variables:**
```bash
# Database (REQUIRED)
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# JWT (REQUIRED)
JWT_SECRET=your-secret-key-min-32-chars

# Environment
ENVIRONMENT=production  # or development

# CORS
CORS_ORIGINS=https://your-frontend.com

# Optional - Cloudinary (for images)
CLOUDINARY_CLOUD_NAME=your-cloud
CLOUDINARY_API_KEY=your-key
CLOUDINARY_API_SECRET=your-secret

# Optional - Redis
REDIS_URL=redis://host:6379/0
```

---

## **Database Setup**

### **Option A: Cloud SQL (Recommended)**
```bash
# Create Cloud SQL instance
gcloud sql instances create postgres-instance \
  --database-version=POSTGRES_14 \
  --tier=db-f1-micro \
  --region=me-central1 \
  --root-password=your-root-password

# Create database
gcloud sql databases create neondb \
  --instance=postgres-instance

# Get connection string
gcloud sql instances describe postgres-instance \
  --format='value(connectionName)'
```

### **Option B: External Database**
Just update `DATABASE_URL` in environment variables.

---

## **CI/CD Pipeline (GitHub Actions)**

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Google Cloud Run

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Cloud SDK
      uses: google-github-actions/setup-gcloud@v1
      with:
        service_account_key: ${{ secrets.GCP_SA_KEY }}
        project_id: ${{ secrets.GCP_PROJECT_ID }}
    
    - name: Build and Push
      run: |
        gcloud builds submit --tag gcr.io/${{ secrets.GCP_PROJECT_ID }}/backend-api:latest
    
    - name: Deploy to Cloud Run
      run: |
        gcloud run deploy backend-api \
          --image gcr.io/${{ secrets.GCP_PROJECT_ID }}/backend-api:latest \
          --platform managed \
          --region me-central1 \
          --allow-unauthenticated
```

---

## **Monitoring & Logging**

### **View Logs:**
```bash
# Cloud Run
gcloud run logs read backend-api --region me-central1

# Filter by severity
gcloud run logs read backend-api \
  --region me-central1 \
  --filter="severity>=ERROR"
```

### **Cloud Monitoring:**
```bash
# Enable monitoring
gcloud monitoring channels create \
  --display-name="Backend Alerts" \
  --type=email \
  --channel-labels=email_address=your-email@example.com
```

---

## **Scaling**

### **Cloud Run Auto-scaling:**
```bash
# Set min/max instances
gcloud run services update backend-api \
  --min-instances=1 \
  --max-instances=10 \
  --region me-central1
```

### **GKE Auto-scaling:**
```bash
kubectl autoscale deployment backend-api \
  --min=2 \
  --max=10 \
  --cpu-percent=80
```

---

## **Cost Optimization**

### **Cloud Run:**
- Min instances: 0 (for dev)
- Min instances: 1 (for prod - avoids cold starts)
- Memory: 512Mi (start small)
- CPU: 1 (can go lower for less traffic)

### **Estimated Monthly Cost (Cloud Run):**
- **Development:** $5-10/month (min instances: 0)
- **Production:** $50-100/month (min instances: 1-2)
- **High Traffic:** $200-500/month (auto-scaled)

---

## **Troubleshooting**

### **Container won't start:**
```bash
# Check logs
gcloud run logs read backend-api --region me-central1 --limit 50

# Test locally
docker run -p 8000:8000 --env-file .env backend-api:latest
```

### **Database connection error:**
```bash
# Test database connection
docker exec -it backend-api psql $DATABASE_URL

# Check Cloud SQL authorized networks
gcloud sql instances patch postgres-instance \
  --authorized-networks=0.0.0.0/0
```

### **Memory issues:**
```bash
# Increase memory
gcloud run services update backend-api \
  --memory=1Gi \
  --region me-central1
```

---

## **Security Best Practices**

1. **Use Secret Manager:**
```bash
gcloud secrets create DATABASE_URL
gcloud secrets versions add DATABASE_URL --data-file=database-url.txt

# Deploy with secret
gcloud run deploy backend-api \
  --set-secrets DATABASE_URL=DATABASE_URL:latest
```

2. **Enable IAM:**
```bash
gcloud run services add-iam-policy-binding backend-api \
  --member=user:your-email@example.com \
  --role=roles/run.invoker \
  --region me-central1
```

3. **Set up VPC (for database access):**
```bash
gcloud run services update backend-api \
  --vpc-connector=your-vpc-connector \
  --region me-central1
```

---

## **Quick Commands Reference**

```bash
# Build locally
docker build -t backend-api:latest .

# Run locally
docker run -p 8000:8000 --env-file .env backend-api:latest

# Push to GCP
gcloud builds submit --tag gcr.io/PROJECT_ID/backend-api

# Deploy to Cloud Run
gcloud run deploy backend-api --image gcr.io/PROJECT_ID/backend-api

# View logs
gcloud run logs read backend-api --region me-central1

# Update environment
gcloud run services update backend-api --set-env-vars KEY=value

# Delete service
gcloud run services delete backend-api --region me-central1
```

---

## **Next Steps**

1. ✅ Build Docker image locally
2. ✅ Test locally with Docker Desktop
3. ✅ Set up Cloud SQL database
4. ✅ Deploy to Cloud Run
5. ✅ Configure custom domain (optional)
6. ✅ Set up CI/CD pipeline
7. ✅ Configure monitoring & alerts

**Deployment Time:** 15-30 minutes
**Cost:** Free tier available for Cloud Run (2M requests/month)
