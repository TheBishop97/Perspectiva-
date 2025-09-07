pipeline {
    agent any
    
    environment {
        // Docker image name
        IMAGE_NAME = 'perspectiva'
        IMAGE_TAG = "${BUILD_NUMBER}"
        CONTAINER_NAME = 'perspectiva-app'
        
        // Application settings
        APP_PORT = '8000'
        DB_NAME = 'perspectiva'
        DB_USER = 'perspectiva'
        DB_PASSWORD = 'perspectiva'
        
        // Network settings (adjust if needed)
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
                        # Create Dockerfile if it doesn't exist
                        if [ ! -f Dockerfile ]; then
                            cat > Dockerfile << 'EOF'
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \\
    PYTHONUNBUFFERED=1 \\
    DEBIAN_FRONTEND=noninteractive

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    postgresql-client \\
    gcc \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \\
    && pip install --no-cache-dir -r requirements.txt

# Download NLTK data for text processing
RUN python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords')"

# Copy project
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash app \\
    && chown -R app:app /app
USER app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:8000/health || exit 1

# Default command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
EOF
                        fi
                        
                        # Build the image
                        docker build -t ${IMAGE_NAME}:${IMAGE_TAG} .
                        docker build -t ${IMAGE_NAME}:latest .
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
                        docker network create ${DOCKER_NETWORK} || true
                        
                        # Stop and remove existing database container
                        docker stop perspectiva-db || true
                        docker rm perspectiva-db || true
                        
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
                        
                        # Wait for database to be ready
                        echo "Waiting for database to be ready..."
                        for i in {1..30}; do
                            if docker exec perspectiva-db pg_isready -U ${DB_USER} -d ${DB_NAME}; then
                                echo "Database is ready!"
                                break
                            fi
                            echo "Waiting for database... ($i/30)"
                            sleep 2
                        done
                    '''
                }
            }
        }
        
        stage('Run Tests') {
            steps {
                script {
                    echo 'Running application tests...'
                    sh '''
                        # Run tests in a temporary container
                        docker run --rm \\
                            --network ${DOCKER_NETWORK} \\
                            -e DATABASE_URL="postgresql+psycopg2://${DB_USER}:${DB_PASSWORD}@perspectiva-db:5432/${DB_NAME}" \\
                            ${IMAGE_NAME}:${IMAGE_TAG} \\
                            python -m pytest tests/ -v || true
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
                        docker stop ${CONTAINER_NAME} || true
                        docker rm ${CONTAINER_NAME} || true
                        
                        # Run database migrations
                        echo "Running database migrations..."
                        docker run --rm \\
                            --network ${DOCKER_NETWORK} \\
                            -e DATABASE_URL="postgresql+psycopg2://${DB_USER}:${DB_PASSWORD}@perspectiva-db:5432/${DB_NAME}" \\
                            ${IMAGE_NAME}:${IMAGE_TAG} \\
                            alembic upgrade head || echo "Migration failed or not needed"
                        
                        # Start new application container
                        docker run -d \\
                            --name ${CONTAINER_NAME} \\
                            --network ${DOCKER_NETWORK} \\
                            -p ${APP_PORT}:8000 \\
                            -e DATABASE_URL="postgresql+psycopg2://${DB_USER}:${DB_PASSWORD}@perspectiva-db:5432/${DB_NAME}" \\
                            -e FEEDS="https://feeds.bbci.co.uk/news/rss.xml,https://rss.cnn.com/rss/edition.rss,https://www.reutersagency.com/feed/?best-topics=business-finance&post_type=best" \\
                            -e FETCH_INTERVAL_SECONDS=300 \\
                            -e MAX_ITEMS_PER_FEED=15 \\
                            -e SUMMARY_SENTENCES=3 \\
                            -e LOG_LEVEL=INFO \\
                            --restart unless-stopped \\
                            ${IMAGE_NAME}:${IMAGE_TAG}
                        
                        # Wait for application to be ready
                        echo "Waiting for application to be ready..."
                        for i in {1..30}; do
                            if curl -f http://localhost:${APP_PORT}/health; then
                                echo "Application is ready!"
                                break
                            fi
                            echo "Waiting for application... ($i/30)"
                            sleep 3
                        done
                    '''
                }
            }
        }
        
        stage('Health Check') {
            steps {
                script {
                    echo 'Performing health check...'
                    sh '''
                        # Check application health
                        curl -f http://localhost:${APP_PORT}/health
                        
                        # Check if container is running
                        docker ps | grep ${CONTAINER_NAME}
                        
                        # Show container logs (last 20 lines)
                        echo "Recent application logs:"
                        docker logs --tail 20 ${CONTAINER_NAME}
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
            echo 'Deployment successful! 🎉'
            echo "Application is running at: http://your-vps-ip:${APP_PORT}"
            echo "API documentation: http://your-vps-ip:${APP_PORT}/docs"
            
            // Clean up old images (keep last 3)
            sh '''
                echo "Cleaning up old Docker images..."
                docker images ${IMAGE_NAME} --format "table {{.Tag}}" | grep -v latest | grep -v TAG | tail -n +4 | xargs -r -I {} docker rmi ${IMAGE_NAME}:{} || true
            '''
        }
        
        failure {
            echo 'Deployment failed! ❌'
            
            // Show logs for debugging
            sh '''
                echo "Application container logs:"
                docker logs ${CONTAINER_NAME} || echo "No application container logs available"
                
                echo "Database container logs:"
                docker logs perspectiva-db || echo "No database container logs available"
            '''
        }
        
        cleanup {
            // Clean up workspace
            cleanWs()
        }
    }
}
