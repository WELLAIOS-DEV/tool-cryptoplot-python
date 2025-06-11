from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

from fastmcp import FastMCP
from starlette.middleware import Middleware

# Import custom authentication middleware and token generation/matching utility
from wellaios.authenticate import (
    AuthenticationMiddleware,
)
from wellaios.crypto_plot import plot_crypto, plot_heatmap
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response

import uvicorn

# Initialize FastMCP application with a specific name for this demo
mcp = FastMCP("wellaios-demo")


@mcp.tool()
async def price_chat_plt(symbol: str) -> str:
    """
    Generates and saves an OHLC chart for the specified cryptocurrency symbol.

    Args:
        symbol (str): The ticker symbol of the cryptocurrency on CoinMarketCap (e.g., 'BTC', 'ETH', '$well').

    Returns:
        str: The URL of the saved chart image.
             Returns Error message if there is an error during the plotting or saving process.
    """
    return plot_crypto(symbol)


@mcp.tool()
async def price_heatmap_plt() -> str:
    """
    Retrieves the current top 20 trending cryptocurrencies and visualizes their
    market data (i.e, price change and volume change) in a Treemap chart.

    Returns:
        str: The URL of the saved chart image.
             Returns an error message if plotting or saving fails.
    """
    return plot_heatmap()


@mcp.custom_route("/plts", methods=["GET"])
async def get_chart(request: Request):
    file_id = request.query_params.get("id")
    try:
        with open(f"plts/{file_id}.svg", "rb") as f:
            headers = {"Content-Disposition": "inline"}
            return Response(
                content=f.read(), media_type="image/svg+xml", headers=headers
            )
    except Exception:
        return PlainTextResponse("File ID error", status_code=400)


if __name__ == "__main__":
    # Define the list of custom middleware to be applied to the HTTP application.
    custom_middleware = [Middleware(AuthenticationMiddleware)]
    # Create the FastMCP HTTP application instance, applying the configured middleware
    http_app = mcp.http_app(middleware=custom_middleware)
    # Run the Uvicorn server, making the application accessible on all network interfaces
    # at port 30000.
    uvicorn.run(http_app, host="0.0.0.0", port=30000)
