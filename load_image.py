"""
Example copied from: https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Process/Examples/S1GRD.html
"""
import io
import os

import boto3
import dotenv
import pandas as pd
import PIL.Image as Image
from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session

dotenv.load_dotenv()

# Your client credentials
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")


def main():
    # Create a session
    client = BackendApplicationClient(client_id=CLIENT_ID)
    oauth = OAuth2Session(client=client)

    # Get token for the session
    oauth.fetch_token(
        token_url="https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token",
        client_secret=CLIENT_SECRET,
        include_client_id=True,
    )

    evalscript = """
    //VERSION=3
    function setup() {
      return {
        input: ["VV"],
        output: { id: "default", bands: 1 },
      }
    }

    function evaluatePixel(samples) {
      return [2 * samples.VV]
    }
    """

    request = {
        "input": {
            "bounds": {
                "bbox": [
                    268574.43,
                    4624494.84,
                    276045.41,
                    4631696.16,
                ],
                "properties": {"crs": "http://www.opengis.net/def/crs/EPSG/0/32633"},
            },
            "data": [
                {
                    "dataFilter": {
                        "timeRange": {
                            "from": "2019-02-02T00:00:00Z",
                            "to": "2019-04-02T23:59:59Z",
                        },
                        "resolution": "HIGH",
                        "acquisitionMode": "IW",
                    },
                    "processing": {
                        "orthorectify": "true",
                        "demInstance": "COPERNICUS_30",
                    },
                    "type": "sentinel-1-grd",
                }
            ],
        },
        "output": {
            "resx": 10,
            "resy": 10,
            "responses": [
                {
                    "identifier": "default",
                    "format": {"type": "image/png"},
                }
            ],
        },
        "evalscript": evalscript,
    }

    url = "https://sh.dataspace.copernicus.eu/api/v1/process"
    response = oauth.post(url, json=request)

    image_bytes = response.content
    image = Image.open(io.BytesIO(image_bytes))
    image.save("img.png")
    print("Image saved in img.png")


if __name__ == "__main__":
    main()
