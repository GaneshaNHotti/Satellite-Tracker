"""
API documentation configuration and utilities.
"""

from typing import Dict, Any, List
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi


def custom_openapi_schema(app: FastAPI) -> Dict[str, Any]:
    """
    Generate custom OpenAPI schema with enhanced documentation.
    
    Args:
        app: FastAPI application instance
        
    Returns:
        Dict containing the OpenAPI schema
    """
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        servers=app.servers
    )
    
    # Add custom security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT token obtained from login endpoint"
        }
    }
    
    # Add global security requirement
    openapi_schema["security"] = [{"BearerAuth": []}]
    
    # Add custom response schemas
    openapi_schema["components"]["schemas"].update({
        "ErrorResponse": {
            "type": "object",
            "properties": {
                "error": {
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "Error code identifier"
                        },
                        "message": {
                            "type": "string",
                            "description": "Human-readable error message"
                        },
                        "details": {
                            "type": "object",
                            "description": "Additional error details"
                        },
                        "correlation_id": {
                            "type": "string",
                            "description": "Request correlation ID for tracking"
                        },
                        "timestamp": {
                            "type": "number",
                            "description": "Error timestamp"
                        }
                    },
                    "required": ["code", "message", "timestamp"]
                }
            },
            "required": ["error"]
        },
        "HealthStatus": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["healthy", "degraded", "unhealthy"],
                    "description": "Overall health status"
                },
                "timestamp": {
                    "type": "number",
                    "description": "Health check timestamp"
                },
                "version": {
                    "type": "string",
                    "description": "API version"
                },
                "checks": {
                    "type": "object",
                    "description": "Individual component health checks"
                }
            },
            "required": ["status", "timestamp"]
        }
    })
    
    # Add common response examples
    add_common_responses(openapi_schema)
    
    # Add tags metadata
    openapi_schema["tags"] = [
        {
            "name": "Authentication",
            "description": "User registration, login, and token management"
        },
        {
            "name": "Users",
            "description": "User profile and location management"
        },
        {
            "name": "Satellites",
            "description": "Satellite search and information retrieval"
        },
        {
            "name": "Favorites",
            "description": "User favorite satellites management"
        },
        {
            "name": "Tracking",
            "description": "Real-time satellite tracking and pass predictions"
        },
        {
            "name": "Health",
            "description": "API health checks and monitoring"
        },
        {
            "name": "Monitoring",
            "description": "Application metrics and monitoring endpoints"
        }
    ]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


def add_common_responses(openapi_schema: Dict[str, Any]):
    """
    Add common response schemas to all endpoints.
    
    Args:
        openapi_schema: OpenAPI schema to modify
    """
    common_responses = {
        "400": {
            "description": "Bad Request",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/ErrorResponse"},
                    "example": {
                        "error": {
                            "code": "BAD_REQUEST",
                            "message": "Invalid request data",
                            "timestamp": 1640995200.0
                        }
                    }
                }
            }
        },
        "401": {
            "description": "Unauthorized",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/ErrorResponse"},
                    "example": {
                        "error": {
                            "code": "UNAUTHORIZED",
                            "message": "Authentication required",
                            "timestamp": 1640995200.0
                        }
                    }
                }
            }
        },
        "403": {
            "description": "Forbidden",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/ErrorResponse"},
                    "example": {
                        "error": {
                            "code": "FORBIDDEN",
                            "message": "Access denied",
                            "timestamp": 1640995200.0
                        }
                    }
                }
            }
        },
        "404": {
            "description": "Not Found",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/ErrorResponse"},
                    "example": {
                        "error": {
                            "code": "NOT_FOUND",
                            "message": "Resource not found",
                            "timestamp": 1640995200.0
                        }
                    }
                }
            }
        },
        "422": {
            "description": "Validation Error",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/ErrorResponse"},
                    "example": {
                        "error": {
                            "code": "VALIDATION_ERROR",
                            "message": "Input validation failed",
                            "details": {
                                "validation_errors": [
                                    {
                                        "field": "email",
                                        "message": "Invalid email format",
                                        "type": "value_error.email"
                                    }
                                ]
                            },
                            "timestamp": 1640995200.0
                        }
                    }
                }
            }
        },
        "429": {
            "description": "Rate Limit Exceeded",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/ErrorResponse"},
                    "example": {
                        "error": {
                            "code": "RATE_LIMIT_EXCEEDED",
                            "message": "Too many requests. Please try again later.",
                            "details": {
                                "retry_after": 300
                            },
                            "timestamp": 1640995200.0
                        }
                    }
                }
            }
        },
        "500": {
            "description": "Internal Server Error",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/ErrorResponse"},
                    "example": {
                        "error": {
                            "code": "INTERNAL_SERVER_ERROR",
                            "message": "An unexpected error occurred",
                            "timestamp": 1640995200.0
                        }
                    }
                }
            }
        },
        "502": {
            "description": "Bad Gateway",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/ErrorResponse"},
                    "example": {
                        "error": {
                            "code": "EXTERNAL_API_ERROR",
                            "message": "External service unavailable",
                            "details": {
                                "api_name": "N2YO"
                            },
                            "timestamp": 1640995200.0
                        }
                    }
                }
            }
        },
        "503": {
            "description": "Service Unavailable",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/ErrorResponse"},
                    "example": {
                        "error": {
                            "code": "SERVICE_UNAVAILABLE",
                            "message": "Service temporarily unavailable",
                            "timestamp": 1640995200.0
                        }
                    }
                }
            }
        }
    }
    
    # Add common responses to all paths
    for path_item in openapi_schema.get("paths", {}).values():
        for operation in path_item.values():
            if isinstance(operation, dict) and "responses" in operation:
                # Don't override existing responses, only add missing ones
                for status_code, response in common_responses.items():
                    if status_code not in operation["responses"]:
                        operation["responses"][status_code] = response


def get_api_tags() -> List[Dict[str, str]]:
    """
    Get API tags for endpoint organization.
    
    Returns:
        List of tag definitions
    """
    return [
        {
            "name": "Authentication",
            "description": "User registration, login, and token management"
        },
        {
            "name": "Users", 
            "description": "User profile and location management"
        },
        {
            "name": "Satellites",
            "description": "Satellite search and information retrieval"
        },
        {
            "name": "Favorites",
            "description": "User favorite satellites management"
        },
        {
            "name": "Tracking",
            "description": "Real-time satellite tracking and pass predictions"
        },
        {
            "name": "Health",
            "description": "API health checks and monitoring"
        },
        {
            "name": "Monitoring",
            "description": "Application metrics and monitoring endpoints"
        }
    ]