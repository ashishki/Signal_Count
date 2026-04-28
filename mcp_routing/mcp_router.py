"""MCP Router Service.

Routes MCP requests from the Yggdrasil P2P bridge to registered MCP servers.
Allows dynamic registration/deregistration of services without restarting the bridge.
"""

import argparse
import asyncio
import logging
import os
from datetime import UTC, datetime
from typing import Any

from aiohttp import ClientSession, ClientTimeout, web

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ROUTER_PORT = 9003
FORWARD_TIMEOUT_SECONDS = float(os.getenv("MCP_ROUTER_FORWARD_TIMEOUT_SECONDS", "30"))

services: dict[str, dict[str, Any]] = {}


async def handle_route(request: web.Request) -> web.Response:
    """Route an MCP request to the appropriate service."""
    try:
        body = await request.json()
    except Exception as exc:
        return web.json_response(
            {"response": None, "error": f"Invalid JSON: {exc}"},
            status=400,
        )

    service_name = body.get("service", "")
    mcp_request = body.get("request")
    from_peer_id = body.get("from_peer_id", "unknown")

    if not service_name:
        return web.json_response(
            {"response": None, "error": "Missing 'service' field"},
            status=400,
        )

    if service_name not in services:
        logger.warning("Service not found: %s", service_name)
        return web.json_response(
            {"response": None, "error": f"Service not found: {service_name}"},
            status=404,
        )

    service = services[service_name]
    endpoint = service["endpoint"]

    logger.info(
        "Routing request to %s from peer %s...",
        service_name,
        str(from_peer_id)[:16],
    )

    try:
        async with ClientSession(
            timeout=ClientTimeout(total=FORWARD_TIMEOUT_SECONDS)
        ) as session:
            async with session.post(
                endpoint,
                json=mcp_request,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream",
                    "X-From-Peer-Id": from_peer_id,
                    "X-Service": service_name,
                },
            ) as response:
                if response.status == 204:
                    return web.json_response({"response": None, "error": None})

                if response.status != 200:
                    error_text = await response.text()
                    logger.error(
                        "Service %s returned %s: %s",
                        service_name,
                        response.status,
                        error_text,
                    )
                    services[service_name]["healthy"] = False
                    return web.json_response(
                        {
                            "response": None,
                            "error": f"Service error: {response.status}",
                        },
                        status=502,
                    )

                response_data = await response.json()
                services[service_name]["healthy"] = True
                return web.json_response({"response": response_data, "error": None})

    except TimeoutError:
        logger.error("Timeout forwarding to %s", service_name)
        services[service_name]["healthy"] = False
        return web.json_response(
            {"response": None, "error": "Service timeout"},
            status=504,
        )
    except Exception as exc:
        logger.error("Error forwarding to %s: %s", service_name, exc)
        services[service_name]["healthy"] = False
        return web.json_response(
            {"response": None, "error": f"Forward error: {exc}"},
            status=502,
        )


async def handle_register(request: web.Request) -> web.Response:
    """Register an MCP service."""
    try:
        body = await request.json()
    except Exception as exc:
        return web.json_response({"error": f"Invalid JSON: {exc}"}, status=400)

    service_name = body.get("service", "")
    endpoint = body.get("endpoint", "")

    if not service_name or not endpoint:
        return web.json_response(
            {"error": "Both 'service' and 'endpoint' are required"},
            status=400,
        )

    services[service_name] = {
        "endpoint": endpoint,
        "registered_at": datetime.now(UTC).isoformat(),
        "healthy": True,
    }

    logger.info("Registered service: %s -> %s", service_name, endpoint)
    return web.json_response({"status": "registered", "service": service_name})


async def handle_deregister(request: web.Request) -> web.Response:
    """Deregister an MCP service."""
    service_name = request.match_info.get("service", "")

    if not service_name:
        return web.json_response({"error": "Service name required"}, status=400)

    if service_name not in services:
        return web.json_response(
            {"error": f"Service not found: {service_name}"},
            status=404,
        )

    del services[service_name]
    logger.info("Deregistered service: %s", service_name)
    return web.json_response({"status": "deregistered", "service": service_name})


async def handle_services(request: web.Request) -> web.Response:
    """List all registered services."""
    return web.json_response(services)


async def handle_health(request: web.Request) -> web.Response:
    """Router health check."""
    return web.json_response(
        {
            "status": "ok",
            "service_count": len(services),
        }
    )


async def run_router(port: int) -> None:
    """Run the MCP router HTTP server."""
    app = web.Application()
    app.router.add_post("/route", handle_route)
    app.router.add_post("/register", handle_register)
    app.router.add_delete("/register/{service}", handle_deregister)
    app.router.add_get("/services", handle_services)
    app.router.add_get("/health", handle_health)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", port)
    await site.start()

    logger.info("MCP Router listening on http://127.0.0.1:%s", port)
    logger.info("Endpoints:")
    logger.info("  POST   /route                - Route MCP request")
    logger.info("  POST   /register             - Register a service")
    logger.info("  DELETE /register/{service}   - Deregister a service")
    logger.info("  GET    /services             - List registered services")
    logger.info("  GET    /health               - Health check")

    while True:
        await asyncio.sleep(3600)


def main() -> None:
    """Entry point."""
    parser = argparse.ArgumentParser(description="MCP Router Service")
    parser.add_argument(
        "--port",
        type=int,
        default=ROUTER_PORT,
        help=f"Port to listen on (default: {ROUTER_PORT})",
    )
    args = parser.parse_args()

    asyncio.run(run_router(args.port))


if __name__ == "__main__":
    main()
