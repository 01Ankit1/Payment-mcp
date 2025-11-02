import json
import logging
from fastapi import HTTPException, Request
from fastapi.security import HTTPBearer
from fastapi.responses import JSONResponse
from scalekit import ScalekitClient
from scalekit.common.scalekit import TokenValidationOptions
from starlette.middleware.base import BaseHTTPMiddleware


from src.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Security scheme for Bearer token
security = HTTPBearer()

# ScaleKit client will be initialized lazily (only when needed)
_scalekit_client = None

def get_scalekit_client():
    """Get or create the ScaleKit client instance (lazy initialization)."""
    global _scalekit_client
    if _scalekit_client is None:
        _scalekit_client = ScalekitClient(
            settings.SCALEKIT_ENVIRONMENT_URL,
            settings.SCALEKIT_CLIENT_ID,
            settings.SCALEKIT_CLIENT_SECRET
        )
    return _scalekit_client


# Authentication middleware
class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Skip auth for well-known endpoints
        if request.url.path.startswith("/.well-known/"):
            return await call_next(request)
        
        # Skip auth for GET requests (health checks, pre-flight checks)
        if request.method == "GET":
            return await call_next(request)

        try:
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                raise HTTPException(status_code=401, detail="Missing or invalid authorization header")

            token = auth_header.split(" ")[1]

            # Read request body once
            request_body = await request.body()
            
            # Log request details for debugging
            logger.info(f"Request to {request.url.path}: method={request.method}, body_length={len(request_body)}")
            if request_body:
                try:
                    body_str = request_body.decode('utf-8')
                    logger.debug(f"Request body: {body_str[:200]}")  # Log first 200 chars
                except:
                    logger.debug(f"Request body (binary): {len(request_body)} bytes")

            # Parse JSON from bytes for auth checks
            try:
                request_data = json.loads(request_body.decode('utf-8')) if request_body else {}
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                logger.warning(f"Failed to parse request body as JSON: {str(e)}")
                request_data = {}

            validation_options = TokenValidationOptions(
                issuer=settings.SCALEKIT_ENVIRONMENT_URL,
                audience=[settings.SCALEKIT_AUDIENCE_NAME],
            )

            is_tool_call = request_data.get("method") == "tools/call"

            required_scopes = []
            if is_tool_call:
                required_scopes = ["search:read"]  # get required scope for your tool
                validation_options.required_scopes = required_scopes

            try:
                scalekit_client = get_scalekit_client()
                scalekit_client.validate_token(token, options=validation_options)
            except Exception as e:
                logger.error(f"Token validation failed: {str(e)}")
                raise HTTPException(status_code=401, detail="Token validation failed")

            # Restore the request body so downstream handlers can read it
            # Replace the request's _receive to replay body
            body_sent = [False]  # Use list for mutable in closure
            
            async def receive_wrapper():
                if not body_sent[0]:
                    body_sent[0] = True
                    return {"type": "http.request", "body": request_body}
                return {"type": "http.request", "body": b""}
            
            request._receive = receive_wrapper

            # Call next middleware/handler
            response = await call_next(request)
            
            # Log response for debugging
            if hasattr(response, 'status_code') and response.status_code >= 400:
                logger.warning(f"Request to {request.url.path} returned status {response.status_code}")
            
            return response

        except HTTPException as e:
            logger.warning(f"HTTPException: {e.status_code} - {e.detail} for path {request.url.path}")
            return JSONResponse(
                status_code=e.status_code,
                content={"error": "unauthorized" if e.status_code == 401 else "forbidden",
                         "error_description": e.detail},
                headers={
                    "WWW-Authenticate": f'Bearer realm="OAuth", resource_metadata="{settings.SCALEKIT_RESOURCE_METADATA_URL}"'
                }
            )
        except Exception as e:
            logger.error(f"Unexpected error in auth middleware for path {request.url.path}: {str(e)}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={"error": "internal_server_error", "error_description": "An unexpected error occurred"}
            )

