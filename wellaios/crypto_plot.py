import base64
import json
import os
import uuid
import pandas as pd
import requests
import plotly.graph_objects as go
import math
from plotly.subplots import make_subplots
from typing import TypedDict

# Load environment variables. These should be set securely.
SERVER_DOMAIN = os.environ.get("SERVER_DOMAIN")  # Base URL of your server
CMC_KEY = os.environ.get("CMC_KEY")  # CoinMarketCap API Key

# Define the folder where generated plots (images) will be saved.
FOLDER = "plts"
# Construct the prefix for the public link to access the saved plots.
LINK_PREFIX = f"{SERVER_DOMAIN}/plts?id="

# Headers required for CoinMarketCap API requests, including the API key.
CMC_HEADER = {
    "Accepts": "application/json",  # Request JSON response
    "X-CMC_PRO_API_KEY": CMC_KEY,  # Your CoinMarketCap API key for authentication
}

# CoinMarketCap API endpoints used.
LATEST_API = "https://pro-api.coinmarketcap.com/v2/cryptocurrency/ohlcv/latest"
HISTORICAL_API = "https://pro-api.coinmarketcap.com/v2/cryptocurrency/ohlcv/historical"
HEATMAP_API = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/trending/latest"

# In a production environment, you should implement a mechanism to regularly
# synchronize this file with the latest data from CoinMarketCap's API
# (e.g., using their /v1/cryptocurrency/map endpoint) to ensure accuracy and completeness.
COIN_FILE_NAME = "cmc_coin_list.json"


class CoinDetails(TypedDict):
    """
    TypedDict to define the structure of a cryptocurrency's details.
    """

    id: int  # Unique ID of the cryptocurrency on CoinMarketCap
    symbol: str  # Trading symbol (e.g., "BTC", "ETH")
    slug: str  # URL-friendly version of the name (e.g., "bitcoin", "ethereum")
    name: str  # Full name (e.g., "Bitcoin", "Ethereum")


def get_coin_list() -> dict[str, CoinDetails]:
    """
    Loads the list of cryptocurrencies from a local JSON file.

    The function reads 'cmc_coin_list.json', parses it, and returns a dictionary
    mapping lowercase coin symbols to their details. This allows for quick lookup
    by symbol.

    Returns:
        A dictionary where keys are lowercase cryptocurrency symbols and values
        are CoinDetails TypedDicts.
    """
    # Open and load the JSON file containing coin data.
    with open(COIN_FILE_NAME) as f:
        data: list[CoinDetails] = json.load(f)
    result: dict[str, CoinDetails] = {}
    # Iterate through the list and populate the dictionary, prioritizing the first
    # entry for a given symbol if duplicates exist.
    for x in data:
        sym = x["symbol"].lower()  # for case-insensitive
        if (
            sym not in result
        ):  # only map to the first appearance of the token with the same symbol
            result[sym] = x
    return result


# Load the coin list once when the module is imported.
coin_list: dict[str, CoinDetails] = get_coin_list()


def generate_unique_file_id() -> str:
    """
    Generates a unique filename (ID) using UUID4.

    The function creates a random UUID and checks if a file with that name
    (plus '.svg' extension) already exists in the `FOLDER`. It retries
    until a unique ID is found.

    Returns:
        str: A unique identifier string suitable for a filename.
    """
    while True:
        file_id = str(uuid.uuid4())  # Generate a new UUID
        filename = f"{file_id}.svg"  # Append .svg extension
        file_path = os.path.join(FOLDER, filename)  # Construct full path
        if not os.path.exists(file_path):  # Check if the file already exists
            return file_id


