from fastapi import FastAPI, HTTPException, status, Depends, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
import logging
from typing import Optional, Dict, Any
import importlib.util
import sys
import os
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext

# Import the scraper functions
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

# Import trafilatura_scraper functions
spec = importlib.util.spec_from_file_location("trafilatura_scraper", os.path.join(parent_dir, "trafilatura_scraper.py"))
if spec is None:
    raise ImportError("Could not create module specification for trafilatura_scraper")
if spec.loader is None:
    raise ImportError("Module specification has no loader for trafilatura_scraper")
trafilatura_scraper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trafilatura_scraper)

# Security configuration
SECRET_KEY = "your-secret-key-here"  # In production, use a proper secret key from environment variables
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

app = FastAPI(
    title="Trafilatura Scraper API",
    description="API for scraping articles using Trafilatura",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Add CORS headers middleware
@app.middleware("http")
async def add_cors_headers(request, call_next):
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "*"
    return response

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('api.log'),
        logging.StreamHandler()
    ]
)

class ScrapeRequest(BaseModel):
    url: str
    include_raw_text: bool = True
    include_metadata: bool = True

# User model for authentication
class User(BaseModel):
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: Optional[bool] = None

class UserInDB(User):
    hashed_password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class ScrapeResponse(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    text_content: Optional[str] = None
    error: Optional[str] = None
    url: str

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Trafilatura Scraper API",
        "version": "1.0.0",
        "endpoints": {
            "/scrape": "POST - Scrape a URL",
            "/batch-scrape": "POST - Scrape multiple URLs",
            "/health": "GET - Health check"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "trafilatura-scraper-api"}

@app.post("/scrape", response_model=ScrapeResponse)
async def scrape_article(request: ScrapeRequest):
    """Scrape an article from a URL using Trafilatura"""
    try:
        logging.info(f"Received scrape request for URL: {request.url}")

        # Call the scraper function
        article_data, text_content = trafilatura_scraper.scrape_article_with_trafilatura(request.url)

        if article_data is None:
            logging.error(f"Scraping failed for {request.url}: {text_content}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=text_content
            )

        logging.info(f"Successfully scraped article from {request.url}")

        # Prepare response
        response_data = {
            "success": True,
            "data": article_data,
            "text_content": text_content if request.include_raw_text else None,
            "error": None,
            "url": request.url
        }

        return response_data

    except HTTPException:
        # Re-raise HTTPExceptions as they are already properly formatted
        raise
    except Exception as e:
        error_msg = f"Error scraping URL {request.url}: {str(e)}"
        logging.error(error_msg)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg
        )

# Authentication utilities
def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str):
    return pwd_context.hash(password)

def get_user(db, username: str):
    if username in db:
        user_dict = db[username]
        return UserInDB(**user_dict)
    return None

def authenticate_user(fake_db, username: str, password: str):
    user = get_user(fake_db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception

    # In a real application, you would get the user from a database
    fake_users_db = {
        "testuser": {
            "username": "testuser",
            "full_name": "Test User",
            "email": "test@example.com",
            "hashed_password": get_password_hash("testpassword"),
            "disabled": False,
        }
    }

    if token_data.username is None:
        raise credentials_exception

    user = get_user(fake_users_db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

# Add authentication endpoints
@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    # Mock user database - in production, this would be a real database
    fake_users_db = {
        "testuser": {
            "username": "testuser",
            "full_name": "Test User",
            "email": "test@example.com",
            "hashed_password": get_password_hash("testpassword"),
            "disabled": False,
        }
    }

    user = authenticate_user(fake_users_db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}


# Add batch processing endpoint
class BatchScrapeRequest(BaseModel):
    urls: list[str]
    include_raw_text: bool = True
    include_metadata: bool = True

@app.post("/batch-scrape", response_model=list[ScrapeResponse])
async def batch_scrape_articles(request: BatchScrapeRequest):
    """Scrape multiple articles from URLs using Trafilatura"""
    results = []

    for url in request.urls:
        try:
            logging.info(f"Processing batch scrape request for URL: {url}")

            # Call the scraper function
            article_data, text_content = trafilatura_scraper.scrape_article_with_trafilatura(url)

            if article_data is None:
                logging.error(f"Scraping failed for {url}: {text_content}")
                results.append({
                    "success": False,
                    "data": None,
                    "text_content": None,
                    "error": f"Scraping failed: {text_content}",
                    "url": url
                })
                continue

            logging.info(f"Successfully scraped article from {url}")

            # Prepare response
            response_data = {
                "success": True,
                "data": article_data,
                "text_content": text_content if request.include_raw_text else None,
                "error": None,
                "url": url
            }

            results.append(response_data)

        except Exception as e:
            error_msg = f"Error scraping URL {url}: {str(e)}"
            logging.error(error_msg)
            results.append({
                "success": False,
                "data": None,
                "text_content": None,
                "error": error_msg,
                "url": url
            })

    return results

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)