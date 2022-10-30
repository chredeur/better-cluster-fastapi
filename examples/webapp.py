from quart import Quart
from discord.ext import cluster

app = Quart(__name__)
ipc = cluster.Client()

@app.route('/')
async def main():
    return await ipc.request("get_user_data", 1, user_id=383946213629624322)

if __name__ == '__main__':
    app.run(port=8000, debug=True)