def plot_crypto(symbol: str) -> str:
    """
    Generates and saves an OHLCV (Open-High-Low-Close-Volume) candlestick chart
    for a given cryptocurrency symbol.

    It fetches historical and latest OHLCV data from CoinMarketCap, processes it,
    creates a Plotly chart, and saves it as an SVG file. A URL to the saved chart
    is returned.

    Args:
        symbol: The cryptocurrency symbol (e.g., "BTC", "ETH") or slug (e.g., "bitcoin")
                to plot. Note that only token on the list is allowed.

    Returns:
        A string containing a URL to the generated chart, or an error message if the
        token is not found or data retrieval fails.
    """
    # Find the coin details using either symbol or slug (case-insensitive).
    coin = None
    sym_low = symbol.lower()
    if sym_low in coin_list:
        coin = coin_list[sym_low]
    else:
        for x in coin_list:
            if sym_low == coin_list[x]["slug"]:
                coin = coin_list[x]
                break

    if coin is None:
        return f"Token {symbol} not found. Please provide a valid cryptocurrency symbol or slug."

    # --- Get historical data ---
    params = {
        "symbol": coin["symbol"],
        "count": 100,
    }
    try:
        response = requests.get(HISTORICAL_API, headers=CMC_HEADER, params=params)
        response.raise_for_status()
        data = response.json()

        values = [
            x["quote"]["USD"] for x in data["data"][coin["symbol"].upper()][0]["quotes"]
        ]
        df = pd.DataFrame(values)

        # 'market_cap' is not needed for OHLCV plot, so drop it.
        df.drop(columns="market_cap", inplace=True)
    except Exception as e:
        return f"An unexpected error occurred during historical data processing for {symbol}: {e}"

    # --- Get latest price data ---
    params = {
        "symbol": coin["symbol"],
    }
    try:
        response = requests.get(LATEST_API, headers=CMC_HEADER, params=params)
        response.raise_for_status()
        data = response.json()

        new_data = data["data"][coin["symbol"].upper()][0]["quote"]["USD"]

        new_data["timestamp"] = new_data["last_updated"]
        new_data.pop("last_updated")  # Remove original key
    except Exception as e:
        return f"An unexpected error occurred during latest data processing for {symbol}: {e}"

    # Combine historical and latest data into a single DataFrame.
    df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
    # Convert the 'timestamp' column to datetime objects for proper plotting.
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    # --- Plot the chart using Plotly ---
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08, row_heights=[0.7, 0.3]
    )  # Allocate more space to OHLC chart (row 1)

    # Add Candlestick Trace to the first row.
    fig.add_trace(
        go.Candlestick(
            x=df["timestamp"].dt.date,  # Use date only for x-axis ticks
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name="Price",  # Name for the legend
        ),
        row=1,
        col=1,
    )

    # Add Volume Bar Trace to the second row.
    fig.add_trace(
        go.Bar(
            x=df["timestamp"].dt.date,
            y=df["volume"],
            name="Volume",
            marker_color="rgba(0, 0, 255, 0.5)",
        ),
        row=2,
        col=1,
    )

    # Try to load and embed a cryptocurrency logo image (if available) for the chart.
    img_base64 = None
    try:
        # Assumes image files are stored in an 'images' folder and named by Coin ID.
        with open(f"images/{coin['id']}.png", "rb") as f:
            # Read image, base64 encode it, and format for Plotly image source.
            encoded_string = base64.b64encode(f.read()).decode("utf-8")
            img_base64 = f"data:image/png;base64,{encoded_string}"
    except Exception as e:
        print(f"Error loading image for coin ID {coin['id']}: {e}")

    # Update chart layout settings.
    fig.update_layout(
        title=f"{coin['name']} ({coin['symbol'].upper()}) Price & Volume",  # Chart title
        xaxis_rangeslider_visible=False,  # Hide the default range slider for a cleaner look
        title_x=0.5,  # Center the title horizontally
        title_xanchor="center",
        showlegend=False,  # Hide legend (as traces are self-explanatory or use annotations)
        height=600,  # Set fixed height for the plot
        template="plotly_white",  # Use a white background theme
        # Add a watermark annotation at the bottom right of the plot area.
        annotations=[
            dict(
                text="By WELLAIOS plot",  # Watermark text
                xref="paper",
                yref="paper",  # Position relative to the plot paper (0 to 1)
                x=1,
                y=0.28,  # Coordinates (right-aligned, slightly above volume chart)
                showarrow=False,  # Don't show an arrow pointing from the annotation
                font=dict(
                    size=20,  # Font size
                    color="rgba(100, 100, 100, 0.3)",  # Light gray with transparency
                ),
                opacity=0.5,  # Overall opacity of the annotation
            ),
        ],
    )

    # Customize x and y axis tick font size and color.
    fig.update_xaxes(tickfont=dict(size=10, color="grey"))
    fig.update_yaxes(tickfont=dict(size=10, color="grey"))

    # Make gridlines thinner and grey for both axes.
    fig.update_xaxes(gridwidth=0.5, gridcolor="rgba(100, 100, 100, 0.4)")
    fig.update_yaxes(gridwidth=0.5, gridcolor="rgba(100, 100, 100, 0.4)")

    # Add the cryptocurrency logo as a layout image if available.
    if img_base64 is not None:
        fig.add_layout_image(
            dict(
                source=img_base64,
                xref="paper",
                yref="paper",  # Reference the entire plot area (0 to 1)
                x=0.01,  # X-position (e.g., near top-left)
                y=1.05,  # Y-position (slightly above the plot area for the title bar)
                sizex=0.08,  # Size of the image (relative to plot width)
                sizey=0.08,  # Size of the image (relative to plot height)
                xanchor="left",  # Anchor the image by its left side
                yanchor="top",  # Anchor the image by its top side
                sizing="contain",  # 'contain' ensures the whole image fits without distortion
                layer="above",  # Place image above other layout elements like gridlines
            )
        )

    # Create the directory to save plots if it doesn't exist.
    os.makedirs(FOLDER, exist_ok=True)

    # Generate a unique file ID and construct the full path for the SVG image.
    file_id = generate_unique_file_id()
    filename = os.path.join(FOLDER, f"{file_id}.svg")
    # Write the Plotly figure to an SVG file.
    fig.write_image(filename, width=1200, height=600)
    # Construct the public URL for the generated chart.
    link = f"{LINK_PREFIX}{file_id}"
    return f"Chart generated at {link}"


