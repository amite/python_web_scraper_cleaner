# Google Cloud Run Deployment Guide

This guide provides step-by-step instructions for deploying the Trafilatura Scraper API to Google Cloud Run.

## Prerequisites

- Google Cloud account with billing enabled
- Basic familiarity with command line interfaces

## Step 1: Install Google Cloud CLI

### On Linux/macOS:
```bash
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
gcloud init
```

### On Windows:
Download and install from: https://cloud.google.com/sdk/docs/install

## Step 2: Authenticate with Google Cloud

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

## Step 3: Enable Required APIs

```bash
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
```
## Artifact Registry

The command we used above to first interact with your **Artifact Registry** repository was:

```bash
gcloud artifacts repositories create scraper-repo \
    --repository-format=docker \
    --location=asia-south1 \
    --description="Repository for scraper microservice"
```

### Purpose of This Command

This command served a critical setup function:

1.  **Creating the Repository:** It established the dedicated, named storage area (`scraper-repo`) within your Google Cloud project. This repository is where your Docker images are securely stored.
2.  **Specifying Format:** The `--repository-format=docker` flag confirmed that this repository is specifically designed to hold **Docker container images**.
3.  **Defining Location:** The `--location=asia-south1` flag ensured the repository was created in the same regional location where you planned to deploy your Cloud Run service, which is generally a best practice for lower latency.

Essentially, before you could **build** and **push** your image, you first had to create the **destination** for that image—the repository in **Artifact Registry**.

## build your Docker image and push it

The next step after interacting with the **Artifact Registry** (by running `gcloud artifacts repositories create scraper-repo...`) was to **build your Docker image and push it** to that newly created repository.

This step utilizes **Google Cloud Build** to execute the instructions in your `Dockerfile`.


That's right, we absolutely interacted with **Secret Manager**! It was a critical component of the deployment. You also correctly recalled that there was a common "bug" or permission issue that needed resolving during the deployment.

Here is a breakdown of our interactions with **Secret Manager** and the specific issue we had to fix.

---

## 🔒 Interacting with Secret Manager

We interacted with Secret Manager in two distinct steps:

### 1. Creation and Storage (Phase 2)
This step created the secret vault entry and stored your key value.

| Command | Role |
| :--- | :--- |
| `printf "your-super-secret-value" | gcloud secrets create scraper-api-key --data-file=-` | This command **created** the secret named `scraper-api-key` and stored the sensitive string as its initial version. |

### 2. Retrieval and Injection (Phase 4)
This step linked the stored secret to your running container.

| Command Segment | Role |
| :--- | :--- |
| `--set-secrets="SECRET_KEY=scraper-api-key:latest"` | This flag, part of the `gcloud run deploy` command, told Cloud Run: "Take the value from the latest version of the secret named `scraper-api-key` in Secret Manager, and inject it into the container as the environment variable named **`SECRET_KEY`**." |

---

### 🐛 The Permission Issue ("The Bug")

The issue we had to resolve is a very common security roadblock when first deploying to Cloud Run, and it deals with **Identity and Access Management (IAM)** permissions.

#### The Problem

During the **Deployment** step (Phase 4), the **Cloud Run Service Agent** (which is a Google-managed account that runs your service) is trying to retrieve the secret's value from **Secret Manager**. By default, for security reasons, it does **not** have permission to read your secrets.

If we had ignored this, the deployment would have failed, or the secret environment variable (`SECRET_KEY`) would have been empty inside your container.

#### The Resolution

The fix involved explicitly granting permission to the service account.

1.  We identified the email address of the **Cloud Run Service Account** (the "who" that needs permission).
2.  We navigated to **Secret Manager** in the console.
3.  We added an IAM Policy Binding for that service account, assigning it the **`Secret Manager Secret Accessor`** role.

This action resolved the "bug" by granting the Cloud Run runtime the necessary, minimal permission to fetch that one specific secret's value during deployment.

The interaction with **Secret Manager** had to happen **before** building the container image, but the secret's value is only **accessed** by the service *after* the container image is deployed.

Here is why that distinction matters:

### 1. **Interaction Before Image Build (Setup)**

You must create the secret in Secret Manager **before** you build your container image.

* **Action:** `gcloud secrets create scraper-api-key...`
* **Reason:** Your Python code (`api/main.py`) expects the environment variable `SECRET_KEY` to be available. While the container build itself **doesn't need the secret's value**, the infrastructure around the application needs to be in place. It's best practice to complete all infrastructure setup (like creating the secret vault) before packaging the application code.

### 2. **No Secret in the Image (Security)**

Crucially, **the container image is built without the secret's value inside it.**

