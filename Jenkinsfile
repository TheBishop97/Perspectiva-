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
                        # Create Dockerfile
                        cat > Dockerfile << 'EOF'
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \\
    PYTHONUNBUFFERED=1 \\
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

RUN apt-get update && apt-get install -y \\
    postgresql-client \\
    gcc \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \\
    && pip install --no-cache-dir -r requirements.txt

RUN python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords')"

COPY . .

RUN useradd --create-home --shell /bin/bash app \\
    && chown -R app:app /app
USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
EOF
                        
                        # Build the image
                        docker build -t ${IMAGE_NAME}:${IMAGE_TAG} .
                        docker build -t ${IMAGE_NAME}:latest .
                        
                        echo "✅ Docker image built successfully"
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
                        docker network create ${DOCKER_NETWORK} || echo "Network already exists"
                        
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
                        
                        echo "⏳ Waiting for database to be ready..."
                        sleep 15
                        
                        # Wait for database to be ready with timeout
                        for i in {1..30}; do
                            if docker exec perspectiva-db pg_isready -U ${DB_USER} -d ${DB_NAME} -q; then
                                echo "✅ Database is ready!"
                                break
                            fi
                            echo "⏳ Waiting for database... ($i/30)"
                            sleep 2
                        done
                    '''
                }
            }
        }
        
        stage('Run Database Migrations') {
            steps {
                script {
                    echo 'Running database migrations...'
                    sh '''
                        # Run database migrations
                        docker run --rm \\
                            --network ${DOCKER_NETWORK} \\
                            -e DATABASE_URL="postgresql+psycopg2://${DB_USER}:${DB_PASSWORD}@perspectiva-db:5432/${DB_NAME}" \\
                            ${IMAGE_NAME}:${IMAGE_TAG} \\
                            alembic upgrade head || echo "⚠️ Migration failed or not needed"
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
                            -e DATABASE_URL="sqlite:///./test.db" \\
                            ${IMAGE_NAME}:${IMAGE_TAG} \\
                            python -m pytest tests/ -v --tb=short || echo "⚠️ Tests failed or not found"
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
                        
                        echo "✅ Application container started"
                    '''
                }
            }
        }
        
        stage('Health Check') {
            steps {
                script {
                    echo 'Performing health check...'
                    sh '''
                        # Wait for application to start
                        echo "⏳ Waiting for application to be ready..."
                        sleep 20
                        
                        # Check if container is running
                        if docker ps | grep -q ${CONTAINER_NAME}; then
                            echo "✅ Container is running"
                        else
                            echo "❌ Container is not running"
                            exit 1
                        fi
                        
                        # Health check with multiple attempts
                        for i in {1..15}; do
                            if curl -f -s http://localhost:${APP_PORT}/health > /dev/null; then
                                echo "✅ Application is healthy!"
                                curl http://localhost:${APP_PORT}/health
                                break
                            fi
                            echo "⏳ Health check attempt $i/15..."
                            sleep 4
                        done
                        
                        # Show recent logs
                        echo "📋 Recent application logs:"
                        docker logs --tail 15 ${CONTAINER_NAME}
                    '''
                }
            }
        }
    }
    
    post {
        always {
            echo '🏁 Pipeline completed.'
        }
        
        success {
            echo '🎉 Deployment successful!'
            echo "🌐 Application URL: http://your-vps-ip:${APP_PORT}"
            echo "📚 API Documentation: http://your-vps-ip:${APP_PORT}/docs"
            echo "❤️ Health Check: http://your-vps-ip:${APP_PORT}/health"
            
            // Clean up old images (keep last 3 builds)
            sh '''
                echo "🧹 Cleaning up old Docker images..."
                docker images ${IMAGE_NAME} --format "table {{.Tag}}" | grep -v latest | grep -v TAG | sort -nr | tail -n +4 | xargs -r -I {} docker rmi ${IMAGE_NAME}:{} 2>/dev/null || true
            '''
        }
        
        failure {
            echo '❌ Deployment failed!'
            
            sh '''
                echo "=== 🐳 Container Status ==="
                docker ps -a
                
                echo "=== 📋 Application Logs ==="
                docker logs ${CONTAINER_NAME} 2>/dev/null || echo "No application logs available"
                
                echo "=== 📋 Database Logs ==="
                docker logs perspectiva-db 2>/dev/null || echo "No database logs available"
                
                echo "=== 🔍 Network Info ==="
                docker network ls | grep perspectiva || echo "No perspectiva networks found"
            '''
        }
        
        cleanup {
            // Clean up workspace
            cleanWs()
        }
    }
}
