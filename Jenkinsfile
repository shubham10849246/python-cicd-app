pipeline {
  agent { label 'python-ci' }

  options {
    timestamps()
    buildDiscarder(logRotator(numToKeepStr: '20'))
  }

  environment {
    VENV_DIR = ".venv"
    PYTHONPATH = "${WORKSPACE}/src"
    IMAGE_NAME = "python-cicd-demo"
    REPORTS_DIR = "reports"
    SONAR_HOST_URL = "http://13.235.95.236:9000"
    SONAR_PROJECT_KEY = "python-cicd-demo"
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
          pip install --upgrade pip
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
          pytest tests/unit \
            --junitxml=reports/unit-junit.xml \
            --cov=app \
            --cov-report=xml:reports/coverage.xml \
            --cov-config=.coveragerc
        '''
      }
      post {
        always {
          junit testResults: 'reports/unit-junit.xml', allowEmptyResults: true
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
          pytest tests/functional \
            --junitxml=${REPORTS_DIR}/functional-junit.xml
        '''
      }
      post {
        always {
          junit testResults: 'reports/functional-junit.xml', allowEmptyResults: true
        }
      }
    }

    stage('Docker Build') {
      steps {
        script {
          env.GIT_SHA = sh(script: "git rev-parse --short HEAD", returnStdout: true).trim()
          env.IMAGE_TAG = "${BUILD_NUMBER}-${GIT_SHA}"
        }
        sh '''
          set -e
          docker build -t ${IMAGE_NAME}:${IMAGE_TAG} .
        '''
      }
    }

    stage('k6 Performance Test') {
      steps {
        sh '''
          set -e
          CID=$(docker run -d -p 0:8080 --name ${IMAGE_NAME}-perf-${BUILD_NUMBER} ${IMAGE_NAME}:${IMAGE_TAG})
          HOST_PORT=$(docker port $CID 8080 | awk -F: '{print $2}')

          for i in $(seq 1 30); do
            curl -s http://127.0.0.1:${HOST_PORT}/health && break
            sleep 1
          done

          docker run --rm \
            -e TARGET_URL=http://127.0.0.1:${HOST_PORT} \
            -i grafana/k6 run - < perf/k6-script.js

          docker rm -f $CID
        '''
      }
    }

    stage('SonarQube Scan') {
      steps {
        withSonarQubeEnv('sonar') {
          sh '''
            docker run --rm \
              -e SONAR_HOST_URL=$SONAR_HOST_URL \
              -e SONAR_TOKEN=$SONAR_AUTH_TOKEN \
              -v "$WORKSPACE:/usr/src" \
              sonarsource/sonar-scanner-cli \
              -Dsonar.projectKey=${SONAR_PROJECT_KEY} \
              -Dsonar.sources=src \
              -Dsonar.tests=tests \
              -Dsonar.python.coverage.reportPaths=reports/coverage.xml
          '''
        }
      }
    }

    stage('Quality Gate') {
      steps {
        timeout(time: 5, unit: 'MINUTES') {
          waitForQualityGate abortPipeline: true
        }
      }
    }
  }

  post {
    success {
      echo "✅ CI completed successfully"
    }
    failure {
      echo "❌ Pipeline failed"
    }
    always {
      sh 'rm -rf ${VENV_DIR} || true'
    }
  }
}