def plot_heatmap() -> str:
    """
    Generates and saves a cryptocurrency heatmap based on trending data.

    It fetches trending cryptocurrency data from CoinMarketCap, processes it to
    determine size (based on volume change) and color (based on price change)
    for each cryptocurrency, creates a Plotly Treemap, and saves it as an SVG file.
    A URL to the saved chart and a JSON string of raw data are returned.

    Returns:
        A string containing a URL to the generated heatmap chart and a JSON string
        of the raw data used for the heatmap.
    """
    # Parameters for the trending (heatmap) API request.
    params = {
        "limit": 20,  # Get top 20 trending cryptocurrencies
    }

    try:
        response = requests.get(HEATMAP_API, headers=CMC_HEADER, params=params)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        return f"An unexpected error occurred during heatmap data retrieval: {e}"

    graph_data = []
    # Process each trending cryptocurrency to extract relevant data for the heatmap.
    for x in data["data"]:
        graph_data.append(
            {
                "price": x["quote"]["USD"]["price"],
                "name": x["name"],
                "symbol": x["symbol"],
                "price_change": x["quote"]["USD"]["percent_change_24h"],
                "vol_change": x["quote"]["USD"]["volume_change_24h"],
            }
        )
    df = pd.DataFrame(graph_data)

    # Calculate 'values' for the treemap, which determine the size of each block.
    # Here, it's based on the absolute 24h volume change, clamped between 1 and 2000.
    values = [abs(x) for x in df["vol_change"]]
    values = [1 if x < 1 else x if x < 2000 else 2000 for x in values]

    # Calculate size fractions for dynamic font sizing and label generation.
    total_size = sum(values)
    size_fractions = [x / total_size for x in values]

    def gen_label(
        symbol: str,
        price: float,
        price_change: float,
        fraction: float,
    ) -> str:
        """
        Generates the HTML label for each block in the treemap.
        The label content and font size adapt based on the block's size (fraction).
        """
        if fraction < 0.01:  # For very small blocks, just show symbol
            return symbol

        # Format price based on its magnitude.
        price_text = f"{price:.4g}" if price < 1 else f"{price:.2f}"

        # Format price change text (with +/- sign).
        if price_change > 0:
            price_change_text = f"+{price_change:.2f}%"
            priceline = f"{price_text} ({price_change_text})"
        elif price_change < 0:
            price_change_text = f"{price_change:.2f}%"  # Will have - sign
            priceline = f"{price_text} ({price_change_text})"
        else:
            priceline = "--"
            price_change_text = "--"

        # Determine font size dynamically based on the fraction (logarithmic scale).
        # This makes larger blocks have proportionally larger text.
        size = math.log(fraction / 0.01) + 1
        if size < 0.5:
            size = 0.5  # Minimum font size to prevent illegibility

        if (
            fraction < 0.02
        ):  # For small to medium blocks, show symbol and percentage change
            return f"<span style='font-size: {size}em;'>{symbol}</span><br />{price_change_text}"

        # For larger blocks, show symbol, price, and percentage change.
        return f"<span style='font-size: {size}em;'>{symbol}</span><br />{priceline}"

    # Generate labels for all cryptocurrencies in the DataFrame.
    labels = [
        gen_label(symbol, price, price_change, fraction)
        for symbol, price, price_change, fraction in zip(
            df["symbol"],
            df["price"],
            df["price_change"],
            size_fractions,
        )
    ]

    # Determine the maximum absolute price change for color scaling.
    # Add a floor of 2 to avoid log(0) or very small numbers causing issues.
    max_positive = math.log(
        df["price_change"].max() if any(df["price_change"] > 1) else 2
    )
    max_negative = math.log(
        -df["price_change"].min() if any(df["price_change"] < -1) else 2
    )
    max_price_change = max(max_positive, max_negative)

    colors = []
    # Assign colors based on price change: green for positive, red for negative, grey for neutral.
    # Intensity of color scales with the magnitude of price change.
    for val in df["price_change"]:
        if val > 1:
            # Scale green intensity based on positive price change
            intensity = 0.2 + 0.6 * (1 - math.log(val) / max_price_change)
            colors.append(f"rgb(0, {int(intensity*255)}, 0)")
        elif val < -1:
            # Scale red intensity based on negative price change
            intensity = 0.2 + 0.6 * (1 - math.log(-val) / max_price_change)
            colors.append(f"rgb({int(intensity*255)}, 0, 0)")
        else:
            # Neutral color for small changes (-1% to +1%)
            colors.append("rgb(100, 100, 100)")

    # Create the Treemap figure.
    fig = go.Figure(
        go.Treemap(
            labels=labels,  # Text labels for each block
            parents=[""]
            * len(labels),  # All blocks are top-level children of an invisible root
            values=values,  # Determines the size of each block
            marker_colors=colors,  # Determines the color of each block
        )
    )

    # Update trace properties for rounded corners.
    fig.update_traces(marker=dict(cornerradius=5))
    # Set margins to 0 for a tight fit, maximizing chart area.
    fig.update_layout(margin=dict(t=0, l=0, r=0, b=0))

    # Configure text positioning within the treemap blocks.
    fig.update_traces(
        textposition="middle center",  # Align text horizontally and vertically center
        textinfo="label",  # Show only the label generated by `gen_label`
    )

    # Create the directory to save plots if it doesn't exist.
    os.makedirs(FOLDER, exist_ok=True)

    # Generate a unique file ID and construct the full path for the SVG image.
    file_id = generate_unique_file_id()
    filename = os.path.join(FOLDER, f"{file_id}.svg")
    # Write the Plotly figure to an SVG file.
    fig.write_image(filename, width=1200, height=600)
    # Construct the public URL for the generated chart.
    link = f"{LINK_PREFIX}{file_id}"
    # Return the link to the chart and the raw data in JSON format.
    return f"Chart generated at {link}\nRaw data is {json.dumps(df.to_dict(orient='records'))}"  # Use orient='records' for list of dicts
