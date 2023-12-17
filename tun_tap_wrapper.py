from pytun import TunTapDevice
from base64 import b64decode, b64encode


class TunTapWrapper:
    def __init__(
        self,
        name: str,
        source_address: str,
        destination_address: str,
        netmask: str,
        mtu: int,
    ):
        self._tun = TunTapDevice(name=name)
        self._tun.addr = source_address
        self._tun.dstaddr = destination_address
        self._tun.netmask = netmask
        self._tun.mtu = mtu
        self._sent = 0
        self._received = 0


    def up(self) -> None:
        self._tun.up()
        print(f"TUN interface with {self._tun.name=} is up")

    def down(self) -> None:
        self._tun.down()
        print(f"TUN interface with {self._tun.name=} is down")

    def read(self) -> str:
        print('TUN_TAP: Before read operation...')
        buffer = self._tun.read(self._tun.mtu)
        print('TUN TAP: Read data successfully')
        b64_data = b64encode(buffer)
        magic_converted_data = ''.join(map(chr, b64_data))
        self._received += len(buffer)
        return magic_converted_data

    def write(self, b64data: str) -> None:
        raw_data = b64decode(b64data)
        print('TUN TAP: Before write operation')
        self._tun.write(raw_data)
        print('TUN TAP: Write operation successful')
        self._sent += len(raw_data)