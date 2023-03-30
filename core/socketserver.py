import socket
from core.logger import Logger

# Set up socket connection

class SocketServer:
    def __init__(self):
        self.conn: socket = None
        self.addr = None
        self.socket = None
        self.open_connection()
    def open_connection(self):
        Logger.info("Opening socket connection...")
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        HOST = '192.168.0.52'
        PORT = 9999
        Logger.debug(f"host: {HOST}")
        Logger.debug(f"port: {PORT}")
        Logger.debug("Binding...")
        self.socket.bind((HOST, PORT))
        Logger.debug("Listening...")
        self.socket.listen(1)
        Logger.debug("Accepting...")
        self.conn, self.addr = self.socket.accept()
        Logger.info("Socket connection opened")

    def moveJ(self, coords: list):
        Logger.debug("cmd: movej")
        self.sendCommand(f"movej:{coords}")

    def moveL(self, coords: list):
        Logger.debug("cmd: movel")
        self.sendCommand(f"movel:{coords}")

    def moveCoords(self, coords):
        Logger.debug("cmd: move_coords")
        self.sendCommand(f"move_coords:{coords}")

    def sendCommand(self, command, blocking=True):
        try:
            self.conn.sendall(command.encode())
        except:
            Logger.debug("Send command failed, reopening connection")
            self.open_connection()
            self.conn.sendall(command.encode())
        while blocking:
            data = self.conn.recv(1024).decode()
            if not data:
                continue
            Logger.debug(f"Socket recieved: {data}")
            break


