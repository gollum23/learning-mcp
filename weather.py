import httpx
from mcp.server.fastmcp import FastMCP
from typing import Any


mcp = FastMCP('Weather MCP server')


NWS_API_BASE_URL = 'https://api.weather.gov'
USER_AGENT = 'weather-mcp/1.0'


async def make_nws_request(url: str) -> dict[str, Any] | None:
    headers = {
        'User-Agent':  USER_AGENT,
        'Accept': 'application/geo+json',
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception:  # TODO: Handle specific exceptions
            return None  # TODO: logging error or send to sentry for example


def format_alert(info: dict) -> str:
    properties = info['properties']
    return f"""
        Event: {properties.get('event', 'Unknown')}
        Area: {properties.get('areaDesc', 'Unknown')}
        Severity: {properties.get('severity', 'Unknown')}
        Description: {properties.get('description', 'No description available')}
        Instruction: {properties.get('instruction', 'No specific instructions')}
    """


@mcp.tool()
async def get_alerts(state: str) -> str:
    """Get weather alerts for a US state.

    Args:
        state: Two-letter US state code (e.g. CA, NY)
    """
    url = f"{NWS_API_BASE_URL}/alerts/active/area/{state}"
    data = await make_nws_request(url)

    if not data or "features" not in data:
        return "Unable to fetch alerts or no alerts found."

    if not data["features"]:
        return "No active alerts for this state."

    alerts = [format_alert(feature) for feature in data["features"]]
    return "\n---\n".join(alerts)


@mcp.tool()
async def get_forecast(latitude: float, longitude: float) -> str:
    """
    Retrieve weather forecast for the specified geographic coordinates.

    The function fetches the weather forecast based on latitude and longitude
    parameters. It performs an asynchronous operation to communicate with the
    weather service and returns the forecast result as a string.
    """
    points_url = f'{NWS_API_BASE_URL}/points/{latitude},{longitude}'
    points_data = await make_nws_request(points_url)

    if not points_data:
        return 'Unable to retrieve forecast data for this location.'

    forecast_url = points_data['properties']['forecast']
    forecast_data = await make_nws_request(forecast_url)

    if not forecast_data:
        return 'Unable to retrieve detailed forecast data for this location.'

    periods = forecast_data['properties']['periods']
    forecasts = []
    for period in periods[:24]:
        forecast = f"""
            Name: {period['name']}
            Temperature: {period['temperature']} {period['temperatureUnit']}
            Wind: {period['windSpeed']} {period['windDirection']}
            Short Forecast: {period['shortForecast']}
            Detailed Forecast: {period['detailedForecast']}
        """
        forecasts.append(forecast)

    return '\n---\n'.join(forecasts)

if __name__ == '__main__':
    print('Starting the Weather MCP server...')
    mcp.run(transport='stdio')
