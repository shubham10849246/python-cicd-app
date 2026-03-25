pipeline {
  agent { label 'python-ci' }

  options {
    timestamps()
    buildDiscarder(logRotator(numToKeepStr: '20'))
  }

  environment {
    // Keep everything inside workspace
    VENV_DIR = ".venv"
    PYTHONPATH = "${WORKSPACE}/src"
    IMAGE_NAME = "python-cicd-demo"
    REPORTS_DIR = "reports"
  }

  stages {

    stage('Checkout') {
      steps {
        checkout scm
        sh '''
          echo "Workspace: $WORKSPACE"
          ls -la
          python3 --version
          docker --version
        '''
      }
    }

    stage('Create Virtualenv + Install Dependencies') {
      steps {
        sh '''
          set -e
          python3 -m venv ${VENV_DIR}
          . ${VENV_DIR}/bin/activate

          python -m pip install --upgrade pip
          pip install -r requirements.txt -r requirements-dev.txt

          mkdir -p ${REPORTS_DIR}
        '''
      }
    }

    stage('Build Wheel Artifact') {
      steps {
        sh '''
          set -e
          . ${VENV_DIR}/bin/activate

          python -m build
          ls -lah dist/
        '''
      }
      post {
        success {
          archiveArtifacts artifacts: 'dist/*.whl', fingerprint: true
        }
      }
    }

    stage('Unit Tests') {
      steps {
        sh '''
          set -e
          . ${VENV_DIR}/bin/activate

          export PYTHONPATH=${PYTHONPATH}
          pytest -q tests/unit \
            --junitxml=${REPORTS_DIR}/unit-junit.xml \
            --cov=app \
            --cov-report=xml:${REPORTS_DIR}/coverage.xml
        '''
      }
      post {
        always {
          junit allowEmptyResults: true, testResults: 'reports/unit-junit.xml'
          archiveArtifacts artifacts: 'reports/coverage.xml', allowEmptyArchive: true
        }
      }
    }

    stage('Functional Tests') {
      steps {
        sh '''
          set -e
          . ${VENV_DIR}/bin/activate

          export PYTHONPATH=${PYTHONPATH}
          pytest -q tests/functional \
            --junitxml=${REPORTS_DIR}/functional-junit.xml
        '''
      }
      post {
        always {
          junit allowEmptyResults: true, testResults: 'reports/functional-junit.xml'
        }
      }
    }

    stage('Docker Build') {
      steps {
        script {
          env.GIT_SHA = sh(script: "git rev-parse --short HEAD", returnStdout: true).trim()
          env.IMAGE_TAG = "${env.BUILD_NUMBER}-${env.GIT_SHA}"
        }
        sh '''
          set -e
          echo "Building image: ${IMAGE_NAME}:${IMAGE_TAG}"
          docker build -t ${IMAGE_NAME}:${IMAGE_TAG} .
          docker images | head
        '''
      }
    }

    stage('k6 Performance Test (auto start/stop container)') {
      steps {
        sh '''
          set -e

          # Start container on random free port
          CID=$(docker run -d -p 0:8080 --name ${IMAGE_NAME}-perf-${BUILD_NUMBER} ${IMAGE_NAME}:${IMAGE_TAG})

          # Get mapped host port for container 8080
          HOST_PORT=$(docker port $CID 8080/tcp | awk -F: '{print $2}')
          echo "Container started: $CID"
          echo "App is available at: http://127.0.0.1:${HOST_PORT}"

          # Wait until app is healthy (max 30 seconds)
          for i in $(seq 1 30); do
            if curl -s http://127.0.0.1:${HOST_PORT}/health | grep -q UP; then
              echo "✅ App is UP"
              break
            fi
            echo "Waiting for app... ($i)"
            sleep 1
          done

          # Run k6 using docker (no need to install k6 on agent)
          docker run --rm \
            -e TARGET_URL=http://127.0.0.1:${HOST_PORT} \
            -i grafana/k6 run - < perf/k6-script.js

          # Stop and remove container
          docker rm -f $CID
        '''
      }
      post {
        always {
          // Extra safety cleanup if container still exists
          sh '''
            docker rm -f ${IMAGE_NAME}-perf-${BUILD_NUMBER} >/dev/null 2>&1 || true
          '''
        }
      }
    }
  }

  post {
    success {
      echo "✅ CI completed (wheel + tests + perf) successfully."
      echo "Next we will add Sonar, Nexus, JFrog, ArgoCD stages."
    }
    failure {
      echo "❌ Pipeline failed. Check stage logs for exact reason."
    }
    always {
      // Clean workspace venv to save disk if needed
      sh 'rm -rf ${VENV_DIR} || true'
    }
  }
}
