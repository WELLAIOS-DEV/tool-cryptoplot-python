# WELLAIOS Crypto Chart Tool Server (Standalone)

This repository showcases a standalone server demonstration for the **WELLAIOS Crypto Chart** tool. This powerful tool leverages data from **CoinMarketCap** to generate various cryptocurrency charts, giving AI agents the ability to visualize market trends.

## Getting Started

Follow these steps to set up and run your WELLAIOS Crypto Chart server:

1. **Get a CoinMarketCap API Key**

   To use this tool, you'll need an API key from CoinMarketCap. This key authenticates your requests to their data service.

   1. **Visit CoinMarketCap API**:
      Go to the [CoinMarketCap API website](https://coinmarketcap.com/api/documentation/v1/).

   2. **Sign Up/Log In**:
      Create an account or log in if you already have one.

   3. **Choose a Plan**:
      Select a suitable plan.

   4. **Generate API Key**:
      Once signed up, you'll find your API key on your dashboard.
      Copy this key.

2. **Install Python and Required Packages**

   Make sure you have Python installed on your system (Python 3.12+ is recommended).
   Then, navigate to your project directory in the terminal and install the necessary Python packages using `pip`:

   ```
   pip install -r requirements.txt
   ```

3. **Configure the Server**

   Create a file named `.env` in the root directory of your project (the same directory as `main.py`). Add the following content, replacing the placeholder values with your actual tokens and API key:

   ```
   AUTH_TOKEN=your_wellaios_auth_token_here
   SERVER_DOMAIN=http://localhost:30000
   CMC_KEY=your_coinmarketcap_api_key_here
   ```

   - `AUTH_TOKEN`:
     This is the bearer token used for authenticating clients with your tool server (e.g., from WELLAIOS).

   - `SERVER_DOMAIN`:
     This variable defines the base URL for your server. For local testing, it is by default `http://localhost:30000`. This is also used to construct public links to generated charts.

   - `CMC_KEY`:
     Your CoinMarketCap API key obtained in Step 1.

4. **Start the Server**

   Once you've installed the packages and configured your .env file, you can launch the tool server:

   ```
   python main.py
   ```

   By default, the server will run on `http://localhost:30000`.

5. **Test Your Tool Server**

   You can test your running tool server

   - **MCP Inspector**:
     For basic testing and inspecting the tool's functionality, you can use the [MCP inspector](https://github.com/modelcontextprotocol/inspector).

     **Note**: The MCP Inspector currently does not support multi-user scenarios. Therefore, you won't be able to test the multi-user specific features using this tool alone.

   - **WELLAIOS Engine**:
     The best way to thoroughly test the multi-user capabilities and the full integration is by connecting your tool server to the WELLAIOS engine itself.
     Refer to the WELLAIOS documentation for instructions on how to connect external tool servers.

## Resources

For the server to run normally and display cryptocurrency charts, the following local resources are required:

1.  `cmc_coin_list.json`

    This file is a cached copy of the cryptocurrency list from CoinMarketCap.
    In a production environment, you'd want to ensure this list is regularly synchronized with CoinMarketCap's latest data to maintain accuracy.

2.  `images/*.png`

    This directory contains cached PNG images of various cryptocurrencies.
    These images are embedded directly into the generated charts to enhance visual appeal and provide quick identification of the assets.

## Guide to connect to MCP Inspector

### Transport Type

Select `Streamble HTTP`

### URL

Enter the MCP path under your server's location.
For example, if your server is running locally on port 30000, the URL would be:

`http://localhost:30000/mcp`

### Authentication

Use `Bearer Token` as the authentication method.
Then, use the exact token you've set in your `.env` file.

## License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file.
