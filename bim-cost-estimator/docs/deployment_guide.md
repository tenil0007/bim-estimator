# Deployment Guide

## AI-Driven BIM Cost & Time Estimator

---

## 1. Local Development

### Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate            # Windows
# source venv/bin/activate       # Linux/Mac

pip install -r requirements.txt

# Train models (first time)
python -m scripts.run_training_pipeline

# Start server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Access
- Dashboard: http://localhost:5173
- API Docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

---

## 2. Docker Deployment

### Build & Run
```bash
docker-compose up --build -d
```

### Verify
```bash
docker-compose ps
docker-compose logs backend
curl http://localhost/health
```

### Stop
```bash
docker-compose down
```

---

## 3. AWS Deployment (ECS + Fargate)

### Step 1: Push to ECR
```bash
aws ecr create-repository --repository-name bim-backend
aws ecr create-repository --repository-name bim-frontend

# Login
aws ecr get-login-password --region ap-south-1 | docker login --username AWS --password-stdin <ACCOUNT>.dkr.ecr.ap-south-1.amazonaws.com

# Build and push
docker build -t bim-backend ./backend
docker tag bim-backend:latest <ACCOUNT>.dkr.ecr.ap-south-1.amazonaws.com/bim-backend:latest
docker push <ACCOUNT>.dkr.ecr.ap-south-1.amazonaws.com/bim-backend:latest

docker build -t bim-frontend ./frontend
docker tag bim-frontend:latest <ACCOUNT>.dkr.ecr.ap-south-1.amazonaws.com/bim-frontend:latest
docker push <ACCOUNT>.dkr.ecr.ap-south-1.amazonaws.com/bim-frontend:latest
```

### Step 2: Create ECS Cluster
```bash
aws ecs create-cluster --cluster-name bim-estimator-cluster
```

### Step 3: Create Task Definition
Create `task-definition.json` with backend and frontend containers, memory/CPU limits, and environment variables.

### Step 4: Create Service with ALB
Configure Application Load Balancer with:
- Port 80 → Frontend container
- Port 8000 → Backend container (path: /api/*)
- Health check: /health

### Step 5: Production Database
```bash
aws rds create-db-instance \
  --db-instance-identifier bim-estimator-db \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --master-username admin \
  --master-user-password <PASSWORD>
```

Update `DATABASE_URL` environment variable in ECS task definition.

---

## 4. Azure Deployment (Container Apps)

### Step 1: Create Container Registry
```bash
az acr create --name bimestimator --sku Basic
az acr login --name bimestimator
```

### Step 2: Build and Push
```bash
az acr build --registry bimestimator --image bim-backend:latest ./backend
az acr build --registry bimestimator --image bim-frontend:latest ./frontend
```

### Step 3: Create Container App Environment
```bash
az containerapp env create --name bim-env --resource-group bim-rg --location centralindia
```

### Step 4: Deploy Backend
```bash
az containerapp create \
  --name bim-backend \
  --resource-group bim-rg \
  --environment bim-env \
  --image bimestimator.azurecr.io/bim-backend:latest \
  --target-port 8000 \
  --ingress external
```

### Step 5: Deploy Frontend
```bash
az containerapp create \
  --name bim-frontend \
  --resource-group bim-rg \
  --environment bim-env \
  --image bimestimator.azurecr.io/bim-frontend:latest \
  --target-port 80 \
  --ingress external
```

---

## 5. CI/CD (GitHub Actions)

Create `.github/workflows/deploy.yml`:

```yaml
name: Build & Deploy

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
      - name: Run tests
        run: |
          cd backend
          python -m pytest tests/ -v

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build Docker images
        run: docker-compose build
      - name: Push to registry
        run: |
          # Push to ECR/ACR
          echo "Push images to container registry"

  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to cloud
        run: |
          # Update ECS/Container Apps
          echo "Deploy to production"
```

---

## 6. Environment Variables (Production)

```env
APP_NAME=BIM Cost & Time Estimator
DEBUG=false
DATABASE_URL=postgresql://user:pass@host:5432/bim_db
BACKEND_CORS_ORIGINS=https://bim.lnt.com
LOG_LEVEL=WARNING
LOG_FORMAT=json
MAX_UPLOAD_SIZE_MB=500
COST_MODEL_TYPE=xgboost
TIME_MODEL_TYPE=xgboost
```

---

## 7. Production Checklist

- [ ] Switch to PostgreSQL
- [ ] Enable HTTPS (SSL/TLS)
- [ ] Add JWT authentication
- [ ] Configure rate limiting
- [ ] Set up monitoring (Prometheus/Grafana)
- [ ] Enable structured JSON logging
- [ ] Configure backup strategy
- [ ] Set up error alerting (Sentry)
- [ ] Load testing (Locust)
- [ ] Security audit
