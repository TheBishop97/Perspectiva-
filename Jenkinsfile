pipeline {
    agent any
    
    environment {
        IMAGE_NAME = 'perspectiva'
        IMAGE_TAG = "${BUILD_NUMBER}"
        CONTAINER_NAME = 'perspectiva-app'
        APP_PORT = '8000'
        DB_NAME = 'perspectiva'
        DB_USER = 'perspectiva'
        DB_PASSWORD = 'perspectiva'
        DOCKER_NETWORK = 'perspectiva-network'
    }
    
    stages {
        stage('Checkout') {
            steps {
                echo 'Checking out code from repository...'
                checkout scm
            }
        }
        
        stage('Build Docker Image') {
            steps {
                script {
                    echo 'Building Docker image...'
                    sh '''
                        # Create Dockerfile with proper PostgreSQL dependencies
                        cat > Dockerfile << 'EOF'
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \\
    PYTHONUNBUFFERED=1 \\
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Install system dependencies including PostgreSQL dev headers
RUN apt-get update && apt-get install -y \\
    postgresql-client \\
    libpq-dev \\
    gcc \\
    g++ \\
    curl \\
    build-essential \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip \\
    && pip install --no-cache-dir -r requirements.txt

# Download NLTK data
RUN python -c "import nltk; nltk.download('punkt', quiet=True); nltk.download('stopwords', quiet=True)"

# Copy project files
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash app \\
    && chown -R app:app /app
USER app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \\
    CMD curl -f http://localhost:8000/health || exit 1

# Default command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
EOF
                        
                        # Build the image
                        echo "Building Docker image: ${IMAGE_NAME}:${IMAGE_TAG}"
                        docker build -t ${IMAGE_NAME}:${IMAGE_TAG} .
                        docker tag ${IMAGE_NAME}:${IMAGE_TAG} ${IMAGE_NAME}:latest
                        
                        echo "Docker image built successfully"
                    '''
                }
            }
        }
        
        stage('Setup Database') {
            steps {
                script {
                    echo 'Setting up PostgreSQL database...'
                    sh '''
                        # Create network if it doesn't exist
                        docker network create ${DOCKER_NETWORK} 2>/dev/null || echo "Network already exists or creation failed"
                        
                        # Stop and remove existing database container
                        docker stop perspectiva-db 2>/dev/null || true
                        docker rm perspectiva-db 2>/dev/null || true
                        
                        # Start PostgreSQL container
                        docker run -d \\
                            --name perspectiva-db \\
                            --network ${DOCKER_NETWORK} \\
                            -e POSTGRES_DB=${DB_NAME} \\
                            -e POSTGRES_USER=${DB_USER} \\
                            -e POSTGRES_PASSWORD=${DB_PASSWORD} \\
                            -v perspectiva-db-data:/var/lib/postgresql/data \\
                            -p 5432:5432 \\
                            postgres:15-alpine
                        
                        echo "Waiting for database to be ready..."
                        sleep 20
                        
                        # Wait for database to be ready with timeout
                        for i in {1..30}; do
                            if docker exec perspectiva-db pg_isready -U ${DB_USER} -d ${DB_NAME} -q; then
                                echo "Database is ready!"
                                break
                            fi
                            echo "Waiting for database... ($i/30)"
                            sleep 2
                        done
                        
                        # Verify database connection
                        docker exec perspectiva-db psql -U ${DB_USER} -d ${DB_NAME} -c "SELECT version();" || echo "Database connection test failed"
                    '''
                }
            }
        }
        
        stage('Run Database Migrations') {
            steps {
                script {
                    echo 'Running database migrations...'
                    sh '''
                        # Initialize database tables using SQLAlchemy
                        docker run --rm \\
                            --network ${DOCKER_NETWORK} \\
                            -e DATABASE_URL="postgresql+psycopg2://${DB_USER}:${DB_PASSWORD}@perspectiva-db:5432/${DB_NAME}" \\
                            ${IMAGE_NAME}:${IMAGE_TAG} \\
                            python -c "
from app.db import Base, engine
try:
    Base.metadata.create_all(bind=engine)
    print('Database tables created successfully')
except Exception as e:
    print(f'Database initialization error: {e}')
" || echo "Database initialization failed or not needed"
                    '''
                }
            }
        }
        
        stage('Deploy Application') {
            steps {
                script {
                    echo 'Deploying application...'
                    sh '''
                        # Stop and remove existing application container
                        docker stop ${CONTAINER_NAME} 2>/dev/null || true
                        docker rm ${CONTAINER_NAME} 2>/dev/null || true
                        
                        # Start new application container
                        docker run -d \\
                            --name ${CONTAINER_NAME} \\
                            --network ${DOCKER_NETWORK} \\
                            -p ${APP_PORT}:8000 \\
                            -e DATABASE_URL="postgresql+psycopg2://${DB_USER}:${DB_PASSWORD}@perspectiva-db:5432/${DB_NAME}" \\
                            -e FEEDS="https://feeds.bbci.co.uk/news/rss.xml,https://rss.cnn.com/rss/edition.rss" \\
                            -e FETCH_INTERVAL_SECONDS=300 \\
                            -e MAX_ITEMS_PER_FEED=15 \\
                            -e SUMMARY_SENTENCES=3 \\
                            -e LOG_LEVEL=INFO \\
                            --restart unless-stopped \\
                            ${IMAGE_NAME}:${IMAGE_TAG}
                        
                        echo "Application container started"
                        sleep 5
                        
                        # Check if container is running
                        if docker ps | grep -q ${CONTAINER_NAME}; then
                            echo "Container is running successfully"
                        else
                            echo "Container failed to start"
                            docker logs ${CONTAINER_NAME}
                            exit 1
                        fi
                    '''
                }
            }
        }
        
        stage('Health Check') {
            steps {
                script {
                    echo 'Performing health check...'
                    sh '''
                        # Wait for application to fully start
                        echo "Waiting for application to be ready..."
                        sleep 30
                        
                        # Health check with multiple attempts
                        HEALTH_CHECK_PASSED=false
                        for i in {1..20}; do
                            if curl -f -s http://localhost:${APP_PORT}/health; then
                                echo ""
                                echo "Application is healthy!"
                                HEALTH_CHECK_PASSED=true
                                break
                            fi
                            echo "Health check attempt $i/20..."
                            sleep 3
                        done
                        
                        if [ "$HEALTH_CHECK_PASSED" = false ]; then
                            echo "Health check failed after multiple attempts"
                            echo "Application logs:"
                            docker logs --tail 50 ${CONTAINER_NAME}
                            exit 1
                        fi
                        
                        # Show application info
                        echo "=== Application Status ==="
                        curl -s http://localhost:${APP_PORT}/health | head -1
                        echo ""
                        echo "Container status:"
                        docker ps | grep ${CONTAINER_NAME}
                    '''
                }
            }
        }
    }
    
    post {
        always {
            echo 'Pipeline completed.'
        }
        
        success {
            echo 'Deployment successful!'
            echo "Application URL: http://your-vps-ip:${APP_PORT}"
            echo "API Documentation: http://your-vps-ip:${APP_PORT}/docs"
            echo "Health Check: http://your-vps-ip:${APP_PORT}/health"
            
            // Clean up old images (keep last 3 builds)
            sh '''
                echo "Cleaning up old Docker images..."
                OLD_IMAGES=$(docker images ${IMAGE_NAME} --format "{{.Tag}}" | grep -E "^[0-9]+$" | sort -nr | tail -n +4)
                if [ ! -z "$OLD_IMAGES" ]; then
                    echo "$OLD_IMAGES" | xargs -I {} docker rmi ${IMAGE_NAME}:{} 2>/dev/null || true
                    echo "Old images cleaned up"
                else
                    echo "No old images to clean up"
                fi
            '''
        }
        
        failure {
            echo 'Deployment failed!'
            
            sh '''
                echo "=== Container Status ==="
                docker ps -a | head -10
                
                echo "=== Application Logs ==="
                docker logs ${CONTAINER_NAME} 2>/dev/null | tail -30 || echo "No application logs available"
                
                echo "=== Database Logs ==="
                docker logs perspectiva-db 2>/dev/null | tail -20 || echo "No database logs available"
                
                echo "=== Network Status ==="
                docker network ls
                
                echo "=== Available Images ==="
                docker images | grep perspectiva || echo "No perspectiva images found"
            '''
        }
        
        cleanup {
            cleanWs()
        }
    }
}
