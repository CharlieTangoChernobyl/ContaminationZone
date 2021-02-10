import argparse
import asyncio
import logging

import serial

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Control SIM800 Modem')
    parser.add_argument(
        'test',
        choices=['sim', 'gps'],
        help='Run a full test of the SIM modem or the GPS logger')
    parser.add_argument("--serial",
                        "-s",
                        help="Serial port",
                        default="/dev/ttyUSB0")
    parser.add_argument(
        "--verbose",
        "-v",
        action="count",
        help="Set logging level (use `-v` for INFO and `-vv` for `DEBUG`)",
    )

    args = parser.parse_args()

    # Set logging level
    if args.verbose is None:
        level = logging.WARNING
    elif args.verbose == 1:
        level = logging.INFO
    else:  # 2 or more
        level = logging.DEBUG
    logging.basicConfig(level=level)

    # Serial port
    logger.info("Connecting serial port %r", args.serial)
    ser = serial.Serial(args.serial, 9600, timeout=5)

    if args.test == 'sim':
        pass
    elif args.test == 'gps':
        import GPS

        logger.info('GPS tracker')
        gps = GPS.GPS(ser)

        asyncio.get_event_loop().run_until_complete(
            asyncio.wait([
                gps.parse(),
            ]))
