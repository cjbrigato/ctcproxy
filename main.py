#!/usr/bin/python
# coding=utf-8

from __future__ import print_function

import socket
import select
import time
import sys
import re
import argparse

verbose = False
debug = False
truncate = False


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


class CustomPrint:

    @staticmethod
    def title():
        s = """      _
  ___| |_ ___ _ __  _ __ _____  ___   _
 / __| __/ __| '_ \| '__/ _ \ \/ / | | |
| (__| || (__| |_) | | | (_) >  <| |_| |
 \___|\__\___| .__/|_|  \___/_/\_\\\__, |
             |_|                  |___/"""
        print(TC.WARN, s, TC.RST, sep="")

    @staticmethod
    def bar():
        # print("########################################")
        print("----------------------------------------")

    def debug(self, *args):
        if debug:
            if truncate:
                print(*args[0:100])
            else:
                print(*args)

    def verbiate(self, *args):
        if verbose:
            print(*args)

printer = CustomPrint()


class Forward:

    def __init__(self):
        self.forward = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def start(self, host, port):
        try:
            self.forward.connect((host, port))
            printer.verbiate("S-> Connect to:", host, port)
            return self.forward
        except Exception as e:
            print(e)
            return False


class CTCProxy:
    client_queue = []
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
        self.proxy = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.proxy.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.proxy.bind((host, port))
        self.proxy.listen(200)
        print("‣ Proxy started...")

    def serve(self, buffersize=4096, delay=0.0001):
        self.client_queue.append(self.proxy)
        while 1:
            time.sleep(delay)
            ss = select.select
            inputready, outputready, exceptready = ss(
                self.client_queue, [], [])
            for self.s in inputready:
                if self.s == self.proxy:
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
        clientsock, clientaddr = self.proxy.accept()
        if forward:
            printer.verbiate("C->", clientaddr, "added to queue")
            self.client_queue.append(clientsock)
            self.client_queue.append(forward)
            self.channel[clientsock] = forward
            self.channel[forward] = clientsock
        else:
            print("ERR: Can't connect to remote !")
            print("Closing connection with client side", clientaddr)
            clientsock.close()

    def on_recv(self):
        data = self.data
        printer.debug(data.decode('utf-8'))
        # Right here we can have interception action on data's
        self.channel[self.s].send(data)

    def on_close(self):
        printer.verbiate("C<-", self.s.getpeername(), "left from queue")
        self.client_queue.remove(self.s)
        self.client_queue.remove(self.channel[self.s])
        out = self.channel[self.s]
        self.channel[out].close()
        self.channel[self.s].close()
        del self.channel[out]
        del self.channel[self.s]


def get_args(argv=None):

    global debug
    global verbose
    global truncate

    parser = argparse.ArgumentParser(description="Very Lightweight tcp proxy")
    parser.add_argument('localport', type=int, help="local tcp port")
    parser.add_argument('remotehost', help="remote hostname")
    parser.add_argument('remoteport', type=int, help="remote tcp port")
    parser.add_argument("-v", "--verbose", action='store_true', help="Talks")
    parser.add_argument("-d", "--debug", action='store_true', help="Debugs")
    parser.add_argument("-t", "--truncate", action='store_true', help="Limits")

    args = parser.parse_args()
    if args.debug:
        args.verbose = True
        debug = True
        if args.truncate:
            truncate = True
    if args.verbose:
        verbose = True
    return args


def print_options(args):
    printer.bar()
    print(' [', TC.BOLD, 'Verbose:', TC.RST, verbose, ' / ', TC.BOLD,
          'Debug:', TC.RST, debug, ']')
    printer.bar()
    print("[LOCAL]\t\t ➔ \t[REMOTE]")
    print(TC.OK, "0.0.0.0",
          ":", args.localport, TC.RST, "\t ➔ \t", TC.INF, args.remotehost, ':',
          args.remoteport, TC.RST, sep="")
    printer.bar()


def main():
    printer.title()
    args = get_args(None)
    print_options(args)

    proxy = CTCProxy('', args.localport, args.remotehost, args.remoteport)
    try:
        proxy.serve(8192, 0.000001)
    except KeyboardInterrupt:
        print("Received SIGINT from Keyboard")
        print("Stopping proxy...")
        sys.exit(1)


if __name__ == '__main__':
    main()
