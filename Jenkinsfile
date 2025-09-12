pipeline {
    agent any

    environment {
        REGISTRY      = "your-docker-registry.com"
        IMAGE_NAME    = "perspectiva"
        IMAGE_TAG     = "latest"
        CONTAINER_IMG = "${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Build Docker Image') {
            steps {
                script {
                    docker.build("${CONTAINER_IMG}", "-f Dockerfile .")
                }
            }
        }

        stage('Run Tests') {
            steps {
                script {
                    docker.image("${CONTAINER_IMG}").inside {
                        sh 'pytest -q --disable-warnings || true'
                    }
                }
            }
        }

        stage('Push to Registry') {
            when {
                branch 'main'
            }
            steps {
                script {
                    docker.withRegistry("https://${REGISTRY}", 'docker-credentials-id') {
                        docker.image("${CONTAINER_IMG}").push()
                    }
                }
            }
        }

        stage('Deploy') {
            when {
                branch 'main'
            }
            steps {
                // Example deployment script — adapt for your environment
                sh '''
                echo "Deploying ${CONTAINER_IMG} ..."
                # Example: Docker Compose or Kubernetes apply
                # docker-compose -f docker-compose.prod.yml up -d
                '''
            }
        }
    }

    post {
        always {
            echo 'Cleaning up...'
            sh 'docker system prune -f || true'
        }
    }
}
