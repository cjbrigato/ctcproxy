#!/usr/bin/python
# coding=utf-8

from __future__ import print_function

import socket
import select
import time
import sys
import argparse

verbose = False
debug = False

class TermColors:

    HEAD = '\033[95m'
    OK = '\033[92m'
    WARN = '\033[93m'
    INF = '\033[93m'
    FAIL = '\033[91m'
    RST = '\033[0m'
    BOLD = '\033[1m'
    UNDR = '\033[4m'

TC = TermColors


class Forward:

    def __init__(self):
        self.forward = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def start(self, host, port):
        try:
            self.forward.connect((host, port))
            return self.forward
        except Exception as e:
            print(e)
            return False


class CTCProxy:
    input_list = []
    channel = {}
    remotehost = ''
    remoteport = ''
    localhost = ''
    localport = ''

    def __init__(self, host, port, remotehost, remoteport):
        self.remotehost = remotehost
        self.remoteport = remoteport
        self.localhost = '0.0.0.0'
        self.localport = port
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((host, port))
        self.server.listen(200)
        print("Proxy started...")

    def main_loop(self, buffersize=4096, delay=0.0001):
        self.input_list.append(self.server)
        while 1:
            time.sleep(delay)
            ss = select.select
            inputready, outputready, exceptready = ss(self.input_list, [], [])
            for self.s in inputready:
                if self.s == self.server:
                    self.on_accept()
                    break

                self.data = self.s.recv(buffersize)
                if len(self.data) == 0:
                    self.on_close()
                    break
                else:
                    self.on_recv()

    def on_accept(self):
        forward = Forward().start(
            self.remotehost, self.remoteport)
        clientsock, clientaddr = self.server.accept()
        if forward:
            if verbose:
                print(clientaddr, "has connected")
            self.input_list.append(clientsock)
            self.input_list.append(forward)
            self.channel[clientsock] = forward
            self.channel[forward] = clientsock
        else:
            print("Can't establish connection with remote server.")
            print("Closing connection with client side", clientaddr)
            clientsock.close()

    def on_close(self):
        if verbose:
            print(self.s.getpeername(), "has disconnected")
        # remove objects from input_list
        self.input_list.remove(self.s)
        self.input_list.remove(self.channel[self.s])
        out = self.channel[self.s]
        # close the connection with client
        self.channel[out].close()  # equivalent to do self.s.close()
        # close the connection with remote server
        self.channel[self.s].close()
        # clear the dict
        del self.channel[out]
        del self.channel[self.s]

    def on_recv(self):
        data = self.data
        # here we can parse and/or modify the data before send forward
        if debug:
            print(data)
        self.channel[self.s].send(data)


def get_args(argv=None):
    global debug
    global verbose
    parser = argparse.ArgumentParser(description="Very Lightweight tcp proxy")
    parser.add_argument('localport', type=int, help="local tcp port")
    parser.add_argument('remotehost', help="remote hostname")
    parser.add_argument('remoteport', type=int, help="remote tcp port")
    parser.add_argument("-v", "--verbose", action='store_true', help="Talks")
    parser.add_argument("-d", "--debug", action='store_true', help="Debugs")
    args = parser.parse_args()
    if args.debug:
        args.verbose = True
        debug = True
    if args.verbose:
        verbose = True
    print(TC.OK, "To  ", TC.RST, " > ", args.remotehost,
          ":", args.remoteport, sep="")
    print(TC.INF, "From", TC.RST, " < ", "0.0.0.0",
          ":", args.localport, sep="")
    return args


def main():
    print(":: Hello from ctcproxy ::")
    args = get_args(None)
    print("--")
    print(debug)
    print(verbose)
    proxy = CTCProxy('', args.localport, args.remotehost, args.remoteport)
    try:
        proxy.main_loop(8192, 0.000001)
    except KeyboardInterrupt:
        print("Received SIGINT from Keyboard")
        print("Stopping proxy...")
        sys.exit(1)


if __name__ == '__main__':
    main()
