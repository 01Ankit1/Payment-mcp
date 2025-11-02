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

# Initialize ScaleKit client for auth
scalekit_client = ScalekitClient(
    settings.SCALEKIT_ENVIRONMENT_URL,
    settings.SCALEKIT_CLIENT_ID,
    settings.SCALEKIT_CLIENT_SECRET
)


# Authentication middleware
class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/.well-known/"):
            return await call_next(request)

        try:
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                raise HTTPException(status_code=401, detail="Missing or invalid authorization header")

            token = auth_header.split(" ")[1]

            # Read request body
            request_body = await request.body()
            
            # Log request details for debugging
            logger.debug(f"Request to {request.url.path}: method={request.method}, body_length={len(request_body)}")
            if request_body:
                try:
                    logger.debug(f"Request body: {request_body.decode('utf-8')[:200]}")  # Log first 200 chars
                except:
                    logger.debug(f"Request body (binary): {len(request_body)} bytes")

            # Parse JSON from bytes
            try:
                request_data = json.loads(request_body.decode('utf-8'))
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
                scalekit_client.validate_token(token, options=validation_options)

            except Exception as e:
                logger.error(f"Token validation failed: {str(e)}")
                raise HTTPException(status_code=401, detail="Token validation failed")

            # Restore the request body so downstream handlers can read it
            # Clear any cached body attribute
            if hasattr(request, '_body'):
                delattr(request, '_body')
            
            # Store original receive and create a new one that replays the body
            original_receive = request._receive
            body_sent = False
            
            async def receive():
                nonlocal body_sent
                if not body_sent:
                    body_sent = True
                    return {"type": "http.request", "body": request_body}
                # After sending body, return empty body as per ASGI spec
                return {"type": "http.request", "body": b""}
            
            request._receive = receive

            # Call next middleware/handler and capture response
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

