from quart import Quart
from discord.ext.cluster import Client

app = Quart(__name__)
ipc = Client(host="127.0.0.1", secret_key="secret", standard_port=1025)


@app.route('/')
async def main():
    return await ipc.request(endpoint="get_user_data", bot_id=812993088749961236, identifier=1, user_id=383946213629624322)

if __name__ == '__main__':
    app.run(port=8000, debug=True)
