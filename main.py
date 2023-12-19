import asyncio
import argparse
import threading
import concurrent.futures
from base64 import b64decode, b64encode

from pytun import TunTapDevice
from telethon import TelegramClient, events
from environs import Env
from tun_tap_wrapper import TunTapWrapper
from datetime import datetime

env = Env()
env.read_env()

API_ID = env('API_ID')
API_HASH = env('API_HASH')

up = False

async def lock_check():
    while True:
        delay_seconds = 5
        print(f"[{datetime.isoformat(datetime.now())}] - lock check is alive, next check after {delay_seconds} seconds")
        await asyncio.sleep(delay_seconds)

def build_tun_tap_wrapper(args) -> TunTapWrapper:
    global up
    print('Configuring TUN interface...')
    if args.server:
        source_address =  args.dst
        destination_address = args.src
    else:
        source_address =  args.src
        destination_address = args.dst

    tun_tap_wrapper = TunTapWrapper(
        name="teletun",
        source_address=source_address,
        destination_address=destination_address,
        netmask=args.mask,
        mtu=args.mtu,
    )
    tun_tap_wrapper.up()
    up = True
    return tun_tap_wrapper


async def read_tun(tun_tap_wrapper: TunTapWrapper, client: TelegramClient, username: str):
    global up
    print('Listening to incoming data on TUN interface...')
    while up:
        with concurrent.futures.ThreadPoolExecutor() as executor:
            loop = asyncio.get_event_loop()
            b64encoded_data = await loop.run_in_executor(executor, tun_tap_wrapper.read)
        print(f'Sending message to {username}...')
        await client.send_message(username, b64encoded_data)


async def main(phone: str, username: str, tun_tap_wrapper: TunTapWrapper):
    client = TelegramClient('teletun', int(API_ID), API_HASH)
    @client.on(events.NewMessage(incoming=True, from_users=username, forwards=False))
    async def new_msg_handler(event):
        tun_tap_wrapper.write(event.message.text)

    print('Initiating connection to Telegram API...')
    await client.start(phone)

    client_live_cycle_task = asyncio.create_task(client.run_until_disconnected())
    read_tun_task = asyncio.create_task(read_tun(tun_tap_wrapper, client, username))
    check_lock_task = asyncio.create_task(lock_check())

    print(f'Starting to listen to incoming messags from {username}...')
    await asyncio.gather(client_live_cycle_task, read_tun_task, check_lock_task)

    up = False
    print('Stopping message receiver and shutting down the tunnel...')
    tun_tap_wrapper.down()
    client.disconnect()

    print(f'Total bytes sent via Telegram: {str(tun_tap_wrapper._sent)}')
    print(f'Total bytes received via Telegram: {str(tun_tap_wrapper._received)}')
    print('Exiting...')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Teletun - IP over Telegram')
    parser.add_argument('-p', '--phone', help='Account phone number', required=True)
    parser.add_argument('-u', '--username', help='username', required=True)
    parser.add_argument('-r', '--server', help='server', action='store_true')
    parser.add_argument('-p', '--src', help='peer address', default='10.0.0.1')
    parser.add_argument('-s', '--dst', help='server address', default='10.0.0.2')
    parser.add_argument('-m', '--mask', help='mask', default='255.255.255.0')
    parser.add_argument('-n', '--mtu', help='MTU', default=1500)
    args = parser.parse_args()
    tun_tap_wrapper = build_tun_tap_wrapper(args)
    asyncio.run(
        main(args.phone, args.username, tun_tap_wrapper)
    )
