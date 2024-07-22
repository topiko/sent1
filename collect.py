import datetime
import os

import dotenv
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session

dotenv.load_dotenv()

# Your client credentials, refer to: https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Overview/Authentication.html#python
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
URL = os.getenv(
    "URL"
)  # = "https://sh.dataspace.copernicus.eu/api/v1/catalog/1.0.0/search"
TOKEN_URL = os.getenv(
    "TOKEN_URL"
)  # ="https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"


# Cover nothern Europe
LATITUDES = np.arange(47, 70, 1.0)
LONGITUDES = np.arange(0, 30, 1.0)


# The mission took off in 2017?
# what would be a correct period here? Too small and you neve see anyhting(?), too large and you'll receive the same area several times.
DATETIMES = np.arange(
    datetime.datetime(2018, 1, 1),
    datetime.datetime(2024, 1, 1),
    datetime.timedelta(hours=6),
).astype(datetime.datetime)


def _parse_datetime(datetime: datetime.datetime) -> str:
    """
    Helper to parse datetime strings that are send to the API.

    Args:
        datetime: datetime.datetime: The datetime to parse.

    Returns:
        str: The parsed datetime.
    """
    return datetime.strftime("%Y-%m-%dT%H:%M:%SZ")


def get_passes(oauth: OAuth2Session) -> pd.DataFrame:
    """
    Get a dataframe containing all of the passes of the satellite in the selected grid.

    Args:
        oauth: OAuth2Session: The session to use.

    Returns:
        pd.DataFrame: Containing the passes of the satellite over the selected area.
    """
    data = {
        "collections": ["sentinel-1-grd"],
        "limit": 10,
    }

    # TODO: this querying is completely agains the API design. I should have queried for a longer
    # period and collected the passes form there. This looping resulted in me running out of my
    # requests quota within 15 mins of collection...
    dfs = []
    for i in range(len(LONGITUDES) - 1):
        lon_left = LONGITUDES[i]
        lon_right = LONGITUDES[i + 1]
        for j in range(len(LATITUDES) - 1):
            lat_bot = LATITUDES[j]
            lat_up = LATITUDES[j + 1]
            print(
                f"Processing lat=[{lat_bot:.2f}, {lat_up:.2f}], lon=[{lon_left:.2f}, {lon_right:.2f}]"
            )
            for idt in range(len(DATETIMES) - 1):
                time_start = DATETIMES[idt]
                time_end = DATETIMES[idt + 1]
                data["bbox"] = [lat_bot, lon_left, lat_up, lon_right]
                data["datetime"] = (
                    _parse_datetime(time_start) + "/" + _parse_datetime(time_end)
                )

                response = oauth.post(URL, json=data).json()

                if response["context"]["returned"] == 0:
                    continue

                df_ = pd.DataFrame(response["features"])
                # The target area can fit into single time slot several times
                # if the satellite is "optimally" passing the target area?
                # This can cause several imgase being available.
                # We only take the first. You though need to make sure
                # the timedelta is small enough.

                if len(df_) > 1:
                    print(
                        f"Warning: multiple ({len(df_)}) images found for single time slot."
                    )
                    df_ = df_.iloc[0].to_frame().T

                df_.loc[:, "lat_bot"] = lat_bot
                df_.loc[:, "lat_up"] = lat_up
                df_.loc[:, "lon_left"] = lon_left
                df_.loc[:, "lon_right"] = lon_right
                df_.loc[:, "time_start"] = time_start
                df_.loc[:, "time_end"] = time_end

                dfs.append(df_)
            print("Currently found passes: ", len(dfs))
    return pd.concat(dfs)


def plot_passes(df: pd.DataFrame, ax: plt.Axes | None = None):
    """
    Plot the number of passes within the collection period in polar coordinates.
    There definitely are "more correct" ways to visualize this data.

    Note this is easily modified to display for given time interval by
    filtering the plotted dataframe.
    Args:
        df: pd.DataFrame: The dataframe containing the passes of the satellite over the selected area.

    """
    print("WARNING: This viz. was never tested...")

    phis = df.lon_left.unique()
    thetas = df.lat_bot.unique()

    r, theta = np.meshgrid(thetas, phis)
    values = df.value_counts(["lon_left", "lat_bot"]).sort_index().values

    if ax is None:
        _, ax = plt.subplots(subplot_kw={"projection": "polar"})
    ax.contourf(theta, r, values)
    interval = (df.time_start.min(), df.time_end.max())
    ax.set_title(f"# passes in interval: [{interval[0]}, {interval[1]})")

    plt.show()


def main():
    if os.path.isfile("passes.h5"):
        df = pd.read_hdf("passes.h5")
        plot_passes(df)
        return

    # Create a session
    client = BackendApplicationClient(client_id=CLIENT_ID)
    oauth = OAuth2Session(client=client)

    # Get token for the session
    oauth.fetch_token(
        token_url=TOKEN_URL,
        client_secret=CLIENT_SECRET,
        include_client_id=True,
    )

    df = get_passes(oauth)

    df.to_hdf("passes.h5", key="data")
    main()


if __name__ == "__main__":
    main()
