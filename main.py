#!/usr/bin/env python3
"""
AWS MCP Proxy for Copilot Studio
A FastAPI proxy that bridges Microsoft Copilot Studio with AWS-hosted MCP servers.
Handles authentication, request forwarding, and response formatting for MCP protocol.
"""
import json
import logging
import os
import time
from typing import Any, Dict

import httpx
import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# AWS Configuration from environment variables
AUTH_URL = os.getenv("AWS_AUTH_URL")
MCP_SERVER_URL = os.getenv("AWS_MCP_URL")
CLIENT_ID = os.getenv("AWS_CLIENT_ID")
CLIENT_SECRET = os.getenv("AWS_CLIENT_SECRET")
SCOPE = os.getenv("AWS_SCOPE")

# Validate required environment variables
required_env_vars = {
    "AWS_AUTH_URL": AUTH_URL,
    "AWS_MCP_URL": MCP_SERVER_URL,
    "AWS_CLIENT_ID": CLIENT_ID,
    "AWS_CLIENT_SECRET": CLIENT_SECRET,
    "AWS_SCOPE": SCOPE
}

missing_vars = [var for var, value in required_env_vars.items() if not value]
if missing_vars:
    logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
    raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

logger.info("AWS configuration loaded successfully")

# Token cache
access_token_cache = {"token": None, "expires_at": 0}

# Create FastAPI app
app = FastAPI(
    title="AWS MCP Proxy",
    description="Proxy server for AWS-hosted MCP servers in Copilot Studio",
    version="1.0.0",
    docs_url="/docs" if os.getenv("ENVIRONMENT") == "development" else None,
    redoc_url=None
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)


async def get_access_token() -> str:
    """Get access token from AWS Cognito with caching"""
    current_time = time.time()
    
    # Check if we have a valid cached token
    if (access_token_cache["token"] and 
        access_token_cache["expires_at"] > current_time + 60):
        return access_token_cache["token"]
    
    try:
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "grant_type": "client_credentials",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "scope": SCOPE
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(AUTH_URL, headers=headers, data=data)
            response.raise_for_status()
            
            token_data = response.json()
            access_token = token_data.get("access_token")
            expires_in = token_data.get("expires_in", 3600)
            
            # Cache the token
            access_token_cache["token"] = access_token
            access_token_cache["expires_at"] = current_time + expires_in
            
            logger.info("Access token refreshed successfully")
            return access_token
            
    except Exception as e:
        logger.error(f"Failed to get access token: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")


async def call_aws_mcp_server(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Forward request to AWS MCP server with authentication"""
    token = await get_access_token()
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream"
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(MCP_SERVER_URL, headers=headers, json=request_data)
            
            # AWS MCP server can return 200 (OK) or 202 (Accepted)
            if response.status_code not in [200, 202]:
                logger.error(f"AWS MCP server error: {response.status_code} - {response.text}")
                raise HTTPException(
                    status_code=response.status_code, 
                    detail=f"AWS MCP server error: {response.text}"
                )
            
            # Handle empty responses (valid for notifications)
            response_text = response.text.strip()
            if not response_text:
                logger.debug("Empty response from AWS MCP server (valid for notifications)")
                return {"jsonrpc": "2.0", "result": None}
            
            # Parse response based on content type
            content_type = response.headers.get('content-type', '')
            
            if 'text/event-stream' in content_type:
                # Parse Server-Sent Events format
                for line in response_text.split('\n'):
                    if line.startswith('data: '):
                        json_data = line[6:]  # Remove 'data: ' prefix
                        if json_data and json_data != '[DONE]':
                            try:
                                return json.loads(json_data)
                            except json.JSONDecodeError:
                                continue
                raise HTTPException(status_code=500, detail="Invalid SSE response from AWS MCP server")
            else:
                # Regular JSON response
                try:
                    return response.json()
                except json.JSONDecodeError:
                    if not response_text:
                        return {"jsonrpc": "2.0", "result": None}
                    raise HTTPException(status_code=500, detail="Invalid JSON response from AWS MCP server")
                
    except httpx.TimeoutException:
        logger.error("Timeout calling AWS MCP server")
        raise HTTPException(status_code=504, detail="AWS MCP server timeout")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error calling AWS MCP server: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/mcp")
async def mcp_endpoint(request: Request):
    """Main MCP endpoint for Copilot Studio integration"""
    try:
        body = await request.body()
        
        if not body:
            raise HTTPException(status_code=400, detail="Empty request body")
            
        # Parse and validate MCP request
        try:
            request_data = json.loads(body)
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")
        
        # Basic MCP validation
        if not isinstance(request_data, dict):
            raise HTTPException(status_code=400, detail="Request must be a JSON object")
        if "jsonrpc" not in request_data:
            raise HTTPException(status_code=400, detail="Missing jsonrpc field")
        if "method" not in request_data:
            raise HTTPException(status_code=400, detail="Missing method field")
        
        # Forward to AWS MCP server
        response_data = await call_aws_mcp_server(request_data)
        return JSONResponse(content=response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in MCP endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/mcp")
async def mcp_get_not_allowed():
    """GET not allowed on MCP endpoint"""
    return JSONResponse(
        status_code=405,
        content={
            "jsonrpc": "2.0",
            "error": {"code": -32000, "message": "Method not allowed."},
            "id": None
        }
    )


@app.delete("/mcp")
async def mcp_delete_not_allowed():
    """DELETE not allowed on MCP endpoint"""
    return JSONResponse(
        status_code=405,
        content={
            "jsonrpc": "2.0",
            "error": {"code": -32000, "message": "Method not allowed."},
            "id": None
        }
    )


@app.get("/")
async def health_check():
    """Health check endpoint for Azure Container Apps"""
    return {"status": "healthy", "service": "AWS MCP Proxy"}


@app.get("/health")
async def detailed_health_check():
    """Detailed health check with AWS authentication test"""
    try:
        await get_access_token()
        return {"status": "healthy", "aws_auth": "ok"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")


if __name__ == "__main__":
    port = int(os.getenv("PORT", 3000))
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
