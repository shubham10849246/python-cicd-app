pipeline {
  agent { label 'python-ci' }

  options {
    timestamps()
    buildDiscarder(logRotator(numToKeepStr: '20'))
  }

  
parameters {
  booleanParam(name: 'SKIP_SONAR', defaultValue: true, description: 'Skip SonarQube + Quality Gate')
}


  environment {
    VENV_DIR = ".venv"
    PYTHONPATH = "${WORKSPACE}/src"
    IMAGE_NAME = "python-cicd-demo"
    REPORTS_DIR = "reports"
    SONAR_HOST_URL = "http://13.235.95.236:9000"
    SONAR_PROJECT_KEY = "python-cicd-demo"
    NEXUS_REGISTRY = "10.0.13.79:8082"
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
      env.TAG = "${env.BUILD_NUMBER}-${env.GIT_SHA}"
    }
    sh '''#!/bin/bash
      set -e
      echo "Building image: ${IMAGE_NAME}:${TAG}"
      docker build -t ${IMAGE_NAME}:${TAG} .
    '''
  }
}

stage('k6 Performance Test') {
  steps {
    sh '''#!/bin/bash
      set -euo pipefail

      # Run the newly built image
      CID=$(docker run -d -p 0:8080 --name ${IMAGE_NAME}-perf-${BUILD_NUMBER} ${IMAGE_NAME}:${TAG})

      # Always cleanup container even if test fails
      cleanup() { docker rm -f "$CID" >/dev/null 2>&1 || true; }
      trap cleanup EXIT

      # Find mapped host port (important: use 8080/tcp)
      HOST_PORT=$(docker port "$CID" 8080/tcp | awk -F: '{print $2}')
      echo "Container: $CID"
      echo "App URL: http://127.0.0.1:${HOST_PORT}"

      # Wait for health endpoint (max 30 seconds)
      for i in $(seq 1 30); do
        if curl -s http://127.0.0.1:${HOST_PORT}/health | grep -q UP; then
          echo "✅ App is UP"
          break
        fi
        echo "Waiting for app... ($i)"
        sleep 1
      done

      # Run k6 test (script is in repo root perf/)
      docker run --rm \
        -e TARGET_URL=http://127.0.0.1:${HOST_PORT} \
        -i grafana/k6 run - < perf/k6-script.js
    '''
  }
}

    stage('Push to ECR') {
  steps {
    withCredentials([usernamePassword(credentialsId: 'aws-ecr-creds',
      usernameVariable: 'AWS_ACCESS_KEY_ID',
      passwordVariable: 'AWS_SECRET_ACCESS_KEY'
    )]) {
      sh '''#!/bin/bash
        set -e
        export AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
        export AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
        export AWS_DEFAULT_REGION=ap-south-1

        ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
        ECR_REGISTRY="${ACCOUNT_ID}.dkr.ecr.${AWS_DEFAULT_REGION}.amazonaws.com"
        ECR_URI="${ECR_REGISTRY}/python-cicd-demo"

        aws ecr get-login-password --region ${AWS_DEFAULT_REGION} | docker login --username AWS --password-stdin ${ECR_REGISTRY}

        docker tag ${IMAGE_NAME}:${TAG} ${ECR_URI}:${TAG}
        docker push ${ECR_URI}:${TAG}

        echo "ECR_URI=${ECR_URI}" > ecr.env
        echo "TAG=${TAG}" >> ecr.env
      '''
    }
  }
}
   
    stage('CD: Update GitOps repo') {
  steps {
    withCredentials([usernamePassword(credentialsId: 'gitops-creds',
      usernameVariable: 'GIT_USER',
      passwordVariable: 'GIT_TOKEN'
    )]) {
      sh '''#!/bin/bash
        set -e
        source ecr.env

        rm -rf gitops
        git clone https://${GIT_USER}:${GIT_TOKEN}@github.com/shubham10849246/python-cicd-gitops.git gitops
        cd gitops

        sed -i "s|image:.*|image: ${ECR_URI}:${TAG}|g" deployment.yaml

        git config user.email "jenkins@ci.local"
        git config user.name "jenkins-ci"
        git add deployment.yaml
        git commit -m "Deploy ${TAG}" || true
        git push
      '''
    }
  }
}

    stage('SonarQube Scan') {
  when { expression { return !params.SKIP_SONAR } }
  steps {
    withSonarQubeEnv('sonar') {
      sh(label: 'Sonar Scan', script: '''#!/bin/bash
        set -euo pipefail

        mkdir -p .scannerwork .sonar

        docker run --rm \
          --user "$(id -u):$(id -g)" \
          --tmpfs /tmp:rw,exec,nosuid,size=1g,mode=1777 \
          -e SONAR_HOST_URL="$SONAR_HOST_URL" \
          -e SONAR_TOKEN="$SONAR_AUTH_TOKEN" \
          -e SONAR_USER_HOME="/tmp/sonar" \
          -v "$WORKSPACE:/usr/src" \
          -v "$WORKSPACE/.sonar:/tmp/sonar" \
          sonarsource/sonar-scanner-cli:latest \
          -Dsonar.projectKey=${SONAR_PROJECT_KEY} \
          -Dsonar.sources=src \
          -Dsonar.tests=tests \
          -Dsonar.python.version=3.10 \
          -Dsonar.python.coverage.reportPaths=reports/coverage.xml \
          -Dsonar.scanner.metadataFilePath=/usr/src/.scannerwork/report-task.txt

        ls -la .scannerwork || true
        cat .scannerwork/report-task.txt || true
      ''')
    }
  }
}

    stage('Quality Gate') {
  when { expression { return !params.SKIP_SONAR } }
  steps {
    timeout(time: 15, unit: 'MINUTES') {
      waitForQualityGate abortPipeline: true
    }
  }
}

 
    stage('Push to Nexus') {
  steps {
    withCredentials([usernamePassword(credentialsId: 'nexus-docker',
      usernameVariable: 'NEXUS_USER',
      passwordVariable: 'NEXUS_PASS')]) {

      sh '''#!/bin/bash
        set -e

        echo "$NEXUS_PASS" | docker login -u "$NEXUS_USER" --password-stdin ${NEXUS_REGISTRY}

        # Tag as registry/image:tag (no repo name in path)
        docker tag ${IMAGE_NAME}:${TAG} ${NEXUS_REGISTRY}/${IMAGE_NAME}:${TAG}

        docker push ${NEXUS_REGISTRY}/${IMAGE_NAME}:${TAG}

        docker logout ${NEXUS_REGISTRY} || true
      '''
    }
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