* **Input to Build:** Your code only contains the instruction `SECRET_KEY = os.getenv("SECRET_KEY")`. It looks for the key but doesn't contain the key itself.
* **Result:** The container image is a "clean" bundle of code that is **safe to store** in Artifact Registry because it contains no sensitive data.

### 3. **Value Access After Deployment (Runtime)**

The secret's actual value is only introduced when the container is run by Cloud Run.

* **Action:** `gcloud run deploy ... --set-secrets="SECRET_KEY=scraper-api-key:latest"`
* **Reason:** Cloud Run uses the `--set-secrets` flag to retrieve the key from Secret Manager at **deployment time** and inject it into the **running container instance** as an environment variable. This is the **most secure pattern** because the secret exists only in the secure Secret Manager and in the container's volatile memory, never on the disk or in the container image file.

## 📦 Next Step: Build and Push the Container Image

The specific command for this was:

```bash
gcloud builds submit --tag asia-south1-docker.pkg.dev/PROJECT_ID/scraper-repo/scraper-api:v1
```

### What This Step Accomplished:

1.  **Source Submission:** The `gcloud builds submit` command zips up your local source code (including your `Dockerfile`, `main.py`, `trafilatura_scraper.py`, and `pyproject.toml`) and securely sends it to the **Cloud Build** service.
2.  **Image Creation:** Cloud Build reads your `Dockerfile` and executes all the commands (like installing `uv` and your Python dependencies) to create the final, static **Container Image**.
3.  **Tagging:** The `--tag` flag applies a recognizable label (`scraper-api:v1`) to the image.
4.  **Pushing:** After the build is successful, Cloud Build automatically pushes the resulting image to the specified destination: your **Artifact Registry** repository (`scraper-repo`).

Once this command finished, your application was successfully packaged and ready to be deployed.

The step immediately after your application was successfully packaged and ready to be deployed (i.e., after the `gcloud builds submit` command) was the **deployment of the service itself to Cloud Run**.

This is the final command that takes the static container image and makes it a live, scalable microservice.

The commands we used were:

## 1\. Deploying the Service and Injecting Secrets

This is the central command for launching your microservice.

```bash
gcloud run deploy scraper-api \
    --image asia-south1-docker.pkg.dev/$(gcloud config get-value project)/scraper-repo/scraper-api:v1 \
    --region asia-south1 \
    --port 8001 \
    --allow-unauthenticated \
    --set-secrets="SECRET_KEY=scraper-api-key:latest"
```

| Component of Command | Action / Role |
| :--- | :--- |
| `gcloud run deploy scraper-api` | **Creates the Cloud Run Service** named `scraper-api`. This service gets a permanent public URL. |
| `--image .../scraper-api:v1` | **Specifies the Image:** Tells Cloud Run which **Container Image** to pull from **Artifact Registry** to run. |
| `--region asia-south1` | **Sets the Location:** Defines the GCP region where the serverless infrastructure will run. |
| `--port 8001` | **Defines Ingress:** Tells the Cloud Run runtime that your internal `uvicorn` process is listening on port `8001`. |
| `--allow-unauthenticated` | **Sets Policy:** Makes the service publicly accessible via its URL (relying on your FastAPI logic to enforce security via JWT tokens). |
| `--set-secrets="SECRET_KEY=..."` | **Injects Secret:** Instructs Cloud Run to connect to **Secret Manager** and inject the secret's value as the container's `SECRET_KEY` environment variable at runtime. |

-----

## 2\. Resolving the Deployment Permission Issue

As a crucial sub-step during or immediately after the first deployment attempt, we had to resolve the permission error for Secret Manager access.

| Action Taken | Role |
| :--- | :--- |
| **IAM Policy Update** | We granted the `Secret Manager Secret Accessor` role to the Cloud Run Service Account. |

This allowed the Cloud Run runtime to successfully fetch the value of `scraper-api-key` and complete the deployment.

After these steps, the command line provided your public service URL, and the deployment was complete.

## Step 7: Access Your API

After deployment completes, you'll receive a service URL. You can access:

- API Documentation: `https://YOUR_SERVICE_URL/docs`
- Health Check: `https://YOUR_SERVICE_URL/health`
- Root Endpoint: `https://YOUR_SERVICE_URL/`

## Troubleshooting

- Check logs: `gcloud logging read "resource.type=cloud_run_revision" --limit 50`
- View service details: `gcloud run services describe trafilatura-scraper-api --region asia-south1`

## Notes

- Replace `YOUR_PROJECT_ID` with your actual Google Cloud project ID
- The service will automatically scale based on traffic
- Cloud Run has cold start times - consider minimum instances if low latency is critical